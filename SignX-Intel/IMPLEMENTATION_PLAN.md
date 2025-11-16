# SignX-Intel Implementation Plan

> **Philosophy**: Ship value incrementally. Measure relentlessly. Compound gains daily.

**Last Updated**: November 3, 2025  
**Planning Horizon**: 90 days (MVP) → 180 days (Full Platform)  
**Team**: Autonomous AI Agent + Brady (validation/domain expertise)

---

## Executive Summary

### Business Objectives

| Objective | Current State | Target State | Timeline | Impact |
|-----------|---------------|--------------|----------|--------|
| **Cost Estimation Accuracy** | Manual (±25% error) | ML-powered (±15% error) | 60 days | Save $100k/year in underestimates |
| **Estimation Speed** | 30 min/project | 2 min/project | 30 days | 93% time reduction = 20 hrs/week saved |
| **Historical Data Utilization** | 0% (PDFs in filing cabinet) | 100% (searchable database) | 45 days | Unlock 20 years of intelligence |
| **Predictive Insights** | None | Real-time anomaly detection | 75 days | Catch bad bids before they cost money |

**ROI Projection**: $150k annual savings, 520 hours/year time savings, payback in < 6 months

---

## Implementation Strategy

### The 90-Day MVP Approach

```
Week 1-2:   Foundation (infrastructure, data ingestion)
Week 3-4:   First Intelligence (basic ML model)
Week 5-6:   Integration (SignX-Studio connector)
Week 7-8:   Refinement (model improvement, UX)
Week 9-10:  Production (monitoring, alerts, handoff)
Week 11-12: Optimization (based on real usage)
```

### Value Delivery Milestones

```
Day 14:  First cost prediction (even if simple)
Day 30:  50 historical projects in database
Day 45:  ML model trained on real data
Day 60:  SignX-Studio integration live
Day 75:  10 predictions/day in production
Day 90:  Autonomous operation (self-monitoring, self-healing)
```

---

## Phase 1: Foundation (Days 1-14)

**Goal**: Infrastructure running, first data flowing

### Week 1: Infrastructure & Data Pipeline

#### Task 1.1: Environment Setup
**Complexity**: S (Small)  
**Priority**: P0 (Must have)  
**Owner**: Agent  
**Dependencies**: None

**Deliverables**:
- [x] Virtual environment with Python 3.12
- [x] Docker Compose running (PostgreSQL, Redis, MinIO)
- [x] Database initialized with migrations
- [ ] Basic API responding to health checks

**Success Metrics**:
- ✅ `docker-compose ps` shows all services healthy
- ✅ `curl localhost:8000/health` returns 200 OK
- ✅ Database accepts connections

**Code Checkpoint**:
```bash
# Verify infrastructure
docker-compose up -d
docker-compose ps  # All green
curl http://localhost:8000/health  # {"status":"healthy"}
psql -h localhost -U signx_intel -d cost_intelligence -c "SELECT 1;"  # Works
```

---

#### Task 1.2: PDF Ingestion Pipeline
**Complexity**: M (Medium)  
**Priority**: P0 (Must have)  
**Owner**: Agent  
**Dependencies**: Task 1.1

**Context**: You have PDF cost summaries in an unknown format. Need to extract structured data.

**Feature Engineering**:
1. **PDF Parsing**
   - Parse tables (tabula-py, pdfplumber)
   - Extract key-value pairs (regex patterns)
   - Handle variations in layout

2. **Data Extraction Patterns**
   ```python
   # Patterns to extract
   patterns = {
       "total_cost": r"total[:\s]+\$?([\d,]+\.?\d*)",
       "labor_cost": r"labor[:\s]+\$?([\d,]+\.?\d*)",
       "material_cost": r"material[s]?[:\s]+\$?([\d,]+\.?\d*)",
       "sign_height": r"height[:\s]+([\d.]+)\s*(ft|feet)",
       "sign_area": r"area[:\s]+([\d.]+)\s*sq\.?\s*ft",
       "wind_speed": r"wind[:\s]+([\d]+)\s*mph",
       "foundation": r"foundation[:\s]+(drilled pier|spread footing|mono column)"
   }
   ```

3. **Validation Rules**
   ```python
   def validate_extracted_data(data: dict) -> tuple[bool, list[str]]:
       errors = []
       
       # Must have total cost
       if not data.get("total_cost"):
           errors.append("Missing total_cost")
       
       # Cost must be positive
       if data.get("total_cost", 0) <= 0:
           errors.append("Invalid total_cost")
       
       # If breakdown exists, should sum to total (±5%)
       breakdown = sum([
           data.get("labor_cost", 0),
           data.get("material_cost", 0),
           data.get("equipment_cost", 0)
       ])
       if breakdown > 0:
           if abs(breakdown - data["total_cost"]) / data["total_cost"] > 0.05:
               errors.append("Cost breakdown doesn't match total")
       
       return len(errors) == 0, errors
   ```

**Deliverables**:
- [ ] `pdf_parser.py` extracts text and tables
- [ ] `validators.py` validates extracted data
- [ ] Process 10 sample PDFs successfully
- [ ] Store extracted data in PostgreSQL

**Success Metrics**:
- ✅ 80%+ extraction accuracy (manual audit of 10 samples)
- ✅ 0 crashes on malformed PDFs
- ✅ Processing time < 30 seconds per PDF
- ✅ Data passes validation (95% of fields)

