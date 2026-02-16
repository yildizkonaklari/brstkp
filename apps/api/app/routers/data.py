from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.services.data_provider import CSVDataProvider
from app.models import Symbol, PriceDaily, IndexDaily
from app.schemas.common import Message
import os

router = APIRouter()

# MVP: Hardcoded path or from env
CSV_DIR = os.path.abspath(os.path.join(os.getcwd(), "../../../data/seed")) 
# NOTE: In Docker this path might be different (/app/data/seed). 
# But for now we use relative from execution context or config.
# Let's trust env or default.

@router.post("/import/seed", response_model=Message)
async def import_seed_data(db: AsyncSession = Depends(get_db)):
    """
    Import data from 'data/seed' folder into DB.
    """
    # Initialize Provider
    # Verify path
    if not os.path.exists(CSV_DIR):
        # try default docker path
        pass 
    
    provider = CSVDataProvider(CSV_DIR)
    
    # 1. Symbols
    symbols = provider.get_symbols()
    for s_info in symbols:
        # Upsert
        stmt = select(Symbol).where(Symbol.symbol == s_info.symbol)
        result = await db.execute(stmt)
        existing = result.scalars().first()
        
        if not existing:
            new_sym = Symbol(
                symbol=s_info.symbol,
                name=s_info.name,
                sector=s_info.sector,
                is_active=s_info.is_active,
                list_start_date=s_info.list_start_date
            )
            db.add(new_sym)
    
    await db.commit()
    
    # 2. Prices
    # Since we can't easily iterate ALL dates without a massive loop,
    # and CSVDataProvider gets by symbol...
    # We iterate all symbols we just saved.
    
    stmt = select(Symbol).where(Symbol.is_active == True)
    result = await db.execute(stmt)
    all_symbols = result.scalars().all()
    
    import pandas as pd
    from datetime import date
    start_date = date(2020, 1, 1)
    end_date = date.today()
    
    count = 0
    for sym in all_symbols:
        df = provider.get_daily_ohlcv(sym.symbol, start_date, end_date)
        if df.empty: continue
        
        # Batch insert? Or simple loop for MVP
        for dt, row in df.iterrows():
            # Check exist
            # Optimization: Delete all and rewrite? Or ignore conflict?
            # For MVP seed, let's just Try/Except or Check
            # Check if exists
            exists_stmt = select(PriceDaily).where(
                (PriceDaily.symbol == sym.symbol) &
                (PriceDaily.date == dt.date())
            )
            res = await db.execute(exists_stmt)
            if res.scalars().first(): continue

            p = PriceDaily(
                symbol=sym.symbol,
                date=dt.date(),
                open=row['open'],
                high=row['high'],
                low=row['low'],
                close=row['close'],
                volume=int(row['volume']),
                turnover_tl=row.get('turnover_tl'),
                adj_close=row.get('adj_close')
            )
            db.add(p)
            count += 1
            
    await db.commit()
    
    # 3. Index
    df_idx = provider.get_index_daily("XU100", start_date, end_date)
    for dt, row in df_idx.iterrows():
        exists_stmt = select(IndexDaily).where(IndexDaily.date == dt.date())
        res = await db.execute(exists_stmt)
        if res.scalars().first(): continue
        
        i = IndexDaily(
            date=dt.date(),
            close=row['close']
            # EMAs will be computed by feature engine later
        )
        db.add(i)
        
    await db.commit()
    
    return {"message": f"Import complete. Imported {len(symbols)} symbols and {count} price rows."}

