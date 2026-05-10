"""
src/api/main.py
===============
Point d'entrée de l'API FastAPI.

Responsabilités :
    - Créer l'application FastAPI avec ses métadonnées
    - Gérer le cycle de vie : charger le modèle au démarrage,
      libérer les ressources à l'arrêt (lifespan)
    - Enregistrer les routers
    - Configurer CORS, logging, middleware
    - Exposer l'app pour Uvicorn

Démarrage :
    uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

Docker :
    CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import analysis_router, data_router, system_router, set_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# =============================================================================
# LIFESPAN — CHARGEMENT DU MODÈLE AU DÉMARRAGE
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestion du cycle de vie de l'application.

    Remplace les événements @app.on_event("startup") dépréciés dans FastAPI.

    STARTUP :
        - Charge le pipeline d'inférence (modèle + tokenizer) en mémoire
        - Le chargement prend 10-30 secondes selon le GPU
        - L'API répond /health avec status="degraded" pendant ce temps

    SHUTDOWN :
        - Libère la mémoire GPU
        - Ferme le pool de connexions PostgreSQL
    """
    # ---- STARTUP ----
    logger.info("=" * 60)
    logger.info("Démarrage de LFM Lean Startup API")
    logger.info("=" * 60)

    # Charger le modèle uniquement si le chemin existe
    model_path = os.getenv("MODEL_PATH", "models/lfm25-350m-lean")

    if os.path.exists(model_path):
        try:
            from src.inference import LeanStartupPipeline, PipelineConfig

            config = PipelineConfig(model_path=model_path)
            pipeline = LeanStartupPipeline(config=config)

            logger.info("Chargement du modèle : %s ...", model_path)
            pipeline.load()

            set_pipeline(pipeline)
            logger.info("✅ Modèle chargé avec succès.")

        except Exception as e:
            logger.error(
                "❌ Échec du chargement du modèle : %s\n"
                "L'API démarre en mode dégradé — /health retournera status='degraded'.",
                e
            )
    else:
        logger.warning(
            "Modèle non trouvé : %s\n"
            "L'API démarre sans modèle. Endpoints /analyze et /concept indisponibles.",
            model_path
        )

    logger.info("API prête. Documentation : http://localhost:8000/docs")

    yield  # ← l'application tourne ici

    # ---- SHUTDOWN ----
    logger.info("Arrêt de l'API en cours...")

    from src.database.client import _ConnectionPool
    _ConnectionPool.close()
    logger.info("Pool PostgreSQL fermé.")

    logger.info("API arrêtée proprement.")


# =============================================================================
# APPLICATION FASTAPI
# =============================================================================

app = FastAPI(
    title="LFM Lean Startup API",
    description=(
        "API d'analyse de startups basée sur LFM2.5-350M fine-tuné. "
        "Identifie les risques critiques, évalue les opportunités d'investissement "
        "et rend accessibles les concepts Lean Startup en langage simple. "
        "\n\n"
        "**Sources de données :**\n"
        "- Modèle LFM2.5-350M fine-tuné sur données Lean Startup\n"
        "- Base PostgreSQL : patterns de risque, benchmarks sectoriels, "
        "cas de startups, critères d'investissement\n\n"
        "**Profils investisseurs supportés :**\n"
        "`angel` · `vc` · `impact` · `strategic` · `entrepreneur` · `both`"
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "Analyse IA",
            "description": "Endpoints d'analyse utilisant le modèle fine-tuné.",
        },
        {
            "name": "Données de référence",
            "description": "Accès direct à la base PostgreSQL (risques, benchmarks, concepts).",
        },
        {
            "name": "Système",
            "description": "Health check et métadonnées de l'API.",
        },
    ],
)

# =============================================================================
# MIDDLEWARE
# =============================================================================

# CORS — autoriser les appels depuis un frontend
ALLOWED_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:8080"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# =============================================================================
# ROUTERS
# =============================================================================

app.include_router(system_router)
app.include_router(analysis_router)
app.include_router(data_router)