**Implementation Approach**:
```python
# src/signx_intel/ingestion/pdf_parser.py

class CostPDFParser:
    def parse_pdf(self, pdf_path: Path) -> CostData:
        """Extract cost data from PDF with robust error handling."""
        
        # 1. Extract raw text
        with pdfplumber.open(pdf_path) as pdf:
            text = "\n".join(page.extract_text() for page in pdf.pages)
            tables = [table for page in pdf.pages for table in page.extract_tables()]
        
        # 2. Extract structured data
        data = self._extract_patterns(text)
        
        # 3. Extract from tables
        if tables:
            table_data = self._extract_from_tables(tables)
            data.update(table_data)
        
        # 4. Validate
        is_valid, errors = validate_extracted_data(data)
        if not is_valid:
            logger.warning("validation_failed", errors=errors, file=pdf_path.name)
        
        # 5. Enrich with metadata
        data["source_file"] = pdf_path.name
        data["extracted_at"] = datetime.utcnow()
        data["validation_status"] = "passed" if is_valid else "failed"
        data["validation_errors"] = errors
        
        return CostData(**data)
```

**Risk Mitigation**:
- **Risk**: PDF format varies → **Mitigation**: Sample 10 PDFs first, build patterns, iterate
- **Risk**: Extraction accuracy low → **Mitigation**: Manual audit feedback loop, improve patterns
- **Risk**: Some PDFs are scanned images → **Mitigation**: Add OCR fallback (pytesseract)

---

#### Task 1.3: Database Schema & Seeding
**Complexity**: S (Small)  
**Priority**: P0 (Must have)  
**Owner**: Agent  
**Dependencies**: Task 1.1

**Deliverables**:
- [x] Database schema created (already done in scaffolding)
- [ ] Sample data seeded for testing
- [ ] Queries validated

**Success Metrics**:
- ✅ Can insert cost records
- ✅ Can query by drivers (JSONB)
- ✅ Foreign key constraints work

**Implementation**:
```sql
-- Verify schema
\dt cost_records
\d cost_records

-- Insert test record
INSERT INTO projects (name, source, status)
VALUES ('Test Project', 'manual', 'draft')
RETURNING id;

INSERT INTO cost_records (
    project_id,
    total_cost,
    labor_cost,
    material_cost,
    drivers
) VALUES (
    '<project-id>',
    12500.00,
    4500.00,
    6800.00,
    '{"sign_height_ft": 25, "sign_area_sqft": 120, "foundation_type": "drilled_pier"}'::jsonb
);

-- Query by driver
SELECT * FROM cost_records 
WHERE drivers->>'foundation_type' = 'drilled_pier';
```

---

### Week 2: API & Basic Prediction

#### Task 1.4: Core API Endpoints
**Complexity**: M (Medium)  
**Priority**: P0 (Must have)  
**Owner**: Agent  
**Dependencies**: Task 1.3

**Deliverables**:
- [ ] POST `/api/v1/projects` - Create project
- [ ] GET `/api/v1/projects` - List projects
- [ ] POST `/api/v1/predict` - Cost prediction (heuristic)
- [ ] GET `/api/v1/insights/summary` - Basic stats

**Success Metrics**:
- ✅ All endpoints return 200 for valid input
- ✅ 400 for invalid input (with clear errors)
- ✅ OpenAPI docs auto-generated
- ✅ Response time p95 < 200ms

**Implementation Priority**:
1. Health endpoints (already done)
2. Projects CRUD (already scaffolded)
3. **Prediction endpoint** (needs implementation)
4. Insights endpoint (simple SQL queries)

**Key Implementation: Prediction Endpoint**
```python
# src/signx_intel/api/routes/predictions.py

@router.post("/predict", response_model=PredictionResponse)
async def predict_cost(
    request: PredictionRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Predict project cost.
    
    ## Phase 1 (Heuristic)
    Simple rule-based estimation until ML model trained.
    
    ## Phase 2 (ML - Week 4+)
    XGBoost model trained on historical data.
    """
    
    # Phase 1: Use heuristic predictor
    predictor = HeuristicPredictor()
    prediction = predictor.predict(request.drivers)
    
    # Store prediction
    await store_prediction(db, prediction, request)
    
    # Return
    return PredictionResponse(
        predicted_cost=prediction.cost,
        confidence_score=prediction.confidence,
        cost_breakdown=prediction.breakdown,
        method="heuristic"
    )
```

**Heuristic Predictor (Domain Knowledge)**:
```python
class HeuristicPredictor:
    """Rule-based predictor using 20 years domain expertise."""
    
    def predict(self, drivers: dict) -> Prediction:
        """Predict cost using Eagle Sign's historical rules."""
        
        # Base cost
        base = 1000.00
        
        # Area-based (primary driver)
        if "sign_area_sqft" in drivers:
            # $50-$100/sqft depending on complexity
            area = drivers["sign_area_sqft"]
            cost_per_sqft = self._calculate_cost_per_sqft(drivers)
            base += area * cost_per_sqft
        
        # Height multiplier (harder to install)
        if "sign_height_ft" in drivers:
            height = drivers["sign_height_ft"]
            if height > 30:
                base *= 1.3  # High installations
            elif height > 20:
                base *= 1.15
        
        # Foundation type
        foundation_costs = {
            "drilled_pier": 1.5,
            "spread_footing": 1.2,
            "mono_column": 1.0
        }
        base *= foundation_costs.get(drivers.get("foundation_type"), 1.0)
        
        # Wind loading (Iowa specific)
        if "wind_speed_mph" in drivers:
            wind = drivers["wind_speed_mph"]
            if wind > 140:
                base *= 1.25  # Extra structural
            elif wind > 120:
                base *= 1.15
        
        # Material type
        material_multipliers = {
            "aluminum": 1.0,
            "acm": 1.2,
            "steel": 1.4,
            "hdpe": 0.9
        }
        base *= material_multipliers.get(drivers.get("material"), 1.0)
        
        # Breakdown (typical ratios)
        return Prediction(
            cost=Decimal(base),
            confidence=0.6,  # Lower for heuristic
            breakdown={
                "material": base * 0.55,
                "labor": base * 0.35,
                "overhead": base * 0.10
            },
            drivers_used=list(drivers.keys())
        )
    
    def _calculate_cost_per_sqft(self, drivers: dict) -> float:
        """Calculate $/sqft based on complexity factors."""
        base_rate = 50.0
        
        # Complexity factors
        if drivers.get("has_lighting"):
            base_rate += 15.0
        if drivers.get("is_double_faced"):
            base_rate += 20.0
        if drivers.get("custom_paint"):
            base_rate += 10.0
        
        return base_rate
```

