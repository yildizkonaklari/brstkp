from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
import structlog

router = APIRouter()
logger = structlog.get_logger()

@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    health_status = {
        "status": "ok",
        "database": "unknown",
        "redis": "unknown" # We will add redis check later
    }
    
    try:
        await db.execute(text("SELECT 1"))
        health_status["database"] = "connected"
    except Exception as e:
        logger.error("Health check failed for database", error=str(e))
        health_status["database"] = "disconnected"
        health_status["status"] = "degraded"
        
    return health_status
