from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db, engine
from app.api.routes import dashboard, log_analyzer, ioc_scanner, hash_analyzer, investigations, reports


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    init_db()
    print(f"Database initialized at {settings.get_abs_database_path()}")
    
    # Create upload directory
    upload_dir = settings.get_abs_database_path().parent / "uploads"
    upload_dir.mkdir(exist_ok=True)
    
    # Create reports directory
    reports_dir = settings.get_abs_database_path().parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    
    yield
    
    # Shutdown
    engine.dispose()
    print("Application shutdown complete")


app = FastAPI(
    title="SentinelAI API",
    description="Offline cybersecurity analysis platform for education",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers under /api prefix
API_PREFIX = "/api"
app.include_router(dashboard.router, prefix=API_PREFIX)
app.include_router(log_analyzer.router, prefix=API_PREFIX)
app.include_router(ioc_scanner.router, prefix=API_PREFIX)
app.include_router(hash_analyzer.router, prefix=API_PREFIX)
app.include_router(investigations.router, prefix=API_PREFIX)
app.include_router(reports.router, prefix=API_PREFIX)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "database": str(settings.database_path)
    }


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "name": "SentinelAI",
        "version": "1.0.0",
        "description": "Offline cybersecurity analysis platform",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )