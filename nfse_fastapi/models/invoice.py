from sqlalchemy import Column, Integer, String, Date, DateTime, Float, Text
from datetime import datetime, timezone
from models.base import Base  # IMPORTA base única

class Invoice(Base):
    __tablename__ = 'invoices'

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String, unique=True, nullable=False)
    cnpj = Column(String)
    date = Column(Date)
    client_cnpj = Column(String)
    client_phone = Column(String)
    client_email = Column(String)
    invoice_value = Column(Float)
    cnae_code = Column(String)
    cnae_service = Column(String)
    city = Column(String)
    invoice_description = Column(Text)
    numero_nfse = Column(String)
    pdf_url = Column(String)
    xml_url = Column(String)
    status = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
