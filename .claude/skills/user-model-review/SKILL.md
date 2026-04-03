---
name: user-model-review
description: >
  Review user models, roles, and permissions for security issues. Trigger for: "user model review",
  "role review", "permission review", "privilege escalation check", "user security", "role separation",
  "PII exposure", "password policy review", "user model audit", "RBAC review", "access control review".
---

# User Model & Permissions Security Review — Tremly

You are a security architect reviewing user models, roles, and permission structures for a multi-tenant property management application.

## Review Steps

### Step 1: User Model Analysis
Read `backend/apps/accounts/models.py` completely.

Check:
1. **Custom user model fields**:
   - `id_number` (SA ID) — Stored as plaintext CharField. Should be encrypted at rest.
   - `phone` — No format validation beyond CharField(max_length=20)
   - `email` — unique=True is good
   - `role` — CharField with TextChoices, not enforced at the DB level with constraints

2. **Role definitions**:
   - TENANT, AGENT, ADMIN, SUPPLIER, OWNER — 5 roles
   - Default role — is it safe for all registration paths?
   - No role hierarchy defined — is AGENT a subset of ADMIN?

3. **Person model** — Separate from User, linked via `linked_user` OneToOneField:
   - Contains duplicate PII (full_name, id_number, phone, email) — risk of inconsistency
   - `company_reg`, `vat_number` — sensitive business data
   - No `role` concept — type is INDIVIDUAL/COMPANY only

4. **OTPCode model**:
   - `code` stored as plaintext CharField — should be hashed
   - `is_used` flag — good, prevents replay
   - No `attempts` counter for brute-force protection
   - No index on `(user, is_used, created_at)` for query performance

5. **PushToken model**:
   - `token` as TextField — unbounded length, potential for abuse
   - No validation of token format per platform

### Step 2: Serializer Review
Read `backend/apps/accounts/serializers.py`.

Check:
1. **UserSerializer**:
   - Which fields are in `fields`?
   - Which fields are in `read_only_fields`?
   - Is `role` writable via PATCH? (Privilege escalation risk)
   - Is `email` writable without verification?
   - Are `is_staff`, `is_superuser` exposed or excluded?

2. **RegisterSerializer**:
   - Is `role` accepted? (Must NOT be)
   - Is there email verification?
   - Password validation applied?

3. **PersonSerializer** (in properties or accounts app):
   - Exposes `id_number`, `phone`, `email`, `company_reg`, `vat_number`?
   - Is `linked_user` writable — could anyone link a person to their own user account?
   - Permission check on who can create/update persons?

### Step 3: View-Level Permission Analysis
Read ALL views that handle user data.

For each view, document:
| View | Endpoint | Permission | Role Check | IDOR Risk |
|------|----------|------------|------------|-----------|

Check specifically:
1. `MeView` — Can users update fields they shouldn't (role, is_staff)?
2. `PersonViewSet` — Does `get_queryset()` return ALL persons? Any authenticated user can list everyone?
3. `PersonDetailView` — Can any authenticated user read/update any person by ID?
4. `TenantsListView` — Should be restricted to agents/admins only.
5. Owner views — Do they verify `role == 'owner'`?
6. Supplier views — Do they verify `role == 'supplier'`?

### Step 4: Permission Class Inventory
Search for all custom permission classes across `backend/apps/`:
- Find classes inheriting from `BasePermission`
- Document which views use which permissions
- Identify views using only `IsAuthenticated` where role checks are needed

Assessment criteria:
- Most views should NOT use only `IsAuthenticated` — role differentiation is needed
- Object-level permissions required for multi-tenant data isolation
- Check if `DjangoModelPermissions` or `DjangoObjectPermissions` are used anywhere

### Step 5: Role Separation Matrix
Build a matrix of what each role SHOULD vs CAN access:

| Resource | TENANT | AGENT | ADMIN | SUPPLIER | OWNER |
|----------|--------|-------|-------|----------|-------|
| All Properties | No | Own | All | No | Own |
| All Units | No | Own | All | No | Own |
| All Persons | No | Yes | Yes | No | No |
| All Leases | Own | Yes | Yes | No | Own |
| All Maintenance | Own | Yes | Yes | Assigned | Own |
| AI Chat | Own | No | No | No | No |
| Supplier Docs | No | Yes | Yes | Own | No |
| E-Signing | Own | Yes | Yes | No | Own |

Compare against actual implementation to find gaps where the current access exceeds what SHOULD be allowed.

### Step 6: Password Policy Review
Read `backend/config/settings/base.py` AUTH_PASSWORD_VALIDATORS.

Check:
- `UserAttributeSimilarityValidator` — present?
- `MinimumLengthValidator` — what length? (Should be 10+)
- `CommonPasswordValidator` — present?
- `NumericPasswordValidator` — present?
- Missing: complexity requirements (uppercase, lowercase, digit, special char)
- Missing: password history (prevent reuse)

### Step 7: Session & Token Management
1. JWT configuration — read `SIMPLE_JWT` in settings
2. Check for logout/token revocation endpoint
3. Check if refresh tokens are properly rotated
4. Check if there's a "revoke all sessions" capability
5. WebSocket authentication — JWT via query string (potential logging risk)

## Output Format

```
# User Model & Permissions Security Review

## Risk Summary
| Category | Severity | Count |
|----------|----------|-------|
| Privilege Escalation | CRITICAL | X |
| IDOR | HIGH | X |
| PII Exposure | HIGH | X |
| Missing Role Checks | MEDIUM | X |
| Password Policy | MEDIUM | X |

## Detailed Findings

### [USR-001] Finding Title
- **Severity**: CRITICAL/HIGH/MEDIUM/LOW
- **Location**: file:line
- **Impact**: [description]
- **Remediation**: [specific fix]

## Role Access Matrix (Current vs Required)
[Matrix table showing gaps]

## Recommended Permission Architecture
[Description of recommended RBAC implementation with code examples]

## Implementation Priority
P0: [immediate fixes]
P1: [this sprint]
P2: [backlog]
```