**Why Start with Heuristic?**
1. ✅ Delivers value immediately (Day 14)
2. ✅ Validates API & integration
3. ✅ Establishes baseline for ML comparison
4. ✅ Provides predictions while collecting training data

---

#### Task 1.5: Monitoring & Observability Setup
**Complexity**: S (Small)  
**Priority**: P1 (Should have)  
**Owner**: Agent  
**Dependencies**: Task 1.4

**Deliverables**:
- [ ] Prometheus metrics collection
- [ ] Structured logging (structlog)
- [ ] Basic Grafana dashboard

**Success Metrics**:
- ✅ Prometheus scraping metrics
- ✅ Logs are structured JSON
- ✅ Dashboard shows API requests, latency, errors

**Quick Win Implementation**:
```python
# Add to main.py
from prometheus_client import make_asgi_app

# Mount Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Middleware for request tracking
@app.middleware("http")
async def track_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    
    # Log
    logger.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=duration * 1000
    )
    
    # Metrics (already instrumented in code)
    
    return response
```

---

### Phase 1 Exit Criteria

**Must Have** (Block next phase):
- [x] Infrastructure running (Docker Compose)
- [ ] API accepting requests
- [ ] 10+ PDFs processed into database
- [ ] First prediction endpoint working (heuristic)
- [ ] Basic monitoring (Prometheus + logs)

**Success Metrics**:
- ✅ Can process 1 PDF in < 30 seconds
- ✅ Can serve 1 prediction in < 200ms
- ✅ 0 crashes in 24-hour stability test
- ✅ Data extraction accuracy > 80%

**Deliverable**: Demo video showing:
1. Upload PDF → Extracted data in database
2. Call `/api/v1/predict` → Get cost estimate
3. Grafana dashboard showing metrics

---

## Phase 2: First Intelligence (Days 15-30)

**Goal**: ML model trained on real data, accuracy better than heuristic

### Week 3: Data Collection & Feature Engineering

#### Task 2.1: Batch PDF Processing
**Complexity**: S (Small)  
**Priority**: P0 (Must have)  
**Owner**: Agent  
**Dependencies**: Phase 1 complete

**Objective**: Process all available historical PDFs

**Deliverables**:
- [ ] Script to batch process PDFs
- [ ] Process 50+ historical projects
- [ ] Data quality audit report

**Success Metrics**:
- ✅ 50+ projects in database
- ✅ Data completeness > 90%
- ✅ Manual audit accuracy > 85%

**Implementation**:
```python
# scripts/batch_process_pdfs.py

async def batch_process_pdfs(pdf_dir: Path):
    """Process all PDFs in directory."""
    
    parser = CostPDFParser()
    pdf_files = list(pdf_dir.glob("*.pdf"))
    
    logger.info("batch_processing_started", file_count=len(pdf_files))
    
    results = {
        "processed": 0,
        "failed": 0,
        "validation_errors": []
    }
    
    for pdf_file in pdf_files:
        try:
            # Parse
            cost_data = parser.parse_pdf(pdf_file)
            
            # Validate
            is_valid, errors = validate_extracted_data(cost_data)
            
            if is_valid:
                # Store in database
                await store_cost_record(cost_data)
                results["processed"] += 1
            else:
                # Quarantine
                await quarantine_record(cost_data, errors)
                results["failed"] += 1
                results["validation_errors"].extend(errors)
        
        except Exception as e:
            logger.error("pdf_processing_failed", file=pdf_file.name, error=str(e))
            results["failed"] += 1
    
    logger.info("batch_processing_complete", **results)
    
    # Generate audit report
    generate_audit_report(results)
```

**Audit Process**:
1. Randomly select 10 processed records
2. Manually verify against original PDFs
3. Calculate accuracy: (correct_fields / total_fields) * 100
4. Identify common extraction errors
5. Improve patterns based on findings

---

#### Task 2.2: Feature Engineering Pipeline
**Complexity**: M (Medium)  
**Priority**: P0 (Must have)  
**Owner**: Agent  
**Dependencies**: Task 2.1

**Objective**: Transform raw drivers into ML-ready features

**Feature Engineering Strategy**:

```python
# src/signx_intel/ml/features/engineering.py

class CostFeatureEngineer:
    """Transform raw cost data into ML features."""
    
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create features for cost prediction."""
        
        # 1. Extract nested JSON drivers
        df = self._extract_drivers(df)
        
        # 2. Create interaction features
        df["area_height_product"] = (
            df["sign_area_sqft"] * df["sign_height_ft"]
        )
        df["wind_load_factor"] = (
            df["wind_speed_mph"] * df["sign_area_sqft"]
        )
        
        # 3. Complexity score (domain knowledge)
        df["complexity_score"] = self._calculate_complexity(df)
        
        # 4. Encode categoricals
        df = pd.get_dummies(df, columns=[
            "material",
            "foundation_type",
            "finish"
        ])
        
        # 5. Scale numeric features
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        df[numeric_cols] = StandardScaler().fit_transform(df[numeric_cols])
        
        # 6. Handle missing values
        df = df.fillna(df.median())
        
        return df
    
    def _calculate_complexity(self, df: pd.DataFrame) -> pd.Series:
        """Calculate complexity score (1-10)."""
        
        complexity = pd.Series(5.0, index=df.index)  # Base
        
        # Height complexity
        complexity += df["sign_height_ft"].apply(
            lambda h: 0 if h < 20 else 2 if h < 30 else 4
        )
        
        # Feature complexity
        if "has_lighting" in df:
            complexity += df["has_lighting"].fillna(False) * 2
        if "is_double_faced" in df:
            complexity += df["is_double_faced"].fillna(False) * 1.5
        if "custom_engineering" in df:
            complexity += df["custom_engineering"].fillna(False) * 3
        
        return complexity.clip(1, 10)
```

