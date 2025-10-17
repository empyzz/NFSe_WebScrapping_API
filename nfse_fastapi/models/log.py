from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from models.base import Base  # IMPORTA base única

class Log(Base):
    __tablename__ = 'logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(String, ForeignKey('invoices.uuid'), nullable=False)
    status = Column(String, nullable=False)
    reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)