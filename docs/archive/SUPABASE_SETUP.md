# Supabase Integration Setup

**Date:** November 1, 2025  
**Status:** ✅ Configured

---

## Overview

APEX now supports Supabase Auth for user authentication and Row Level Security (RLS) for data access control.

---

## Docker Compose Configuration

A local Supabase PostgreSQL database service has been added to `infra/compose.yaml`:

- **Service:** `supabase-db`
- **Port:** `5433` (to avoid conflict with main `db` service on `5432`)
- **Image:** `supabase/postgres:15.1.0.117`
- **Volume:** `supabase_db` (persistent storage)

---

## Environment Variables

### For Local Development (Optional)

If using local Supabase stack:

```bash
# .env file (not committed to git)
SUPABASE_URL=http://localhost:8000  # Supabase Studio URL (if running locally)
SUPABASE_KEY=your-anon-key           # Supabase anon/public key
SUPABASE_SERVICE_KEY=your-service-role-key  # Supabase service role key (admin)
```

### For Production (Cloud Supabase)

Set these environment variables:

```bash
APEX_SUPABASE_URL=https://your-project.supabase.co
APEX_SUPABASE_KEY=your-anon-key
APEX_SUPABASE_SERVICE_KEY=your-service-role-key
```

**Note:** The `APEX_` prefix is automatically added by the Settings class (see `services/api/src/apex/api/deps.py`).

---

## API Endpoints

### Register User

```bash
POST /auth/register?email=test@example.com&password=Test123!&account_id=eagle-sign
```

**Response:**
```json
{
  "result": {
    "user_id": "uuid",
    "email": "test@example.com",
    "email_confirmed": false,
    "account_id": "eagle-sign"
  },
  "assumptions": ["Email confirmation required - check your inbox"],
  "confidence": 1.0,
  "trace": {...}
}
```

### Login

```bash
POST /auth/token
Content-Type: application/x-www-form-urlencoded

grant_type=password&username=test@example.com&password=Test123!
```

**Response:**
```json
{
  "result": {
    "access_token": "eyJhbGc...",
    "refresh_token": "eyJhbGc...",
    "token_type": "bearer",
    "expires_in": 3600,
    "user": {
      "id": "uuid",
      "email": "test@example.com",
      "account_id": "eagle-sign"
    }
  },
  "trace": {...}
}
```

### Authenticated Request

```bash
GET /projects/
Authorization: Bearer <access_token>
```

---

## Row Level Security (RLS)

RLS policies have been created in `services/api/src/apex/domains/signage/db/rls_policies.sql`.

### To Apply RLS Policies

1. **If using Supabase Cloud:**
   - Copy the SQL from `rls_policies.sql`
   - Run it in the Supabase SQL Editor

2. **If using local Supabase stack:**
   ```bash
   docker exec -i apex-supabase-db-1 psql -U supabase -d postgres < services/api/src/apex/domains/signage/db/rls_policies.sql
   ```

### Policies Created

1. **Projects Table:**
   - Users can view own projects
   - Users can create projects (enforced via API)
   - Users can update own projects
   - Users can delete own projects

2. **Project Payloads Table:**
   - Users can view payloads for own projects
   - Users can create payloads for own projects

3. **User Accounts Table:**
   - Users can view own account memberships

---

## Authentication Flow

1. **Register** → User signs up via `/auth/register`
2. **Confirm Email** → (If required by Supabase config)
3. **Login** → User authenticates via `/auth/token`
4. **Get Token** → Receives Supabase JWT access token
5. **API Requests** → Include token in `Authorization: Bearer <token>` header

### Token Validation

The API automatically:
- Tries Supabase token verification first (if configured)
- Falls back to legacy JWT validation (for backwards compatibility)
- Extracts user metadata (account_id, roles) from Supabase user object

---

## Project Integration

### Create Project (Authenticated)

```python
# In routes/projects.py
@router.post("/")
async def create_project(
    req: ProjectCreateRequest,
    current_user: TokenData | None = Depends(get_current_user_optional),
):
    # Uses current_user.user_id as created_by
    # Uses current_user.account_id from metadata
```

### Access Control

Projects are automatically:
- Tagged with `created_by = current_user.user_id`
- Tagged with `account_id = current_user.account_id`
- Protected by RLS policies in Supabase

---

## Testing

### PowerShell Test Script

```powershell
$baseUrl = "http://localhost:8000"

# Register
Invoke-WebRequest `
    -Uri "$baseUrl/auth/register?email=test@example.com&password=Test123!&account_id=eagle-sign" `
    -Method POST

# Login
$loginBody = "grant_type=password&username=test@example.com&password=Test123!"
$loginResult = Invoke-WebRequest `
    -Uri "$baseUrl/auth/token" `
    -Method POST `
    -Body $loginBody `
    -ContentType "application/x-www-form-urlencoded"

$token = ($loginResult.Content | ConvertFrom-Json).result.access_token

# Test authenticated endpoint
$headers = @{ Authorization = "Bearer $token" }
Invoke-WebRequest -Uri "$baseUrl/projects/" -Headers $headers
```

---

## Migration Path

### From Mock Auth to Supabase

1. ✅ Supabase client utilities created
2. ✅ Auth routes updated to use Supabase
3. ✅ Token validation supports both Supabase and legacy JWT
4. ✅ Project routes use authenticated user
5. ✅ RLS policies defined
6. ⏭️ Deploy and configure Supabase URL/keys

### Backwards Compatibility

- Legacy JWT tokens still work (fallback)
- Mock auth still available for development
- Optional authentication on project creation

---

## Security Notes

1. **Service Role Key:** Only use `SUPABASE_SERVICE_KEY` server-side, never expose to client
2. **Anon Key:** Safe to use in frontend/client applications
3. **RLS:** Always enabled in Supabase for data protection
4. **Tokens:** Supabase tokens are JWT, validated server-side

---

## Troubleshooting

### "Authentication service not configured"

**Solution:** Set Supabase environment variables:
```bash
export APEX_SUPABASE_URL=https://your-project.supabase.co
export APEX_SUPABASE_KEY=your-anon-key
```

### "Registration failed"

**Possible causes:**
- Email already exists
- Password doesn't meet Supabase requirements
- Supabase not accessible

### "Invalid credentials"

**Possible causes:**
- Wrong email/password
- Email not confirmed (if required)
- User account disabled

---

## Next Steps

1. **Setup Supabase Project:**
   - Create project at https://supabase.com
   - Get URL and keys from Settings → API

2. **Configure Environment:**
   - Add Supabase vars to `.env` or Docker Compose
   - Restart API service

3. **Apply RLS Policies:**
   - Run `rls_policies.sql` in Supabase SQL Editor

4. **Test Authentication:**
   - Use provided PowerShell script
   - Verify token validation works

5. **Update Frontend:**
   - Update frontend to call `/auth/register` and `/auth/token`
   - Store tokens in localStorage/sessionStorage
   - Include tokens in API requests

---

**Status:** ✅ Ready for Supabase configuration  
**Next:** Set Supabase environment variables and test authentication

