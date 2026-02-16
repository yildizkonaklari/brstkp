from sqlalchemy import Column, String, Date, Float, ForeignKey, PrimaryKeyConstraint
from app.database import Base

class FeatureDaily(Base):
    __tablename__ = "features_daily"

    symbol = Column(String, ForeignKey("symbols.symbol"), nullable=False)
    date = Column(Date, nullable=False)
    
    ema50 = Column(Float, nullable=True)
    ema200 = Column(Float, nullable=True)
    atr14_pct = Column(Float, nullable=True)
    dd60 = Column(Float, nullable=True)
    rs_3m = Column(Float, nullable=True)
    rs_6m = Column(Float, nullable=True)
    bo_120 = Column(Float, nullable=True)
    vol_surge = Column(Float, nullable=True)
    up_ratio_20 = Column(Float, nullable=True)
    adv20_tl = Column(Float, nullable=True)

    __table_args__ = (
        PrimaryKeyConstraint('symbol', 'date'),
    )
