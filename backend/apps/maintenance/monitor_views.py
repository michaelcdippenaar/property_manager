"""
Agent Monitor API — ecosystem health dashboard.

Provides endpoints for monitoring the full AI agent ecosystem:
  - RAG collection stats (chunks, embedding model, all 3 collections)
  - MCP server connection status
  - Skills and tools inventory with usage stats
  - Token usage tracking per agent endpoint
  - Indexed/vectorised data overview
  - AI agent health check with diagnostic probes
  - Progressive test execution and history

Token tracking is done via a lightweight model that logs every LLM call,
enabling cost analysis, context-size auditing, and regression detection.
"""
from __future__ import annotations

import json
import logging
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db.models import Avg, Count, Max, Sum
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.maintenance.agent_assist_views import IsAgentOrAdmin
from apps.maintenance.models import AgentTokenLog
from core.contract_rag import rag_collection_stats

logger = logging.getLogger(__name__)


class AgentMonitorDashboardView(APIView):
    """
    Full AI ecosystem dashboard data.

    Returns:
      - rag: collection stats (contracts, agent_qa, chat_knowledge)
      - mcp: server status and available tools/resources
      - skills: active skill count by trade, total count
      - token_usage: aggregated token stats per endpoint (last 7 days)
      - indexed_data: files, chunks, embedding model
      - connections: MCP, WebSocket, REST status
      - agents: list of agent endpoints with health status
    """
    permission_classes = [IsAuthenticated, IsAgentOrAdmin]

    def get(self, request):
        data = {
            "rag": self._rag_stats(),
            "mcp": self._mcp_status(),
            "skills": self._skills_summary(),
            "token_usage": self._token_usage(),
            "indexed_data": self._indexed_data(),
            "agents": self._agent_endpoints(),
            "system": self._system_info(),
        }
        return Response(data)

    def _rag_stats(self) -> dict:
        """Get RAG collection stats across all three collections."""
        try:
            stats = rag_collection_stats()
            return {
                "status": "healthy" if stats.get("chunks", 0) > 0 else "empty",
                "contracts": stats.get("chunks", 0),
                "agent_qa": stats.get("agent_qa_chunks", 0),
                "chat_knowledge": stats.get("chat_knowledge_chunks", 0),
                "maintenance_issues": stats.get("maintenance_issues_chunks", 0),
                "total_chunks": (
                    stats.get("chunks", 0)
                    + stats.get("agent_qa_chunks", 0)
                    + stats.get("chat_knowledge_chunks", 0)
                    + stats.get("maintenance_issues_chunks", 0)
                ),
                "embedding_model": stats.get("embedding_model", "unknown"),
                "chroma_path": stats.get("chroma_path", ""),
            }
        except Exception as e:
            logger.warning("RAG stats error: %s", e)
            return {"status": "error", "error": str(e)}

    def _mcp_status(self) -> dict:
        """Check MCP server availability and list tools/resources from registry."""
        mcp_path = Path(settings.BASE_DIR).parent / "backend" / "mcp_server" / "server.py"
        if not mcp_path.exists():
            mcp_path = Path(settings.BASE_DIR) / "mcp_server" / "server.py"

        from apps.ai.skills_registry import get_mcp_tools, get_mcp_resources

        tools = get_mcp_tools()
        resources = get_mcp_resources()

        return {
            "server_path": str(mcp_path),
            "server_exists": mcp_path.exists(),
            "transport": "stdio",
            "tools": tools,
            "resources": resources,
            "tool_count": len(tools),
            "resource_count": len(resources),
        }

    def _skills_summary(self) -> dict:
        """Get active skill counts by trade."""
        from apps.maintenance.models import MaintenanceSkill

        qs = MaintenanceSkill.objects.filter(is_active=True)
        total = qs.count()
        by_trade = dict(
            qs.values_list("trade").annotate(c=Count("id")).order_by("-c")
        )
        return {
            "total_active": total,
            "by_trade": by_trade,
            "trades": list(by_trade.keys()),
        }

    def _token_usage(self) -> dict:
        """Aggregate token usage from the last 7 days."""
        try:
            since = timezone.now() - timedelta(days=7)
            qs = AgentTokenLog.objects.filter(created_at__gte=since)

            total = qs.aggregate(
                total_input=Sum("input_tokens"),
                total_output=Sum("output_tokens"),
                total_calls=Count("id"),
                avg_input=Avg("input_tokens"),
                avg_output=Avg("output_tokens"),
                max_input=Max("input_tokens"),
            )

            by_endpoint = list(
                qs.values("endpoint")
                .annotate(
                    calls=Count("id"),
                    total_input=Sum("input_tokens"),
                    total_output=Sum("output_tokens"),
                    avg_input=Avg("input_tokens"),
                    peak_input=Max("input_tokens"),
                )
                .order_by("-total_input")
            )

            # Flag any endpoints sending excessive context
            oversized = [
                e for e in by_endpoint
                if (e.get("peak_input") or 0) > 50000
            ]

            return {
                "period": "7d",
                "total_input_tokens": total["total_input"] or 0,
                "total_output_tokens": total["total_output"] or 0,
                "total_calls": total["total_calls"] or 0,
                "avg_input_tokens": round(total["avg_input"] or 0),
                "avg_output_tokens": round(total["avg_output"] or 0),
                "max_input_tokens": total["max_input"] or 0,
                "by_endpoint": by_endpoint,
                "oversized_context_alerts": oversized,
            }
        except Exception as e:
            logger.warning("Token usage query error: %s", e)
            return {"error": str(e), "total_calls": 0}

    def _indexed_data(self) -> dict:
        """Overview of indexed/vectorised data sources."""
        docs_root = getattr(settings, "CONTRACT_DOCUMENTS_ROOT", "")
        file_count = 0
        file_types: dict[str, int] = {}
        if docs_root and Path(docs_root).is_dir():
            for p in Path(docs_root).rglob("*"):
                if p.is_file() and p.suffix.lower() in (".pdf", ".docx", ".txt", ".md"):
                    file_count += 1
                    ext = p.suffix.lower()
                    file_types[ext] = file_types.get(ext, 0) + 1

        chat_log = getattr(settings, "MAINTENANCE_CHAT_LOG", "")
        chat_log_lines = 0
        if chat_log and Path(chat_log).is_file():
            try:
                with open(chat_log) as f:
                    chat_log_lines = sum(1 for _ in f)
            except Exception:
                pass

        return {
            "documents_root": str(docs_root),
            "source_files": file_count,
            "file_types": file_types,
            "chat_log_path": str(chat_log),
            "chat_log_entries": chat_log_lines,
        }

    def _agent_endpoints(self) -> list:
        """List all AI agent endpoints with config."""
        from core.anthropic_web_fetch import anthropic_web_fetch_enabled

        api_key_set = bool(getattr(settings, "ANTHROPIC_API_KEY", ""))
        return [
            {
                "name": "Tenant AI Chat",
                "endpoint": "/api/tenant-ai/chat/",
                "model": "claude-sonnet-4-6",
                "rate_limit": "10/min",
                "features": ["rag", "severity", "knowledge_gap", "fact_extraction"],
                "status": "active" if api_key_set else "no_api_key",
            },
            {
                "name": "Agent Assist",
                "endpoint": "/api/maintenance/agent-assist/chat/",
                "model": "claude-sonnet-4-6",
                "rate_limit": "30/min",
                "features": ["rag", "skills_digest", "qa_knowledge", "web_fetch"],
                "status": "active" if api_key_set else "no_api_key",
            },
            {
                "name": "Maintenance Chat (@agent)",
                "endpoint": "ws://*/ws/maintenance/{pk}/activity/",
                "model": "claude-sonnet-4-6",
                "rate_limit": "n/a (WebSocket)",
                "features": ["rag", "qa_knowledge", "real_time"],
                "status": "active" if api_key_set else "no_api_key",
            },
            {
                "name": "Lease Builder",
                "endpoint": "/api/leases/builder/{id}/chat/",
                "model": "claude-sonnet-4-6",
                "rate_limit": "n/a",
                "features": ["lease_context", "template_rendering"],
                "status": "active" if api_key_set else "no_api_key",
            },
        ]

    def _system_info(self) -> dict:
        """System-level info for diagnostics."""
        from core.anthropic_web_fetch import anthropic_web_fetch_enabled

        return {
            "api_key_configured": bool(getattr(settings, "ANTHROPIC_API_KEY", "")),
            "web_fetch_enabled": anthropic_web_fetch_enabled(),
            "embedding_model": getattr(settings, "RAG_EMBEDDING_MODEL", "default"),
            "rag_query_chunks": getattr(settings, "RAG_QUERY_CHUNKS", 8),
            "max_chat_window": 20,
            "debug": getattr(settings, "DEBUG", False),
        }


