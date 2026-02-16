from pydantic import BaseModel
from datetime import date, datetime
from typing import List, Optional, Dict, Any

class BacktestCreate(BaseModel):
    start_date: date
    end_date: date
    initial_capital: float = 100000.0
    fee_bps: float = 10.0
    slippage_bps: float = 8.0
    
class BacktestTradeResponse(BaseModel):
    date: date
    symbol: str
    action: str
    qty: float
    price: float
    reason: str

class BacktestEquityPoint(BaseModel):
    date: date
    equity: float
    benchmark_equity: Optional[float]

class BacktestResultResponse(BaseModel):
    run_id: str
    status: str
    metrics: Optional[Dict[str, Any]] = None
    trades: List[BacktestTradeResponse] = []
    equity_curve: List[BacktestEquityPoint] = []
