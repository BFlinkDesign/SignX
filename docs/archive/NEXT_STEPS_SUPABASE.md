# 📋 Next Steps: Supabase Configuration

**Current Status:** ✅ Implementation Complete  
**Next Action:** Configure Supabase credentials and test

---

## Immediate Actions (5-10 minutes)

### 1. Get Supabase Credentials ⏭️

**If you don't have a Supabase project yet:**
1. Go to https://supabase.com
2. Sign up / Sign in
3. Create new project
4. Wait for project to initialize (~2 minutes)

**Get credentials:**
1. Go to **Settings** → **API**
2. Copy:
   - **Project URL**: `https://xxxxx.supabase.co`
   - **anon public**: `eyJhbGc...` (safe for frontend)
   - **service_role**: `eyJhbGc...` (⚠️ SECRET - server only)

### 2. Configure Environment Variables ⏭️

**Create `.env` file in project root:**

```bash
# Supabase Authentication
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlvdXItcHJvamVjdC1pZCIsInJvbGUiOiJhbm9uIiwiaWF0IjoxNjExMDMxMjAwLCJleHAiOjE5MjY2MDcyMDB9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlvdXItcHJvamVjdC1pZCIsInJvbGUiOiJzZXJ2aWNlX3JvbGUiLCJpYXQiOjE2MTEwMzEyMDAsImV4cCI6MTkyNjYwNzIwMH0...
```

**Note:** `.env` should be in `.gitignore` (already excluded)

### 3. Restart API Service ⏭️

```powershell
cd "C:\Scripts\Leo Ai Clone"
docker-compose -f infra\compose.yaml restart api
```

This loads the new environment variables.

### 4. Apply RLS Policies ⏭️

**In Supabase Dashboard:**
1. Go to **SQL Editor**
2. Click **New Query**
3. Copy contents from `services/api/src/apex/domains/signage/db/rls_policies.sql`
4. Paste and click **Run**
5. Verify policies created (check Policies tab)

### 5. Test Authentication ⏭️

**Quick Test:**
```powershell
# Register
Invoke-WebRequest `
    -Uri "http://localhost:8000/auth/register?email=test@example.com&password=Test123!&account_id=eagle-sign" `
    -Method POST

# Login
$body = "grant_type=password&username=test@example.com&password=Test123!"
Invoke-WebRequest `
    -Uri "http://localhost:8000/auth/token" `
    -Method POST `
    -Body $body `
    -ContentType "application/x-www-form-urlencoded"
```

**Or use test script:**
```bash
python scripts/test_supabase_auth.py
```

---

## Verification Checklist

After configuration, verify:

- [ ] API restarted with new environment variables
- [ ] `/auth/register` endpoint works (returns 200, not 503)
- [ ] `/auth/token` endpoint works (returns token)
- [ ] RLS policies applied in Supabase
- [ ] Can create project with authenticated user
- [ ] Token validation works on authenticated endpoints

---

## Expected Results

### ✅ Success Indicators

1. **Registration:**
   - Returns `user_id` and `email`
   - May include `email_confirmed: false` if confirmation required
   - Status: 200 OK

2. **Login:**
   - Returns `access_token` and `refresh_token`
   - Token is JWT format (starts with `eyJ...`)
   - Status: 200 OK

3. **Authenticated Request:**
   - Can access `/projects/` with Bearer token
   - User ID extracted from token
   - Projects filtered by user (if RLS applied)

### ❌ Error Indicators

1. **503 Service Unavailable:**
   - "Authentication service not configured"
   - → Environment variables not set or API not restarted

2. **400 Bad Request:**
   - "Registration failed: ..."
   - → Email exists, password invalid, or Supabase config issue

3. **401 Unauthorized:**
   - "Invalid credentials"
   - → Wrong email/password or email not confirmed

---

## Quick Reference

### Environment Variables Format

```bash
# In .env file (no APEX_ prefix needed)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGc...  # anon public key
SUPABASE_SERVICE_KEY=eyJhbGc...  # service_role key (secret!)
```

**The API automatically adds `APEX_` prefix when reading from environment.**

### API Endpoints

- **Register:** `POST /auth/register?email=...&password=...&account_id=...`
- **Login:** `POST /auth/token` (OAuth2PasswordRequestForm)
- **Projects:** `GET /projects/` (requires Authorization header)

### Supabase Dashboard Links

- **SQL Editor:** https://app.supabase.com/project/_/sql
- **API Settings:** https://app.supabase.com/project/_/settings/api
- **Authentication:** https://app.supabase.com/project/_/auth/users

---

## Support

**Documentation:**
- `SUPABASE_SETUP.md` - Full setup guide
- `QUICKSTART_SUPABASE.md` - Quick reference
- `SUPABASE_VALIDATION_REPORT.md` - Validation details

**Troubleshooting:**
- Check API logs: `docker-compose -f infra/compose.yaml logs api`
- Verify environment: `docker-compose -f infra/compose.yaml exec api env | grep SUPABASE`
- Test connectivity: Verify Supabase URL is reachable

---

**Status:** Ready for configuration  
**Estimated Time:** 5-10 minutes  
**Prerequisites:** Supabase account and project

