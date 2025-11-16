# 🚀 Quick Start: Configure Supabase Authentication

**Next Action:** Configure Supabase credentials to activate authentication

---

## Step 1: Get Supabase Credentials

### Option A: Supabase Cloud (Recommended for Production)

1. Go to https://supabase.com
2. Create a new project or select existing
3. Go to **Settings** → **API**
4. Copy:
   - **Project URL** → `SUPABASE_URL`
   - **anon public** key → `SUPABASE_KEY`
   - **service_role** key → `SUPABASE_SERVICE_KEY` (⚠️ Keep secret!)

### Option B: Local Supabase (For Development)

If using the local Supabase stack in Docker Compose:
- URL will be your local Supabase Studio URL (typically http://localhost:54321)
- Keys from your local Supabase configuration

---

## Step 2: Set Environment Variables

### Method 1: Create `.env` file (Recommended)

Create a `.env` file in the project root:

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Note:** The `APEX_` prefix is added automatically by the Settings class.

### Method 2: Export in Shell (Temporary)

```powershell
# PowerShell
$env:SUPABASE_URL="https://your-project.supabase.co"
$env:SUPABASE_KEY="your-anon-key"
$env:SUPABASE_SERVICE_KEY="your-service-role-key"

# Then restart API
docker-compose -f infra\compose.yaml restart api
```

### Method 3: Docker Compose Environment (Persistent)

Update `infra/compose.yaml` API service:

```yaml
api:
  environment:
    # ... existing vars ...
    - APEX_SUPABASE_URL=${SUPABASE_URL}
    - APEX_SUPABASE_KEY=${SUPABASE_KEY}
    - APEX_SUPABASE_SERVICE_KEY=${SUPABASE_SERVICE_KEY}
```

Then:
```bash
docker-compose -f infra/compose.yaml up -d api
```

---

## Step 3: Apply RLS Policies

### If Using Supabase Cloud:

1. Go to your Supabase project
2. Open **SQL Editor**
3. Copy contents of `services/api/src/apex/domains/signage/db/rls_policies.sql`
4. Paste and run in SQL Editor
5. Verify policies are created

### If Using Local Supabase DB:

```bash
# Copy RLS policies to Supabase database
docker cp services/api/src/apex/domains/signage/db/rls_policies.sql apex-supabase-db-1:/tmp/rls.sql
docker exec -i apex-supabase-db-1 psql -U supabase -d postgres < services/api/src/apex/domains/signage/db/rls_policies.sql
```

---

## Step 4: Verify Configuration

### Test API Health

```powershell
Invoke-WebRequest -Uri http://localhost:8000/health
```

### Test Registration Endpoint

```powershell
$result = Invoke-WebRequest `
    -Uri "http://localhost:8000/auth/register?email=test@example.com&password=Test123!&account_id=eagle-sign" `
    -Method POST

$result.Content | ConvertFrom-Json | ConvertTo-Json -Depth 3
```

**Expected:**
- ✅ Status 200: Supabase configured correctly
- ❌ Status 503: Supabase not configured (set environment variables)
- ❌ Status 400: Registration failed (user exists or invalid data)

### Test Login

```powershell
$body = "grant_type=password&username=test@example.com&password=Test123!"
$login = Invoke-WebRequest `
    -Uri "http://localhost:8000/auth/token" `
    -Method POST `
    -Body $body `
    -ContentType "application/x-www-form-urlencoded"

$token = ($login.Content | ConvertFrom-Json).result.access_token
Write-Host "Token: $($token.Substring(0,30))..."
```

### Test Authenticated Request

```powershell
$headers = @{ Authorization = "Bearer $token" }
Invoke-WebRequest -Uri "http://localhost:8000/projects/" -Headers $headers
```

---

## Step 5: Run Integration Tests

```bash
# Install httpx if needed
pip install httpx

# Run tests
python scripts/test_supabase_auth.py
```

---

## Troubleshooting

### "Authentication service not configured" (503)

**Cause:** Supabase environment variables not set

**Fix:**
1. Set `SUPABASE_URL` and `SUPABASE_KEY` environment variables
2. Restart API: `docker-compose -f infra/compose.yaml restart api`

### "Registration failed" (400)

**Possible causes:**
- Email already exists
- Password doesn't meet requirements
- Supabase project settings restrict registration

**Fix:**
- Use a different email
- Check Supabase dashboard → Authentication → Settings
- Verify password meets requirements (min 8 characters)

### "Invalid credentials" (401)

**Possible causes:**
- Wrong email/password
- Email not confirmed (if email confirmation required)
- User doesn't exist

**Fix:**
- Verify credentials
- Check Supabase dashboard → Authentication → Users
- Confirm email if required

### Token validation fails

**Possible causes:**
- Token expired
- Token format incorrect
- Supabase URL/key mismatch

**Fix:**
- Get new token via login
- Verify `Authorization: Bearer <token>` header format
- Check Supabase credentials are correct

---

## Configuration Checklist

- [ ] Supabase project created
- [ ] Credentials obtained (URL, anon key, service role key)
- [ ] Environment variables set
- [ ] API service restarted
- [ ] RLS policies applied
- [ ] Registration tested
- [ ] Login tested
- [ ] Authenticated requests tested

---

## Security Reminders

⚠️ **Important:**
- Never commit `.env` file to git
- Service role key has admin access - keep secret
- Anon key can be used in frontend (safe)
- Enable email confirmation for production

---

## Next Steps After Configuration

1. ✅ Test authentication endpoints
2. ⏭️ Update frontend to use auth
3. ⏭️ Test full user workflow
4. ⏭️ Configure email templates (if using email confirmation)
5. ⏭️ Set up user roles/permissions

---

**Ready to configure?** Set your Supabase credentials and restart the API service!

