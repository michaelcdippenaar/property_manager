# Bug Workflow: Manual Issue → Red Test → Fix → Green

This is the mandatory protocol when a manual test session identifies an issue.
**No code changes are made before a red test exists and is confirmed failing.**

---

## The 7-Step Protocol

```
MANUAL ISSUE FOUND
       ↓
1. AUDIT — search existing tests for coverage
       ↓
2. DOCUMENT — create issues/<module>/<issue_slug>.md
       ↓
3. RED — write failing test (@pytest.mark.red)
       ↓
4. CONFIRM RED — run pytest, confirm xfail
       ↓
5. FIX — implement the fix
       ↓
6. USER CONFIRMS — manual verification passes
       ↓
7. GREEN — change marker, run pytest, confirm pass
```

---

## Step 1: Audit Existing Tests

Before writing anything, check if the issue is already covered:

```bash
# Search by keyword
cd backend && pytest --co -q | grep -i "<keyword>"

# Search test files for related assertions
grep -r "keyword" apps/test_hub/<module>/

# Check the module context file
cat apps/test_hub/context/modules/<module>.md
```

**Rules:**
- If an existing test SHOULD have caught this bug but didn't → investigate why the test passed
- If the test exists but tests the wrong case → update the test, don't duplicate it
- If genuinely not covered → proceed to Step 2

---

## Step 2: Document the Issue

Create `apps/test_hub/issues/<module>/<YYYY-MM-DD>_<slug>.md` using this template:

```markdown
# Issue: <short title>

**Module:** <module>
**Status:** RED
**Discovered:** <date> (manual testing)
**Test file:** apps/test_hub/<module>/<tier>/test_<file>.py::<Class>::<method>

## Description
What was observed during manual testing.

## Reproduction Steps
1. Step one
2. Step two
3. Expected: X — Got: Y

## Root Cause
(Fill in after investigation)

## Fix Applied
(Fill in after fix)

## Test Coverage
- New test: `<test path>`
- Duplicate check: confirmed NOT covered by existing tests
  - Checked: <list test files reviewed>

## Status History
- YYYY-MM-DD: Identified during manual testing
- YYYY-MM-DD: Red test created
- YYYY-MM-DD: Fix applied
- YYYY-MM-DD: Green — user confirmed
```

---

## Step 3: Write the Red Test

Add to the appropriate test file (unit/ or integration/ based on what needs to be tested):

```python
@pytest.mark.red
@pytest.mark.integration  # or unit
def test_<descriptive_name>(self):
    """
    RED: <one-line description of what this test verifies>
    Issue: apps/test_hub/issues/<module>/<date>_<slug>.md
    """
    # Arrange
    ...
    # Act
    response = self.client.post(...)
    # Assert — this assertion currently fails (that's correct)
    self.assertEqual(response.status_code, 200)
```

**Key rules:**
- Test name must describe the BUG, not the fix — `test_lease_end_date_before_start_date_rejected`, not `test_date_validation_fix`
- Include a link to the issue .md file in the docstring
- The test must be atomic — one assertion, one scenario

---

## Step 4: Confirm Red

```bash
cd backend && pytest apps/test_hub/<module>/ -m red -v
```

Expected output:
```
XFAIL test_<name> - RED: implementation not written yet
```

If it shows PASSED instead of XFAIL → the bug doesn't exist or the test is wrong. Stop and investigate.

---

## Step 5: Fix the Implementation

Make the minimum change required to fix the issue. Do not refactor unrelated code.

---

## Step 6: User Confirms

The user manually verifies the fix works before the test is changed to green.

---

## Step 7: Mark Green

1. Change `@pytest.mark.red` → `@pytest.mark.green`
2. Run:
```bash
cd backend && pytest apps/test_hub/<module>/ -m green -v
```
3. Update the issue .md file:
   - Change `**Status:** RED` → `**Status:** FIXED`
   - Fill in Root Cause, Fix Applied, Status History

---

## Deduplication Rules

### Before creating any test:
1. `pytest --co -q | grep -i <subject>` — check collected test names
2. `grep -r "def test_" apps/test_hub/<module>/` — scan all test methods
3. If a similar test exists: **extend it**, don't create a new one

### Naming collision resolution:
- If `test_lease_dates_valid` exists and you need `test_lease_end_before_start`:
  - These are DIFFERENT tests — both are valid, keep both
- If `test_register_invalid_email` exists and you found a new email edge case:
  - Add a parametrize case or new method `test_register_email_with_plus_sign` — don't replace

### Coverage audit per module:
Track what each test file covers in the module .md context file under a `## Current Coverage` section.

---

## Issue File Location

```
apps/test_hub/issues/
├── README.md
├── leases/
│   └── 2026-04-04_end-date-before-start.md
├── accounts/
│   └── 2026-04-04_otp-expired-still-accepted.md
└── ...
```

Issues are **never deleted** — they form the bug history of the project.

---

## Quick Reference

```bash
# Confirm issue is RED (xfail)
pytest apps/test_hub/<module>/ -m red -v

# After fix, confirm GREEN (pass)
pytest apps/test_hub/<module>/ -m green -v

# Check deduplication
pytest --co -q | grep -i <keyword>

# Full module health check
pytest apps/test_hub/<module>/ -v

# TDD cycle report
python manage.py run_tdd --module <module>
```
