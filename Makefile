# Klikk Rentals v1 — project-level Makefile
# Run targets from the repo root.

.PHONY: compile-emails check-emails

## compile-emails: Compile base.mjml → compiled/base.html and re-apply Django conditionals
compile-emails:
	@bash scripts/compile_email_templates.sh

## check-emails: CI guard — fail if compiled/base.html is stale or missing conditionals
check-emails:
	@bash scripts/compile_email_templates.sh --check
