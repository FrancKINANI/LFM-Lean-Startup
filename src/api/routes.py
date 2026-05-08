from fastapi import APIRouter, HTTPException, Depends
import logging
from src.api.schemas import QueryRequest, QueryResponse, HealthResponse
from src.inference.pipeline import LeanStartupAnalystPipeline
from src.database.client import health_check

logger = logging.getLogger(__name__)
router = APIRouter()

# Chargement du modèle en Lazy Loading (Singleton)
pipeline_instance = None

def get_pipeline():
    global pipeline_instance
    if pipeline_instance is None:
        try:
            logger.info("Initialisation du pipeline d'inférence (chargement du modèle)...")
            pipeline_instance = LeanStartupAnalystPipeline()
        except Exception as e:
            logger.error(f"Erreur de chargement du modèle : {e}")
            raise HTTPException(status_code=500, detail=f"Failed to load model: {e}")
    return pipeline_instance

@router.get("/health", response_model=HealthResponse)
def get_health():
    """Vérifie l'état de l'API et de la base de données PostgreSQL."""
    db_health = health_check()
    if db_health.get("status") == "error":
        raise HTTPException(status_code=503, detail=db_health)
    return db_health

@router.post("/analyze", response_model=QueryResponse)
def analyze_startup(request: QueryRequest, pipe: LeanStartupAnalystPipeline = Depends(get_pipeline)):
    """
    Point d'entrée principal. Le LLM analyse la requête en utilisant potentiellement ses outils (Tool Use).
    """
    try:
        response = pipe.run(user_query=request.query, system_prompt=request.system_prompt)
        return QueryResponse(answer=response, tool_calls=[]) # Note: L'extraction exacte des outils appelés pourrait être enrichie
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse : {e}")
        raise HTTPException(status_code=500, detail=str(e))
