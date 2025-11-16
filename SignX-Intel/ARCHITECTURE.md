# SignX-Intel Architecture

> **Design Philosophy**: Build systems that compound value over time through intelligent automation, observable operations, and self-healing resilience.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architectural Principles](#architectural-principles)
3. [Component Architecture](#component-architecture)
4. [Data Architecture](#data-architecture)
5. [ML Pipeline Architecture](#ml-pipeline-architecture)
6. [Integration Architecture](#integration-architecture)
7. [Observability & Monitoring](#observability--monitoring)
8. [Security Architecture](#security-architecture)
9. [Deployment Architecture](#deployment-architecture)
10. [Decision Records](#decision-records)

---

## System Overview

### Vision Statement
SignX-Intel is an autonomous cost intelligence platform that transforms Eagle Sign's 20+ years of estimating expertise into a real-time, self-improving prediction engine. It replaces manual estimation with ML-powered automation while maintaining the domain knowledge that creates competitive advantage.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        External Systems                          │
│  KeyedIn CRM │ SignX-Studio │ CorelDRAW │ Telegram │ Weather   │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway Layer                           │
│              FastAPI + Auth + Rate Limiting + CORS               │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Business Logic Layer                        │
│   Projects │ Predictions │ Insights │ Validation │ Events       │
└────┬───────┴─────┬───────────────────────┬──────────────────────┘
     │             │                       │
     ▼             ▼                       ▼
┌─────────┐  ┌──────────────┐      ┌────────────────┐
│Database │  │  ML Pipeline  │      │  Event Bus     │
│PostgreSQL  │  XGBoost      │      │  Redis Streams │
│+ pgvector│  │  Feature Eng │      │  + Webhooks    │
└─────────┘  └──────────────┘      └────────────────┘
     │             │                       │
     ▼             ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Lake Layer                             │
│         Parquet Files │ Delta Lake │ Model Registry             │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Observability Stack                             │
│  Prometheus │ OpenTelemetry │ Structlog │ Sentry │ Grafana     │
└─────────────────────────────────────────────────────────────────┘
```

### Key Characteristics

- **Event-Driven**: All state changes emit events; systems react autonomously
- **API-First**: Every capability exposed as API before UI
- **Observable by Default**: Metrics, traces, structured logs on every operation
- **Self-Healing**: Circuit breakers, retries, fallbacks built-in
- **ML-Native**: Models are infrastructure, versioned and monitored
- **Data Quality Enforced**: Zero-trust validation, comprehensive SLAs

---

## Architectural Principles

### 1. Composition Over Inheritance

**Why**: Inheritance creates rigid hierarchies; composition enables flexible recombination.

```python
# ✅ Good: Compose behaviors
class CostEstimator:
    def __init__(
        self,
        material_pricer: MaterialPricer,
        labor_calculator: LaborCalculator,
        overhead_allocator: OverheadAllocator,
        risk_adjuster: RiskAdjuster
    ):
        self.components = [
            material_pricer,
            labor_calculator,
            overhead_allocator,
            risk_adjuster
        ]
    
    async def estimate(self, spec: SignSpec) -> Cost:
        costs = await asyncio.gather(*[
            component.calculate(spec) 
            for component in self.components
        ])
        return sum(costs)

# Easy to test each component independently
# Easy to swap implementations (mock, real, cached)
# Easy to add new cost factors
```

**Design Pattern**: **Strategy Pattern** + **Dependency Injection**

---

### 2. Immutable Data Structures

**Why**: Immutability prevents bugs, enables caching, makes concurrency safe.

```python
from dataclasses import dataclass, replace

@dataclass(frozen=True)
class CostPrediction:
    """Immutable prediction result."""
    base_cost: Decimal
    confidence: float
    model_version: str
    timestamp: datetime
    
    # All transformations return NEW instances
    def with_markup(self, percent: float) -> "CostPrediction":
        return replace(self, base_cost=self.base_cost * (1 + percent/100))
    
    def with_contingency(self, percent: float) -> "CostPrediction":
        return replace(self, base_cost=self.base_cost * (1 + percent/100))
    
    # Hashable = cacheable
    def __hash__(self):
        return hash((self.base_cost, self.model_version, self.timestamp))
```

**Benefits**:
- Thread-safe by default
- Easy to cache (hashable)
- Time-travel debugging (maintain history)
- No surprising mutations

---

### 3. Command Query Separation (CQS)

**Why**: Clear intent; commands mutate, queries observe.

```python
# Commands: Mutate state, return nothing (or acknowledgment)
async def create_cost_prediction(
    spec: SignSpec,
    db: AsyncSession
) -> None:
    """Command: Create prediction (side effect)."""
    prediction = await predictor.predict(spec)
    await db.execute(insert(predictions).values(**prediction.dict()))
    await db.commit()
    await event_bus.publish("prediction.created", prediction)

# Queries: Return data, no side effects
async def get_cost_prediction(
    prediction_id: UUID,
    db: AsyncSession
) -> CostPrediction:
    """Query: Read prediction (pure)."""
    result = await db.execute(
        select(predictions).where(predictions.c.id == prediction_id)
    )
    return CostPrediction.from_row(result.one())
```

**Design Pattern**: **CQRS (Command Query Responsibility Segregation)**

---

### 4. Fail Fast, Fail Loud

**Why**: Detect problems immediately; don't propagate corrupt state.

```python
from pydantic import BaseModel, Field, field_validator

class SignSpecification(BaseModel):
    """Fail fast validation at API boundary."""
    
    width_inches: float = Field(gt=0, le=600)  # Max 50 feet
    height_inches: float = Field(gt=0, le=600)
    wind_speed_mph: float = Field(ge=90, le=200)  # Iowa minimum
    
    @field_validator("wind_speed_mph")
    def check_iowa_code(cls, v):
        if v < 90:
            raise ValueError(
                f"Wind speed {v} mph below Iowa IBC minimum (90 mph). "
                "Cannot proceed with unsafe design."
            )
        return v
    
    @model_validator(mode="after")
    def check_structural_feasibility(self):
        area = self.width_inches * self.height_inches / 144  # sqft
        if area > 500:  # Large sign
            if self.wind_speed_mph > 150:
                raise ValueError(
                    f"Large sign ({area} sqft) with high wind ({self.wind_speed_mph} mph) "
                    "requires engineering review. Use /review endpoint."
                )
        return self
```

**Benefits**:
- Errors caught at input boundary
- Invalid data never enters system
- Clear error messages guide users
- Production data stays clean

---

### 5. Observable Everything

**Why**: You can't improve what you don't measure.

```python
from opentelemetry import trace, metrics
import structlog

tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)
logger = structlog.get_logger()

# Counter: How many predictions?
predictions_counter = meter.create_counter(
    "cost_predictions_total",
    description="Total cost predictions made"
)

# Histogram: How long do they take?
prediction_latency = meter.create_histogram(
    "cost_prediction_duration_seconds",
    description="Time to generate prediction"
)

# Gauge: How confident are we?
prediction_confidence = meter.create_up_down_counter(
    "cost_prediction_confidence",
    description="Average confidence score"
)

@tracer.start_as_current_span("predict_sign_cost")
async def predict_sign_cost(spec: SignSpec) -> CostPrediction:
    """Every operation is traced, metered, logged."""
    
    start = time.time()
    
    with tracer.start_as_current_span("feature_engineering"):
        features = engineer_features(spec)
        logger.info("features_ready", feature_count=len(features))
    
    with tracer.start_as_current_span("model_inference"):
        prediction = model.predict(features)
        
        # Record metrics
        predictions_counter.add(1, {"material": spec.material})
        prediction_latency.record(time.time() - start)
        prediction_confidence.add(prediction.confidence)
        
        # Structured logging
        logger.info(
            "prediction_complete",
            predicted_cost=float(prediction.cost),
            confidence=prediction.confidence,
            material=spec.material,
            area_sqft=spec.area_sqft
        )
    
    return prediction
```

**Observable Components**:
- **Traces**: Request flow through system
- **Metrics**: Aggregated statistics (rates, durations, distributions)
- **Logs**: Individual events with context
- **Events**: State changes for audit trail

---

### 6. Self-Healing Systems

**Why**: Transient failures are normal; systems should recover automatically.

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
from circuit_breaker import CircuitBreaker

# Circuit breaker prevents cascading failures
keyedin_breaker = CircuitBreaker(
    fail_max=5,              # Open after 5 failures
    timeout_duration=60,     # Stay open for 60s
    expected_exception=NetworkError
)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(NetworkError)
)
@keyedin_breaker
async def fetch_order_from_keyedin(order_id: str) -> Order:
    """Resilient external API call."""
    try:
        return await keyedin_client.get(f"/orders/{order_id}")
    
    except NetworkError as e:
        logger.warning("keyedin_fetch_failed", 
                      order_id=order_id, 
                      error=str(e))
        
        # Fallback 1: Check cache
        cached = await redis.get(f"order:{order_id}")
        if cached:
            logger.info("serving_from_cache", order_id=order_id)
            return Order.parse_raw(cached)
        
        # Fallback 2: Check local database
        local = await db.get_order(order_id)
        if local and local.age_minutes < 60:
            logger.info("serving_from_local_db", order_id=order_id)
            return local
        
        # All fallbacks exhausted
        raise
```

**Resilience Patterns**:
- **Retry with exponential backoff**: Transient failures
- **Circuit breaker**: Prevent cascading failures
- **Fallback**: Serve stale data rather than fail
- **Timeout**: Don't wait forever
- **Bulkhead**: Isolate failures

---

### 7. Data as a Product

**Why**: Treat data like production systems (versioned, monitored, with SLAs).

```python
from dataclasses import dataclass
from datetime import timedelta

@dataclass
class DatasetContract:
    """Every dataset has a contract."""
    
    name: str
    owner: str
    description: str
    
    # Schema
    schema: Type[BaseModel]
    
    # SLAs
    update_frequency: timedelta
    freshness_sla: timedelta  # Max age
    completeness_sla: float   # Min % non-null
    accuracy_sla: float       # Min % correct (vs audit)
    
    # Quality checks
    async def validate_quality(self) -> DataQualityReport:
        """Run automated quality checks."""
        
        # Check freshness
        latest = await get_latest_record_timestamp(self.name)
        age = datetime.utcnow() - latest
        freshness_ok = age <= self.freshness_sla
        
        # Check completeness
        completeness = await calculate_completeness(self.name, self.schema)
        completeness_ok = completeness >= self.completeness_sla
        
        # Check accuracy (sample audit)
        accuracy = await audit_data_accuracy(self.name, sample_size=100)
        accuracy_ok = accuracy >= self.accuracy_sla
        
        report = DataQualityReport(
            dataset=self.name,
            timestamp=datetime.utcnow(),
            freshness={"ok": freshness_ok, "age_seconds": age.total_seconds()},
            completeness={"ok": completeness_ok, "score": completeness},
            accuracy={"ok": accuracy_ok, "score": accuracy}
        )
        
        # Alert on SLA violations
        if not report.all_checks_passed:
            await alert_data_owner(self.owner, report)
        
        return report

# Define datasets
COST_DATASET = DatasetContract(
    name="production_costs",
    owner="brady@eaglesign.com",
    description="Historical project costs for ML training",
    schema=CostRecord,
    update_frequency=timedelta(hours=1),
    freshness_sla=timedelta(hours=2),
    completeness_sla=0.95,
    accuracy_sla=0.90
)

# Monitor continuously
async def monitor_data_quality():
    """Run quality checks on schedule."""
    while True:
        for dataset in [COST_DATASET, ORDERS_DATASET, MATERIALS_DATASET]:
            report = await dataset.validate_quality()
            await publish_metrics(report)
        
        await asyncio.sleep(3600)  # Every hour
```

---

### 8. ML as Infrastructure

**Why**: Models are code; treat them like production services.

```python
@dataclass
class ModelCard:
    """Comprehensive model metadata."""
    
    # Identity
    name: str
    version: str
    trained_at: datetime
    
    # Performance
    training_metrics: dict  # MAE, RMSE, R²
    validation_metrics: dict
    production_metrics: dict  # Measured in prod
    
    # Data lineage
    training_data_hash: str
    feature_schema: dict
    
    # Deployment
    deployment_date: datetime
    rollback_version: str
    
    # Monitoring
    retraining_trigger: Callable[[dict], bool]
    alert_threshold: dict

class ModelRegistry:
    """Central model registry with health monitoring."""
    
    async def check_health(self, model_name: str) -> ModelHealth:
        """Continuous model monitoring."""
        
        # Get current production performance
        prod_metrics = await measure_production_performance(model_name)
        
        # Compare to baseline
        card = await self.get_model_card(model_name)
        baseline = card.validation_metrics
        
        # Check for degradation
        degradation_detected = (
            prod_metrics["mape"] > baseline["mape"] * 1.2  # 20% worse
        )
        
        if degradation_detected:
            logger.warning(
                "model_degradation",
                model=model_name,
                prod_mape=prod_metrics["mape"],
                baseline_mape=baseline["mape"]
            )
            
            # Auto-trigger retraining
            if card.retraining_trigger(prod_metrics):
                await self.trigger_retraining(model_name)
        
        return ModelHealth(
            model_name=model_name,
            status="healthy" if not degradation_detected else "degraded",
            metrics=prod_metrics,
            last_check=datetime.utcnow()
        )
```

**Model Lifecycle**:
1. **Training**: Versioned, reproducible, tracked in MLflow
2. **Validation**: Holdout set + cross-validation
3. **Deployment**: A/B test, gradual rollout
4. **Monitoring**: Track performance, detect drift
5. **Retraining**: Automatic when performance degrades
6. **Rollback**: Fast rollback if issues detected

---

## Component Architecture

### API Layer

**Technology**: FastAPI 0.110+ (async)

**Responsibilities**:
- Request validation (Pydantic)
- Authentication & authorization
- Rate limiting
- CORS handling
- OpenAPI documentation
- Request tracing

```python
# src/signx_intel/api/main.py

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

app = FastAPI(
    title="SignX-Intel Cost Intelligence",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Auto-instrumentation
FastAPIInstrumentor.instrument_app(app)

# Routes
app.include_router(predictions.router, prefix="/api/v1", tags=["predictions"])
app.include_router(projects.router, prefix="/api/v1", tags=["projects"])
app.include_router(insights.router, prefix="/api/v1", tags=["insights"])
```

**API Design Principles**:
- RESTful conventions
- Versioned (`/api/v1/`)
- Async endpoints (I/O bound)
- Dependency injection
- Comprehensive error responses

---

### Business Logic Layer

**Pattern**: Service Layer + Domain Models

```python
# src/signx_intel/services/prediction_service.py

class PredictionService:
    """Business logic for cost predictions."""
    
    def __init__(
        self,
        db: AsyncSession,
        cache: CacheClient,
        model_registry: ModelRegistry,
        event_bus: EventBus
    ):
        self.db = db
        self.cache = cache
        self.models = model_registry
        self.events = event_bus
    
    async def predict_cost(
        self,
        spec: SignSpecification,
        user_id: str
    ) -> CostPrediction:
        """Generate cost prediction with full orchestration."""
        
        # 1. Validate input
        await self.validate_specification(spec)
        
        # 2. Check cache
        cache_key = self.cache_key_for(spec)
        cached = await self.cache.get(cache_key)
        if cached:
            return CostPrediction.parse_raw(cached)
        
        # 3. Load model
        model = await self.models.get_latest("cost_predictor")
        
        # 4. Engineer features
        features = await self.engineer_features(spec)
        
        # 5. Predict
        prediction = await model.predict(features)
        
        # 6. Validate output
        await self.validate_prediction(prediction, spec)
        
        # 7. Store in database
        await self.store_prediction(prediction, user_id)
        
        # 8. Cache result
        await self.cache.set(cache_key, prediction.json(), ttl=3600)
        
        # 9. Emit event
        await self.events.publish("prediction.created", prediction)
        
        # 10. Return
        return prediction
```

**Benefits**:
- Testable (mock dependencies)
- Reusable (called from API, CLI, workers)
- Observable (instrumented once)
- Transaction boundaries clear

---

### Data Access Layer

**Pattern**: Repository Pattern + Unit of Work

```python
# src/signx_intel/repositories/cost_repository.py

class CostRecordRepository:
    """Data access for cost records."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, record: CostRecord) -> UUID:
        """Insert cost record."""
        stmt = insert(cost_records).values(**record.dict()).returning(cost_records.c.id)
        result = await self.db.execute(stmt)
        return result.scalar_one()
    
    async def get_by_id(self, record_id: UUID) -> Optional[CostRecord]:
        """Fetch by ID."""
        stmt = select(cost_records).where(cost_records.c.id == record_id)
        result = await self.db.execute(stmt)
        row = result.one_or_none()
        return CostRecord.from_row(row) if row else None
    
    async def find_similar(
        self,
        spec: SignSpec,
        limit: int = 10
    ) -> List[CostRecord]:
        """Find similar historical projects."""
        # Use pgvector for semantic similarity
        stmt = select(cost_records).where(
            cost_records.c.embedding.cosine_distance(spec.embedding) < 0.3
        ).order_by(
            cost_records.c.embedding.cosine_distance(spec.embedding)
        ).limit(limit)
        
        result = await self.db.execute(stmt)
        return [CostRecord.from_row(row) for row in result]
```

**Benefits**:
- Database logic isolated
- Easy to switch databases
- Testable with mocks
- Query optimization centralized

---

## Data Architecture

### Database Schema

**Technology**: PostgreSQL 17 + pgvector

#### Core Tables

```sql
-- Projects (high-level container)
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(500) NOT NULL,
    source VARCHAR(50) NOT NULL,  -- signx-studio, crm, manual, pdf_import
    status VARCHAR(50) NOT NULL,  -- draft, quoted, approved, in_progress, completed
    customer_name VARCHAR(255),
    location VARCHAR(500),
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    project_date TIMESTAMPTZ
);

CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_source ON projects(source);
CREATE INDEX idx_projects_created_at ON projects(created_at DESC);

-- Cost Records (detailed cost data)
CREATE TABLE cost_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    
    -- Cost breakdown
    total_cost NUMERIC(12, 2) NOT NULL,
    labor_cost NUMERIC(12, 2),
    material_cost NUMERIC(12, 2),
    equipment_cost NUMERIC(12, 2),
    overhead_cost NUMERIC(12, 2),
    tax NUMERIC(12, 2),
    shipping NUMERIC(12, 2),
    
    -- Flexible drivers (sign_height_ft, sign_area_sqft, foundation_type, etc.)
    drivers JSONB NOT NULL DEFAULT '{}',
    
    -- ML metadata
    predicted_cost NUMERIC(12, 2),
    confidence_score FLOAT,
    cost_drivers_importance JSONB,
    anomaly_score FLOAT,
    
    -- Semantic search
    embedding VECTOR(384),  -- Sentence-BERT embeddings
    
    -- Audit
    notes TEXT,
    tags JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    cost_date TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_cost_records_project_id ON cost_records(project_id);
CREATE INDEX idx_cost_records_cost_date ON cost_records(cost_date DESC);
CREATE INDEX idx_cost_records_total_cost ON cost_records(total_cost);
CREATE INDEX idx_cost_records_drivers ON cost_records USING GIN (drivers);
CREATE INDEX idx_cost_records_embedding ON cost_records USING ivfflat (embedding vector_cosine_ops);
```

#### Flexible Driver Schema

**Design**: JSONB allows domain-specific drivers without schema migrations.

```json
{
  "sign_height_ft": 25.0,
  "sign_area_sqft": 120.0,
  "foundation_type": "drilled_pier",
  "wind_speed_mph": 130,
  "exposure_category": "C",
  "material": "aluminum",
  "finish": "powder_coat",
  "has_lighting": true,
  "is_double_faced": false,
  "mounting_type": "pole",
  "install_complexity": "medium",
  "site_conditions": "flat_terrain",
  "permit_required": true,
  "custom_engineering": false
}
```

**Query Patterns**:
```sql
-- Find all projects with high wind loads
SELECT * FROM cost_records 
WHERE (drivers->>'wind_speed_mph')::int > 140;

-- Find all drilled pier foundations
SELECT * FROM cost_records
WHERE drivers->>'foundation_type' = 'drilled_pier';

-- Aggregations
SELECT 
    drivers->>'material' as material,
    AVG(total_cost) as avg_cost,
    COUNT(*) as project_count
FROM cost_records
GROUP BY drivers->>'material';
```

---

### Data Lake Architecture

**Technology**: Parquet + Delta Lake

**Purpose**: Long-term storage, ML training, analytics

```
data/
├── raw/                    # Immutable source data
│   └── pdfs/              # Original PDF cost summaries
│       └── 2024/
│           ├── 01/
│           └── 02/
│
├── processed/             # Cleaned, normalized
│   └── cost_records/
│       ├── year=2024/
│       │   ├── month=01/
│       │   │   └── data.parquet
│       │   └── month=02/
│       │       └── data.parquet
│       └── _delta_log/   # Delta Lake transaction log
│
└── features/             # Engineered features for ML
    └── cost_prediction_features_v1/
        └── features.parquet
```

**Benefits**:
- **Columnar**: Fast analytics queries
- **Partitioned**: Query only relevant data
- **Compressed**: 10x smaller than CSV
- **Schema evolution**: Add columns without rewriting
- **Time travel**: Delta Lake maintains history

```python
# Write to data lake
from signx_intel.storage.lake.parquet_writer import ParquetWriter

writer = ParquetWriter(base_path="./data/processed")
writer.write_cost_records(
    records=extracted_data,
    partition_by="year_month"  # Partition for efficient queries
)

# Read from data lake with filters
df = writer.read_cost_records(
    filters=[('year', '=', 2024), ('month', '>=', 6)],
    columns=["total_cost", "drivers", "predicted_cost"]
)
```

---

## ML Pipeline Architecture

### Training Pipeline

```
┌──────────────┐
│ Raw Data     │
│ (PostgreSQL, │
│  Parquet)    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Feature      │
│ Engineering  │
│ (pandas/     │
│  polars)     │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Train/Val    │
│ Split        │
│ (sklearn)    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Model        │
│ Training     │
│ (XGBoost,    │
│  LightGBM)   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Validation   │
│ & Metrics    │
│ (MAE, RMSE,  │
│  R², SHAP)   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Model        │
│ Registry     │
│ (MLflow)     │
└──────────────┘
```

### Feature Engineering

```python
# src/signx_intel/ml/features/engineering.py

class FeatureEngineer:
    """Transform raw drivers into ML features."""
    
    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fit and transform training data."""
        
        # 1. Extract nested JSON
        df = self.explode_drivers(df)
        
        # 2. Create interaction features
        df["area_height_interaction"] = df["sign_area_sqft"] * df["sign_height_ft"]
        df["wind_load_factor"] = df["wind_speed_mph"] * df["sign_area_sqft"]
        
        # 3. Encode categoricals
        df = self.encode_categoricals(df)
        
        # 4. Scale numerics
        df = self.scale_features(df)
        
        # 5. Handle missing
        df = df.fillna(df.median())
        
        return df
```

### Model Training

```python
# src/signx_intel/ml/training/cost_predictor.py

class CostPredictor:
    """XGBoost cost prediction model."""
    
    def train(self, df: pd.DataFrame) -> ModelCard:
        """Train and validate model."""
        
        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            df.drop("total_cost", axis=1),
            df["total_cost"],
            test_size=0.2,
            random_state=42
        )
        
        # Train XGBoost
        model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            tree_method="gpu_hist",  # GPU acceleration
            random_state=42
        )
        
        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            early_stopping_rounds=10,
            verbose=False
        )
        
        # Evaluate
        y_pred = model.predict(X_test)
        metrics = {
            "mae": mean_absolute_error(y_test, y_pred),
            "rmse": np.sqrt(mean_squared_error(y_test, y_pred)),
            "r2": r2_score(y_test, y_pred),
            "mape": mean_absolute_percentage_error(y_test, y_pred)
        }
        
        # SHAP explainability
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X_test)
        
        # Save to MLflow
        with mlflow.start_run():
            mlflow.log_params(model.get_params())
            mlflow.log_metrics(metrics)
            mlflow.sklearn.log_model(model, "model")
            mlflow.log_artifact("shap_summary.png")
        
        return ModelCard(
            name="cost_predictor",
            version=f"v{datetime.now():%Y%m%d_%H%M%S}",
            metrics=metrics,
            feature_schema=X_train.columns.tolist()
        )
```

### Inference Service

```python
# src/signx_intel/ml/inference/predictor.py

class InferenceService:
    """Production inference with caching and monitoring."""
    
    def __init__(self):
        self.model = self.load_model()
        self.feature_engineer = FeatureEngineer.load()
        self.cache = CacheClient()
    
    async def predict(self, spec: SignSpec) -> CostPrediction:
        """Predict with full production safeguards."""
        
        # 1. Check cache
        cache_key = self.cache_key(spec)
        cached = await self.cache.get(cache_key)
        if cached:
            return CostPrediction.parse_raw(cached)
        
        # 2. Engineer features
        features = self.feature_engineer.transform(spec)
        
        # 3. Predict
        with tracer.start_as_current_span("model_inference"):
            prediction = self.model.predict(features)[0]
        
        # 4. Calculate confidence
        confidence = self.calculate_confidence(features, prediction)
        
        # 5. Detect anomalies
        anomaly_score = self.detect_anomaly(features)
        
        # 6. SHAP explanation
        shap_values = self.explain(features)
        
        result = CostPrediction(
            cost=Decimal(prediction),
            confidence=confidence,
            anomaly_score=anomaly_score,
            drivers_importance=shap_values,
            model_version=self.model.version
        )
        
        # 7. Cache
        await self.cache.set(cache_key, result.json(), ttl=3600)
        
        return result
```

---

## Integration Architecture

### External System Connectors

#### KeyedIn CRM Integration

```python
# src/signx_intel/connectors/keyedin.py

class KeyedInConnector:
    """Bidirectional sync with KeyedIn CRM."""
    
    async def sync_orders(self, since: datetime) -> List[Order]:
        """Pull new orders from KeyedIn."""
        
        orders = await self.client.get(
            "/api/orders",
            params={"modified_since": since.isoformat()}
        )
        
        for order in orders:
            # Extract cost data
            cost_data = self.extract_cost_data(order)
            
            # Store in SignX-Intel
            await cost_repository.create(cost_data)
            
            # Emit event
            await event_bus.publish("order.imported", order)
        
        return orders
    
    async def push_prediction(
        self,
        order_id: str,
        prediction: CostPrediction
    ):
        """Push prediction back to KeyedIn."""
        
        await self.client.post(
            f"/api/orders/{order_id}/cost_estimate",
            json={
                "estimated_cost": float(prediction.cost),
                "confidence": prediction.confidence,
                "source": "signx_intel_ml",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
```

#### Webhook System

```python
# src/signx_intel/connectors/webhooks.py

class WebhookManager:
    """Event-driven webhooks for real-time integration."""
    
    def __init__(self):
        self.subscriptions: Dict[str, List[WebhookSubscription]] = {}
    
    def register(
        self,
        event_type: str,
        url: str,
        secret: str
    ):
        """Register webhook subscription."""
        subscription = WebhookSubscription(
            event_type=event_type,
            url=url,
            secret=secret,
            active=True
        )
        
        if event_type not in self.subscriptions:
            self.subscriptions[event_type] = []
        
        self.subscriptions[event_type].append(subscription)
    
    async def dispatch(self, event: Event):
        """Dispatch event to all subscribers."""
        
        subscribers = self.subscriptions.get(event.type, [])
        
        for sub in subscribers:
            if not sub.active:
                continue
            
            # Sign payload
            signature = hmac.new(
                sub.secret.encode(),
                event.json().encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Send webhook
            try:
                await httpx.post(
                    sub.url,
                    json=event.dict(),
                    headers={"X-Signature": signature},
                    timeout=10
                )
            except Exception as e:
                logger.error("webhook_delivery_failed",
                           url=sub.url,
                           event_type=event.type,
                           error=str(e))
```

---

## Observability & Monitoring

### Three Pillars

#### 1. Metrics (Prometheus)

```python
from prometheus_client import Counter, Histogram, Gauge

# Business metrics
predictions_total = Counter(
    "cost_predictions_total",
    "Total cost predictions",
    ["material", "status"]
)

prediction_value = Histogram(
    "cost_prediction_value_dollars",
    "Distribution of predicted costs",
    buckets=[1000, 5000, 10000, 25000, 50000, 100000]
)

# Technical metrics
api_latency = Histogram(
    "http_request_duration_seconds",
    "API request latency",
    ["method", "endpoint", "status"]
)

model_confidence = Gauge(
    "ml_model_confidence_score",
    "Average model confidence",
    ["model_version"]
)
```

#### 2. Traces (OpenTelemetry)

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

@tracer.start_as_current_span("process_order")
async def process_order(order_id: str):
    """Trace entire order processing flow."""
    
    with tracer.start_as_current_span("fetch_order"):
        order = await fetch_order(order_id)
    
    with tracer.start_as_current_span("validate_order"):
        validate_order(order)
    
    with tracer.start_as_current_span("predict_cost"):
        prediction = await predict_cost(order.spec)
    
    with tracer.start_as_current_span("store_result"):
        await store_result(prediction)
    
    return prediction
```

#### 3. Logs (Structlog)

```python
import structlog

logger = structlog.get_logger()

# Structured logging with context
logger.info(
    "prediction_created",
    order_id=order.id,
    predicted_cost=float(prediction.cost),
    confidence=prediction.confidence,
    model_version=prediction.model_version,
    user_id=user.id,
    duration_ms=duration
)

# Automatic context propagation
logger = logger.bind(
    request_id=request.headers["X-Request-ID"],
    user_id=current_user.id
)

# All subsequent logs include context
logger.info("starting_validation")  # Includes request_id, user_id
logger.warning("low_confidence_detected")  # Includes request_id, user_id
```

### Dashboards

**Grafana Dashboards**:
1. **Business Health**: Predictions/day, average cost, accuracy trends
2. **API Performance**: Latency p50/p95/p99, error rates, throughput
3. **ML Model Health**: Confidence distribution, prediction drift, retraining triggers
4. **Data Quality**: Completeness, freshness, validation failures

---

## Security Architecture

### Defense in Depth

#### 1. Authentication & Authorization

```python
from fastapi import Security, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> User:
    """Validate JWT token."""
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=["HS256"]
        )
        user_id = payload.get("sub")
        user = await user_repository.get_by_id(user_id)
        if not user:
            raise HTTPException(401, "Invalid token")
        return user
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid token")

@router.post("/predictions")
async def create_prediction(
    spec: SignSpec,
    current_user: User = Depends(get_current_user)
):
    """Protected endpoint."""
    # Only authenticated users can predict
    pass
```

#### 2. Input Validation

**Zero-trust principle**: Validate everything.

```python
class SignSpec(BaseModel):
    """Comprehensive input validation."""
    
    # Range validation
    width_inches: float = Field(gt=0, le=600)
    height_inches: float = Field(gt=0, le=600)
    
    # Enum validation
    material: Literal["aluminum", "acm", "steel", "hdpe"]
    
    # Custom validators
    @field_validator("wind_speed_mph")
    def validate_wind_speed(cls, v):
        if v < 90:  # Iowa minimum
            raise ValueError("Wind speed below code minimum")
        if v > 200:  # Unrealistic
            raise ValueError("Wind speed exceeds realistic maximum")
        return v
    
    # Cross-field validation
    @model_validator(mode="after")
    def validate_structural_limits(self):
        area = self.width_inches * self.height_inches / 144
        if area > 1000:
            raise ValueError("Sign area exceeds manufacturing capability")
        return self
```

#### 3. Secrets Management

```python
# .env (never commit)
SECRET_KEY=...
DATABASE_URL=postgresql://...
OPENAI_API_KEY=sk-...

# Load with pydantic-settings
class Settings(BaseSettings):
    secret_key: str
    database_url: str
    openai_api_key: str | None = None
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False
    )

settings = Settings()
```

#### 4. Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/predict")
@limiter.limit("100/hour")  # 100 requests per hour per IP
async def predict_cost(request: Request, spec: SignSpec):
    """Rate-limited endpoint."""
    pass
```

---

## Deployment Architecture

### Docker Compose (Development)

```yaml
version: '3.9'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://signx_intel:password@postgres:5432/cost_intelligence
    depends_on:
      - postgres
      - redis
  
  postgres:
    image: postgres:17-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_PASSWORD: password
  
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
  
  mlflow:
    image: ghcr.io/mlflow/mlflow:v2.16.0
    ports:
      - "5000:5000"
    depends_on:
      - postgres
```

### Production (Kubernetes - Future)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: signx-intel-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: signx-intel
  template:
    metadata:
      labels:
        app: signx-intel
    spec:
      containers:
      - name: api
        image: signx-intel:latest
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
```

---

## Decision Records

### ADR-001: Why FastAPI over Flask/Django?

**Context**: Need high-performance async API.

**Decision**: FastAPI

**Rationale**:
- Native async/await support
- Automatic OpenAPI documentation
- Pydantic validation built-in
- Best-in-class performance (Starlette + Uvicorn)
- Modern Python 3.12 features

**Consequences**: 
- ✅ Faster development
- ✅ Better performance
- ❌ Smaller ecosystem than Django

---

### ADR-002: Why PostgreSQL over MongoDB?

**Context**: Need flexible schema but strong consistency.

**Decision**: PostgreSQL 17 with JSONB

**Rationale**:
- JSONB gives schema flexibility
- pgvector enables semantic search
- ACID transactions critical for cost data
- Better ecosystem (Alembic, SQLAlchemy)
- Proven at scale

**Consequences**:
- ✅ Data integrity guaranteed
- ✅ Rich query capabilities (SQL + JSON)
- ❌ Slightly more complex than MongoDB

---

### ADR-003: Why XGBoost over Neural Networks?

**Context**: Need accurate, explainable cost predictions.

**Decision**: XGBoost for tabular data

**Rationale**:
- Best performance on tabular data
- Built-in GPU support
- SHAP explainability
- Less data required than deep learning
- Faster training and inference

**Consequences**:
- ✅ High accuracy with small datasets
- ✅ Explainable predictions
- ❌ Less flexible than neural networks

---

*Architecture is never done. It evolves. This document should too.*

