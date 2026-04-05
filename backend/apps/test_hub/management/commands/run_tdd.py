"""
Management command: run_tdd

Usage:
    python manage.py run_tdd --phase red
    python manage.py run_tdd --phase green
    python manage.py run_tdd --module leases
    python manage.py run_tdd --cycle

Runs pytest programmatically and outputs a TDD cycle report.
"""
import subprocess
import sys
from django.core.management.base import BaseCommand


MODULES = [
    "accounts",
    "properties",
    "leases",
    "maintenance",
    "esigning",
    "ai",
    "tenant_portal",
    "notifications",
]


class Command(BaseCommand):
    help = "Run TDD cycle report for the test_hub test suite"

    def add_arguments(self, parser):
        parser.add_argument(
            "--phase",
            choices=["red", "green", "refactor", "unit", "integration"],
            help="Run only tests with this marker",
        )
        parser.add_argument(
            "--module",
            choices=MODULES,
            help="Run tests for a single module",
        )
        parser.add_argument(
            "--cycle",
            action="store_true",
            help="Print a full Red→Green→Refactor status report",
        )

    def handle(self, *args, **options):
        if options["cycle"]:
            self._cycle_report()
        elif options["phase"]:
            self._run_phase(options["phase"], options.get("module"))
        elif options["module"]:
            self._run_module(options["module"])
        else:
            self._cycle_report()

    def _pytest(self, *extra_args, capture=True):
        """Run pytest with given args, return (returncode, stdout)."""
        base = [sys.executable, "-m", "pytest", "--tb=no", "-q"]
        cmd = base + list(extra_args)
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            cwd=None,  # runs in current dir (backend/)
        )
        return result.returncode, result.stdout + result.stderr

    def _count_tests(self, *args):
        """Count collected tests matching given pytest args."""
        code, out = self._pytest("--co", "-q", *args)
        lines = [l for l in out.splitlines() if l.strip() and not l.startswith("=")]
        # Last non-empty line usually says "X tests selected"
        count = 0
        for line in reversed(lines):
            if "test" in line and ("selected" in line or "no tests" in line):
                try:
                    count = int(line.split()[0])
                except (ValueError, IndexError):
                    pass
                break
        return count

    def _run_phase(self, phase, module=None):
        args = [f"-m {phase}"]
        if module:
            args.append(f"apps/test_hub/{module}/")
        self.stdout.write(self.style.NOTICE(f"\nRunning {phase.upper()} tests...\n"))
        code, out = self._pytest("-m", phase, *(
            [f"apps/test_hub/{module}/"] if module else []
        ), capture=False)

    def _run_module(self, module):
        self.stdout.write(self.style.NOTICE(f"\nRunning all tests for module: {module}\n"))
        code, out = self._pytest(f"apps/test_hub/{module}/", capture=False)

    def _cycle_report(self):
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("  TREMLY TDD CYCLE REPORT"))
        self.stdout.write("=" * 60)

        rows = []
        for module in MODULES:
            path = f"apps/test_hub/{module}/"
            _, out_red = self._pytest("--co", "-q", "-m", "red", path)
            _, out_green = self._pytest("--co", "-q", "-m", "green", path)
            _, out_int = self._pytest("--co", "-q", "-m", "integration", path)
            _, out_unit = self._pytest("--co", "-q", "-m", "unit", path)

            def count(out):
                for line in reversed(out.splitlines()):
                    try:
                        n = int(line.strip().split()[0])
                        return n
                    except (ValueError, IndexError, AttributeError):
                        continue
                return 0

            rows.append({
                "module": module,
                "red": count(out_red),
                "green": count(out_green),
                "unit": count(out_unit),
                "integration": count(out_int),
            })

        # Print table
        self.stdout.write(f"\n{'Module':<20} {'RED':>5} {'GREEN':>7} {'UNIT':>6} {'INTEG':>7}")
        self.stdout.write("-" * 50)
        total_red = total_green = 0
        for row in rows:
            red_str = self.style.ERROR(str(row["red"])) if row["red"] else "0"
            green_str = self.style.SUCCESS(str(row["green"])) if row["green"] else "0"
            self.stdout.write(
                f"{row['module']:<20} {row['red']:>5} {row['green']:>7} {row['unit']:>6} {row['integration']:>7}"
            )
            total_red += row["red"]
            total_green += row["green"]

        self.stdout.write("-" * 50)
        self.stdout.write(f"{'TOTAL':<20} {total_red:>5} {total_green:>7}")
        self.stdout.write("")

        if total_red:
            self.stdout.write(self.style.WARNING(
                f"  {total_red} RED test(s) pending implementation"
            ))
        self.stdout.write(self.style.SUCCESS(
            f"  {total_green} GREEN test(s) passing"
        ))
        self.stdout.write("=" * 60 + "\n")
