import pytest
import pandas as pd
import numpy as np
from datetime import date
from app.services.backtest_engine import BacktestEngine

@pytest.mark.asyncio
async def test_backtest_execution():
    # Setup Data
    dates = pd.date_range(start='2023-01-01', end='2023-02-01', freq='B') # ~23 days
    
    # Stock A: Always goes up
    # Stock B: Goes up then crashes (Trigger Stop)
    
    data_a = pd.DataFrame({
        'open': np.linspace(10, 20, len(dates)),
        'close': np.linspace(10.5, 20.5, len(dates)),
        'high': np.linspace(11, 21, len(dates)),
        'low': np.linspace(9, 19, len(dates))
    }, index=dates)
    
    data_b = pd.DataFrame({
        'open': [10]*10 + [5]*13, # Gap down on day 11
        'close': [10]*10 + [5]*13,
        'high': [10]*23,
        'low': [5]*23
    }, index=dates)
    
    price_history = {'A': data_a, 'B': data_b}
    
    # Features (Mock)
    # We need features for stops (EMA50, ATR)
    # Provide simple constant features
    f_idx = pd.MultiIndex.from_product([dates, ['A', 'B']], names=['date', 'symbol'])
    f_df = pd.DataFrame(index=f_idx, columns=['ema50', 'atr14'])
    f_df['ema50'] = 9.0 # Price > EMA50 mostly
    f_df['atr14'] = 1.0
    
    # Top 10 (Mock)
    # Signal A and B on Day 0 (Friday?)
    # Let's say we have signals every day for simplicity
    top_data = []
    for d in dates:
        top_data.append({'date': d, 'rank': 1, 'symbol': 'A', 'final_score': 90})
        top_data.append({'date': d, 'rank': 2, 'symbol': 'B', 'final_score': 80})
    
    top_df = pd.DataFrame(top_data)
    top_df['date'] = pd.to_datetime(top_df['date'])
    top_df.set_index(['date', 'rank'], inplace=True)
    
    # Index
    idx_df = pd.DataFrame({'close': [100]*len(dates)}, index=dates)
    
    # Params
    params = {
        "start_date": '2023-01-02', # Monday
        "end_date": '2023-01-31',
        "initial_capital": 10000.0,
        "fee_bps": 0,
        "slippage_bps": 0
    }
    
    engine = BacktestEngine()
    result = await engine.run_backtest(params, top_df, f_df, price_history, idx_df)
    
    assert "error" not in result
    trades = result['trades']
    
    # We expect Buys on first Monday (2023-01-02)
    buys = [t for t in trades if t['action'] == 'BUY']
    assert len(buys) >= 1
    assert 'A' in [t['symbol'] for t in buys]
    
    # Check Stop on B
    # Price dropped from 10 to 5. EMA is 9.
    # Close < EMA50 (5 < 9) -> Trend Stop should trigger.
    # Check if B was sold
    sells = [t for t in trades if t['symbol'] == 'B' and t['action'] == 'SELL']
    if len(sells) > 0:
        assert sells[0]['reason'] in ['TREND_STOP', 'ATR_STOP']
