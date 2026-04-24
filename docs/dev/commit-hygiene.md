# Commit hygiene

## Rule: always use explicit paths with `git add`

Never run `git add -A` or `git add .`. These commands stage every modified and untracked file in the working tree, which routinely bundles:

- coverage artefacts (`.coverage`, `coverage.xml`)
- env config files (`backend/.env.production`, `backend/.env.staging`)
- build artefacts, OS metadata (`.DS_Store`), IDE files

**For humans and agents alike, stage only the files your task touches:**

```bash
# Good
git add backend/apps/leases/models.py admin/src/pages/LeaseDetail.vue

# Bad — stages everything in the working tree
git add -A
git add .
```

## Agent implementers

The `rentals-implementer` agent instructions already enforce this. When writing your final commit step, list each file explicitly. Reference the task's "Files likely touched" section as your staging checklist.

## What belongs in `.gitignore`

| Pattern | Reason |
|---------|--------|
| `.coverage` / `backend/.coverage` | pytest-cov binary artefact, changes every run |
| `coverage.xml` / `backend/coverage.xml` | XML coverage report, machine-generated |
| `backend/.env.production` / `backend/.env.staging` | Non-secret config but changes frequently with ops work; keep off the index to avoid noise |
| `admin/.env.production` / `admin/.env.staging` | Same reason |
| `*.env.secrets` / `.env.secrets` | Real secrets — already ignored, never commit |

Real secrets (`SECRET_KEY`, `DB_PASSWORD`, `ANTHROPIC_API_KEY`, SES credentials) live in `.env.secrets` on the server and are never committed. The env config files (`*.env.production`, `*.env.staging`) contain only non-secret configuration; they are now also ignored to avoid commit noise.
