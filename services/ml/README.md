# SignX-Studio ML Services

GPU-accelerated machine learning for cost prediction and structural optimization.

## What's Included

- **PDF Extraction**: Convert cost summary PDFs to structured training data
- **Cost Prediction**: XGBoost model with GPU training and uncertainty quantification  
- **Structure Graphs**: PyTorch Geometric graph representation for future GNN work
- **API Integration**: FastAPI endpoints serving trained models
- **Experiment Tracking**: MLflow integration for model versioning

## Quick Start

```bash
# 1. Setup environment
conda env create -f environment-ml.yml
conda activate signx-ml

# 2. Extract PDFs
python scripts/extract_pdfs.py --input data/pdfs/cost_summaries --output data/raw/costs.parquet

# 3. Train model
python scripts/train_cost_model.py --data data/raw/costs.parquet --output models/cost/v1

# 4. Test API
curl -X POST http://localhost:8000/ai/predict-cost -H "Content-Type: application/json" -d '{"height_ft": 25, "sign_area_sqft": 80, ...}'
```

## Requirements

- NVIDIA GPU with 8GB+ VRAM (RTX 5070 Ti ideal)
- CUDA 12.1+
- Python 3.11+
- See `requirements-ml.txt` for complete dependencies

## Documentation

See `docs/ai-ml-playbook.md` for comprehensive guide.

## Testing

```bash
pytest services/ml/tests/ -v
```