**Feature Importance Analysis**:
```python
# After feature engineering, analyze which features matter
def analyze_feature_importance(X: pd.DataFrame, y: pd.Series):
    """Quick feature importance check."""
    
    # Correlation with target
    correlations = X.corrwith(y).abs().sort_values(ascending=False)
    
    # Random forest quick check
    rf = RandomForestRegressor(n_estimators=50, random_state=42)
    rf.fit(X, y)
    importance = pd.Series(rf.feature_importances_, index=X.columns)
    
    return {
        "correlations": correlations.head(10),
        "rf_importance": importance.sort_values(ascending=False).head(10)
    }
```

---

### Week 4: ML Model Training

#### Task 2.3: Train First XGBoost Model
**Complexity**: M (Medium)  
**Priority**: P0 (Must have)  
**Owner**: Agent  
**Dependencies**: Task 2.2

**Objective**: Train model that beats heuristic baseline

**Training Strategy**:

```python
# src/signx_intel/ml/training/cost_predictor.py

async def train_production_model():
    """Train model on all available data."""
    
    # 1. Load data
    df = await load_training_data()
    logger.info("training_data_loaded", records=len(df))
    
    # 2. Feature engineering
    fe = CostFeatureEngineer()
    X = fe.engineer_features(df)
    y = df["total_cost"]
    
    # 3. Train/test split (temporal)
    # Use last 20% chronologically as test set
    split_idx = int(len(df) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    logger.info("data_split", train=len(X_train), test=len(X_test))
    
    # 4. Train XGBoost
    with mlflow.start_run(run_name=f"cost_predictor_{datetime.now():%Y%m%d}"):
        # Hyperparameters
        params = {
            "n_estimators": 100,
            "max_depth": 6,
            "learning_rate": 0.1,
            "tree_method": "hist",  # Use gpu_hist if GPU available
            "random_state": 42
        }
        mlflow.log_params(params)
        
        # Train
        model = xgb.XGBRegressor(**params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            early_stopping_rounds=10,
            verbose=True
        )
        
        # 5. Evaluate
        y_pred = model.predict(X_test)
        metrics = {
            "mae": mean_absolute_error(y_test, y_pred),
            "rmse": np.sqrt(mean_squared_error(y_test, y_pred)),
            "r2": r2_score(y_test, y_pred),
            "mape": mean_absolute_percentage_error(y_test, y_pred) * 100
        }
        mlflow.log_metrics(metrics)
        
        logger.info("model_trained", **metrics)
        
        # 6. SHAP explainability
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_test)
        
        # Plot feature importance
        shap.summary_plot(shap_values, X_test, show=False)
        plt.savefig("shap_summary.png")
        mlflow.log_artifact("shap_summary.png")
        
        # 7. Save model
        mlflow.sklearn.log_model(model, "model")
        
        # 8. Save feature engineer
        joblib.dump(fe, "feature_engineer.joblib")
        mlflow.log_artifact("feature_engineer.joblib")
    
    return model, metrics
```

**Success Criteria** (compared to heuristic):
- ✅ MAPE < 15% (vs heuristic ~20%)
- ✅ R² > 0.80
- ✅ No systematic bias (balanced over/under prediction)
- ✅ Inference time < 100ms

**If Model Underperforms**:
```python
# Debugging checklist
def debug_model_performance(model, X_test, y_test):
    """Analyze why model underperforms."""
    
    y_pred = model.predict(X_test)
    errors = np.abs(y_test - y_pred) / y_test
    
    # 1. Find high-error cases
    high_error_idx = errors > 0.3  # >30% error
    high_error_cases = X_test[high_error_idx]
    
    print(f"High error cases: {high_error_idx.sum()}")
    
    # 2. Look for patterns
    # - Specific material types?
    # - Large projects?
    # - Unusual combinations?
    
    # 3. Check for data issues
    # - Missing values?
    # - Outliers?
    # - Data quality problems?
    
    # 4. Try different approaches
    # - More features?
    # - Different model (LightGBM)?
    # - Ensemble?
    
    return high_error_cases
```

---

#### Task 2.4: Model Deployment
**Complexity**: S (Small)  
**Priority**: P0 (Must have)  
**Owner**: Agent  
**Dependencies**: Task 2.3

**Objective**: Replace heuristic with ML model in production

