from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import logging
import uvicorn
from services.nfse_service import NFSeService
from services.database_service import DatabaseService


# Force o Python a usar o WindowsSelectorEventLoopPolicy
import sys
import asyncio

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Criar instância do FastAPI
app = FastAPI(
    title="NFSe API Headless",
    description="API para emissão de NFSe em segundo plano usando web scraping headless",
    version="1.0.0"
)

# Configurar CORS para permitir requisições de qualquer origem
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos Pydantic para validação de dados
class NFSeRequest(BaseModel):
    cnpj_emissor: str
    senha_emissor: str
    data_emissao: str  # formato: DD/MM/YYYY
    cnpj_cliente: str
    telefone_cliente: str
    email_cliente: str
    valor: float
    cnae_code: str
    cnae_service: str
    city: str  # formato: "Cidade/Estado"
    descricao_servico: str

class NFSeResponse(BaseModel):
    success: bool
    message: str
    uuid: Optional[str] = None
    numero_nfse: Optional[str] = None
    pdf_url: Optional[str] = None
    xml_url: Optional[str] = None

class StatusResponse(BaseModel):
    status: str
    message: str

# Instanciar serviços
nfse_service = NFSeService()
db_service = DatabaseService()

@app.get("/", response_model=StatusResponse)
async def root():
    """
    Endpoint raiz da API
    """
    return StatusResponse(
        status="online",
        message="NFSe API Headless está funcionando corretamente"
    )

@app.get("/health", response_model=StatusResponse)
async def health_check():
    """
    Endpoint de health check para monitoramento
    """
    return StatusResponse(
        status="healthy",
        message="API está saudável e operacional"
    )

@app.post("/api/emitir-nfse", response_model=NFSeResponse)
async def emitir_nfse(request: NFSeRequest, background_tasks: BackgroundTasks):
    """
    Endpoint principal para emissão de NFSe
    """
    try:
        logger.info(f"Recebida requisição de emissão para CNPJ: {request.cnpj_emissor}")
        
        # Converter request para dict
        data = request.model_dump()
        
        # Criar registro no banco de dados
        nfse_record = db_service.create_nfse(data)
        db_service.create_log(nfse_record["uuid"], "PROCESSING", "Iniciando emissão")
        
        # Executar emissão em background
        background_tasks.add_task(
            process_nfse_emission, 
            nfse_record["uuid"], 
            data
        )
        
        return NFSeResponse(
            success=True,
            message="Emissão de NFSe iniciada. Verifique o status usando o UUID fornecido.",
            uuid=nfse_record["uuid"]
        )
        
    except Exception as e:
        logger.error(f"Erro na requisição de emissão: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")


@app.get("/api/nfse/{uuid}", response_model=dict)
async def get_nfse(uuid: str):
    """
    Endpoint para consultar uma NFSe pelo UUID
    """
    logger.info(f"🔍 Buscando no banco de dados MySQL o UUID: {uuid}")

    try:
        nfse = db_service.get_nfse(uuid)
        if not nfse:
            raise HTTPException(status_code=404, detail="NFSe não encontrada")
        
        return {
            "success": True,
            "data": nfse
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar NFSe: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")

@app.get("/api/nfse/{uuid}/logs", response_model=dict)
async def get_nfse_logs(uuid: str):
    """
    Endpoint para buscar logs de uma NFSe
    """
    try:
        logs = db_service.get_logs(uuid)
        return {
            "success": True,
            "data": logs
        }
        
    except Exception as e:
        logger.error(f"Erro ao buscar logs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")

@app.get("/api/nfses", response_model=dict)
async def list_nfses(limit: int = 50, offset: int = 0, status: Optional[str] = None):
    """
    Endpoint para listar NFSes com paginação e filtros
    """
    try:
        nfses = db_service.list_nfses(limit=limit, offset=offset, status=status)
        
        return {
            "success": True,
            "data": nfses,
            "pagination": {
                "limit": limit,
                "offset": offset
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao listar NFSes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro interno do servidor: {str(e)}")

async def process_nfse_emission(uuid: str, data: dict):
    """
    Função para processar a emissão de NFSe em background
    """
    try:
        logger.info(f"Iniciando processamento da NFSe {uuid}")
        
        # Emitir a NFSe usando o serviço
        result = await nfse_service.emitir_nfse(data)
        
        if result["success"]:
            # Atualizar registro com sucesso
            db_service.update_nfse(uuid, {
                "numero_nfse": result.get("numero_nfse"),
                "pdf_url": result.get("pdf_path"),
                "xml_url": result.get("xml_path"),
                "status": "SUCCESS"
            })
            db_service.create_log(uuid, "SUCCESS", "NFSe emitida com sucesso")
            logger.info(f"NFSe {uuid} emitida com sucesso")
        else:
            # Atualizar registro com erro
            db_service.update_nfse(uuid, {
                "status": "ERROR"
            })
            db_service.create_log(uuid, "ERROR", result.get("message"))
            logger.error(f"Erro na emissão da NFSe {uuid}: {result.get('message')}")
            
    except Exception as e:
        logger.error(f"Erro no processamento da NFSe {uuid}: {str(e)}")
        db_service.update_nfse(uuid, {
            "status": "ERROR"
        })
        db_service.create_log(uuid, "ERROR", f"Erro no processamento: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

