from sqlalchemy import Column, String, Boolean, Date
from app.database import Base

class Symbol(Base):
    __tablename__ = "symbols"

    symbol = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=True)
    sector = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    list_start_date = Column(Date, nullable=True)
