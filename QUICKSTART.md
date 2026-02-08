# SignX Autonomous PWA - Quick Start Guide

## 🚀 Getting Started

This guide will help you set up and test the SignX autonomous PWA system across all 7 phases.

---

## 📋 Prerequisites

### Required

- Python 3.11 or higher
- Node.js 18+ (for PWA frontend)
- PostgreSQL 17
- Redis (for caching and sessions)
- Git

### Optional

- Docker Desktop (for containerized deployment)
- Visual Studio Code or PyCharm

---

## ⚙️ Phase 1: Backend API Setup

### 1. Clone and Navigate

```powershell
cd C:\Scripts\SignX
```

### 2. Set Up Python Environment

```powershell
# Navigate to API service
cd services\api

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements-dev.txt

# Install new auth dependencies
pip install pyotp qrcode twilio sendgrid aiohttp PyJWT
```

### 3. Configure Environment Variables

Create `.env` file in `services/api/.env`:

```env
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/signx
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-super-secret-key-change-in-production

# Gemini API
GEMINI_API_KEY=your-gemini-api-key

# MFA - Twilio (SMS)
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# MFA - SendGrid (Email)
SENDGRID_API_KEY=your_sendgrid_api_key
EMAIL_FROM=noreply@signx.com

# SSO - Azure AD
AZURE_TENANT_ID=common
AZURE_CLIENT_ID=your_azure_client_id
AZURE_CLIENT_SECRET=your_azure_client_secret

# SSO - Google
GOOGLE_CLIENT_ID=your_google_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_google_client_secret

# SSO - Apple
APPLE_CLIENT_ID=com.eaglesign.signx
APPLE_TEAM_ID=your_apple_team_id
APPLE_KEY_ID=your_apple_key_id
APPLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"

# App Config
BASE_URL=http://localhost:8000
ENV=dev
CORS_ALLOW_ORIGINS=["http://localhost:3000", "http://localhost:8000"]
```

### 4. Run Database Migrations

```powershell
# Run Alembic migrations (when created)
alembic upgrade head
```

### 5. Start the API Server

```powershell
# Start development server
python -m uvicorn apex.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Test the API

Open browser to: `http://localhost:8000/docs`

You should see the Swagger UI with all API endpoints including:

- Auth & MFA endpoints (`/api/v1/auth/*`)
- Engineering solvers
- Project management
- AI/ML endpoints

---

## 🎨 Phase 2: PWA Frontend Setup

### 1. Navigate to Frontend

```powershell
cd C:\Scripts\SignX\SignX-Studio
```

### 2. Install Dependencies

```powershell
npm install
```

### 3. Configure Environment

Create `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

### 4. Start Development Server

```powershell
npm run dev
```

Open browser to: `http://localhost:3000`

---

## 🧪 Testing

### Test MFA Setup

1. **Set Up TOTP (Authenticator App)**

```powershell
curl -X POST http://localhost:8000/api/v1/auth/mfa/setup/totp \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"
```

Expected response:

```json
{
  "secret": "JBSWY3DPEHPK3PXP",
  "qr_code_url": "otpauth://totp/SignX:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=SignX",
  "backup_codes": [
    "ABCD-1234",
    "EFGH-5678",
    ...
  ]
}
```

2. **Verify TOTP Code**

```powershell
curl -X POST http://localhost:8000/api/v1/auth/mfa/verify/totp \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "secret": "JBSWY3DPEHPK3PXP",
    "code": "123456"
  }'
```

3. **Send SMS Code**

```powershell
curl -X POST http://localhost:8000/api/v1/auth/mfa/send/sms \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "method": "sms",
    "phone_number": "+15551234567"
  }'
```

4. **Check MFA Status**

```powershell
curl -X GET http://localhost:8000/api/v1/auth/mfa/status \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## 🔍 Troubleshooting

### Common Issues

#### Port Already in Use

```powershell
# Kill process on port 8000
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

#### Database Connection Error

```powershell
# Check PostgreSQL is running
Get-Service postgresql*

# Start if stopped
Start-Service postgresql-x64-17
```

#### Redis Connection Error

```powershell
# Install Redis on Windows using WSL or Docker
docker run -d -p 6379:6379 redis:latest
```

#### Import Errors

```powershell
# Reinstall dependencies
pip install --upgrade -r requirements-dev.txt
```

---

## 📁 Project Structure

```
C:\Scripts\SignX\
├── services/
│   └── api/
│       ├── src/apex/api/
│       │   ├── main.py                    # Main FastAPI app
│       │   ├── auth.py                    # Base auth (existing)
│       │   ├── auth_mfa.py               # ✨ NEW: MFA implementation
│       │   ├── auth_providers.py         # ✨ NEW: SSO providers
│       │   └── routes/
│       │       ├── auth.py                # Existing auth routes
│       │       └── auth_mfa.py           # ✨ NEW: MFA routes
│       ├── .env                           # Environment config
│       └── requirements-dev.txt
│
├── SignX-Studio/                          # Frontend (Next.js)
│   ├── src/
│   │   ├── app/                          # Next.js 14 app router
│   │   ├── components/                   # React components
│   │   └── lib/                          # Utilities
│   ├── public/
│   ├── package.json
│   └── .env.local
│
├── AUTONOMOUS_PWA_IMPLEMENTATION.md       # ✨ Complete implementation plan
├── PROGRESS_REPORT.md                     # ✨ Current progress
└── QUICKSTART.md                          # ✨ This file
```

---

## 🎯 Next Steps

### Completed ✅

- MFA module implementation
- SSO provider integration  
- API route registration

### In Progress 🟡

- SSO callback routes
- Account management
- Session management

### Coming Soon 🔲

- PWA service worker
- AI orchestration layer
- Engineering solver APIs
- Database schema migrations

---

## 📚 Documentation

- **API Docs**: <http://localhost:8000/docs> (when running)
- **Implementation Plan**: [AUTONOMOUS_PWA_IMPLEMENTATION.md](AUTONOMOUS_PWA_IMPLEMENTATION.md)
- **Progress Report**: [PROGRESS_REPORT.md](PROGRESS_REPORT.md)
- **Main README**: [README.md](README.md)

---

## 🆘 Getting Help

### Resources

- Gemini integration guide: [GEMINI.md](GEMINI.md)
- FastAPI docs: <https://fastapi.tiangolo.com>
- Supabase docs: <https://supabase.com/docs>
- Next.js docs: <https://nextjs.org/docs>

### Common Commands

**Backend**:

```powershell
# Start API  
cd services\api
.\.venv\Scripts\Activate.ps1
uvicorn apex.api.main:app --reload

# Run tests
pytest

# Run linter
ruff check .
```

**Frontend**:

```powershell
# Start dev server
cd SignX-Studio
npm run dev

# Build for production
npm run build

# Run tests
npm test
```

---

## 🔐 Security Notes

### Development vs Production

#### Development (Current)

- Using development JWT secret
- Mock MFA codes accepted
- CORS allows localhost
- Detailed error messages

#### Production (TODO)

- Strong JWT secret from environment
- Real MFA verification
- Restrictive CORS
- Generic error messages
- Rate limiting enabled
- HTTPS only

---

## ✅ Health Check

Once everything is running, verify:

1. **API Health**: <http://localhost:8000/health>
2. **API Docs**: <http://localhost:8000/docs>
3. **Frontend**: <http://localhost:3000>
4. **Database**: Connection shown in API logs
5. **Redis**: Connection shown in API logs

---

**Last Updated**: 2025-11-23  
**Version**: 0.1.0 (Phase 1 - Auth Enhancement)