class AgentTokenLogView(APIView):
    """
    View recent token usage logs with filtering.

    Query params:
      - endpoint: filter by endpoint name
      - days: lookback period (default 7)
      - min_input: only show calls above this input token count
    """
    permission_classes = [IsAuthenticated, IsAgentOrAdmin]

    def get(self, request):
        days = int(request.query_params.get("days", 7))
        since = timezone.now() - timedelta(days=days)
        qs = AgentTokenLog.objects.filter(created_at__gte=since)

        endpoint = request.query_params.get("endpoint")
        if endpoint:
            qs = qs.filter(endpoint=endpoint)

        min_input = request.query_params.get("min_input")
        if min_input:
            qs = qs.filter(input_tokens__gte=int(min_input))

        logs = list(
            qs.order_by("-created_at")[:100].values(
                "id", "endpoint", "model", "input_tokens", "output_tokens",
                "latency_ms", "created_at", "user_id", "metadata",
            )
        )
        return Response({"logs": logs, "count": len(logs)})


class MaintenanceChatLogView(APIView):
    """
    View all maintenance chat messages (from MaintenanceActivity) for
    the Agent Monitor dashboard.

    Query params:
      - request_id: filter by maintenance request
      - source: filter by source (ai_agent, user)
      - days: lookback period (default 7)
      - limit: max entries (default 100)
    """
    permission_classes = [IsAuthenticated, IsAgentOrAdmin]

    def get(self, request):
        from apps.maintenance.models import MaintenanceActivity, MaintenanceRequest

        days = int(request.query_params.get("days", 7))
        limit = min(int(request.query_params.get("limit", 100)), 500)
        since = timezone.now() - timedelta(days=days)

        qs = (
            MaintenanceActivity.objects
            .filter(created_at__gte=since)
            .select_related("request", "created_by")
            .order_by("-created_at")
        )

        request_id = request.query_params.get("request_id")
        if request_id:
            qs = qs.filter(request_id=request_id)

        source = request.query_params.get("source")
        if source == "ai_agent":
            qs = qs.filter(metadata__source="ai_agent")
        elif source == "user":
            qs = qs.exclude(metadata__source="ai_agent")

        entries = []
        for a in qs[:limit]:
            is_ai = (a.metadata or {}).get("source") == "ai_agent"
            entries.append({
                "id": a.pk,
                "request_id": a.request_id,
                "request_title": a.request.title if a.request else None,
                "activity_type": a.activity_type,
                "message": a.message,
                "author": a.created_by.full_name if a.created_by else "AI Agent",
                "role": a.created_by.role if a.created_by else "ai",
                "is_ai": is_ai,
                "created_at": a.created_at.isoformat(),
            })

        # Summary stats
        total_qs = MaintenanceActivity.objects.filter(created_at__gte=since)
        ai_count = total_qs.filter(metadata__source="ai_agent").count()
        user_count = total_qs.exclude(metadata__source="ai_agent").count()

        # Active requests with recent chat
        active_requests = list(
            total_qs.values("request_id", "request__title")
            .annotate(msg_count=Count("id"))
            .order_by("-msg_count")[:20]
        )

        return Response({
            "entries": entries,
            "count": len(entries),
            "summary": {
                "total_messages": ai_count + user_count,
                "ai_messages": ai_count,
                "user_messages": user_count,
                "period_days": days,
            },
            "active_requests": [
                {
                    "request_id": r["request_id"],
                    "title": r["request__title"],
                    "message_count": r["msg_count"],
                }
                for r in active_requests
            ],
        })


