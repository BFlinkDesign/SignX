# Getting Started with SignX-Intel

This guide will help you get SignX-Intel up and running.

## Quick Start (5 minutes)

### Option 1: Automated Setup (Recommended)

```powershell
# Run the setup script
.\scripts\setup.ps1
```

This will:
- ✅ Check Python 3.12 installation
- ✅ Create virtual environment
- ✅ Install dependencies
- ✅ Create .env file
- ✅ Start Docker services
- ✅ Create data directories

### Option 2: Manual Setup

```powershell
# 1. Create virtual environment
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy environment file
# Edit .env with your settings

# 4. Start Docker services
docker-compose up -d

# 5. Create data directories
mkdir -p data/raw data/processed data/models migrations/versions
```

---

## Initialize Database

```powershell
# Run migrations
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

---

## Start the API Server

```powershell
# Option 1: Using helper script
.\scripts\start_api.ps1

# Option 2: Direct command
uvicorn src.signx_intel.api.main:app --host 127.0.0.1 --port 8000 --reload
```

The API will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/api/v1/docs
- **MLflow**: http://localhost:5000

---

## Test the Installation

### 1. Health Check

```powershell
# PowerShell
Invoke-WebRequest http://localhost:8000/health

# Or open in browser
start http://localhost:8000/api/v1/docs
```

### 2. Run Tests

```powershell
.\scripts\run_tests.ps1
```

### 3. Test Prediction

```powershell
# PowerShell
$body = @{
    drivers = @{
        sign_height_ft = 25
        sign_area_sqft = 120
        foundation_type = "drilled_pier"
    }
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/api/v1/predict" `
    -ContentType "application/json" -Body $body
```

---

## Add Your PDF Data

1. **Place PDFs in `data/raw/`**
   ```powershell
   # Copy your PDF cost summaries
   Copy-Item "C:\path\to\your\pdfs\*.pdf" data\raw\
   ```

2. **Process PDFs**
   ```powershell
   .\scripts\process_pdfs.ps1
   ```

3. **Review Extracted Data**
   ```powershell
   # Check data/processed/ for CSV/Parquet files
   Get-ChildItem data\processed\
   ```

---

## Train Your First Model

```powershell
# Activate environment
.\.venv\Scripts\Activate.ps1

# Run training (when you have data)
python -m src.signx_intel.ml.training.cost_predictor
```

Or use Jupyter:
```powershell
jupyter notebook notebooks/exploration.ipynb
```

---

## Docker Services

```powershell
# View running services
docker-compose ps

# View logs
docker-compose logs -f api

# Stop services
docker-compose down

# Restart services
docker-compose restart
```

---

## Troubleshooting

### Port Already in Use
```powershell
# Check what's using port 8000
netstat -ano | findstr :8000

# Kill the process (replace PID)
taskkill /PID <pid> /F
```

### Database Connection Error
```powershell
# Check PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres
```

### Import Errors
```powershell
# Ensure virtual environment is activated
.\.venv\Scripts\Activate.ps1

# Reinstall dependencies
pip install -r requirements.txt
```

---

## Next Steps

1. **Configure your environment** - Edit `.env` with production settings
2. **Import historical data** - Add your PDF cost summaries to `data/raw/`
3. **Train models** - Process data and train cost prediction models
4. **Integrate with SignX-Studio** - Use the API to get predictions
5. **Scale up** - Deploy to production with Docker

---

## Useful Commands

| Task | Command |
|------|---------|
| Start API | `.\scripts\start_api.ps1` |
| Run tests | `.\scripts\run_tests.ps1` |
| Process PDFs | `.\scripts\process_pdfs.ps1` |
| Start Docker | `docker-compose up -d` |
| Stop Docker | `docker-compose down` |
| View logs | `docker-compose logs -f` |
| Run migrations | `alembic upgrade head` |

---

## Getting Help

- 📖 Read the full README.md
- 🐛 Check logs: `docker-compose logs -f api`
- 🧪 Run tests: `.\scripts\run_tests.ps1`
- 📊 MLflow UI: http://localhost:5000
- 📝 API Docs: http://localhost:8000/api/v1/docs

---

**Ready to build intelligent cost predictions!** 🚀

