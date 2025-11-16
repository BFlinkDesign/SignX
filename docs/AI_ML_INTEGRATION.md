# AI/ML Integration with SignX-Studio

This document explains how the AI/ML cost prediction system integrates with the core SignX-Studio platform.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     SignX-Studio API                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  FastAPI Routes                                       │  │
│  │  • /projects (CRUD)                                   │  │
│  │  │  • /ai/predict-cost (ML predictions) ←── NEW      │  │
│  │  • /signage/* (calculations)                          │  │
│  │  • /ai/model-info                        ←── NEW      │  │
│  └───────────────┬──────────────────────────────────────┘  │
│                  │                                           │
│  ┌───────────────┴─────────────┬──────────────────────┐    │
│  │  Domain Services             │   ML Services        │    │
│  │  • signage/solvers.py        │   • cost_model.py    │    │
│  │  • signage/asce7_wind.py     │   • pdf_extractor.py │    │
│  │  • signage/single_pole.py    │   • structure_graph  │    │
│  └──────────────────────────────┴──────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
           ┌──────────────────────────────┐
           │  Data Layer                   │
           │  • PostgreSQL (projects)      │
           │  • Parquet (training data)    │
           │  • MLflow (experiments)       │
           │  • MinIO (model artifacts)    │
           └──────────────────────────────┘
```

## Integration Points

### 1. Project Workflow Enhancement

When a user creates/edits a project:

1. **Design Entry** → Core SignX-Studio captures specs
2. **Calculation** → Deterministic solvers run (wind, pole, foundation)
3. **AI Prediction** → ML model estimates cost with confidence intervals
4. **PE Review** → Engineer reviews both calculations and cost estimate
5. **Approval** → Project marked complete, data flows to training set

### 2. Data Flow

```
PDF Cost Summaries (historical)
        ↓
  [PDF Extractor]
        ↓
  Structured Data (Parquet)
        ↓
  [Data Validator]
        ↓
  Training Dataset
        ↓
  [XGBoost GPU Training]
        ↓
  Trained Model (versioned)
        ↓
  [FastAPI Endpoint]
        ↓
  Real-time Predictions
```

### 3. API Integration

The AI endpoints are exposed alongside existing routes:

```python
# services/api/src/apex/api/main.py
app.include_router(projects_router, tags=["projects"])
app.include_router(ai_router, tags=["ai-ml"])  # NEW
```

Clients can call:
```bash
POST /ai/predict-cost
```

With the same authentication and envelope format as other endpoints.

### 4. Envelope Consistency

AI predictions return the standard APEX envelope:

```json
{
  "result": {
    "predicted_cost": 11250.50,
    "confidence_interval_90": [10100.25, 12450.75],
    ...
  },
  "assumptions": [
    "Based on historical Eagle Sign Company project data",
    "Model trained on 850 projects"
  ],
  "confidence": 0.85,
  "trace": {
    "data": {
      "inputs": {...},
      "outputs": {...}
    },
    "code_version": {...},
    "model_config": {
      "provider": "xgboost",
      "model": "cost_predictor_v1",
      ...
    }
  }
}
```

## Separation of Concerns

### Core Calculations (Deterministic)
- Wind loads (ASCE 7-22)
- Pole sizing (AISC 360-22)
- Foundation depth (IBC 2024)
- **Always runs** - Required for PE stamp

### AI Predictions (Probabilistic)
- Cost estimation
- Design optimization suggestions
- Feature importance insights
- **Optional enhancement** - Speeds up quoting

The AI layer **never replaces** engineering calculations—it complements them.

## Deployment Scenarios

### Scenario 1: Core Only (No AI)
- Deploy without ML dependencies
- Skip model training
- AI endpoints return 503 (service unavailable)
- System functions normally

### Scenario 2: Full Stack (with AI)
- Install ML requirements
- Train models on historical data
- AI endpoints active
- Enhanced cost prediction available

### Scenario 3: Hybrid (Optional AI)
- Deploy with ML dependencies
- Load models if available
- Graceful degradation if models missing
- Log warnings but don't fail

## Security Considerations

### Data Privacy
- All training data stays on-premises
- No external ML API calls
- Models trained with your GPU locally
- Predictions computed locally

### Model Versioning
- Models stored in `models/cost/v{X}/`
- Metadata includes training date, samples, metrics
- Can roll back to previous versions
- Audit trail via MLflow

### Rate Limiting
AI endpoints use the same rate limiting as other routes:
- 100 requests/minute per IP (default)
- Configurable via `APEX_RATE_LIMIT_PER_MIN`

## Testing Strategy

### Unit Tests
```bash
pytest services/ml/tests/ -v
```

Tests cover:
- PDF extraction logic
- Feature engineering
- Model training/prediction
- Data validation

### Integration Tests
```bash
pytest services/api/tests/integration/test_ai_endpoints.py
```

Tests verify:
- API request/response format
- Envelope consistency
- Error handling
- Rate limiting

### End-to-End Test
```bash
python scripts/test_ai_prediction.py
```

Validates entire pipeline with realistic scenarios.

## Performance Monitoring

### Metrics to Track

1. **Prediction Accuracy**
   - Compare predictions to actual costs
   - Track MAE/MAPE over time
   - Alert if accuracy degrades

2. **Model Drift**
   - Monitor feature distributions
   - Detect when retraining is needed
   - Log warnings for out-of-distribution inputs

3. **API Performance**
   - Prediction latency (<100ms target)
   - GPU utilization during training
   - Error rates

### Retraining Triggers

Retrain the model when:
- 100+ new completed projects added
- Prediction accuracy drops >5%
- New cost drivers identified
- Quarterly schedule (minimum)

## Future Enhancements

### Short Term (1-3 months)
- Material price forecasting
- Lead time prediction
- Bid win probability

### Medium Term (3-6 months)
- Structural GNN for stress prediction
- Design optimization via RL
- Multi-task learning (cost + schedule)

### Long Term (6-12 months)
- Transfer learning across sign types
- Explainable AI for PE review
- Active learning for edge cases

---

**Integration Status:** ✅ Complete  
**Dependencies:** Optional (graceful degradation)  
**Performance Impact:** Minimal (<10ms overhead)  
**Maintenance:** Quarterly retraining recommended

