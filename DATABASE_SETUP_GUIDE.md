# SignX Studio Database Setup Guide

## PostgreSQL Not Found

PostgreSQL needs to be installed before database operations can proceed.

### Option 1: Install PostgreSQL (Recommended)

1. **Download PostgreSQL:**
   - Visit: https://www.postgresql.org/download/windows/
   - Download PostgreSQL 16.x installer
   - Recommended: EDB installer (includes pgAdmin GUI)

2. **Install PostgreSQL:**
   - Run installer as Administrator
   - Default port: 5432
   - Set password for 'postgres' user (remember this!)
   - Install pgAdmin 4 (GUI tool)

3. **After Installation - Run Setup Script:**
   ```powershell
   cd C:\Scripts
   .\setup_database.ps1
   ```
   This will:
   - Find PostgreSQL installation
   - Rename database (if needed)
   - Create .env file
   - Test connection

### Option 2: Manual Database Setup

If PostgreSQL is already installed but not found by the script:

#### Step 1: Rename Database (if calcusign_apex exists)
```sql
-- Open pgAdmin or psql, then:

-- Terminate connections
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'calcusign_apex'
  AND pid <> pg_backend_pid();

-- Rename database
ALTER DATABASE calcusign_apex RENAME TO signx_studio;
```

#### Step 2: Create Database (if starting fresh)
```sql
CREATE DATABASE signx_studio
  WITH OWNER = postgres
  ENCODING = 'UTF8'
  LC_COLLATE = 'English_United States.1252'
  LC_CTYPE = 'English_United States.1252'
  TABLESPACE = pg_default
  CONNECTION LIMIT = -1;
```

#### Step 3: Create .env File Manually

Create `C:\Scripts\Leo Ai Clone\.env` (or `C:\Scripts\SignX-Studio\.env` if renamed):

```env
# SignX Studio Environment Configuration

# Database Configuration
DB_NAME=signx_studio
DB_USER=postgres
DB_PASSWORD=YOUR_PASSWORD_HERE
DB_HOST=localhost
DB_PORT=5432

# Database URL (for SQLAlchemy)
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD_HERE@localhost:5432/signx_studio

# Application Settings
APP_ENV=development
DEBUG=true
LOG_LEVEL=INFO

# API Settings
API_HOST=localhost
API_PORT=8000

# Redis (if used)
REDIS_URL=redis://localhost:6379/0

# Secret Key (change in production!)
SECRET_KEY=dev-secret-key-change-in-production
```

**Replace `YOUR_PASSWORD_HERE` with your actual PostgreSQL password!**

#### Step 4: Test Connection
```powershell
# Using psql (adjust path to your PostgreSQL installation)
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -h localhost -U postgres -d signx_studio -c "SELECT version();"
```

Or use pgAdmin 4 to connect and verify.

### Option 3: Docker PostgreSQL

If you prefer Docker:

```powershell
# Start PostgreSQL container
docker run --name signx-postgres `
  -e POSTGRES_PASSWORD=your_password `
  -e POSTGRES_DB=signx_studio `
  -p 5432:5432 `
  -d postgres:16

# Create .env file with:
DB_HOST=localhost
DB_PORT=5432
DB_NAME=signx_studio
DB_USER=postgres
DB_PASSWORD=your_password
```

---

## Next Steps After Database Setup

1. **Verify .env file exists:**
   ```powershell
   Get-Content .env
   ```

2. **Update Python files to use .env:**
   - Run Command 3 (already prepared)

3. **Run migrations:**
   ```powershell
   cd services/api
   alembic upgrade head
   ```

4. **Test the application:**
   ```powershell
   python create_single_pole_module.py
   ```

---

## Troubleshooting

### "psql: command not found"
- Add PostgreSQL to PATH:
  - System Properties → Environment Variables → Path
  - Add: `C:\Program Files\PostgreSQL\16\bin`

### "password authentication failed"
- Check .env file has correct password
- Verify password in pgAdmin
- Reset password if needed:
  ```sql
  ALTER USER postgres PASSWORD 'new_password';
  ```

### "database does not exist"
- Create database manually (see Step 2 above)
- Or run migrations which will create it

---

**Current Status:** PostgreSQL not installed - choose Option 1, 2, or 3 above.