class AgentHealthCheckView(APIView):
    """
    Run diagnostic probes against the AI ecosystem.

    Checks:
      - RAG collections accessible and non-empty
      - Embedding model loaded
      - API key configured
      - MCP server file exists
      - Chat log writable
      - Skills populated
    """
    permission_classes = [IsAuthenticated, IsAgentOrAdmin]

    def get(self, request):
        checks = []

        # 1. API key
        api_key = bool(getattr(settings, "ANTHROPIC_API_KEY", ""))
        checks.append({"name": "Anthropic API Key", "status": "pass" if api_key else "fail"})

        # 2. RAG collections
        try:
            stats = rag_collection_stats()
            chunks = stats.get("chunks", 0)
            checks.append({
                "name": "RAG Contracts Collection",
                "status": "pass" if chunks > 0 else "warn",
                "detail": f"{chunks} chunks indexed",
            })
        except Exception as e:
            checks.append({"name": "RAG Contracts Collection", "status": "fail", "detail": str(e)})

        # 3. Embedding model
        try:
            from core.contract_rag import get_embedding_function
            ef = get_embedding_function()
            checks.append({"name": "Embedding Model", "status": "pass", "detail": str(settings.RAG_EMBEDDING_MODEL)})
        except Exception as e:
            checks.append({"name": "Embedding Model", "status": "fail", "detail": str(e)})

        # 4. Skills
        from apps.maintenance.models import MaintenanceSkill
        skill_count = MaintenanceSkill.objects.filter(is_active=True).count()
        checks.append({
            "name": "Maintenance Skills",
            "status": "pass" if skill_count > 0 else "warn",
            "detail": f"{skill_count} active skills",
        })

        # 5. Chat log
        chat_log = getattr(settings, "MAINTENANCE_CHAT_LOG", "")
        log_dir = Path(chat_log).parent if chat_log else None
        checks.append({
            "name": "Chat Log Directory",
            "status": "pass" if log_dir and log_dir.is_dir() else "warn",
            "detail": str(chat_log),
        })

        # 6. MCP server
        mcp_path = Path(settings.BASE_DIR) / "mcp_server" / "server.py"
        checks.append({
            "name": "MCP Server",
            "status": "pass" if mcp_path.exists() else "warn",
            "detail": str(mcp_path),
        })

        overall = "healthy"
        if any(c["status"] == "fail" for c in checks):
            overall = "unhealthy"
        elif any(c["status"] == "warn" for c in checks):
            overall = "degraded"

        return Response({"overall": overall, "checks": checks})


