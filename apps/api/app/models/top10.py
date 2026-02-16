from sqlalchemy import Column, String, Date, Float, Integer, ForeignKey, PrimaryKeyConstraint
from app.database import Base

class Top10Daily(Base):
    __tablename__ = "top10_daily"

    date = Column(Date, nullable=False)
    rank = Column(Integer, nullable=False)
    symbol = Column(String, ForeignKey("symbols.symbol"), nullable=False)
    final_score = Column(Float, nullable=False)
    universe_tag = Column(String, nullable=True) # e.g. "ALL", "LIQUID"

    __table_args__ = (
        PrimaryKeyConstraint('date', 'rank'),
    )
