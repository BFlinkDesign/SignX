# Windows 11 Pro Deployment Guide

**Purpose**: Windows 11 Pro specific deployment instructions and configuration  
**Last Updated**: 2025-01-27  
**Target**: Windows 11 Pro (21H2 or later)

---

## Prerequisites

### System Requirements

- **OS**: Windows 11 Pro (21H2 or later)
- **RAM**: 8GB minimum (16GB recommended)
- **Disk Space**: 50GB free minimum
- **CPU**: 4 cores recommended
- **WSL2**: Optional but recommended

---

## Docker Desktop Configuration

### Installation

1. **Download Docker Desktop**
   - Visit: https://www.docker.com/products/docker-desktop
   - Download: Docker Desktop for Windows
   - Version: Latest stable (4.20+)

2. **Install Docker Desktop**
   ```powershell
   # Run installer as Administrator
   # Follow installation wizard
   # Enable "Use WSL 2 based engine" (recommended)
   ```

3. **Verify Installation**
   ```powershell
   docker --version
   docker compose version
   # Should show: Docker version 24.x.x or later
   ```

---

### Docker Desktop Settings

#### General Settings

- [x] **Use WSL 2 based engine** (Recommended)
- [x] **Start Docker Desktop when you log in**
- [x] **Use the WSL 2 based engine**
- [ ] **Send usage statistics** (Optional)

#### Resources Settings

**Memory**: Allocate at least 4GB (8GB recommended)
```
Settings → Resources → Advanced
- CPUs: 4+ (or half of available)
- Memory: 4096 MB minimum (8192 MB recommended)
- Swap: 2048 MB
- Disk image size: 60 GB
```

**File Sharing**: Enable for project directory
```
Settings → Resources → File Sharing
- Add: C:\Scripts\Leo Ai Clone
- Add: C:\Users\<username>\AppData\Local\Docker (if needed)
```

**Network**: Use default bridge network
```
Settings → Resources → Network
- Use default network settings
```

---

### WSL2 Backend Setup (Optional but Recommended)

#### Why WSL2?

- Better performance than Hyper-V backend
- Native Linux filesystem support
- Lower resource overhead
- Better Docker Compose compatibility

#### Installation Steps

1. **Enable WSL2**
   ```powershell
   # Run as Administrator
   wsl --install
   
   # Or manually
   dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
   dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
   ```

2. **Set WSL2 as Default**
   ```powershell
   wsl --set-default-version 2
   ```

3. **Install Linux Distribution**
   ```powershell
   # Install Ubuntu (recommended)
   wsl --install -d Ubuntu
   
   # Or from Microsoft Store
   # Search: Ubuntu 22.04 LTS
   ```

4. **Configure Docker Desktop**
   ```
   Settings → General → Use WSL 2 based engine
   Settings → Resources → WSL Integration
   - Enable integration with default WSL distro
   - Enable Ubuntu (or your distro)
   ```

5. **Verify WSL2 Backend**
   ```powershell
   wsl --list --verbose
   # Should show: VERSION 2 for your distro
   
   docker info | Select-String "Operating System"
   # Should show: Docker Desktop WSL2
   ```

---

## Port Configuration

### Common Port Conflicts

Windows 11 may have services using common ports:

| Port | Service | Conflict | Resolution |
|------|---------|----------|------------|
| 3000 | IIS / Node.js | Common | Use 3001 for Grafana |
| 5432 | PostgreSQL | May conflict | Use Docker networking |
| 6379 | Redis | Rare | Usually available |
| 8000 | IIS / Other | Common | Check with netstat |
| 9200 | OpenSearch | Rare | Usually available |

---

### Checking Port Availability

```powershell
# Check if port is in use
netstat -ano | findstr "8000"
netstat -ano | findstr "5432"
netstat -ano | findstr "3001"
netstat -ano | findstr "6379"

# Alternative: Using PowerShell
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
Get-NetTCPConnection -LocalPort 5432 -ErrorAction SilentlyContinue
Get-NetTCPConnection -LocalPort 3001 -ErrorAction SilentlyContinue
```

**If Port is in Use**:

1. **Identify Process**
   ```powershell
   # Find process using port
   netstat -ano | findstr "8000"
   # Note the PID
   tasklist | findstr "<PID>"
   ```

2. **Stop Conflicting Service**
   ```powershell
   # Example: Stop IIS (if running)
   iisreset /stop
   
   # Or stop specific service
   Stop-Service -Name "ServiceName"
   ```

3. **Alternative: Change APEX Port**
   ```yaml
   # In infra/compose.yaml, change:
   ports:
     - "8001:8000"  # Use 8001 instead
   ```

