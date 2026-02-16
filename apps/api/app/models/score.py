from sqlalchemy import Column, String, Date, Float, JSON, ForeignKey, PrimaryKeyConstraint
from app.database import Base

class ScoreDaily(Base):
    __tablename__ = "scores_daily"

    symbol = Column(String, ForeignKey("symbols.symbol"), nullable=False)
    date = Column(Date, nullable=False)
    
    potential_score = Column(Float, nullable=True)
    risk_score = Column(Float, nullable=True)
    final_score = Column(Float, nullable=True)
    explain_json = Column(JSON, nullable=True)

    __table_args__ = (
        PrimaryKeyConstraint('symbol', 'date'),
    )
