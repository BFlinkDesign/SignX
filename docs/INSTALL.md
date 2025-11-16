# SignX Studio - Installation Guide for Estimators

**Quick Start Guide for Engineering Estimators**

Version: 1.0.0
Last Updated: 2025-11-01

---

## Table of Contents

- [Overview](#overview)
- [System Requirements](#system-requirements)
- [Quick Installation (Windows)](#quick-installation-windows)
- [Manual Installation](#manual-installation)
- [First-Time Setup](#first-time-setup)
- [Using SignX Studio](#using-signx-studio)
- [Troubleshooting](#troubleshooting)
- [Getting Help](#getting-help)

---

## Overview

SignX Studio is a structural engineering calculation platform designed for sign estimators and engineers. It provides automated calculations for wind loads, structural analysis, and material selection based on ASCE 7-22 and IBC 2024 standards.

**Key Features:**
- Automated wind load calculations
- Material database with AISC sections
- Calculation audit trails for PE review
- Export calculations to PDF/Excel
- Project management and history

---

## System Requirements

### Minimum Requirements
- **Operating System:** Windows 10 (64-bit) or Windows 11
- **RAM:** 8 GB minimum, 16 GB recommended
- **Storage:** 10 GB free space
- **Processor:** Intel Core i5 or equivalent
- **Network:** Internet connection for initial setup

### Software Prerequisites
- Docker Desktop (will be installed automatically)
- Modern web browser (Chrome, Edge, or Firefox)

---

## Quick Installation (Windows)

The easiest way to install SignX Studio is using the automated installer.

### Step 1: Download the Installer

1. Download `install_signx.ps1` from your IT department or shared drive
2. Save it to a folder like `C:\Temp` or your Desktop

### Step 2: Run the Installer

1. **Right-click** on Windows Start menu
2. Select **"Windows PowerShell (Admin)"** or **"Terminal (Admin)"**
3. Navigate to the folder containing the installer:
   ```powershell
   cd C:\Temp
   ```
4. Run the installer:
   ```powershell
   .\install_signx.ps1
   ```

### Step 3: Follow the Prompts

The installer will:
- Check if Docker is installed (and install it if needed)
- Create necessary folders
- Generate secure passwords
- Download and start SignX Studio
- Open your browser to the application

**Installation takes 10-15 minutes** depending on your internet speed.

### Step 4: Verify Installation

Once complete, you should see:
- A browser window open to `http://localhost:8000/docs`
- The SignX Studio API documentation

**You're ready to go!** Proceed to [First-Time Setup](#first-time-setup).

---

## Manual Installation

If you prefer manual installation or the automated installer doesn't work:

### Step 1: Install Docker Desktop

1. Download Docker Desktop from: https://www.docker.com/products/docker-desktop
2. Run the installer
3. Restart your computer when prompted
4. Launch Docker Desktop and wait for it to start

### Step 2: Download SignX Studio

1. Copy the SignX Studio folder to `C:\SignX-Studio`
2. The folder should contain:
   - `docker-compose.prod.yml`
   - `services/` folder
   - `scripts/` folder
   - `.env.example` file

### Step 3: Configure Environment

1. Open PowerShell as Administrator
2. Navigate to the installation folder:
   ```powershell
   cd C:\SignX-Studio
   ```
3. Copy the example environment file:
   ```powershell
   cp .env.example .env
   ```
4. Edit `.env` in Notepad and set secure passwords:
   ```
   POSTGRES_PASSWORD=your-secure-password-here
   REDIS_PASSWORD=your-secure-password-here
   SECRET_KEY=your-secret-key-here
   ```

### Step 4: Create Data Folders

```powershell
mkdir data\postgres
mkdir backups
mkdir logs
```

### Step 5: Start SignX Studio

```powershell
docker-compose -f docker-compose.prod.yml up -d
```

Wait 1-2 minutes for all services to start, then open your browser to:
- http://localhost:8000/docs

---

## First-Time Setup

### 1. Verify the Installation

Open your browser to: http://localhost:8000/health

You should see a green checkmark with "healthy" status.

### 2. Access the API Documentation

Navigate to: http://localhost:8000/docs

This is the interactive API documentation where you can test calculations.

### 3. Run Your First Calculation

Let's calculate wind pressure for a simple sign:

1. In the API docs, find **POST /api/v1/calculations/wind-pressure**
2. Click "Try it out"
3. Enter the following JSON:
   ```json
   {
     "velocity": 115,
     "exposure_category": "C",
     "elevation": 20,
     "structure_type": "sign",
     "enclosed": false
   }
   ```
4. Click "Execute"
5. You should see wind pressure results in the response

**Congratulations!** SignX Studio is working correctly.

### 4. Bookmark Important URLs

Add these to your browser bookmarks:
- **API Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health
- **API Base:** http://localhost:8000/api

---

## Using SignX Studio

### Daily Workflow

1. **Start the Application**
   - Docker Desktop should start automatically with Windows
   - SignX Studio will start automatically when Docker starts
   - If not, open PowerShell and run:
     ```powershell
     cd C:\SignX-Studio
     docker-compose -f docker-compose.prod.yml up -d
     ```

2. **Access the API**
   - Open http://localhost:8000/docs in your browser
   - Use the interactive documentation to run calculations

3. **Create a Calculation**
   - Use the POST endpoints to create new calculations
   - Each calculation is saved with a unique ID
   - Results include full audit trail for PE review

4. **Export Results**
   - Use the GET endpoints to retrieve calculations
   - Export to PDF for project documentation
   - Export to Excel for cost estimation

### Common Operations

#### Check System Status
```powershell
cd C:\SignX-Studio
docker-compose -f docker-compose.prod.yml ps
```

#### View Logs
```powershell
docker-compose -f docker-compose.prod.yml logs -f api
```
Press `Ctrl+C` to stop viewing logs.

#### Stop SignX Studio
```powershell
docker-compose -f docker-compose.prod.yml down
```

#### Start SignX Studio
```powershell
docker-compose -f docker-compose.prod.yml up -d
```

#### Restart After Changes
```powershell
docker-compose -f docker-compose.prod.yml restart
```

---

## Troubleshooting

### Problem: "Docker is not running"

**Solution:**
1. Open Docker Desktop from the Start menu
2. Wait for the whale icon to stop animating in the system tray
3. Try your command again

### Problem: "Port 8000 is already in use"

**Solution:**
1. Check what's using port 8000:
   ```powershell
   netstat -ano | findstr :8000
   ```
2. Either stop that application or change the port in `.env`:
   ```
   API_PORT=8001
   ```

### Problem: "Can't access http://localhost:8000"

**Solution:**
1. Check if services are running:
   ```powershell
   docker-compose -f docker-compose.prod.yml ps
   ```
2. Check service health:
   ```powershell
   docker-compose -f docker-compose.prod.yml logs api
   ```
3. Try restarting:
   ```powershell
   docker-compose -f docker-compose.prod.yml restart
   ```

### Problem: "Database connection error"

**Solution:**
1. Check if database is running:
   ```powershell
   docker-compose -f docker-compose.prod.yml ps db
   ```
2. Check database logs:
   ```powershell
   docker-compose -f docker-compose.prod.yml logs db
   ```
3. Restart the database:
   ```powershell
   docker-compose -f docker-compose.prod.yml restart db
   ```

### Problem: "Out of disk space"

**Solution:**
1. Clean up old Docker images:
   ```powershell
   docker system prune -a
   ```
2. Remove old backups:
   ```powershell
   cd C:\SignX-Studio\backups
   # Delete files older than 30 days manually
   ```

### Problem: "Calculation results are incorrect"

**Solution:**
1. Verify input parameters match project requirements
2. Check that you're using the correct building code (ASCE 7-22, IBC 2024)
3. Review the audit trail in the calculation response
4. Contact engineering for verification

---

## Getting Help

### Documentation
- **Installation Guide:** This document
- **Deployment Guide:** `docs/DEPLOY.md` (for IT staff)
- **API Documentation:** http://localhost:8000/docs

### Support Contacts
- **IT Support:** Contact your IT department for installation issues
- **Engineering Support:** Contact the engineering team for calculation questions
- **Software Issues:** Report bugs to the development team

### Useful Commands Reference

```powershell
# Check if Docker is running
docker ps

# View all running services
docker-compose -f docker-compose.prod.yml ps

# View logs for specific service
docker-compose -f docker-compose.prod.yml logs api
docker-compose -f docker-compose.prod.yml logs db

# Stop all services
docker-compose -f docker-compose.prod.yml down

# Start all services
docker-compose -f docker-compose.prod.yml up -d

# Restart a specific service
docker-compose -f docker-compose.prod.yml restart api

# View disk usage
docker system df

# Clean up unused resources
docker system prune

# Create a database backup
.\scripts\backup_database.ps1

# Check application health
curl http://localhost:8000/health
```

---

## Next Steps

After successful installation:

1. **Learn the API** - Explore http://localhost:8000/docs
2. **Run Test Calculations** - Try sample calculations with known results
3. **Set Up Backups** - Configure automated backups (see DEPLOY.md)
4. **Train Your Team** - Share this guide with other estimators
5. **Provide Feedback** - Report issues and suggest improvements

---

## Appendix: Default File Locations

| Item | Location |
|------|----------|
| Application | `C:\SignX-Studio` |
| Database Data | `C:\SignX-Studio\data\postgres` |
| Backups | `C:\SignX-Studio\backups` |
| Logs | `C:\SignX-Studio\logs` |
| Configuration | `C:\SignX-Studio\.env` |

---

**For IT deployment and advanced configuration, see [DEPLOY.md](DEPLOY.md)**
