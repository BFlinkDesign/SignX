"""FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from signx_intel.api.routes import health, projects, predictions, insights
from signx_intel.config import get_settings
from signx_intel.storage.database import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("🚀 Starting SignX-Intel Cost Intelligence Platform...")
    await init_db()
    print("✅ Database initialized")
    yield
    # Shutdown
    print("👋 Shutting down...")


app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    docs_url=f"{settings.api_v1_prefix}/docs",
    redoc_url=f"{settings.api_v1_prefix}/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(health.router, prefix=settings.api_v1_prefix, tags=["health"])
app.include_router(projects.router, prefix=settings.api_v1_prefix, tags=["projects"])
app.include_router(predictions.router, prefix=settings.api_v1_prefix, tags=["predictions"])
app.include_router(insights.router, prefix=settings.api_v1_prefix, tags=["insights"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "SignX-Intel Cost Intelligence",
        "version": settings.version,
        "docs": f"{settings.api_v1_prefix}/docs",
        "status": "operational"
    }

