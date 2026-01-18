# Security Implementation Quick Reference

**Phase**: Phase 5 - Immediate Security
**Status**: 50% Complete (Tasks 5.1 & 5.2 Done)
**Last Updated**: January 18, 2026

---

## Quick Start

### 1. API Key Management (✅ COMPLETE)

**Create API Key**:
```bash
curl -X POST http://localhost:8000/api-keys \
  -H "Authorization: Bearer <jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "CI Integration",
    "scope": ["api:read", "ci:read"],
    "expires_at": "2026-12-31T23:59:59Z"
  }'
```

**Use API Key for Auth**:
```bash
curl http://localhost:8000/api/definitions \
  -H "Authorization: Bearer sk_a1b2c3d4e5f6..."
```

**List Your API Keys**:
```bash
curl http://localhost:8000/api-keys \
  -H "Authorization: Bearer <jwt-token>"
```

**Revoke API Key**:
```bash
curl -X DELETE http://localhost:8000/api-keys/{key_id} \
  -H "Authorization: Bearer <jwt-token>"
```

---

### 2. Resource Permissions (✅ COMPLETE)

**Check My Permissions**:
```bash
curl http://localhost:8000/permissions/me \
  -H "Authorization: Bearer <jwt-token>"
```

**Grant Permission (Admin Only)**:
```bash
curl -X POST \
  "http://localhost:8000/permissions/grant?user_id=user-123&resource_type=api&permission=api:delete&resource_id=api-456" \
  -H "Authorization: Bearer <admin-token>"
```

**Revoke Permission (Admin Only)**:
```bash
curl -X DELETE \
  "http://localhost:8000/permissions/revoke?user_id=user-123&resource_type=api&permission=api:delete" \
  -H "Authorization: Bearer <admin-token>"
```

**Check User Permission (Admin)**:
```bash
curl "http://localhost:8000/permissions/check?user_id=user-123&permission=api:delete" \
  -H "Authorization: Bearer <admin-token>"
```

---

## Architecture Overview

### Authentication Flow
```
User
  ├─ JWT Token (from /auth/login)
  │  └─ Valid for 30 minutes
  │     └─ Contains: user_id, role, tenant_id
  │
└─ API Key (from /api-keys)
   └─ Persistent until revoked/expired
      └─ Contains: user_id, scopes, expiration
```

### Authorization Flow
```
Request with Authorization Header
  ├─ Extract credentials (JWT or API Key)
  ├─ Verify user exists & is active
  ├─ Check permission against:
  │  ├─ Resource-specific override (if applicable)
  │  ├─ Resource-type override (if applicable)
  │  └─ Role-based defaults (fallback)
  └─ Grant or Deny access
```

---

## Key Concepts

### 1. API Keys (Task 5.1)

| Feature | Details |
|---------|---------|
| **Format** | `sk_` + 32 random hex chars |
| **Storage** | bcrypt hashed in database |
| **Scopes** | 12 permission types |
| **Expiration** | Optional (checked on validation) |
| **Last Used** | Tracked for monitoring |
| **Revocation** | Soft delete (audit trail preserved) |

**Scopes Available**:
```
api:read, api:write, api:delete, api:execute
ci:read, ci:write, ci:delete
metric:read, graph:read, history:read
cep:read, cep:write
```

### 2. Permissions (Task 5.2)

| Feature | Details |
|---------|---------|
| **Types** | 40+ granular permissions |
| **Roles** | Admin, Manager, Developer, Viewer |
| **Levels** | Resource-specific, resource-type, role-based |
| **Expiration** | Optional (checked on each request) |
| **Audit** | Who granted, when, to whom |

**Permission Categories**:
- API Management (6)
- CI/CD Management (6)
- Metrics & Monitoring (2)
- Graph & Assets (2)
- History & Audit (3)
- CEP Rules (5)
- Documents (4)
- UI & Settings (6+)

---

## Role Permissions

### Admin (All Permissions)
```
✅ api:*, ci:*, metric:*, graph:*, history:*
✅ cep:*, document:*, ui:*, asset:*
✅ settings:*, user:*, audit:*
```