---

## Firewall Configuration

### Windows Defender Firewall Rules

Create inbound rules for APEX services:

```powershell
# Run PowerShell as Administrator

# Port 8000 (API)
New-NetFirewallRule -DisplayName "APEX API" `
    -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow

# Port 3001 (Grafana)
New-NetFirewallRule -DisplayName "APEX Grafana" `
    -Direction Inbound -LocalPort 3001 -Protocol TCP -Action Allow

# Port 5173 (Frontend)
New-NetFirewallRule -DisplayName "APEX Frontend" `
    -Direction Inbound -LocalPort 5173 -Protocol TCP -Action Allow

# Port 8002 (Signcalc)
New-NetFirewallRule -DisplayName "APEX Signcalc" `
    -Direction Inbound -LocalPort 8002 -Protocol TCP -Action Allow

# Port 5432 (PostgreSQL - Docker internal, optional)
New-NetFirewallRule -DisplayName "APEX PostgreSQL" `
    -Direction Inbound -LocalPort 5432 -Protocol TCP -Action Allow

# Port 6379 (Redis - Docker internal, optional)
New-NetFirewallRule -DisplayName "APEX Redis" `
    -Direction Inbound -LocalPort 6379 -Protocol TCP -Action Allow
```

**Or via GUI**:
1. Open Windows Defender Firewall
2. Advanced Settings → Inbound Rules → New Rule
3. Port → TCP → Specific ports: `8000,3001,5173,8002`
4. Allow connection → Apply to all profiles
5. Name: "APEX Services"

---

### Verify Firewall Rules

```powershell
# List APEX firewall rules
Get-NetFirewallRule -DisplayName "APEX*" | Format-Table DisplayName, Enabled, Direction, Action
```

---

## Antivirus Exclusions

### Windows Defender Exclusions

Add Docker volumes and project directories to exclusions:

```powershell
# Run PowerShell as Administrator

# Add project directory
Add-MpPreference -ExclusionPath "C:\Scripts\Leo Ai Clone"

# Add Docker data directory
Add-MpPreference -ExclusionPath "C:\ProgramData\Docker"
Add-MpPreference -ExclusionPath "$env:LOCALAPPDATA\Docker"

# Add WSL directory (if using WSL2)
Add-MpPreference -ExclusionPath "$env:LOCALAPPDATA\Packages\CanonicalGroupLimited.Ubuntu*"
```

**Via GUI**:
1. Windows Security → Virus & threat protection
2. Manage settings → Exclusions
3. Add or remove exclusions
4. Add folder: `C:\Scripts\Leo Ai Clone`
5. Add folder: `C:\ProgramData\Docker`

---

### Third-Party Antivirus

If using third-party antivirus (Norton, McAfee, etc.):

1. **Add Exclusions**:
   - Project directory: `C:\Scripts\Leo Ai Clone`
   - Docker volumes: `C:\ProgramData\Docker`
   - WSL filesystem (if using WSL2)

2. **Disable Real-Time Scanning for Docker** (Optional):
   - Temporarily disable during initial build
   - Re-enable after deployment

---

## PowerShell Execution Policy

### Check Current Policy

```powershell
Get-ExecutionPolicy
# Should show: RemoteSigned or Unrestricted
```

---

### Set Execution Policy (If Needed)

**For Current User**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**For System** (Requires Administrator):
```powershell
# Run PowerShell as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope LocalMachine
```

**Verify**:
```powershell
Get-ExecutionPolicy -List
```

---

### Bypass for Single Session

If you cannot change policy:
```powershell
# Run script with bypass
powershell -ExecutionPolicy Bypass -File .\scripts\execute_deployment.ps1
```

---

## SQL Server Port Conflicts

### If SQL Server is Installed

SQL Server may use port 1433 (default) but could conflict with PostgreSQL port configuration:

**Check SQL Server**:
```powershell
# Check if SQL Server is running
Get-Service | Where-Object {$_.Name -like "*SQL*"}

# Check SQL Server ports
Get-NetTCPConnection -LocalPort 1433 -ErrorAction SilentlyContinue
```

**Resolution**:
- Docker PostgreSQL uses internal port 5432 (not exposed by default)
- No conflict unless you're running PostgreSQL on host
- If needed, change SQL Server port or stop SQL Server service

---

## IIS Configuration

### If IIS is Running

IIS may conflict with ports 80, 443, 8000:

**Check IIS**:
```powershell
Get-Service | Where-Object {$_.Name -like "*W3SVC*"}
# If running, IIS is active
```

