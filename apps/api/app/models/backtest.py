from sqlalchemy import Column, String, Date, Float, Integer, ForeignKey, JSON, DateTime, func
from app.database import Base

class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    run_id = Column(String, primary_key=True)
    created_at = Column(DateTime, server_default=func.now())
    params_json = Column(JSON, nullable=False)
    status = Column(String, default="PENDING") # PENDING, RUNNING, COMPLETED, FAILED

class BacktestTrade(Base):
    __tablename__ = "backtest_trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, ForeignKey("backtest_runs.run_id"), nullable=False)
    date = Column(Date, nullable=False)
    symbol = Column(String, nullable=False)
    action = Column(String, nullable=False) # BUY, SELL
    qty = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    fee = Column(Float, default=0.0)
    slippage = Column(Float, default=0.0)
    reason = Column(String, nullable=True)

class BacktestEquity(Base):
    __tablename__ = "backtest_equity_curve"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, ForeignKey("backtest_runs.run_id"), nullable=False)
    date = Column(Date, nullable=False)
    equity = Column(Float, nullable=False)
    benchmark_equity = Column(Float, nullable=True)
