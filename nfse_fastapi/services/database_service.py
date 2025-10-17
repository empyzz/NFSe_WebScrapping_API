import logging
from datetime import datetime, date
import uuid
from typing import Dict, Any, List, Optional
import os
from dotenv import load_dotenv
from config.settings import settings
from sqlalchemy import create_engine, text, desc
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from models.base import Base
from models.invoice import Invoice
from models.log import Log

load_dotenv()

# Configurar logging

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        self.database_url = settings.get_database_url()
        connect_args = {}
        if self.database_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}

        self.engine = create_engine(self.database_url, connect_args=connect_args, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(bind=self.engine, autocommit=False, autoflush=False)
        Base.metadata.create_all(self.engine)


    ''' # Validação básica para evitar erro silencioso
        missing_vars = [k for k, v in self.db_config.items() if not v]
        if missing_vars:
            raise ValueError(f"Variáveis de ambiente faltando: {', '.join(missing_vars)}")

        logger.info("Conectando com as configurações do banco de dados:")
        logger.info(self.db_config)

        # Tenta conectar ao banco para validar a configuração
        try:
            self.connection = mysql.connector.connect(**self.db_config)
            if self.connection.is_connected():
                db_Info = self.connection.get_server_info()
                logger.info(f"Conectado ao MySQL Server versão {db_Info}")
        except Error as e:
            logger.error(f"Erro ao conectar ao MySQL: {e}")
            raise

    def close_connection(self):
        """Fecha a conexão com o banco de dados."""
        if self.connection.is_connected():
            self.connection.close()
            logger.info("Conexão com o banco de dados encerrada.")'''
    
    def get_session(self) -> Session:
        return self.SessionLocal()
    

    def create_nfse(self, data: Dict[str, Any]) -> Dict[str, Any]:
        session = self.get_session()
        try:
            nfse_uuid = str(uuid.uuid4())
            data_emissao = datetime.strptime(data['data_emissao'], '%d/%m/%Y').date()

            insert_sql = text("""
            INSERT INTO invoices (
                uuid, cnpj, date, client_cnpj, client_phone, client_email,
                invoice_value, cnae_code, cnae_service, city, invoice_description, status, created_at, updated_at
            ) VALUES (
                :uuid, :cnpj, :date, :client_cnpj, :client_phone, :client_email,
                :invoice_value, :cnae_code, :cnae_service, :city, :invoice_description, :status, :created_at, :updated_at
            )
            """)

            params = {
                "uuid": nfse_uuid,
                "cnpj": data['cnpj_emissor'],
                "date": data_emissao,
                "client_cnpj": data['cnpj_cliente'],
                "client_phone": data['telefone_cliente'],
                "client_email": data['email_cliente'],
                "invoice_value": float(data['valor']),
                "cnae_code": data['cnae_code'],
                "cnae_service": data['cnae_service'],
                "city": data['city'],
                "invoice_description": data['descricao_servico'],
                "status": "PROCESSING",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

            session.execute(insert_sql, params)
            session.commit()

            result = session.execute(text("SELECT id FROM invoices WHERE uuid = :uuid"), {"uuid": nfse_uuid})
            nfse_id = result.scalar_one_or_none()

            logger.info(f"NFSe criada com UUID: {nfse_uuid}, ID: {nfse_id}")

            return {"id": nfse_id, "uuid": nfse_uuid, "status": "PROCESSING"}

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Erro ao criar NFSe: {e}")
            raise
        finally:
            session.close()

    
    def update_nfse(self, nfse_uuid: str, updates: Dict[str, Any]) -> bool:
        """
        Atualiza um registro de NFSe (tabela invoices) usando SQLAlchemy Core.
        Aceita somente os campos definidos em `allowed_fields`.
        """
        allowed_fields = {"numero_nfse", "pdf_url", "xml_url", "status"}
        set_fields = {k: v for k, v in updates.items() if k in allowed_fields}

        if not set_fields:
            return False  # nada a atualizar

        # Adiciona updated_at
        set_fields["updated_at"] = datetime.utcnow()
        set_fields["uuid"] = nfse_uuid  # usado na cláusula WHERE

        # Gera a parte SET dinâmica:  "campo1 = :campo1, campo2 = :campo2 ..."
        set_clause = ", ".join(f"{field} = :{field}" for field in set_fields if field != "uuid")

        sql = text(f"UPDATE invoices SET {set_clause} WHERE uuid = :uuid")

        session = self.get_session()
        try:
            result = session.execute(sql, set_fields)
            session.commit()

            updated = result.rowcount > 0
            if updated:
                logger.info("NFSe atualizada: %s", nfse_uuid)
            return updated

        except SQLAlchemyError as e:
            session.rollback()
            logger.error("Erro ao atualizar NFSe: %s", e)
            raise
        finally:
            session.close()

    
    def get_nfse(self, nfse_uuid: str) -> Optional[Dict[str, Any]]:
        session = self.get_session()
        try:
            nfse = session.query(Invoice).filter(Invoice.uuid == nfse_uuid).first()
            if not nfse:
                return None

            return {
                "id": nfse.id,
                "uuid": nfse.uuid,
                "cnpj": nfse.cnpj,
                "date": nfse.date.strftime("%d/%m/%Y") if nfse.date else None,
                "client_cnpj": nfse.client_cnpj,
                "client_phone": nfse.client_phone,
                "client_email": nfse.client_email,
                "invoice_value": float(nfse.invoice_value) if nfse.invoice_value else None,
                "cnae_code": nfse.cnae_code,
                "cnae_service": nfse.cnae_service,
                "city": nfse.city,
                "invoice_description": nfse.invoice_description,
                "numero_nfse": nfse.numero_nfse,
                "pdf_url": nfse.pdf_url,
                "xml_url": nfse.xml_url,
                "status": nfse.status,
                "created_at": nfse.created_at.isoformat() if nfse.created_at else None,
                "updated_at": nfse.updated_at.isoformat() if nfse.updated_at else None,
            }
        finally:
            session.close()

    
    def list_nfses(self, limit: int = 50, offset: int = 0, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lista NFSes com paginação e filtro opcional por status.
        """
        session: Session = self.get_session()
        try:
            query = session.query(Invoice)

            if status:
                query = query.filter(Invoice.status == status)

            query = query.order_by(desc(Invoice.created_at)).limit(limit).offset(offset)
            nfses = query.all()

            formatted_results = []
            for nfse in nfses:
                # Formatando campos que são datetime ou date
                formatted_results.append({
                    "id": nfse.id,
                    "uuid": nfse.uuid,
                    "cnpj": nfse.cnpj,
                    "date": nfse.date.strftime("%d/%m/%Y") if isinstance(nfse.date, (datetime, date)) else nfse.date,
                    "client_cnpj": nfse.client_cnpj,
                    "client_phone": nfse.client_phone,
                    "client_email": nfse.client_email,
                    "invoice_value": float(nfse.invoice_value) if nfse.invoice_value is not None else None,
                    "cnae_code": nfse.cnae_code,
                    "cnae_service": nfse.cnae_service,
                    "city": nfse.city,
                    "invoice_description": nfse.invoice_description,
                    "numero_nfse": nfse.numero_nfse,
                    "pdf_url": nfse.pdf_url,
                    "xml_url": nfse.xml_url,
                    "status": nfse.status,
                    "created_at": nfse.created_at.isoformat() if isinstance(nfse.created_at, (datetime, date)) else nfse.created_at,
                    "updated_at": nfse.updated_at.isoformat() if isinstance(nfse.updated_at, (datetime, date)) else nfse.updated_at,
                })

            return formatted_results

        except Exception as e:
            logger.error(f"Erro ao listar NFSes: {e}")
            raise
        finally:
            session.close()
    

    def create_log(self, nfse_uuid: str, status: str, message: Optional[str] = None) -> bool:
        """
        Cria um log para uma NFSe na tabela `logs`.
        """
        session = self.get_session()
        try:
            insert_sql = text("""
                INSERT INTO logs (invoice_id, status, reason, created_at)
                VALUES (:invoice_id, :status, :reason, :created_at)
            """)

            params = {
                "invoice_id": nfse_uuid,
                "status": status,
                "reason": message,
                "created_at": datetime.utcnow(),
            }

            session.execute(insert_sql, params)
            session.commit()

            logger.info(f"Log criado para NFSe {nfse_uuid}: {status}")
            return True

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Erro ao criar log: {str(e)}")
            raise
        finally:
            session.close()

    
    def get_logs(self, nfse_uuid: str) -> List[Dict[str, Any]]:
        session = self.get_session()
        try:
            logs = session.query(Log).filter(Log.invoice_id == nfse_uuid).order_by(Log.created_at.desc()).all()

            return [
                {
                    "id": log.id,
                    "invoice_id": log.invoice_id,
                    "status": log.status,
                    "reason": log.reason,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in logs
            ]
        finally:
            session.close()
    

    def get_emission_data(self) -> Optional[Dict[str, Any]]:
        """
        Busca as informações para emissão da nota (1ª na fila com status 'QUEUED').
        """
        session = self.get_session()
        try:
            query = text("""
                SELECT i.id, i.uuid, i.cnpj, iq.password, i.date, i.client_cnpj, 
                    i.client_phone, i.client_email, i.invoice_value, i.cnae_code, 
                    i.cnae_service, i.city, i.invoice_description, i.status 
                FROM invoices i
                JOIN invoice_queue iq ON i.uuid = iq.invoice_id
                WHERE i.status = 'QUEUED'
                LIMIT 1
            """)

            result = session.execute(query).mappings().first()

            if result:
                row = dict(result)
                if row.get("date"):
                    row["date"] = row["date"].strftime("%d/%m/%Y")
                if row.get("invoice_value") is not None:
                    row["invoice_value"] = float(row["invoice_value"])
                return row

            return None

        except SQLAlchemyError as e:
            logger.error(f"Erro ao buscar dados de emissão: {e}")
            return None
        finally:
            session.close()