**Resolution Options**:

1. **Stop IIS** (if not needed):
   ```powershell
   iisreset /stop
   ```

2. **Change IIS Ports**:
   - IIS Manager → Sites → Bindings
   - Change HTTP port from 80 to 8080
   - Change HTTPS port from 443 to 8443

3. **Use Different APEX Ports**:
   ```yaml
   # In infra/compose.yaml
   ports:
     - "8080:8000"  # Use 8080 instead of 8000
   ```

---

## Docker Volume Permissions

### Windows Path Format

Docker Compose on Windows should use forward slashes:

```yaml
# Correct
volumes:
  - ./data:/app/data

# Avoid (may cause issues)
volumes:
  - C:\Scripts\Leo Ai Clone\data:/app/data
```

**Use relative paths**:
```yaml
volumes:
  - ../data:/app/data  # Relative to compose.yaml location
```

---

### Volume Access Issues

If containers can't write to volumes:

1. **Check Volume Ownership**
   ```powershell
   # Docker Desktop handles permissions automatically
   # But verify volume mounts
   docker compose exec api ls -la /app/data
   ```

2. **Create Volumes with Proper Permissions**
   ```powershell
   # Create named volumes (better for Windows)
   docker volume create apex-data
   # Use in compose.yaml:
   volumes:
     - apex-data:/app/data
   ```

---

## Network Configuration

### Docker Network Isolation

Docker creates isolated networks. Services communicate via service names:

```yaml
# In compose.yaml, services can reach each other:
database_url: postgresql://apex:password@db:5432/apex
redis_url: redis://cache:6379/0
```

**Verify Network**:
```powershell
docker network ls
docker network inspect apex_default
```

---

### Host Network Access

To access services from host (Windows):
- Use `localhost` (127.0.0.1)
- Ports must be exposed in `compose.yaml`
- Firewall rules must allow connections

---

## Performance Optimization

### WSL2 Backend (Recommended)

- [x] Use WSL2 for better performance
- [x] Store project in WSL filesystem for faster I/O
- [x] Allocate sufficient resources (4GB+ RAM)

### Hyper-V Backend (Alternative)

- Use if WSL2 not available
- May have slower file I/O
- Requires Hyper-V feature enabled

---

## Troubleshooting Windows-Specific Issues

### Issue: "Docker daemon not running"

**Solution**:
```powershell
# Start Docker Desktop
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# Or check service
Get-Service *docker*
```

---

### Issue: "Permission denied" on volumes

**Solution**:
- Use named volumes instead of bind mounts
- Check Docker Desktop file sharing settings
- Verify antivirus exclusions

---

### Issue: "Port already in use"

**Solution**:
```powershell
# Find process
netstat -ano | findstr "PORT"

# Kill process (if safe)
taskkill /PID <PID> /F
```

---

### Issue: "Connection refused" from host

**Solution**:
- Check firewall rules
- Verify ports are exposed in compose.yaml
- Check service is actually running: `docker compose ps`

---

## Quick Reference Commands

### Docker Commands

```powershell
# Start services
cd infra
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f api

# Stop services
docker compose down

# Rebuild images
docker compose build --no-cache

# Clean everything
docker compose down -v
docker system prune -a
```

---

### Verification Commands

```powershell
# Check ports
netstat -ano | findstr "8000 3001 5173"

# Check Docker
docker --version
docker compose version

# Check WSL (if using)
wsl --list --verbose

# Check firewall
Get-NetFirewallRule -DisplayName "APEX*"
```

---

## Deployment on Windows 11

### Step-by-Step

1. **Install Docker Desktop** ✅
2. **Configure Docker Desktop** ✅
3. **Set firewall rules** ✅
4. **Add antivirus exclusions** ✅
5. **Set PowerShell execution policy** ✅
6. **Check port availability** ✅
7. **Run deployment**:
   ```powershell
   cd C:\Scripts\Leo Ai Clone
   .\scripts\execute_deployment.ps1
   ```

---

## Windows-Specific Best Practices

1. **Use WSL2 Backend**: Better performance and compatibility
2. **Named Volumes**: Prefer named volumes over bind mounts
3. **Relative Paths**: Use relative paths in compose.yaml
4. **Firewall Rules**: Create specific rules, don't disable firewall
5. **Antivirus**: Exclude Docker directories, don't disable
6. **PowerShell**: Use PowerShell 7+ for better cross-platform support
7. **Port Management**: Check and resolve conflicts before deployment

---

**Document Version**: 1.0  
**Last Updated**: 2025-01-27  
**Target Platform**: Windows 11 Pro (21H2+)

