# SignX-Studio AI/ML Quick Start

Get GPU-accelerated cost prediction running in 30 minutes.

## Prerequisites

- ✅ NVIDIA GPU with 8GB+ VRAM (you have RTX 5070 Ti - perfect!)
- ✅ CUDA 12.1+ compatible drivers
- ✅ Python 3.11+
- ✅ Historical cost data in PDF format

## Step 1: Install CUDA & ML Stack (10 min)

```powershell
# Install CUDA Toolkit
winget install --id Nvidia.CUDA

# Create ML environment
conda env create -f environment-ml.yml
conda activate signx-ml

# Install PyTorch Geometric wheels
pip install torch-scatter torch-sparse torch-cluster torch-spline-conv `
  -f https://data.pyg.org/whl/torch-2.4.0+cu121.html

# Verify GPU detected
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

## Step 2: Prepare Your PDF Data (5 min)

```powershell
# Create data directory
mkdir -p data/pdfs/cost_summaries

# Copy your PDF cost summaries to:
# data/pdfs/cost_summaries/
# (Organize by year if desired)
```

## Step 3: Extract Training Data (5 min)

```powershell
python scripts/extract_pdfs.py `
  --input data/pdfs/cost_summaries `
  --output data/raw/extracted_costs.parquet `
  --verbose

# Review extraction report
code reports/extraction_report.json
```

Expected output:
```
✅ Extraction complete:
   Valid records: 250
   Failed extractions: 5

📊 Data Quality Report:
   Completeness: 92.5%
   Cost range: $4,250 - $28,900
```

## Step 4: Train Cost Model (10 min)

```powershell
python scripts/train_cost_model.py `
  --data data/raw/extracted_costs.parquet `
  --output models/cost/v1

# Watch GPU working (in another terminal)
nvidia-smi -l 1
```

Expected output:
```
🎯 Training model (GPU: True)...

📊 Training Results:
   Test MAE: $1,245.50
   Test MAPE: 11.2%
   Test R²: 0.887
   Training time: 8.3s

🎯 Top Features:
   1. sign_area_sqft          0.3521
   2. height_ft               0.2847
   3. pole_size               0.1693

✅ Model training complete!
```

## Step 5: Test Predictions (2 min)

```powershell
python scripts/test_ai_prediction.py
```

Output shows predictions for small/medium/large designs with confidence intervals.

## Step 6: Use in API (immediate)

Start the API server:
```powershell
cd services/api
uvicorn src.apex.api.main:app --reload
```

Test the AI endpoint:
```bash
curl -X POST http://localhost:8000/ai/predict-cost \
  -H "Content-Type: application/json" \
  -d '{
    "height_ft": 25,
    "sign_area_sqft": 80,
    "wind_speed_mph": 115,
    "exposure_category": "C",
    "pole_size": 8,
    "pole_type": "round_hss",
    "foundation_type": "direct_burial",
    "embedment_depth_ft": 8
  }'
```

Response:
```json
{
  "result": {
    "predicted_cost": 11250.50,
    "confidence_interval_90": [10100.25, 12450.75],
    "model_version": "1.0"
  },
  "confidence": 0.85
}
```

## Troubleshooting

### GPU Not Detected
```powershell
# Check CUDA
nvidia-smi

# Check PyTorch
python -c "import torch; print(torch.cuda.is_available())"

# Restart computer if just installed CUDA
```

### PDF Extraction Fails
- Verify PDFs are text-based (not scans)
- Check PDF template matches extraction patterns
- Review error records in reports

### Model Performance Poor
- Need 100+ training samples minimum
- Check data quality report for outliers
- Verify feature engineering makes sense

## Next Steps

1. **Improve data**: Add more historical PDFs
2. **Tune model**: Experiment with hyperparameters
3. **Add features**: Capture more cost drivers
4. **Deploy**: Integrate with estimating workflow
5. **Monitor**: Track prediction accuracy over time

## Cost Savings

With 16GB GPU (RTX 5070 Ti):
- Model training: 8-12s (vs 2-5 min on CPU)
- Batch predictions: <1s for 100 designs
- No cloud ML costs (runs 100% locally)

## Support

- Full docs: `docs/ai-ml-playbook.md`
- ML services: `services/ml/README.md`
- Issues: Check linter errors with `ruff check services/ml/`