**Deployment Strategy**:
```python
# src/signx_intel/ml/inference/predictor.py

class ProductionPredictor:
    """Production inference with fallback."""
    
    def __init__(self):
        self.ml_predictor = None
        self.heuristic_predictor = HeuristicPredictor()
        self.load_ml_model()
    
    def load_ml_model(self):
        """Load ML model if available."""
        try:
            self.ml_predictor = CostPredictor()
            self.ml_predictor.load("cost_predictor_v1")
            logger.info("ml_model_loaded", version="v1")
        except FileNotFoundError:
            logger.warning("ml_model_not_found", fallback="heuristic")
    
    async def predict(self, spec: SignSpec) -> CostPrediction:
        """Predict with ML, fallback to heuristic."""
        
        if self.ml_predictor:
            try:
                prediction = await self.ml_predictor.predict(spec)
                
                # Only use if high confidence
                if prediction.confidence >= 0.7:
                    prediction.method = "ml_model"
                    return prediction
                else:
                    logger.warning("low_confidence_prediction",
                                  confidence=prediction.confidence)
            
            except Exception as e:
                logger.error("ml_prediction_failed", error=str(e))
        
        # Fallback to heuristic
        prediction = self.heuristic_predictor.predict(spec.drivers)
        prediction.method = "heuristic_fallback"
        return prediction
```

**A/B Testing Setup** (Optional but Recommended):
```python
class ABTestPredictor:
    """A/B test ML vs Heuristic."""
    
    def __init__(self, ml_traffic_pct: float = 0.5):
        self.ml_predictor = CostPredictor()
        self.heuristic_predictor = HeuristicPredictor()
        self.ml_traffic_pct = ml_traffic_pct
    
    async def predict(self, spec: SignSpec, user_id: str) -> CostPrediction:
        """Route traffic between ML and heuristic."""
        
        # Hash-based routing (consistent per user)
        user_hash = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
        use_ml = (user_hash % 100) < (self.ml_traffic_pct * 100)
        
        if use_ml:
            prediction = await self.ml_predictor.predict(spec)
            prediction.method = "ml_model_ab"
        else:
            prediction = self.heuristic_predictor.predict(spec.drivers)
            prediction.method = "heuristic_ab"
        
        # Log for analysis
        await log_ab_test_result(user_id, prediction)
        
        return prediction
```

---

### Phase 2 Exit Criteria

**Must Have**:
- [ ] ML model trained (MAPE < 15%)
- [ ] Model deployed to production
- [ ] Model performs better than heuristic
- [ ] SHAP explainability working

**Success Metrics**:
- ✅ MAPE < 15% on test set
- ✅ R² > 0.80
- ✅ Inference < 100ms p95
- ✅ 0 prediction crashes in 1000 requests

**Deliverable**: Model performance report showing:
- Baseline (heuristic): MAPE 20%, R² 0.65
- ML model: MAPE 12%, R² 0.87
- Improvement: 40% better accuracy

---

## Phase 3: Integration (Days 31-45)

**Goal**: SignX-Studio using SignX-Intel for real estimates

### Week 5: SignX-Studio Connector

#### Task 3.1: Build SignX-Studio Connector
**Complexity**: M (Medium)  
**Priority**: P0 (Must have)  
**Owner**: Agent  
**Dependencies**: Phase 2 complete

**Objective**: Bidirectional sync with SignX-Studio

**Implementation**:
```python
# src/signx_intel/connectors/signx_studio.py

class SignXStudioConnector:
    """Integrate with SignX-Studio."""
    
    def __init__(self, base_url: str, api_key: str):
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={"X-API-Key": api_key},
            timeout=30.0
        )
    
    async def fetch_project(self, project_id: str) -> Project:
        """Fetch project from SignX-Studio."""
        response = await self.client.get(f"/api/projects/{project_id}")
        response.raise_for_status()
        return Project.parse_obj(response.json())
    
    async def push_cost_estimate(
        self,
        project_id: str,
        estimate: CostPrediction
    ):
        """Push cost estimate back to SignX-Studio."""
        await self.client.post(
            f"/api/projects/{project_id}/cost-estimate",
            json={
                "estimated_cost": float(estimate.cost),
                "confidence": estimate.confidence,
                "breakdown": estimate.cost_breakdown,
                "source": "signx_intel_ml",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def sync_completed_projects(
        self,
        since: datetime
    ) -> list[Project]:
        """Pull completed projects for training data."""
        response = await self.client.get(
            "/api/projects",
            params={
                "status": "completed",
                "updated_since": since.isoformat()
            }
        )
        return [Project.parse_obj(p) for p in response.json()]
```

**Integration Flow**:
```
1. SignX-Studio creates project
2. SignX-Studio calls SignX-Intel /api/v1/predict
3. SignX-Intel returns cost estimate
4. SignX-Studio displays estimate to user
5. User accepts/modifies estimate
6. Project completed → SignX-Studio sends actual cost
7. SignX-Intel stores for model retraining
```

---

#### Task 3.2: API Client Library (Python)
**Complexity**: S (Small)  
**Priority**: P1 (Should have)  
**Owner**: Agent  
**Dependencies**: Task 3.1

**Objective**: Make it easy for SignX-Studio to call SignX-Intel

**Implementation**:
```python
# signx_intel_client.py (distribute to SignX-Studio)

class SignXIntelClient:
    """Client library for SignX-Intel API."""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"}
        )
    
    async def predict_cost(
        self,
        sign_height_ft: float,
        sign_area_sqft: float,
        foundation_type: str,
        **kwargs
    ) -> CostPrediction:
        """Get cost prediction."""
        
        drivers = {
            "sign_height_ft": sign_height_ft,
            "sign_area_sqft": sign_area_sqft,
            "foundation_type": foundation_type,
            **kwargs
        }
        
        response = await self.client.post(
            "/api/v1/predict",
            json={"drivers": drivers}
        )
        response.raise_for_status()
        
        return CostPrediction(**response.json())
    
    async def close(self):
        await self.client.aclose()

# Usage in SignX-Studio
client = SignXIntelClient(
    base_url="http://localhost:8000",
    api_key=os.getenv("SIGNX_INTEL_API_KEY")
)

estimate = await client.predict_cost(
    sign_height_ft=25,
    sign_area_sqft=120,
    foundation_type="drilled_pier",
    wind_speed_mph=130,
    material="aluminum"
)

print(f"Estimated cost: ${estimate.predicted_cost:,.2f}")
print(f"Confidence: {estimate.confidence_score:.0%}")
```

