from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from typing import List
import uuid
import json
import pandas as pd
from datetime import date

from app.database import get_db, AsyncSessionLocal
from app.models import BacktestRun, BacktestTrade, BacktestEquity, Top10Daily, FeatureDaily, PriceDaily, IndexDaily
from app.schemas.backtest import BacktestCreate, BacktestResultResponse, BacktestTradeResponse, BacktestEquityPoint
from app.services.backtest_engine import BacktestEngine

router = APIRouter()

async def run_backtest_task(run_id: str, params: dict):
    # Create new session
    async with AsyncSessionLocal() as db:
        try:
            # Update status to RUNNING
            run = await db.get(BacktestRun, run_id)
            if run:
                run.status = "RUNNING"
                await db.commit()
            
            # 1. Load Data
            # This can be heavy. Optimization needed for Prod.
            # Loading ALL history for backtest period.
            
            start = pd.to_datetime(params['start_date']).date()
            end = pd.to_datetime(params['end_date']).date()
            
            # Prices
            # optimization: load only needed columns
            # For massive data, convert to parquet or lazy load. 
            # For MVP with seed data, SELECT ALL is fine.
            stmt = select(PriceDaily).where(PriceDaily.date >= start, PriceDaily.date <= end)
            res = await db.execute(stmt)
            prices_rows = res.scalars().all()
            
            price_history = {}
            # Convert to dict of DFs
            # Group by symbol
            data = [
                {'symbol': p.symbol, 'date': p.date, 'open': p.open, 'close': p.close, 'high': p.high, 'low': p.low}
                for p in prices_rows
            ]
            if not data:
                raise ValueError("No price data found")
                
            df_all = pd.DataFrame(data)
            df_all['date'] = pd.to_datetime(df_all['date'])
            df_all.set_index('date', inplace=True)
            
            for sym, group in df_all.groupby('symbol'):
                price_history[str(sym)] = group
                
            # Features
            stmt = select(FeatureDaily).where(FeatureDaily.date >= start, FeatureDaily.date <= end)
            res = await db.execute(stmt)
            feat_rows = res.scalars().all()
            
            f_data = [
                {'symbol': f.symbol, 'date': f.date, 'ema50': f.ema50, 'atr14_pct': f.atr14_pct} # Add needed columns
                for f in feat_rows
            ]
            df_feat = pd.DataFrame(f_data)
            if not df_feat.empty:
                df_feat['date'] = pd.to_datetime(df_feat['date'])
                df_feat.set_index(['date', 'symbol'], inplace=True)
                df_feat.sort_index(inplace=True)
            
            # Top10
            stmt = select(Top10Daily).where(Top10Daily.date >= start, Top10Daily.date <= end)
            res = await db.execute(stmt)
            top_rows = res.scalars().all()
            
            t_data = [
                {'date': t.date, 'rank': t.rank, 'symbol': t.symbol, 'final_score': t.final_score}
                for t in top_rows
            ]
            df_top = pd.DataFrame(t_data)
            if not df_top.empty:
                df_top['date'] = pd.to_datetime(df_top['date'])
                df_top.set_index(['date', 'rank'], inplace=True)
                df_top.sort_index(inplace=True)
                
            # Index
            stmt = select(IndexDaily).where(IndexDaily.date >= start, IndexDaily.date <= end)
            res = await db.execute(stmt)
            idx_rows = res.scalars().all()
            
            i_data = [{'date': i.date, 'close': i.close, 'ema50': i.ema50} for i in idx_rows]
            df_index = pd.DataFrame(i_data)
            if not df_index.empty:
                df_index['date'] = pd.to_datetime(df_index['date'])
                df_index.set_index('date', inplace=True)
            
            # 2. Run Engine
            engine = BacktestEngine()
            results = await engine.run_backtest(
                params, 
                df_top, 
                df_feat, 
                price_history, 
                df_index
            )
            
            if "error" in results:
                raise ValueError(results["error"])
                
            # 3. Save Results
            # Trades
            for t in results['trades']:
                trade = BacktestTrade(
                    run_id=run_id,
                    date=t['date'],
                    symbol=t['symbol'],
                    action=t['action'],
                    qty=t['qty'],
                    price=t['price'],
                    fee=t['fee'],
                    slippage=t['slippage'],
                    reason=t['reason']
                )
                db.add(trade)
                
            # Equity
            for e in results['equity_curve']:
                eq = BacktestEquity(
                    run_id=run_id,
                    date=e['date'],
                    equity=e['equity'],
                    benchmark_equity=e.get('benchmark_equity')
                )
                db.add(eq)
                
            # Update Run
            run = await db.get(BacktestRun, run_id)
            if run:
                run.status = "COMPLETED"
                # Save metrics? We can put them in params or separate field
                # For now puts in params_json['metrics']
                p = run.params_json.copy()
                p['metrics'] = results['metrics']
                run.params_json = p
                
            await db.commit()
            
        except Exception as e:
            # Log error
            print(f"Backtest failed: {e}")
            run = await db.get(BacktestRun, run_id)
            if run:
                run.status = "FAILED"
                await db.commit()

@router.post("/run", response_model=BacktestResultResponse)
async def create_backtest(
    params: BacktestCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    run_id = str(uuid.uuid4())
    
    # Create Record
    run_rec = BacktestRun(
        run_id=run_id,
        params_json=params.model_dump(mode='json'),
        status="PENDING"
    )
    db.add(run_rec)
    await db.commit()
    
    # Trigger Task
    background_tasks.add_task(run_backtest_task, run_id, params.model_dump(mode='json'))
    
    return BacktestResultResponse(
        run_id=run_id,
        status="PENDING"
    )

@router.get("/{run_id}", response_model=BacktestResultResponse)
async def get_backtest_result(run_id: str, db: AsyncSession = Depends(get_db)):
    run = await db.get(BacktestRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    # Get Trades
    stmt = select(BacktestTrade).where(BacktestTrade.run_id == run_id).order_by(BacktestTrade.date)
    res = await db.execute(stmt)
    trades = res.scalars().all()
    
    # Get Equity
    stmt = select(BacktestEquity).where(BacktestEquity.run_id == run_id).order_by(BacktestEquity.date)
    res = await db.execute(stmt)
    equity = res.scalars().all()
    
    return BacktestResultResponse(
        run_id=run.run_id,
        status=run.status,
        metrics=run.params_json.get('metrics'),
        trades=[BacktestTradeResponse(
            date=t.date,
            symbol=t.symbol,
            action=t.action,
            qty=t.qty,
            price=t.price,
            reason=t.reason or ""
        ) for t in trades],
        equity_curve=[BacktestEquityPoint(
            date=e.date,
            equity=e.equity,
            benchmark_equity=e.benchmark_equity
        ) for e in equity]
    )