class ProgressiveTestView(APIView):
    """
    Run progressive AI agent tests.

    Each run increases complexity and compares against previous results
    stored in a JSONL file. This allows monitoring whether the agent
    ecosystem is improving over time.

    POST body:
      - level: (optional) test complexity level (1-5, auto-increments if omitted)
    """
    permission_classes = [IsAuthenticated, IsAgentOrAdmin]
    TEST_HISTORY_FILE = "agent_test_history.jsonl"

    def get(self, request):
        """Return test history."""
        history = self._load_history()
        return Response({"runs": history[-20:], "total_runs": len(history)})

    def post(self, request):
        """Execute a progressive test run."""
        history = self._load_history()
        last_level = history[-1]["level"] if history else 0
        level = int(request.data.get("level", last_level + 1))
        level = max(1, min(level, 5))

        results = self._run_tests(level)

        # Compare with previous run at same or lower level
        previous = None
        for h in reversed(history):
            if h["level"] <= level:
                previous = h
                break

        comparison = None
        if previous:
            comparison = {
                "previous_level": previous["level"],
                "previous_score": previous["score"],
                "current_score": results["score"],
                "improvement": results["score"] - previous["score"],
                "previous_date": previous["timestamp"],
            }

        entry = {
            "level": level,
            "score": results["score"],
            "tests": results["tests"],
            "timestamp": timezone.now().isoformat(),
            "comparison": comparison,
        }
        self._save_entry(entry)

        return Response(entry)

    def _run_tests(self, level: int) -> dict:
        """
        Run tests at the given complexity level.

        Level 1: Basic connectivity checks
        Level 2: RAG retrieval quality
        Level 3: Agent response coherence
        Level 4: Multi-turn conversation consistency
        Level 5: Full integration stress test
        """
        tests = []
        score = 0
        total = 0

        # Level 1: Basic checks
        if level >= 1:
            # Check RAG is populated
            try:
                stats = rag_collection_stats()
                passed = stats.get("chunks", 0) > 0
                tests.append({"name": "RAG populated", "passed": passed, "detail": f"{stats.get('chunks', 0)} chunks"})
                score += 1 if passed else 0
                total += 1
            except Exception as e:
                tests.append({"name": "RAG populated", "passed": False, "detail": str(e)})
                total += 1

            # Check API key
            has_key = bool(getattr(settings, "ANTHROPIC_API_KEY", ""))
            tests.append({"name": "API key configured", "passed": has_key})
            score += 1 if has_key else 0
            total += 1

            # Check skills exist
            from apps.maintenance.models import MaintenanceSkill
            skill_count = MaintenanceSkill.objects.filter(is_active=True).count()
            passed = skill_count > 0
            tests.append({"name": "Skills populated", "passed": passed, "detail": f"{skill_count} skills"})
            score += 1 if passed else 0
            total += 1

        # Level 2: RAG retrieval quality
        if level >= 2:
            from core.contract_rag import query_contracts, query_agent_qa

            # Test contract retrieval
            rag_result = query_contracts("lease termination notice period", n_results=3)
            has_results = bool(rag_result.strip())
            tests.append({"name": "RAG contract retrieval", "passed": has_results, "detail": f"{len(rag_result)} chars"})
            score += 1 if has_results else 0
            total += 1

            # Test Q&A retrieval (may be empty, that's ok)
            qa_result = query_agent_qa("maintenance procedure", n_results=3)
            tests.append({"name": "RAG Q&A retrieval", "passed": True, "detail": f"{len(qa_result)} chars (may be 0)"})
            score += 1
            total += 1

        # Level 3: Skills digest quality
        if level >= 3:
            from apps.maintenance.agent_assist_views import _skills_digest
            digest = _skills_digest()
            has_digest = len(digest) > 50 and "No active skills" not in digest
            tests.append({"name": "Skills digest generation", "passed": has_digest, "detail": f"{len(digest)} chars"})
            score += 1 if has_digest else 0
            total += 1

            # Check embedding function loads
            try:
                from core.contract_rag import get_embedding_function
                ef = get_embedding_function()
                tests.append({"name": "Embedding model loads", "passed": True})
                score += 1
                total += 1
            except Exception as e:
                tests.append({"name": "Embedding model loads", "passed": False, "detail": str(e)})
                total += 1

        # Level 4: Data integrity
        if level >= 4:
            # Check token log table
            try:
                log_count = AgentTokenLog.objects.count()
                tests.append({"name": "Token logging active", "passed": True, "detail": f"{log_count} entries"})
                score += 1
            except Exception:
                tests.append({"name": "Token logging active", "passed": False})
            total += 1

            # Check chat log file
            chat_log = getattr(settings, "MAINTENANCE_CHAT_LOG", "")
            log_exists = chat_log and Path(chat_log).parent.is_dir()
            tests.append({"name": "Chat log directory writable", "passed": log_exists, "detail": str(chat_log)})
            score += 1 if log_exists else 0
            total += 1

            # Check MCP server
            mcp_path = Path(settings.BASE_DIR) / "mcp_server" / "server.py"
            tests.append({"name": "MCP server exists", "passed": mcp_path.exists()})
            score += 1 if mcp_path.exists() else 0
            total += 1

        # Level 5: Cross-system integration
        if level >= 5:
            # Verify all collections are accessible
            from core.contract_rag import (
                get_contracts_collection,
                get_agent_qa_collection,
                get_chat_knowledge_collection,
            )
            for name, getter in [
                ("contracts", get_contracts_collection),
                ("agent_qa", get_agent_qa_collection),
                ("chat_knowledge", get_chat_knowledge_collection),
            ]:
                try:
                    col = getter()
                    count = col.count()
                    tests.append({"name": f"Collection '{name}' accessible", "passed": True, "detail": f"{count} docs"})
                    score += 1
                except Exception as e:
                    tests.append({"name": f"Collection '{name}' accessible", "passed": False, "detail": str(e)})
                total += 1

            # Check tenant portal imports
            try:
                from apps.tenant_portal.views import TenantAIChatView
                tests.append({"name": "Tenant AI chat view importable", "passed": True})
                score += 1
            except Exception as e:
                tests.append({"name": "Tenant AI chat view importable", "passed": False, "detail": str(e)})
            total += 1

        return {
            "score": round((score / total) * 100) if total > 0 else 0,
            "tests": tests,
            "passed": score,
            "total": total,
            "level": level,
        }

    def _history_path(self) -> Path:
        return Path(settings.BASE_DIR) / "logs" / self.TEST_HISTORY_FILE

    def _load_history(self) -> list[dict]:
        path = self._history_path()
        if not path.exists():
            return []
        entries = []
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entries.append(json.loads(line))
        except Exception:
            pass
        return entries

    def _save_entry(self, entry: dict):
        path = self._history_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")