---

### Week 6: Real-World Validation

#### Task 3.3: Production Testing
**Complexity**: S (Small)  
**Priority**: P0 (Must have)  
**Owner**: Agent + Brady  
**Dependencies**: Task 3.2

**Objective**: Validate predictions against real quotes

**Test Plan**:
1. Run 10 new projects through SignX-Intel
2. Compare ML prediction vs manual estimate
3. Track actual cost when project completes
4. Calculate accuracy metrics

**Tracking Sheet**:
```python
# Track production predictions
@dataclass
class ProductionPredictionTracking:
    project_id: str
    project_name: str
    
    # Predictions
    ml_prediction: Decimal
    manual_estimate: Decimal
    
    # Actual (when available)
    actual_cost: Optional[Decimal]
    
    # Metadata
    predicted_at: datetime
    completed_at: Optional[datetime]
    
    @property
    def ml_error_pct(self) -> Optional[float]:
        if self.actual_cost:
            return abs(self.ml_prediction - self.actual_cost) / self.actual_cost * 100
        return None
    
    @property
    def manual_error_pct(self) -> Optional[float]:
        if self.actual_cost:
            return abs(self.manual_estimate - self.actual_cost) / self.actual_cost * 100
        return None
```

---

### Phase 3 Exit Criteria

**Must Have**:
- [ ] SignX-Studio connector working
- [ ] 10+ projects estimated via API
- [ ] Predictions logged for tracking
- [ ] User feedback collected

**Success Metrics**:
- ✅ API integration works end-to-end
- ✅ Response time < 500ms p95 (including SignX-Studio → SignX-Intel → back)
- ✅ 0 integration failures in 100 calls
- ✅ User satisfaction: "This is faster than manual"

**Deliverable**: Integration demo showing:
1. SignX-Studio project created
2. Cost estimate requested
3. SignX-Intel prediction displayed
4. Breakdown shown (material, labor, overhead)

---

## Phase 4: Refinement (Days 46-60)

**Goal**: Production-grade system with monitoring, alerts, continuous improvement

### Week 7: Monitoring & Observability

#### Task 4.1: Grafana Dashboards
**Complexity**: M (Medium)  
**Priority**: P1 (Should have)  
**Owner**: Agent  
**Dependencies**: Phase 3 complete

**Dashboards to Build**:

**1. Business Health Dashboard**
```json
{
  "title": "SignX-Intel Business Health",
  "panels": [
    {
      "title": "Predictions Today",
      "type": "stat",
      "metric": "cost_predictions_total"
    },
    {
      "title": "Model Accuracy (MAPE)",
      "type": "graph",
      "metric": "cost_prediction_mape_percent"
    },
    {
      "title": "Confidence Distribution",
      "type": "piechart",
      "metric": "prediction_confidence_bucket"
    },
    {
      "title": "Time Saved (Hours/Week)",
      "type": "stat",
      "calculation": "predictions * 0.5"
    }
  ]
}
```

**2. System Health Dashboard**
```json
{
  "title": "SignX-Intel System Health",
  "panels": [
    {
      "title": "API Latency (p50/p95/p99)",
      "type": "graph",
      "metrics": [
        "histogram_quantile(0.50, http_request_duration_seconds)",
        "histogram_quantile(0.95, http_request_duration_seconds)",
        "histogram_quantile(0.99, http_request_duration_seconds)"
      ]
    },
    {
      "title": "Error Rate",
      "type": "graph",
      "metric": "rate(http_requests_total{status=~'5..'}[5m])"
    },
    {
      "title": "Database Query Time",
      "type": "graph"
    }
  ]
}
```

---

#### Task 4.2: Alerting Rules
**Complexity**: S (Small)  
**Priority**: P1 (Should have)  
**Owner**: Agent  
**Dependencies**: Task 4.1

**Critical Alerts** (Telegram):
```yaml
alerts:
  - name: service_down
    condition: up{job="signx-intel"} == 0
    for: 1m
    severity: critical
    message: "🚨 SignX-Intel API DOWN"
  
  - name: high_error_rate
    condition: rate(http_requests_total{status=~"5.."}[5m]) > 0.01
    for: 5m
    severity: critical
    message: "🚨 Error rate > 1%: {{$value}}%"
  
  - name: model_accuracy_degraded
    condition: cost_prediction_mape_percent > 20
    for: 1h
    severity: critical
    message: "⚠️ Model MAPE degraded: {{$value}}%"
```

**Warning Alerts** (Slack):
```yaml
  - name: slow_api
    condition: histogram_quantile(0.95, http_request_duration_seconds) > 1.0
    for: 10m
    severity: warning
    message: "⚠️ API slow: p95 = {{$value}}s"
  
  - name: low_confidence_predictions
    condition: rate(predictions{confidence="low"}[1h]) / rate(predictions[1h]) > 0.3
    for: 1h
    severity: warning
    message: "📊 30% predictions have low confidence"
```

---

### Week 8: Continuous Improvement

#### Task 4.3: Automated Model Retraining
**Complexity**: M (Medium)  
**Priority**: P1 (Should have)  
**Owner**: Agent  
**Dependencies**: Task 4.2

