from __future__ import annotations

import json

from django.core.management.base import BaseCommand

from apps.tenant_portal.training_validate import load_training_cases, validate_all_cases


class Command(BaseCommand):
    help = (
        "Load tenant_ai_training_cases.json: list cases, validate schema, "
        "and optionally run embedded parse regression (no Anthropic calls)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--parse-check",
            action="store_true",
            help="Run expect_chat_parse / expect_draft_parse against sample_*_raw fields",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Print full fixture JSON to stdout (for piping)",
        )

    def handle(self, *args, **options):
        data = load_training_cases()
        cases = data.get("cases", [])

        if options["json"]:
            self.stdout.write(json.dumps(data, ensure_ascii=False, indent=2))
            return

        self.stdout.write(
            self.style.NOTICE(
                f"tenant_ai_training_cases.json v{data.get('version', '?')}: "
                f"{len(cases)} cases"
            )
        )

        if options["parse_check"]:
            errors = validate_all_cases(data)
        else:
            errors = []
            seen: set[str] = set()
            for i, case in enumerate(cases):
                if not isinstance(case, dict):
                    errors.append(f"case[{i}] not an object")
                    continue
                cid = case.get("id")
                if not cid:
                    errors.append(f"case[{i}] missing id")
                    continue
                if cid in seen:
                    errors.append(f"duplicate case id: {cid}")
                seen.add(str(cid))

        if errors:
            for e in errors:
                self.stderr.write(self.style.ERROR(e))
            self.stderr.write(self.style.ERROR(f"\n{len(errors)} error(s)"))
            raise SystemExit(1)

        self.stdout.write(self.style.SUCCESS("OK — no errors"))
        if not options["parse_check"]:
            self.stdout.write(
                "Tip: run with --parse-check to verify sample_chat_assistant_raw / "
                "sample_draft_model_raw expectations."
            )
