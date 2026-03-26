# Klikk Tenant Mobile App — Services & API Reference

## API Configuration

**File:** `lib/config/api_config.dart`

```dart
ApiConfig.baseUrl
// Priority:
// 1. --dart-define=API_BASE_URL=https://...
// 2. Android emulator: http://10.0.2.2:8000/api/v1
// 3. Default (iOS sim): http://127.0.0.1:8000/api/v1
```

All API paths below are relative to `ApiConfig.baseUrl`.

---

## ApiClient (`lib/services/api_client.dart`)

**Singleton:** `final apiClient = ApiClient()`

### Methods

| Method | Signature | Notes |
|--------|-----------|-------|
| `get` | `Future<Map> get(String path, {Map<String,String>? params})` | Single object response |
| `getList` | `Future<List> getList(String path, {Map<String,String>? params})` | Extracts `results` from paginated response |
| `post` | `Future<Map> post(String path, {Map? body})` | JSON POST |
| `patch` | `Future<Map> patch(String path, {Map? body})` | JSON PATCH |
| `postMultipart` | `Future<Map> postMultipart(String path, {String? content, String? filePath})` | File upload + text |
| `tryRefresh` | `Future<bool> tryRefresh()` | Refresh access token |

### Token Management
- Tokens stored in `FlutterSecureStorage` (keys: `access_token`, `refresh_token`)
- All requests include `Authorization: Bearer <access_token>` when token exists
- On 401: automatically calls `tryRefresh()`, retries original request once
- Concurrent refresh calls are de-duplicated via `Completer` lock
- Failed refresh clears both tokens

### Error Handling
- Throws `ApiException(message, {statusCode})` on non-2xx responses
- Parses `detail` or `error` field from JSON error body
- Falls back to `'Request failed ($statusCode)'` if no parseable message

---

## AuthService (`lib/services/auth_service.dart`)

**Constructor:** `AuthService({FlutterSecureStorage? storage})`

### Endpoints

| Method | HTTP | Endpoint | Body | Response |
|--------|------|----------|------|----------|
| `login(email, password)` | POST | `/auth/login/` | `{email, password}` | Saves tokens, returns `AuthUser` |
| `fetchMe()` | GET | `/auth/me/` | — | Returns `AuthUser` |
| `tryRefresh()` | — | — | — | Delegates to `apiClient.tryRefresh()` |

### Login Error Handling
- Parses `non_field_errors` array from Django REST response
- Throws `AuthException(message)` on failure

### AuthUser Model
```dart
class AuthUser {
  final int id;
  final String email;
  final String fullName;  // from json['full_name']
  final String role;

  factory AuthUser.fromJson(Map<String, dynamic> json)
}
```

---

## MaintenanceService (`lib/services/maintenance_service.dart`)

**Singleton:** `final maintenanceService = MaintenanceService()`

### Endpoints

| Method | HTTP | Endpoint | Params/Body |
|--------|------|----------|-------------|
| `listIssues({params})` | GET | `/maintenance/issues/` | Optional: `{status: 'open,in_progress'}` |
| `getIssue(id)` | GET | `/maintenance/issues/{id}/` | — |
| `createIssue({title, description, category, priority})` | POST | `/maintenance/issues/` | `{title, description, category, priority}` |

### MaintenanceIssue Model
```dart
class MaintenanceIssue {
  final int id;
  final String title;
  final String description;
  final String status;      // open, in_progress, resolved, closed
  final String priority;    // low, medium, high, urgent
  final String category;    // plumbing, electrical, roof, appliance, security, pest, garden, other
  final String ticketRef;   // from json['ticket_ref']
  final String createdAt;   // from json['created_at']

  factory MaintenanceIssue.fromJson(Map<String, dynamic> json)
}
```

---

## InfoService (`lib/services/info_service.dart`)

**Singleton:** `final infoService = InfoService()`

### Endpoints

| Method | HTTP | Endpoint |
|--------|------|----------|
| `listUnitInfo()` | GET | `/properties/unit-info/` |

### UnitInfoItem Model
```dart
class UnitInfoItem {
  final int id;
  final String iconType;  // wifi, alarm, electricity, water, rules, other
  final String label;
  final String value;

  factory UnitInfoItem.fromJson(Map<String, dynamic> json)
}
```

**Sensitive types:** `wifi` and `alarm` are masked in the UI (tap to reveal).

---

## LeaseService (`lib/services/lease_service.dart`)

**Singleton:** `final leaseService = LeaseService()`

### Endpoints

| Method | HTTP | Endpoint |
|--------|------|----------|
| `listLeases()` | GET | `/leases/` |

### TenantLease Model
```dart
class TenantLease {
  final int id;
  final String status;
  final String unitLabel;  // from json['unit_label']

  factory TenantLease.fromJson(Map<String, dynamic> json)
}
```

---

## ESigningService (`lib/services/esigning_service.dart`)

**Singleton:** `final esigningService = ESigningService()`

### Endpoints

| Method | HTTP | Endpoint |
|--------|------|----------|
| `listForLease(leaseId)` | GET | `/esigning/submissions/?lease={leaseId}` |
| `getSubmission(id)` | GET | `/esigning/submissions/{id}/` |

### ESigningSubmission Model
```dart
class ESigningSubmission {
  final int id;
  final int leaseId;       // from json['lease']
  final String leaseLabel; // from json['lease_label']
  final String status;     // pending, completed, declined
  final String signingMode; // sequential, parallel
  final String signedPdfUrl;
  final String createdAt;
  final List<ESigningSigner> signers;  // sorted by order

  factory ESigningSubmission.fromJson(Map<String, dynamic> json)
}
```

### ESigningSigner Model
```dart
class ESigningSigner {
  final int? id;
  final String name;
  final String email;
  final String role;     // tenant, landlord, agent, witness
  final String status;   // pending, opened, signed, declined
  final String embedSrc; // DocuSeal embed URL
  final int order;

  factory ESigningSigner.fromJson(Map<String, dynamic> json)
}
```

### Helper Function
```dart
ESigningSigner? actionableSignerForUser({
  required String userEmail,
  required ESigningSubmission submission,
})
```
Returns the first signer who:
1. Matches `userEmail`
2. Has not yet signed (status != `signed`)
3. In sequential mode: is the next signer in order (all prior signers completed)
4. In parallel mode: any unsigned signer can act

---

## Chat API (inline in ChatDetailScreen)

Chat doesn't have a separate service file. API calls are made directly in the screen:

| Action | HTTP | Endpoint | Body |
|--------|------|----------|------|
| List conversations | GET | `/tenant-portal/conversations/` | — |
| Create conversation | POST | `/tenant-portal/conversations/` | `{title: 'New conversation'}` |
| Get messages | GET | `/tenant-portal/conversations/{id}/messages/` | — |
| Send text message | POST | `/tenant-portal/conversations/{id}/messages/` | `{content: '...'}` |
| Send with attachment | POST (multipart) | `/tenant-portal/conversations/{id}/messages/` | content + file |

### Message Shape (from API)
```json
{
  "id": 1,
  "role": "user" | "assistant",
  "content": "message text",
  "attachment_url": "https://...",
  "attachment_type": "image" | "video",
  "maintenance_report_suggested": true,
  "maintenance_draft": {"title": "...", "description": "...", "category": "..."},
  "created_at": "2026-03-25T..."
}
```