**Retraining Strategy**:
```python
# Scheduled retraining job
@scheduler.scheduled_job('cron', day_of_week='sun', hour=2)
async def weekly_model_retraining():
    """Retrain model weekly with new data."""
    
    # 1. Check if retraining needed
    current_metrics = await get_production_metrics()
    baseline_metrics = await get_baseline_metrics()
    
    degradation_pct = (
        (current_metrics.mape - baseline_metrics.mape) 
        / baseline_metrics.mape
    )
    
    if degradation_pct < 0.1:  # < 10% degradation
        logger.info("retraining_skipped", reason="performance_acceptable")
        return
    
    logger.info("retraining_triggered", degradation_pct=degradation_pct)
    
    # 2. Load fresh data (last 12 months)
    df = await load_training_data(months=12)
    
    # 3. Train new model
    new_model, metrics = await train_production_model(df)
    
    # 4. Validate on holdout set
    validation_passed = metrics["mape"] < baseline_metrics.mape * 1.05
    
    if validation_passed:
        # 5. Deploy new model
        await deploy_model(new_model, version=f"v{datetime.now():%Y%m%d}")
        
        # 6. Update baseline
        await update_baseline_metrics(metrics)
        
        logger.info("retraining_complete", new_mape=metrics["mape"])
    else:
        logger.warning("retraining_failed_validation", metrics=metrics)
```

---

#### Task 4.4: User Feedback Loop
**Complexity**: S (Small)  
**Priority**: P2 (Nice to have)  
**Owner**: Agent  
**Dependencies**: Task 4.3

**Feedback Collection**:
```python
# Add feedback endpoint
@router.post("/predictions/{prediction_id}/feedback")
async def submit_feedback(
    prediction_id: UUID,
    feedback: PredictionFeedback,
    db: AsyncSession = Depends(get_db_session)
):
    """Collect user feedback on predictions."""
    
    await db.execute(
        insert(prediction_feedback).values(
            prediction_id=prediction_id,
            accuracy_rating=feedback.accuracy_rating,  # 1-5
            confidence_rating=feedback.confidence_rating,
            comments=feedback.comments,
            was_helpful=feedback.was_helpful
        )
    )
    
    # If prediction was way off, flag for review
    if feedback.accuracy_rating <= 2:
        await flag_for_review(prediction_id, reason="low_user_rating")
```

---

### Phase 4 Exit Criteria

**Must Have**:
- [ ] Grafana dashboards deployed
- [ ] Critical alerts configured
- [ ] Monitoring working 24/7
- [ ] Automated retraining scheduled

**Success Metrics**:
- ✅ Dashboards refresh real-time
- ✅ Alerts trigger correctly (test by breaking things)
- ✅ MTTR < 30 minutes (mean time to recovery)
- ✅ Model retrains successfully

**Deliverable**: Operations runbook showing:
- How to check system health
- How to respond to alerts
- How to manually retrain model
- How to rollback if needed

---

## Phase 5: Advanced Features (Days 61-90)

**Goal**: Advanced intelligence, anomaly detection, cost optimization

### Week 9-10: Anomaly Detection

#### Task 5.1: Isolation Forest Anomaly Detector
**Complexity**: M (Medium)  
**Priority**: P2 (Nice to have)  
**Owner**: Agent  

**Objective**: Flag unusual projects for review

```python
# Train anomaly detector
from sklearn.ensemble import IsolationForest

def train_anomaly_detector(df: pd.DataFrame):
    """Train to detect unusual cost patterns."""
    
    # Use same features as cost predictor
    features = engineer_features(df)
    
    # Train Isolation Forest
    detector = IsolationForest(
        contamination=0.05,  # Expect 5% anomalies
        random_state=42
    )
    detector.fit(features)
    
    # Test on training data
    predictions = detector.predict(features)
    anomalies = predictions == -1
    
    print(f"Detected {anomalies.sum()} anomalies ({anomalies.mean():.1%})")
    
    return detector

# Use in production
async def predict_with_anomaly_check(spec: SignSpec):
    prediction = await cost_predictor.predict(spec)
    
    # Check if input is anomalous
    features = engineer_features_single(spec)
    is_anomaly = anomaly_detector.predict([features])[0] == -1
    
    if is_anomaly:
        prediction.anomaly_score = 1.0
        prediction.warnings.append("Unusual project configuration detected")
        logger.warning("anomaly_detected", spec=spec.dict())
    
    return prediction
```

---

### Week 11-12: Optimization & Scale

#### Task 5.2: Performance Optimization
**Complexity**: M (Medium)  
**Priority**: P2 (Nice to have)  
**Owner**: Agent  

**Optimizations**:
1. **Caching** (Redis)
   - Cache predictions for identical specs
   - Cache feature engineering results
   - Cache model outputs

2. **Database Indexing**
   ```sql
   -- Add GIN index for JSONB queries
   CREATE INDEX idx_cost_records_drivers_gin ON cost_records USING gin(drivers);
   
   -- Add partial index for recent data
   CREATE INDEX idx_cost_records_recent ON cost_records(created_at) 
   WHERE created_at > NOW() - INTERVAL '90 days';
   ```

3. **Batch Prediction Endpoint**
   ```python
   @router.post("/predict/batch")
   async def predict_batch(requests: list[PredictionRequest]):
       """Predict multiple projects at once (more efficient)."""
       
       # Batch feature engineering
       specs = [req.drivers for req in requests]
       features = batch_engineer_features(specs)
       
       # Batch prediction
       predictions = model.predict(features)
       
       return [
           PredictionResponse(cost=pred, ...)
           for pred in predictions
       ]
   ```

---

#### Task 5.3: Data Lake Migration
**Complexity**: L (Large)  
**Priority**: P2 (Nice to have)  
**Owner**: Agent  

**Objective**: Move old data to Parquet for efficient analytics