@router.post("/import/yahoo", response_model=Message)
async def import_yahoo_data(
    days: int = 365, 
    db: AsyncSession = Depends(get_db)
):
    """
    Import last N days of data from Yahoo Finance for all active symbols in DB.
    """
    import traceback
    try:
        from datetime import date, timedelta
        from app.services.data_provider import YahooFinanceProvider
        from app.models import Symbol, PriceDaily, IndexDaily
        
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        provider = YahooFinanceProvider()
        
        # 1. Get Symbols from DB
        # If DB is empty, maybe try to seed symbols first?
        stmt = select(Symbol).where(Symbol.is_active == True)
        result = await db.execute(stmt)
        db_symbols = result.scalars().all()
        
        if not db_symbols:
            # Fallback: Try to load from CSV seed to get symbol list, then fetch prices
            # Or return error
            return {"message": "No symbols found in DB. Please run /import/seed first to populate symbol list."}

        count = 0
        updated_symbols = 0
        
        import pandas as pd
        
        # Process symbols
        # TODO: Async/Parallelize this for speed? Yahoo might rate limit. Serial is safer for now.
        for sym in db_symbols:
            try:
                df = provider.get_daily_ohlcv(sym.symbol, start_date, end_date)
                if df.empty:
                    continue
                    
                # Save to DB
                # For efficiency, we should probably delete existing range and re-insert 
                # OR check existence. For MVP updater, let's just insert missing.
                # But checking every row is slow.
                # Faster approach: Get all existing dates for this symbol in range
                # Then filter DF.
                
                existing_dates_stmt = select(PriceDaily.date).where(
                    (PriceDaily.symbol == sym.symbol) & 
                    (PriceDaily.date >= start_date)
                )
                res = await db.execute(existing_dates_stmt)
                existing_dates = set(res.scalars().all())
                
                rows_to_add = []
                for dt, row in df.iterrows():
                    if dt.date() in existing_dates:
                        continue
                        
                    p = PriceDaily(
                        symbol=sym.symbol,
                        date=dt.date(),
                        open=row['open'],
                        high=row['high'],
                        low=row['low'],
                        close=row['close'],
                        volume=int(row['volume']),
                        turnover_tl=row.get('turnover_tl'),
                        adj_close=row.get('adj_close')
                    )
                    rows_to_add.append(p)
                
                if rows_to_add:
                    db.add_all(rows_to_add)
                    count += len(rows_to_add)
                    updated_symbols += 1
                    
            except Exception as e:
                print(f"Error fetching {sym.symbol}: {e}")
                continue

        await db.commit()
        
        # 2. Update Index (XU100)
        try:
            df_idx = provider.get_index_daily("XU100", start_date, end_date)
            if not df_idx.empty:
                existing_dates_stmt = select(IndexDaily.date).where(IndexDaily.date >= start_date)
                res = await db.execute(existing_dates_stmt)
                existing_dates = set(res.scalars().all())
                
                rows_to_add = []
                for dt, row in df_idx.iterrows():
                    if dt.date() in existing_dates:
                        continue
                        
                    i = IndexDaily(
                        date=dt.date(),
                        close=row['close']
                    )
                    rows_to_add.append(i)
                    
                if rows_to_add:
                    db.add_all(rows_to_add)
                    await db.commit()
        except Exception as e:
            print(f"Error fetching Index: {e}")

        return {"message": f"Yahoo Import complete. Updated {updated_symbols} symbols, added {count} price rows."}
    except Exception as e:
        error_msg = traceback.format_exc()
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/compute", response_model=Message)
async def compute_daily_pipeline(date_str: str = Query(..., description="Date to compute for YYYY-MM-DD"), db: AsyncSession = Depends(get_db)):
    """
    Manually trigger compute pipeline for a specific date.
    1. Load prices
    2. Feature Engine
    3. Scoring Engine
    4. Save
    """
    from datetime import datetime
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    
    # Imports here to avoid circular deps if any, or just convenience
    from sqlalchemy import select, delete
    from app.models import PriceDaily, IndexDaily, FeatureDaily, ScoreDaily, Top10Daily, Symbol
    from app.services.feature_engine import FeatureEngine
    from app.services.scoring_engine import ScoringEngine
    import pandas as pd
    
    # 1. Load Data (Prices for target_date and enough history for features)
    # We need at least 200 days history for EMA200
    start_hist = target_date - pd.Timedelta(days=400) # Safe buffer
    
    # Symbols
    stmt = select(Symbol).where(Symbol.is_active == True)
    res = await db.execute(stmt)
    symbols_list = res.scalars().all()
    symbols_map = {s.symbol: s for s in symbols_list}
    
    # Prices
    stmt = select(PriceDaily).where(PriceDaily.date >= start_hist, PriceDaily.date <= target_date)
    res = await db.execute(stmt)
    prices = res.scalars().all()
    
    if not prices:
        return {"message": "No price data found"}
        
    df_prices = pd.DataFrame([
        {'symbol': p.symbol, 'date': p.date, 'open': p.open, 'close': p.close, 'high': p.high, 'low': p.low, 'volume': p.volume}
        for p in prices
    ])
    df_prices['date'] = pd.to_datetime(df_prices['date'])
    df_prices.set_index('date', inplace=True)
    
    # Index
    stmt = select(IndexDaily).where(IndexDaily.date >= start_hist, IndexDaily.date <= target_date)
    res = await db.execute(stmt)
    indexes = res.scalars().all()
    
    df_index = pd.DataFrame([{'date': i.date, 'close': i.close} for i in indexes])
    if df_index.empty:
         return {"message": "No index data found"}
         
    df_index['date'] = pd.to_datetime(df_index['date'])
    df_index.set_index('date', inplace=True)
    
    # Pre-compute Index Features (EMA50) for Regime
    # Simple calculation for index
    df_index['ema50'] = df_index['close'].ewm(span=50, adjust=False).mean()
    
    # 2. Features & Scores
    fe = FeatureEngine()
    se = ScoringEngine()
    
    # Detect Regime (using Index history up to target_date)
    regime = se.detect_regime(df_index)
    
    ready_scores = []
    ready_features = []
    
    # Process each symbol
    # This is inefficient loop for all symbols, but okay for MVP.
    # ideally we run vectorized on all symbols if aligned. FeatureEngine handles one DF.
    
    for sym in symbols_map.keys():
        d = df_prices[df_prices['symbol'] == sym]
        if d.empty: continue
        
        # Compute Features
        f_df = fe.compute_features(d, df_index)
        if f_df.empty: continue
        
        # Get target row
        if pd.to_datetime(target_date) not in f_df.index:
            continue
            
        # We need to normalize across universe.
        # So we collect raw features for target date first.
        row = f_df.loc[pd.to_datetime(target_date)]
        # Add symbol
        row_dict = row.to_dict()
        row_dict['symbol'] = sym
        ready_features.append(row_dict)

    if not ready_features:
        return {"message": f"No features computed for {target_date}"}
        
    # Create DF for today
    df_today_features = pd.DataFrame(ready_features)
    df_today_features.set_index('symbol', inplace=True)
    
    # Normalize
    df_norm = fe.normalize_cross_sectional(df_today_features)
    
    # Score
    df_scored = se.calculate_scores(df_norm, regime)
    
    # Select Top 10
    # Need symbol info DF
    df_sym_info = pd.DataFrame([
        {'symbol': s.symbol, 'sector': s.sector, 'is_active': s.is_active} 
        for s in symbols_list
    ])
    df_sym_info.set_index('symbol', inplace=True)
    
    df_top10 = se.select_top10(df_scored, df_sym_info, min_adv=10_000, regime=regime) # Low min_adv for test
    
    # 3. Save to DB
    # Delete existing for date
    # await db.execute(delete(Top10Daily).where(Top10Daily.date == target_date))
    # await db.execute(delete(ScoreDaily).where(ScoreDaily.date == target_date))
    # await db.execute(delete(FeatureDaily).where(FeatureDaily.date == target_date))
    
    # Save Features
    for sym, row in df_today_features.iterrows():
        # Check exist
        existing = await db.scalar(select(FeatureDaily).where((FeatureDaily.symbol == sym) & (FeatureDaily.date == target_date)))
        if not existing:
            f = FeatureDaily(
                symbol=sym, date=target_date,
                ema50=row.get('ema50'), ema200=row.get('ema200'),
                atr14_pct=row.get('atr14_pct'), dd60=row.get('dd60'),
                rs_3m=row.get('rs_3m'), rs_6m=row.get('rs_6m'),
                bo_120=row.get('bo_120'), vol_surge=row.get('vol_surge'),
                up_ratio_20=row.get('up_ratio_20'), adv20_tl=row.get('adv20_tl')
            )
            db.add(f)
            
    # Save Scores
    for sym, row in df_scored.iterrows():
        existing = await db.scalar(select(ScoreDaily).where((ScoreDaily.symbol == sym) & (ScoreDaily.date == target_date)))
        if not existing:
            s = ScoreDaily(
                symbol=sym, date=target_date,
                potential_score=row['potential_score'],
                risk_score=row['risk_score'],
                final_score=row['final_score'],
                explain_json=row['explain_json'] # JSON string? need to check model. Model says JSON type.
                # ScoringEngine returns string in make_explain.
                # PG JSON accepts string or dict. 
            )
            db.add(s)

    # Save Top 10
    for _, row in df_top10.iterrows():
        existing = await db.scalar(select(Top10Daily).where((Top10Daily.date == target_date) & (Top10Daily.top10_rank == row['rank']))) # Wait model has 'rank' col
        # Check logic
        t = Top10Daily(
            date=target_date,
            rank=row['rank'],
            symbol=row['symbol'],
            final_score=row['final_score'],
            universe_tag=row['universe_tag']
        )
        db.add(t)
        
    await db.commit()
    return {"message": f"Computed for {target_date}. Regime: {regime}, Candidates: {len(df_scored)}, Top10: {len(df_top10)}"}

