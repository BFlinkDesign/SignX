# ML Data Directory Structure

This directory contains training data, model artifacts, and quality reports for the SignX-Studio AI/ML pipeline.

## Directory Layout

```
data/
├── pdfs/                          # Source PDF files (you provide)
│   └── cost_summaries/            # PDF cost summaries from Eagle Sign
│       ├── 2020/
│       ├── 2021/
│       ├── 2022/
│       ├── 2023/
│       └── 2024/
├── raw/                           # Extracted raw data
│   ├── extracted_costs.parquet    # Primary dataset
│   └── extraction_errors.json     # Failed extractions
├── curated/                       # Cleaned, validated datasets
│   ├── latest/
│   │   ├── train.parquet
│   │   ├── test.parquet
│   │   └── manifest.json
│   └── v1.0/                      # Versioned snapshots
│       ├── train.parquet
│       ├── test.parquet
│       └── manifest.json
└── samples/                       # Sample/demo data
    └── demo_costs.parquet

models/
├── cost/                          # Cost prediction models
│   ├── v1/
│   │   ├── model.pkl
│   │   ├── metadata.json
│   │   └── feature_importances.csv
│   └── latest -> v1/              # Symlink to latest
└── structural/                    # Future GNN models
    └── gnn_v1/

reports/
├── extraction_report.json         # Data quality after extraction
├── training_report.json           # Model training metrics
└── validation/                    # Ongoing validation reports
    └── 2025-11-02_validation.json
```

## Data Schema

See `services/ml/data_schema.py` for complete field definitions.

Key fields:
- **Project specs**: height, area, wind speed, exposure
- **Structural design**: pole size/type, foundation type/depth
- **Costs**: material, labor, engineering, total
- **Metadata**: dates, location, PE approval status

## Adding Your PDFs

1. Place PDF cost summaries in `data/pdfs/cost_summaries/`
2. Organize by year if desired (optional)
3. Run extraction:
   ```bash
   python scripts/extract_pdfs.py \
     --input data/pdfs/cost_summaries \
     --output data/raw/extracted_costs.parquet
   ```

## Data Quality Requirements

For good model performance:
- **Minimum**: 50-100 historical projects
- **Good**: 200-500 projects
- **Excellent**: 1,000+ projects

Required fields:
- Total cost (must have)
- Height and sign area (must have)
- Wind speed (must have)
- Pole size (must have)

Nice-to-have fields:
- Material/labor breakdown
- Foundation details
- Project dates
- Location data

## Privacy & Security

- All cost data stays local (not uploaded to cloud)
- Models trained on-premises with your GPU
- No external API calls for predictions
- Data can be encrypted at rest if needed

