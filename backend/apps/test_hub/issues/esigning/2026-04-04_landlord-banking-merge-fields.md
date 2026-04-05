# Issue: Landlord & Banking Merge Fields Not Populated on Signing Page
**Module:** esigning
**Status:** RED
**Discovered:** 2026-04-04 (manual testing)
**Test file:** apps/test_hub/esigning/integration/test_html_rendering.py::LandlordBankingMergeFieldTests

## Description
On the signing page (`/sign/:token/`), landlord details (name, email, registration, VAT, representative) and banking details (bank name, account number, branch code, etc.) display as `—` instead of real values.

## Reproduction Steps
1. Navigate to `/sign/11f15062-1868-404d-861a-6c2e5e857103/`
2. Observe that landlord fields show `—`
3. Observe that banking fields show `—`

## Root Cause
The existing test `BuildLeaseContextTests.test_context_has_required_keys` only checks that dict keys **exist** (`assertIn`) — not that they hold real values. The test setup also never creates the required data chain: `PropertyOwnership` → `Landlord` → `BankAccount`. Banking fields aren't even in the required_keys list.

## Fix Applied
1. Added factory methods: `create_landlord()`, `create_bank_account()`, `create_property_ownership()` to `TremlyAPITestCase`
2. New test class `LandlordBankingMergeFieldTests` with 13 tests verifying actual values
3. Strengthened existing `BuildLeaseContextTests` to verify values, not just key presence

## Test Coverage
- New tests: `apps/test_hub/esigning/integration/test_html_rendering.py::LandlordBankingMergeFieldTests`
- Duplicate check: confirmed NOT covered — checked: `test_html_rendering.py`, `test_leases.py` merge field tests

## Status History
- 2026-04-04: Discovered during manual testing → RED