### Manager (All Except User Management)
```
✅ api:*, ci:*, metric:*, graph:*, history:*
✅ cep:*, document:*, ui:*, asset:*
✅ settings:*, audit:*
❌ user:*
```

### Developer (Create, Read, Update, Execute)
```
✅ api:read, api:create, api:update, api:execute
✅ ci:read, ci:create, ci:update, ci:execute
✅ metric:read, graph:read, history:read
✅ cep:read, cep:create, cep:update, cep:execute
✅ document:read, document:upload
✅ ui:read, ui:create, ui:update
❌ api:delete, ci:delete, document:delete, ui:delete
```

### Viewer (Read-Only)
```
✅ api:read, metric:read, graph:read, history:read
✅ cep:read, document:read, ui:read, asset:read
✅ settings:read, audit:read
❌ Any create, update, delete, execute
```

---

## Integration Checklist

### For API Endpoints

**Protect with Role**:
```python
@router.get("/apis")
def list_apis(
    current_user: TbUser = Depends(get_current_user),
):
    # User must be authenticated
    # Role-based permissions apply automatically
```

**Protect with Specific Permission**:
```python
@router.post("/apis")
def create_api(
    payload: ApiCreate,
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    # Check specific permission
    if not check_permission_sync(
        session, current_user.id, current_user.role,
        ResourcePermission.API_CREATE
    ):
        raise HTTPException(403, "Permission denied")
```

**Protect with Resource Permission**:
```python
@router.delete("/apis/{api_id}")
def delete_api(
    api_id: str,
    current_user: TbUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    # Check resource-specific permission
    if not check_permission_sync(
        session, current_user.id, current_user.role,
        ResourcePermission.API_DELETE,
        resource_type="api",
        resource_id=api_id
    ):
        raise HTTPException(403, "Permission denied")
```

---

## Common Tasks

### Grant Emergency Access (Admin)
```bash
# Grant 24-hour elevated access to specific resource
curl -X POST \
  "http://localhost:8000/permissions/grant?user_id=dev-123&resource_type=api&permission=api:delete&resource_id=api-999&expires_at=2026-01-19T15:00:00Z" \
  -H "Authorization: Bearer <admin-token>"
```

### Grant Team Access
```bash
# Grant all API permissions to team member
curl -X POST \
  "http://localhost:8000/permissions/grant?user_id=new-dev&resource_type=api&permission=api:create" \
  -H "Authorization: Bearer <admin-token>"
```

### Revoke Access
```bash
# Immediately revoke dangerous permission
curl -X DELETE \
  "http://localhost:8000/permissions/revoke?user_id=departing-emp&resource_type=api&permission=api:delete" \
  -H "Authorization: Bearer <admin-token>"
```

### List All Team Permissions
```bash
curl http://localhost:8000/permissions/team-member-id \
  -H "Authorization: Bearer <manager-token>"
```

---

## Database Tables

### tb_api_key
```sql
id (UUID) - Primary key
user_id (FK) - Owner
name - Human-readable name
key_prefix - First 8 chars (preview only)
key_hash - bcrypt hash (secure storage)
scope - JSON array of permission scopes
is_active - Revocation flag
last_used_at - Last authentication
expires_at - Optional expiration
created_at, updated_at - Timestamps
created_by_trace_id - Audit trail
```

### tb_role_permission
```sql
id (UUID) - Primary key
role - admin, manager, developer, viewer
permission - Permission string (e.g., "api:read")
is_granted - Boolean (allow/deny)
created_at, updated_at - Timestamps
```

### tb_resource_permission
```sql
id (UUID) - Primary key
user_id (FK) - User granted to
resource_type - "api", "ci", "metric", etc.
resource_id - Specific resource (NULL = all of type)
permission - Permission string
is_granted - Allow/deny flag
expires_at - Optional auto-expiration
created_at, updated_at - Timestamps
created_by_user_id - Who granted it
```

---

## Security Best Practices