```python
# Migrate old data to data lake
async def migrate_to_data_lake(older_than_days: int = 730):
    """Migrate old data to Parquet."""
    
    # 1. Query old records
    old_records = await db.execute(
        select(cost_records)
        .where(cost_records.c.created_at < datetime.now() - timedelta(days=older_than_days))
    )
    
    # 2. Write to Parquet (partitioned by year/month)
    writer = ParquetWriter("./data/archive")
    writer.write_cost_records(
        records=[r._asdict() for r in old_records],
        partition_by="year_month"
    )
    
    # 3. Verify write success
    verification_count = writer.count_records()
    assert verification_count == len(old_records)
    
    # 4. Delete from database (keep last 2 years)
    await db.execute(
        delete(cost_records)
        .where(cost_records.c.created_at < datetime.now() - timedelta(days=older_than_days))
    )
    
    logger.info("migration_complete", 
                records_migrated=len(old_records),
                space_saved_mb=calculate_space_saved())
```

---

## Success Metrics Summary

### Business Metrics (What Brady Cares About)

| Metric | Baseline | Target | Timeline | Status |
|--------|----------|--------|----------|---------|
| Estimation Time | 30 min | 2 min | Day 30 | 🟡 In Progress |
| Accuracy (MAPE) | 25% (manual) | <15% (ML) | Day 45 | 🟡 In Progress |
| Time Saved | 0 hrs/week | 20 hrs/week | Day 60 | ⚪ Not Started |
| Projects Using ML | 0% | 70% | Day 75 | ⚪ Not Started |
| Revenue Protected | $0 | $50k/month | Day 90 | ⚪ Not Started |

### Technical Metrics (What Agent Monitors)

| Metric | Target | Alert Threshold | Dashboard |
|--------|--------|----------------|-----------|
| API Latency (p95) | <500ms | >1000ms | System Health |
| Error Rate | <0.1% | >1.0% | System Health |
| Model MAPE | <15% | >20% | ML Health |
| Data Freshness | <60 min | >120 min | Data Quality |
| Test Coverage | >80% | <75% | Engineering |

---

## Risk Register

| Risk | Impact | Probability | Mitigation | Owner |
|------|--------|-------------|------------|-------|
| PDF extraction accuracy low | High | Medium | Manual audit + iterative improvement | Agent |
| Insufficient training data | High | Medium | Start with heuristic, collect more | Agent |
| Model doesn't beat baseline | Medium | Medium | Ensemble methods, feature engineering | Agent |
| SignX-Studio integration issues | Medium | Low | Build client library, thorough testing | Agent |
| Performance bottlenecks | Low | Medium | Caching, optimization, monitoring | Agent |
| Data quality issues | Medium | Medium | Validation rules, quarantine bad data | Agent |

---

## Resource Requirements

### Infrastructure
- [x] Docker + Docker Compose (already set up)
- [ ] PostgreSQL 17 (4 CPU, 8GB RAM, 100GB storage)
- [ ] Redis (2GB RAM)
- [ ] MinIO (50GB storage)
- [ ] Grafana + Prometheus

### External Services
- [ ] OpenAI API key (optional, for PDF extraction fallback)
- [ ] Telegram bot token (for alerts)
- [ ] MLflow tracking server

### Time Commitment (Brady)
- Week 1-2: 2 hours (provide sample PDFs, validate extraction)
- Week 3-4: 3 hours (review model, provide feedback)
- Week 5-6: 4 hours (test integration, user acceptance)
- Week 7-8: 2 hours (review monitoring, adjust alerts)
- Week 9-12: 1 hour/week (review metrics, feedback)

**Total**: ~20 hours over 12 weeks

---

## Communication Plan

### Daily
- Automated: Morning report (Telegram)
  - Predictions yesterday
  - Model accuracy
  - System health
  - Anomalies detected

### Weekly
- Automated: Friday summary (Email)
  - Progress vs plan
  - Metrics dashboard
  - Action items for next week

### Monthly
- Manual: Review meeting (30 min)
  - Business impact
  - Technical health
  - Next priorities

---

## Rollout Strategy

### Phase 1-2 (Days 1-30): Internal Testing
- Use SignX-Intel internally only
- Brady tests predictions
- Collect feedback, iterate fast

### Phase 3 (Days 31-45): Soft Launch
- 10 real projects through SignX-Intel
- Compare ML vs manual estimates
- Track accuracy

### Phase 4 (Days 46-60): Production Rollout
- SignX-Studio uses SignX-Intel for all new projects
- Monitor closely
- Quick fixes as needed

### Phase 5 (Days 61-90): Optimization
- Advanced features (anomaly detection)
- Performance tuning
- Scale testing

---

## Success Definition

**We know SignX-Intel succeeded when:**

✅ **Day 30**: "I processed 50 PDFs and predictions look reasonable"  
✅ **Day 45**: "ML model beats my manual estimates"  
✅ **Day 60**: "SignX-Studio integration works, I'm using it daily"  
✅ **Day 75**: "I trust the predictions enough to use them in customer quotes"  
✅ **Day 90**: "This saved me 20 hours this week, caught 2 bad bids, paid for itself"

---

## Next Actions

**Immediate (This Week)**:
1. ✅ Review this plan with Brady
2. ⚪ Gather sample PDFs (need 10+ for pattern development)
3. ⚪ Start Task 1.2: PDF ingestion pipeline
4. ⚪ Process first PDF successfully

**This Month**:
- Complete Phase 1 (Foundation)
- Demo: Show PDF → Database → API prediction working

**This Quarter**:
- Complete Phases 1-4
- Deliverable: Production system with SignX-Studio integration

---

**Ready to execute? Let's start with Task 1.2: PDF Ingestion Pipeline.** 🚀

Would you like me to begin implementation, or do you want to adjust the plan first?

