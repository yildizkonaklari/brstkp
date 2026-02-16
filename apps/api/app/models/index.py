from sqlalchemy import Column, Date, Float
from app.database import Base

class IndexDaily(Base):
    __tablename__ = "index_daily"

    date = Column(Date, primary_key=True)
    close = Column(Float, nullable=False)
    return_1d = Column(Float, nullable=True)
    ema50 = Column(Float, nullable=True)
    ema200 = Column(Float, nullable=True)
