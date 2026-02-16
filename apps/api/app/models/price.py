from sqlalchemy import Column, String, Date, Float, BigInteger, ForeignKey, PrimaryKeyConstraint
from app.database import Base

class PriceDaily(Base):
    __tablename__ = "prices_daily"

    symbol = Column(String, ForeignKey("symbols.symbol"), nullable=False)
    date = Column(Date, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=False)
    turnover_tl = Column(Float, nullable=True)
    adj_close = Column(Float, nullable=True)

    __table_args__ = (
        PrimaryKeyConstraint('symbol', 'date'),
    )