### 1. API Keys
- ✅ Never share keys over email
- ✅ Rotate keys periodically
- ✅ Use narrow scopes (principle of least privilege)
- ✅ Set expiration dates when possible
- ✅ Revoke immediately if compromised

### 2. Permissions
- ✅ Use role-based permissions for default policy
- ✅ Grant resource-specific only for exceptions
- ✅ Use time-limited permissions for elevated access
- ✅ Regularly audit permission grants
- ✅ Revoke promptly on departures

### 3. Authentication
- ✅ Use strong passwords
- ✅ Protect JWT tokens (HTTPOnly cookies)
- ✅ Refresh tokens regularly (30-min default)
- ✅ Enable HTTPS/TLS in production
- ✅ Monitor failed login attempts

### 4. Audit Trail
- ✅ All permission grants logged (created_by_user_id)
- ✅ All API key creations logged
- ✅ All permission checks logged
- ✅ Timestamp all security events
- ✅ Retain logs for compliance

---

## Troubleshooting

### "Permission Denied" Error

**Check My Permissions**:
```bash
curl http://localhost:8000/permissions/me \
  -H "Authorization: Bearer <token>"
```

**Check My Role**:
```bash
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer <token>"
```

**Ask Admin to Check**:
```bash
curl "http://localhost:8000/permissions/check?user_id=myid&permission=api:create" \
  -H "Authorization: Bearer <admin-token>"
```

### "Invalid Token" Error

**For JWT**: Token may be expired (30-min lifetime)
```bash
# Get new token
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "..."}'
```

**For API Key**: Key may be revoked or expired
```bash
# Check active keys
curl http://localhost:8000/api-keys \
  -H "Authorization: Bearer <jwt-token>"
```

---

## Monitoring

### Permission Usage Stats
```bash
# Get my effective permissions
curl http://localhost:8000/permissions/me \
  -H "Authorization: Bearer <token>" | jq '.data.effective_permissions'
```

### API Key Usage
```bash
# List all my keys with last used timestamp
curl http://localhost:8000/api-keys \
  -H "Authorization: Bearer <token>" | jq '.data.api_keys[] | {name, last_used_at}'
```

### Permission Audit
```bash
# Check when permission expires
curl "http://localhost:8000/permissions/check?user_id=xyz&permission=api:delete" \
  -H "Authorization: Bearer <admin-token>" | jq '.data.expires_at'
```

---

## Migration Path

### Phase 5 Completion Timeline
1. **✅ Day 1**: Task 5.1 API Keys
2. **✅ Day 1**: Task 5.2 Permissions
3. **⏳ Days 2-3**: Task 5.3 Encryption
4. **🔜 Day 4**: Task 5.4 UI
5. **🔜 Weeks 2-3**: Phase 6 (HTTPS/Headers)
6. **🔜 Weeks 3-4**: Phase 7 (OPS AI)
7. **🔜 Weeks 4-5**: Phase 8 (CI Mgmt)

### Deployment Order
1. ✅ Run 5.1 & 5.2 migrations immediately
2. ✅ Deploy 5.1 & 5.2 code
3. 🔜 Run 5.3 migration after 5.3 complete
4. 🔜 Add 5.4 UI when ready

---

## Related Documentation

- `TASK_5_1_API_KEYS_IMPLEMENTATION.md` - Full API Keys details
- `TASK_5_2_PERMISSIONS_IMPLEMENTATION.md` - Full Permissions details
- `PHASE_5_PROGRESS_UPDATE.md` - Phase progress and metrics
- `P0_COMPLETION_PLAN.md` - Overall P0 roadmap

---

## Support & Questions

**For issues or questions**:
1. Check the full implementation docs above
2. Review test cases for usage examples
3. Check API endpoint docstrings
4. Review database schema

**Files to reference**:
- API Keys: `apps/api/app/modules/api_keys/`
- Permissions: `apps/api/app/modules/permissions/`
- Tests: `apps/api/tests/test_api_keys.py`, `test_permissions.py`

---

**Last Updated**: January 18, 2026
**Next Phase**: Task 5.3 (Encryption) - Starting Soon
