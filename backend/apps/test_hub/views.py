"""
test_hub API views — developer portal endpoints.

All endpoints require IsAdmin or IsAgentOrAdmin permission.
No public access — these are internal developer tools.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

from django.http import StreamingHttpResponse
from django.utils import timezone
from django.views import View
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError

from apps.accounts.models import User
from apps.accounts.permissions import IsAgentOrAdmin
from apps.test_hub.models import (
    TestRunRecord, TestIssue, TestHealthSnapshot, TestModuleSelfHealth
)
from apps.test_hub.serializers import (
    TestRunRecordSerializer, TestIssueSerializer,
    TestHealthSnapshotSerializer, TestModuleSelfHealthSerializer,
)


MODULES = [
    "accounts", "properties", "leases", "maintenance",
    "esigning", "ai", "tenant_portal", "notifications",
]


class TestRunRecordViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/v1/test-hub/runs/          — list all runs
    GET /api/v1/test-hub/runs/{id}/     — run detail
    POST /api/v1/test-hub/runs/trigger/ — trigger a pytest run
    """
    serializer_class = TestRunRecordSerializer
    permission_classes = [IsAgentOrAdmin]
    filterset_fields = ["module", "tier", "phase", "triggered_by"]
    ordering = ["-run_at"]

    def get_queryset(self):
        return TestRunRecord.objects.all()[:100]

    @action(detail=False, methods=["post"], url_path="trigger")
    def trigger_run(self, request):
        """Trigger a pytest run via subprocess. Async — returns job started immediately."""
        module = request.data.get("module")
        tier = request.data.get("tier", "all")

        # Build pytest command
        test_hub_root = Path(__file__).parent
        if module:
            test_path = f"apps/test_hub/{module}/"
        else:
            test_path = "apps/test_hub/"

        tier_filter = f"-m {tier}" if tier != "all" else ""

        try:
            cmd = [sys.executable, "-m", "pytest", test_path, "--tb=short", "-q", "--no-header"]
            if tier_filter:
                cmd += ["-m", tier]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(test_hub_root.parent.parent),  # backend/
            )
            output = result.stdout + result.stderr

            # Parse basic stats from pytest output
            passed = failed = xfailed = 0
            for line in output.splitlines():
                if "passed" in line:
                    for part in line.split(","):
                        part = part.strip()
                        if "passed" in part:
                            try:
                                passed = int(part.split()[0])
                            except Exception:
                                pass
                        elif "failed" in part:
                            try:
                                failed = int(part.split()[0])
                            except Exception:
                                pass
                        elif "xfailed" in part:
                            try:
                                xfailed = int(part.split()[0])
                            except Exception:
                                pass

            record = TestRunRecord.objects.create(
                module=module or "all",
                tier=tier,
                phase="all",
                triggered_by="ai_agent" if request.user else "manual",
                tests_run=passed + failed + xfailed,
                tests_passed=passed,
                tests_failed=failed,
                tests_xfailed=xfailed,
                raw_output=output[:10000],
            )
            return Response(TestRunRecordSerializer(record).data, status=status.HTTP_201_CREATED)
        except subprocess.TimeoutExpired:
            return Response({"error": "Test run timed out (>5 min)"}, status=status.HTTP_408_REQUEST_TIMEOUT)
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TestRunStreamView(View):
    """
    GET /api/v1/test-hub/runs/stream/?module=leases&token=<jwt>
    Server-Sent Events stream of live pytest output.
    Auth via ?token= query param because EventSource doesn't support headers.
    Fully async Django View (not DRF APIView) to work with Daphne/ASGI.
    """

    async def get(self, request):
        import asyncio

        raw_token = request.GET.get("token", "")
        try:
            from asgiref.sync import sync_to_async
            token_obj = AccessToken(raw_token)
            user = await sync_to_async(User.objects.get)(pk=token_obj["user_id"])
            if user.role not in ("admin", "agent"):
                raise PermissionError("Insufficient role")
        except Exception:
            response = StreamingHttpResponse(
                (f"data: {json.dumps({'type': 'error', 'message': 'Unauthorized'})}\n\n" for _ in range(1)),
                content_type="text/event-stream",
                status=401,
            )
            return response

        module = request.GET.get("module", "")
        backend_root = str(Path(__file__).resolve().parents[2])

        if module and module not in MODULES:
            response = StreamingHttpResponse(
                (f"data: {json.dumps({'type': 'error', 'message': f'Unknown module: {module}'})}\n\n" for _ in range(1)),
                content_type="text/event-stream",
                status=400,
            )
            return response

        test_path = f"apps/test_hub/{module}/" if module else "apps/test_hub/"
        cmd = [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short", "--no-header", "-p", "no:cacheprovider"]

        def _sse(msg: dict) -> str:
            return f"data: {json.dumps(msg)}\n\n"

        async def generate():
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=backend_root,
            )
            passed = failed = xfailed = total = 0
            output_lines = []
            failed_tests = []  # [(test_id, short_error), ...]
            _in_failure_block = False
            _current_failure_id = ""
            _failure_lines = []

            try:
                async for raw_line in proc.stdout:
                    line = raw_line.decode(errors="replace").rstrip()
                    output_lines.append(line)

                    # Detect start of FAILURES section
                    if line.strip().startswith("= FAILURES =") or line.strip().startswith("=== FAILURES ===") or "FAILURES" in line and line.strip().startswith("="):
                        _in_failure_block = True
                        continue

                    # Inside failure block: capture per-test tracebacks
                    if _in_failure_block:
                        # New failure header: ___ test_name ___
                        fail_header = re.match(r'^_{3,}\s+(.+?)\s+_{3,}$', line.strip())
                        if fail_header:
                            # Save previous failure if any
                            if _current_failure_id and _failure_lines:
                                short_err = "\n".join(_failure_lines[-5:])  # last 5 lines
                                failed_tests.append({"test": _current_failure_id, "error": short_err})
                            _current_failure_id = fail_header.group(1)
                            _failure_lines = []
                            continue
                        # End of failures section
                        if line.strip().startswith("=") and ("passed" in line or "failed" in line or "error" in line or "short test summary" in line.lower()):
                            if _current_failure_id and _failure_lines:
                                short_err = "\n".join(_failure_lines[-5:])
                                failed_tests.append({"test": _current_failure_id, "error": short_err})
                            _in_failure_block = False
                            _current_failure_id = ""
                            _failure_lines = []
                        elif _current_failure_id:
                            _failure_lines.append(line)
                        continue

                    m = re.search(r'collected (\d+)', line)
                    if m:
                        total = int(m.group(1))
                        yield _sse({"type": "start", "total": total})
                        continue

                    pct_m = re.search(r'\[\s*(\d+)%\]', line)
                    pct = int(pct_m.group(1)) if pct_m else None
                    test_name = line.strip().split("::")[-1].split(" ")[0] if "::" in line else ""
                    # Full test ID for matching failures (e.g. test_file.py::TestClass::test_method)
                    test_id = "::".join(line.strip().split("::")[:-1] + [test_name]) if "::" in line and test_name else test_name

                    if " PASSED" in line:
                        passed += 1
                        yield _sse({"type": "progress", "passed": passed, "failed": failed,
                                    "xfailed": xfailed, "total": total, "pct": pct, "current": test_name})
                    elif " FAILED" in line:
                        failed += 1
                        yield _sse({"type": "progress", "passed": passed, "failed": failed,
                                    "xfailed": xfailed, "total": total, "pct": pct, "current": test_name,
                                    "status": "failed"})
                    elif " XFAIL" in line:
                        xfailed += 1
                        yield _sse({"type": "progress", "passed": passed, "failed": failed,
                                    "xfailed": xfailed, "total": total, "pct": pct, "current": test_name})

                await proc.wait()
            except asyncio.CancelledError:
                proc.kill()
                return

            # Capture any trailing failure
            if _current_failure_id and _failure_lines:
                short_err = "\n".join(_failure_lines[-5:])
                failed_tests.append({"test": _current_failure_id, "error": short_err})

            raw_output = "\n".join(output_lines)

            try:
                from asgiref.sync import sync_to_async

                @sync_to_async
                def _save():
                    record = TestRunRecord.objects.create(
                        module=module or "all",
                        tier="all",
                        phase="all",
                        triggered_by="agent",
                        tests_run=passed + failed + xfailed,
                        tests_passed=passed,
                        tests_failed=failed,
                        tests_xfailed=xfailed,
                        raw_output=raw_output[:10000],
                    )
                    return TestRunRecordSerializer(record).data

                record_data = await _save()
            except Exception:
                record_data = None

            yield _sse({
                "type": "done",
                "passed": passed,
                "failed": failed,
                "xfailed": xfailed,
                "total": total,
                "returncode": proc.returncode,
                "record": record_data,
                "failures": failed_tests[:50],  # cap at 50 failures
            })

        response = StreamingHttpResponse(generate(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        response["Access-Control-Allow-Origin"] = "*"
        return response


class TestIssueViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/v1/test-hub/issues/      — list issues
    GET /api/v1/test-hub/issues/{id}/ — detail
    """
    serializer_class = TestIssueSerializer
    permission_classes = [IsAgentOrAdmin]
    filterset_fields = ["module", "status"]
    ordering = ["-discovered_at"]

    def get_queryset(self):
        return TestIssue.objects.all()


class TestHealthSnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/v1/test-hub/snapshots/        — list snapshots (trend data)
    GET /api/v1/test-hub/snapshots/latest/ — most recent snapshot
    """
    serializer_class = TestHealthSnapshotSerializer
    permission_classes = [IsAgentOrAdmin]

    def get_queryset(self):
        return TestHealthSnapshot.objects.all()[:30]

    @action(detail=False, methods=["get"])
    def latest(self, request):
        snap = TestHealthSnapshot.objects.first()
        if not snap:
            return Response(
                {"detail": "No snapshots yet. Run: python manage.py run_tdd --snapshot"},
                status=404,
            )
        return Response(TestHealthSnapshotSerializer(snap).data)


class SelfCheckView(APIView):
    """
    GET  /api/v1/test-hub/selfcheck/  — latest self-check result
    POST /api/v1/test-hub/selfcheck/  — run selfcheck now (via management command)
    """
    permission_classes = [IsAgentOrAdmin]

    def get(self, request):
        checks = TestModuleSelfHealth.objects.all()[:10]
        return Response(TestModuleSelfHealthSerializer(checks, many=True).data)

    def post(self, request):
        try:
            from django.core.management import call_command
            call_command("test_hub_selfcheck", no_db=False)
            latest = TestModuleSelfHealth.objects.first()
            if latest:
                return Response(TestModuleSelfHealthSerializer(latest).data)
            return Response({"detail": "Self-check ran but no DB record written."})
        except Exception as exc:
            return Response({"error": str(exc)}, status=500)


class RAGStatusView(APIView):
    """
    GET  /api/v1/test-hub/rag-status/   — RAG store document count + freshness
    """
    permission_classes = [IsAgentOrAdmin]

    def get(self, request):
        try:
            from core.contract_rag import get_test_context_collection
            col = get_test_context_collection()
            count = col.count()
            return Response({
                "document_count": count,
                "collection": "test_context",
                "status": "ok" if count > 0 else "empty",
            })
        except Exception as exc:
            return Response({"error": str(exc), "status": "unavailable"}, status=503)


class RAGReindexView(APIView):
    """POST /api/v1/test-hub/rag-reindex/ — triggers ingest_test_context management command."""
    permission_classes = [IsAgentOrAdmin]

    def post(self, request):
        module = request.data.get("module")
        reset = request.data.get("reset", False)
        try:
            from django.core.management import call_command
            kwargs = {}
            if module:
                kwargs["module"] = module
            if reset:
                kwargs["reset"] = True
            call_command("ingest_test_context", **kwargs)
            return Response({"status": "re-indexed", "module": module or "all"})
        except Exception as exc:
            return Response({"error": str(exc)}, status=500)


class ModuleStatsView(APIView):
    """
    GET /api/v1/test-hub/module/<module>/
    Returns live test counts for a specific module by collecting from pytest.
    """
    permission_classes = [IsAgentOrAdmin]

    def get(self, request, module):
        import re
        if module not in MODULES:
            return Response({"error": f"Unknown module: {module}"}, status=400)

        backend_root = Path(__file__).resolve().parents[2]  # backend/

        def collect(marker=None, subdir=None, base_module=None):
            mod = base_module or module
            path = f"apps/test_hub/{mod}/{subdir}/" if subdir else f"apps/test_hub/{mod}/"
            cmd = [sys.executable, "-m", "pytest", "--co", "--tb=no", path]
            if marker:
                cmd += ["-m", marker]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(backend_root))
            lines = result.stdout.splitlines()
            fn_names = []
            sections = {}  # file_stem -> [test_name, ...]
            current_file = None
            for l in lines:
                # Track which file we're currently inside
                if "<Module " in l:
                    m = re.search(r'<Module (.+?)>', l)
                    if m:
                        current_file = m.group(1).replace(".py", "")
                # Catch both pure pytest functions and Django TestCase methods
                fn_name = None
                if "<Function " in l:
                    fn_name = l.split("<Function ")[-1].rstrip(">").strip()
                elif "<TestCaseFunction " in l:
                    fn_name = l.split("<TestCaseFunction ")[-1].rstrip(">").strip()
                elif "::" in l and "test_" in l and not l.strip().startswith("<"):
                    fn_name = l.strip().split("::")[-1]
                if fn_name:
                    fn_names.append(fn_name)
                    if current_file:
                        sections.setdefault(current_file, []).append(fn_name)
            # Parse count from line like "==== 52 tests collected in 0.07s ===="
            total = 0
            for l in reversed(lines):
                m = re.search(r'(\d+)(?:/\d+)? tests? (?:collected|selected)', l)
                if m:
                    total = int(m.group(1))
                    break
                if "no tests ran" in l or "no tests were found" in l:
                    break
            return fn_names, total, sections

        from concurrent.futures import ThreadPoolExecutor

        tasks = {
            "unit": lambda: collect(subdir="unit"),
            "integration": lambda: collect(subdir="integration"),
            "red": lambda: collect(marker="red"),
            "green": lambda: collect(marker="green"),
        }
        if module == "leases":
            tasks["esig_unit"] = lambda: collect(subdir="unit", base_module="esigning")
            tasks["esig_int"] = lambda: collect(subdir="integration", base_module="esigning")

        results = {}
        with ThreadPoolExecutor(max_workers=len(tasks)) as pool:
            futures = {k: pool.submit(fn) for k, fn in tasks.items()}
            for k, fut in futures.items():
                results[k] = fut.result()

        unit_names, unit_total, unit_sections = results["unit"]
        integ_names, integ_total, integ_sections = results["integration"]
        red_names, red_total, _ = results["red"]
        _, green_total, _ = results["green"]

        # Latest run record for this module
        latest_run = TestRunRecord.objects.filter(module=module).order_by("-run_at").first()

        response_data = {
            "module": module,
            "unit": {"count": unit_total, "tests": unit_names[:200], "sections": unit_sections},
            "integration": {"count": integ_total, "tests": integ_names[:200], "sections": integ_sections},
            "red": {"count": red_total, "tests": red_names[:50]},
            "green": {"count": green_total},
            "total": unit_total + integ_total,
            "last_run": TestRunRecordSerializer(latest_run).data if latest_run else None,
        }

        # For leases, include esigning tests as a related section
        if module == "leases":
            esig_unit_names, esig_unit_total, esig_unit_sections = results["esig_unit"]
            esig_int_names, esig_int_total, esig_int_sections = results["esig_int"]
            response_data["related_esigning"] = {
                "unit": {"count": esig_unit_total, "sections": esig_unit_sections},
                "integration": {"count": esig_int_total, "sections": esig_int_sections},
            }

        return Response(response_data)


class HealthDashboardView(APIView):
    """
    GET /api/v1/test-hub/health/
    Returns a combined health summary for the portal dashboard.
    """
    permission_classes = [IsAgentOrAdmin]

    def get(self, request):
        latest_snap = TestHealthSnapshot.objects.first()
        latest_run = TestRunRecord.objects.first()
        open_issues = TestIssue.objects.filter(status="red").count()
        fixed_issues = TestIssue.objects.filter(status="fixed").count()
        latest_selfcheck = TestModuleSelfHealth.objects.first()

        rag_count = 0
        try:
            from core.contract_rag import get_test_context_collection
            rag_count = get_test_context_collection().count()
        except Exception:
            pass

        # Per-module breakdown from latest run records
        module_stats = []
        for module in MODULES:
            runs = TestRunRecord.objects.filter(module=module).order_by("-run_at")[:5]
            latest = runs.first()
            module_stats.append({
                "module": module,
                "green": latest.tests_passed if latest else 0,
                "red": latest.tests_xfailed if latest else 0,
                "failed": latest.tests_failed if latest else 0,
                "last_run": latest.run_at if latest else None,
                "pass_rate": latest.pass_rate if latest else None,
            })

        return Response({
            "health_score": latest_snap.health_score if latest_snap else None,
            "snapshot": TestHealthSnapshotSerializer(latest_snap).data if latest_snap else None,
            "latest_run": TestRunRecordSerializer(latest_run).data if latest_run else None,
            "open_issues": open_issues,
            "fixed_issues": fixed_issues,
            "selfcheck_healthy": latest_selfcheck.is_healthy if latest_selfcheck else None,
            "rag_document_count": rag_count,
            "module_stats": module_stats,
        })


class FrontendTestStatsView(APIView):
    """
    GET /api/v1/test-hub/frontend/stats/
    Returns Vitest test stats (collected tests, last run record).
    Runs `npx vitest list` to collect test names without running them.
    """
    permission_classes = [IsAgentOrAdmin]

    def get(self, request):
        admin_root = str(Path(__file__).resolve().parents[3] / "admin")
        try:
            result = subprocess.run(
                ["node", "node_modules/.bin/vitest", "list", "--reporter=verbose"],
                capture_output=True, text=True, timeout=30, cwd=admin_root,
            )
            output = result.stdout + result.stderr
            lines = output.splitlines()
            test_names = []
            file_sections: dict = {}
            current_file = None
            for line in lines:
                # File header: " src/__tests__/browser/foo.browser.test.ts"
                if line.strip().startswith("src/") and ".test." in line:
                    current_file = line.strip().split("/")[-1].replace(".browser.test.ts", "").replace(".test.ts", "")
                    continue
                # Test name lines: "  ✓ test name" or "  × test name"
                test_match = re.match(r'^\s+[✓×✗·]\s+(.+)$', line)
                if test_match:
                    name = test_match.group(1).strip()
                    test_names.append(name)
                    if current_file:
                        file_sections.setdefault(current_file, []).append(name)

            latest_run = TestRunRecord.objects.filter(module="frontend").order_by("-run_at").first()
            return Response({
                "total": len(test_names),
                "tests": test_names[:200],
                "sections": file_sections,
                "last_run": TestRunRecordSerializer(latest_run).data if latest_run else None,
            })
        except subprocess.TimeoutExpired:
            return Response({"error": "vitest list timed out"}, status=408)
        except Exception as exc:
            return Response({"error": str(exc), "total": 0, "tests": [], "sections": {}, "last_run": None})


class FrontendTestStreamView(View):
    """
    GET /api/v1/test-hub/runs/stream-frontend/?token=<jwt>
    SSE stream of live Vitest run output.
    Runs `npx vitest run --reporter=verbose` in the admin directory.
    Auth via ?token= query param (EventSource doesn't support headers).
    """

    async def get(self, request):
        import asyncio

        raw_token = request.GET.get("token", "")
        try:
            from asgiref.sync import sync_to_async
            token_obj = AccessToken(raw_token)
            user = await sync_to_async(User.objects.get)(pk=token_obj["user_id"])
            if user.role not in ("admin", "agent"):
                raise PermissionError("Insufficient role")
        except Exception:
            response = StreamingHttpResponse(
                (f"data: {json.dumps({'type': 'error', 'message': 'Unauthorized'})}\n\n" for _ in range(1)),
                content_type="text/event-stream",
                status=401,
            )
            return response

        admin_root = str(Path(__file__).resolve().parents[3] / "admin")
        cmd = ["node", "node_modules/.bin/vitest", "run", "--reporter=verbose"]

        def _sse(msg: dict) -> str:
            return f"data: {json.dumps(msg)}\n\n"

        async def generate():
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=admin_root,
            )
            passed = failed = total = 0
            output_lines = []
            failed_tests: list = []
            _current_failure_id = ""
            _failure_lines: list = []
            _in_failure_block = False

            try:
                async for raw_line in proc.stdout:
                    line = raw_line.decode(errors="replace").rstrip()
                    output_lines.append(line)

                    # Vitest summary line: "Test Files  X passed | Y failed (Z)"
                    summary_m = re.search(r'Tests\s+(\d+) passed', line)
                    if summary_m:
                        passed = int(summary_m.group(1))
                        fail_m = re.search(r'(\d+) failed', line)
                        if fail_m:
                            failed = int(fail_m.group(1))
                        continue

                    # Total collected: "Test Files  X passed (Y)"
                    files_m = re.search(r'Test Files\s+.*\((\d+)\)', line)
                    if files_m and total == 0:
                        # Don't use this as total — use Tests line
                        pass

                    # Vitest verbose: " ✓ test name Xms" or " × test name"
                    pass_m = re.match(r'^\s+✓\s+(.+?)(?:\s+\d+ms)?$', line)
                    fail_m2 = re.match(r'^\s+[×✗]\s+(.+?)(?:\s+\d+ms)?$', line)

                    if pass_m:
                        test_name = pass_m.group(1).strip()
                        # Skip suite names (no timing and indented 2 levels usually)
                        passed += 1
                        yield _sse({"type": "progress", "passed": passed, "failed": failed,
                                    "current": test_name, "status": "passed"})
                    elif fail_m2:
                        test_name = fail_m2.group(1).strip()
                        failed += 1
                        _current_failure_id = test_name
                        _failure_lines = []
                        _in_failure_block = True
                        yield _sse({"type": "progress", "passed": passed, "failed": failed,
                                    "current": test_name, "status": "failed"})
                    elif _in_failure_block:
                        if line.strip().startswith("✓") or line.strip().startswith("×") or line.strip().startswith("✗") or (line.strip() == "" and len(_failure_lines) > 3):
                            if _current_failure_id and _failure_lines:
                                failed_tests.append({"test": _current_failure_id, "error": "\n".join(_failure_lines[-6:])})
                            _in_failure_block = False
                            _current_failure_id = ""
                            _failure_lines = []
                        else:
                            _failure_lines.append(line)

                await proc.wait()
            except asyncio.CancelledError:
                proc.kill()
                return

            if _current_failure_id and _failure_lines:
                failed_tests.append({"test": _current_failure_id, "error": "\n".join(_failure_lines[-6:])})

            raw_output = "\n".join(output_lines)
            total = passed + failed

            try:
                from asgiref.sync import sync_to_async

                @sync_to_async
                def _save():
                    record = TestRunRecord.objects.create(
                        module="frontend",
                        tier="browser",
                        phase="all",
                        triggered_by="agent",
                        tests_run=total,
                        tests_passed=passed,
                        tests_failed=failed,
                        tests_xfailed=0,
                        raw_output=raw_output[:10000],
                    )
                    return TestRunRecordSerializer(record).data

                record_data = await _save()
            except Exception:
                record_data = None

            yield _sse({
                "type": "done",
                "passed": passed,
                "failed": failed,
                "total": total,
                "returncode": proc.returncode,
                "record": record_data,
                "failures": failed_tests[:50],
            })

        response = StreamingHttpResponse(generate(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        response["Access-Control-Allow-Origin"] = "*"
        return response
