# SignX-Intel 🚀

**Super Intelligent Centralized Cost Database** for sign, structural, and construction estimating.

GPU-accelerated cost prediction pipeline using the latest 2025 ML stack.

---

## Features

- 📄 **PDF Ingestion**: Extract cost data from PDF summaries using pdfplumber + LangChain
- 🗄️ **Universal Cost Database**: PostgreSQL with flexible JSON schema for any project type
- 🤖 **GPU-Accelerated ML**: XGBoost + cuDF for 10-50x faster training
- 🔮 **Cost Predictions**: Real-time cost forecasting with SHAP explainability
- 🔗 **Multi-Tool Integration**: REST API for SignX-Studio, CRM, and other tools
- 📊 **MLflow Tracking**: Experiment tracking and model registry

---

## Tech Stack (November 2025)

| Component | Technology | Version |
|-----------|------------|---------|
| **API** | FastAPI | 0.110.0 |
| **Database** | PostgreSQL | 17 |
| **ML** | XGBoost + cuDF | 2.1.4 / 25.10 |
| **Storage** | Delta Lake | 0.19 |
| **MLOps** | MLflow + Prefect | 2.16 / 3.0 |
| **PDF** | pdfplumber + LangChain | Latest |

---

## Quick Start

### 1. Clone & Setup

```bash
cd SignX-Intel

# Create virtual environment
py -3.12 -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### 3. Start Services

```bash
# Start PostgreSQL, Redis, MinIO, MLflow
docker-compose up -d

# Verify services
docker-compose ps
```

### 4. Run Migrations

```bash
alembic upgrade head
```

### 5. Start API

```bash
uvicorn src.signx_intel.api.main:app --host 127.0.0.1 --port 8000 --reload
```

### 6. Verify

```bash
# Health check (PowerShell)
Invoke-WebRequest http://localhost:8000/health

# API docs
start http://localhost:8000/api/v1/docs

# MLflow UI
start http://localhost:5000
```

---

## Adding Your PDF Cost Summaries

1. Drop PDFs into `data/raw/`
2. Run ingestion pipeline:
```bash
python -m src.signx_intel.ingestion.pdf_parser
```
3. Extracted data appears in `data/processed/`

---

## Training Your First Model

```bash
python -m src.signx_intel.ml.training.cost_predictor
```

Models are versioned in MLflow and saved to `data/models/`.

---

## API Usage Examples

### Get Cost Prediction

```bash
curl -X POST http://localhost:8000/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{
    "drivers": {
      "sign_height_ft": 25,
      "sign_area_sqft": 120,
      "foundation_type": "drilled_pier",
      "wind_speed_mph": 130
    }
  }'
```

### Response

```json
{
  "predicted_cost": 12500.00,
  "confidence": 0.87,
  "cost_drivers": {
    "material": 0.45,
    "labor": 0.30,
    "foundation": 0.15,
    "other": 0.10
  }
}
```

---

## Development

### Run Tests

```bash
python -m pytest -v
```

### Code Formatting

```bash
black src/ tests/
ruff check src/ tests/
```

### Type Checking

```bash
mypy src/
```

---

## Integration with SignX-Studio

Add this to your SignX-Studio code:

```python
import httpx

async def get_cost_prediction(project_data: dict) -> float:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/v1/predict",
            json={"drivers": project_data}
        )
        return response.json()["predicted_cost"]
```

---

## Project Structure

```
SignX-Intel/
├── src/signx_intel/
│   ├── api/              # FastAPI routes & schemas
│   ├── ingestion/        # PDF parsing & validation
│   ├── storage/          # Database models & data lake
│   ├── ml/               # Training, inference, explainability
│   └── connectors/       # External integrations
├── data/
│   ├── raw/              # Input PDFs
│   ├── processed/        # Extracted data
│   └── models/           # Trained models
├── migrations/           # Alembic migrations
├── tests/                # Test suite
└── notebooks/            # Jupyter exploration
```

---

## Roadmap

- [x] Phase 1: Project scaffolding & Docker setup
- [ ] Phase 2: PDF ingestion + database schema
- [ ] Phase 3: Cost prediction ML pipeline
- [ ] Phase 4: SignX-Studio integration
- [ ] Phase 5: GNN structural optimization

---

## License

MIT

---

## Support

Questions? Open an issue or reach out!

