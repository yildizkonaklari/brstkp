from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from typing import List, Optional
from datetime import date
from app.database import get_db
from app.models import Top10Daily, ScoreDaily, FeatureDaily
from app.schemas.signals import SignalResponse, Top10Item, ScoreDetail

router = APIRouter()

@router.get("/top10", response_model=SignalResponse)
async def get_top10(
    date: Optional[date] = None,
    mode: str = Query("RISK_ON", description="Regime mode filter if applicable"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get Top 10 signals for a specific date. Defaults to today.
    """
    if date is None:
        from datetime import date as dt_date
        date = dt_date.today()
    # Validate date?
    
    # Get Top 10
    stmt = select(Top10Daily).where(Top10Daily.date == date).order_by(Top10Daily.rank)
    result = await db.execute(stmt)
    items = result.scalars().all()
    
    if not items:
        # Fallback or 404? Return empty for now
        return SignalResponse(date=date, regime="UNKNOWN", top10=[])
        
    # Get Regime from scores or store it? 
    # Current Top10 table doesn't have regime. 
    # Use ScoreDaily of first item to find regime from explain_json?
    # Or just return what we have.
    
    top10_list = []
    for item in items:
        top10_list.append(Top10Item(
            rank=item.rank,
            symbol=item.symbol,
            final_score=item.final_score
        ))
        
    return SignalResponse(
        date=date,
        regime=mode, # Placeholder, we should store regime daily
        top10=top10_list
    )

@router.get("/stock/{symbol}", response_model=List[ScoreDetail])
async def get_stock_scores(
    symbol: str, 
    limit: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """
    Get score history for a stock.
    """
    stmt = select(ScoreDaily).where(ScoreDaily.symbol == symbol).order_by(desc(ScoreDaily.date)).limit(limit)
    result = await db.execute(stmt)
    items = result.scalars().all()
    
    res = []
    for i in items:
        res.append(ScoreDetail(
            symbol=i.symbol,
            date=i.date,
            potential_score=i.potential_score,
            risk_score=i.risk_score,
            final_score=i.final_score,
            explain_json=i.explain_json
        ))
    return res
