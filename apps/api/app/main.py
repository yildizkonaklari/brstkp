from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.utils.logging import setup_logging
from app.routers import health, data, signals, backtest

settings = get_settings()
setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    import structlog
    from app.database import engine, Base
    # Import models so they are registered in Base
    from app import models 
    
    log = structlog.get_logger()
    log.info("Application starting up...", version=settings.VERSION)
    
    async with engine.begin() as conn:
        # Create tables
        # In production with Alembic, we might not want this, but for MVP it's fine.
        await conn.run_sync(Base.metadata.create_all)
        
    yield
    # Shutdown
    log.info("Application shutting down...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# CORS
origins = [
    "http://localhost",
    "http://localhost:3000",
    "https://brstkp.vercel.app",  # Production frontend
    "*" # Allow all for MVP testing
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,

    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router, tags=["Health"])
app.include_router(data.router, prefix=f"{settings.API_V1_STR}/data", tags=["Data"])
app.include_router(signals.router, prefix=f"{settings.API_V1_STR}/signals", tags=["Signals"])
app.include_router(backtest.router, prefix=f"{settings.API_V1_STR}/backtest", tags=["Backtest"])

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

