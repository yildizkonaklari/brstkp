from pydantic import BaseModel
from datetime import date
from typing import Optional, Dict

class SymbolResponse(BaseModel):
    symbol: str
    name: Optional[str] = None
    sector: Optional[str] = None
    is_active: bool

class Top10Item(BaseModel):
    rank: int
    symbol: str
    final_score: float
    # We can enrich with name/sector in service
    
class ScoreDetail(BaseModel):
    symbol: str
    date: date
    potential_score: float
    risk_score: float
    final_score: float
    explain_json: Optional[Dict] = None

class SignalResponse(BaseModel):
    date: date
    regime: str
    top10: list[Top10Item]
