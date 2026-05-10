"""
src/api/routes.py
=================
Définition de tous les endpoints de l'API.

Organisation en trois routers :
    - analysis_router  : endpoints d'analyse IA (POST /analyze, POST /concept)
    - data_router      : endpoints de données PostgreSQL (GET /risks, /benchmarks)
    - system_router    : endpoints système (GET /health)

Chaque endpoint :
    1. Valide l'entrée via Pydantic (automatique avec FastAPI)
    2. Appelle la couche métier appropriée (pipeline ou queries)
    3. Retourne une réponse typée
    4. Gère les erreurs avec des codes HTTP explicites
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    BenchmarksResponse,
    BenchmarkItem,
    ConceptRequest,
    ConceptResponse,
    EvaluationResponse,
    HealthResponse,
    RiskItem,
    RisksResponse,
)
from src.database import health_check as db_health_check
from src.database import queries

logger = logging.getLogger(__name__)


# =============================================================================
# DÉPENDANCE : PIPELINE D'INFÉRENCE
# Le pipeline est instancié une seule fois dans main.py (lifespan)
# et injecté ici via FastAPI Dependency Injection
# =============================================================================

_pipeline_instance = None


def get_pipeline():
    """
    Dependency injection du pipeline d'inférence.
    Lève une HTTPException 503 si le modèle n'est pas encore chargé.
    """
    if _pipeline_instance is None or not _pipeline_instance.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Le modèle n'est pas encore chargé. Réessayez dans quelques secondes.",
        )
    return _pipeline_instance


def set_pipeline(pipeline) -> None:
    """Appelé par main.py lors du démarrage pour enregistrer le pipeline."""
    global _pipeline_instance
    _pipeline_instance = pipeline


# =============================================================================
# ROUTER 1 — ANALYSE IA
# =============================================================================

analysis_router = APIRouter(prefix="/api/v1", tags=["Analyse IA"])


@analysis_router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="Analyser une startup",
    description=(
        "Point d'entrée principal. Accepte une description libre d'une startup "
        "et retourne une analyse structurée : identification des risques critiques, "
        "évaluation de l'opportunité d'investissement, et recommandations actionnables. "
        "Le modèle consulte automatiquement la base PostgreSQL pour enrichir son analyse "
        "avec des benchmarks sectoriels et des cas similaires."
    ),
)
async def analyze_startup(
    request: AnalyzeRequest,
    pipeline=Depends(get_pipeline),
) -> AnalyzeResponse:
    """
    Analyse complète d'une startup à partir d'une description en texte libre.

    Le pipeline :
    1. Construit le contexte (system prompt + profil investisseur)
    2. Génère une première réponse (peut inclure des tool calls PostgreSQL)
    3. Exécute les tool calls et injecte les données
    4. Génère la réponse finale enrichie
    """
    from src.inference import AnalysisRequest

    logger.info(
        "Requête /analyze — profil: %s | longueur: %d chars",
        request.investor_profile,
        len(request.description),
    )

    analysis_request = AnalysisRequest(
        user_input=request.description,
        investor_profile=request.investor_profile.value,
        conversation_history=request.conversation_history,
    )

    response = pipeline.analyze(analysis_request)

    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur du pipeline d'inférence : {response.error}",
        )

    return AnalyzeResponse(
        analysis=response.final_answer,
        tool_calls_made=response.tool_calls_made,
        tool_calls_successful=response.tool_calls_successful,
        data_sources_used=response.data_sources_used,
    )


@analysis_router.post(
    "/concept",
    response_model=ConceptResponse,
    summary="Expliquer un concept Lean Startup",
    description=(
        "Retourne l'explication d'un concept Lean Startup depuis la base de données, "
        "avec deux niveaux : simple (accessible) et technique (niveau whitepaper). "
        "Utile pour rendre les termes complexes accessibles à tous les interlocuteurs."
    ),
)
async def explain_concept(request: ConceptRequest) -> ConceptResponse:
    """
    Explication d'un concept Lean Startup depuis PostgreSQL.
    Ne nécessite pas le modèle — requête directe à la base.
    """
    concept = queries.get_lean_concept(request.concept_name)

    if not concept:
        return ConceptResponse(
            concept_name=request.concept_name,
            found=False,
            simple_def=f"Concept '{request.concept_name}' non trouvé dans la base. "
                       f"Essayez avec un terme différent (ex: 'MVP', 'churn', 'pivot').",
        )

    if request.detail_level == "simple":
        return ConceptResponse(
            concept_name=concept["concept_name"],
            found=True,
            simple_def=concept.get("simple_def"),
            analogy=concept.get("analogy"),
            example=concept.get("example"),
            related_risks=concept.get("related_risks"),
            source=concept.get("source_whitepaper"),
        )
    else:
        return ConceptResponse(
            concept_name=concept["concept_name"],
            found=True,
            simple_def=concept.get("simple_def"),
            technical_def=concept.get("technical_def"),
            analogy=concept.get("analogy"),
            example=concept.get("example"),
            related_risks=concept.get("related_risks"),
            source=concept.get("source_whitepaper"),
        )


# =============================================================================
# ROUTER 2 — DONNÉES POSTGRESQL
# =============================================================================

data_router = APIRouter(prefix="/api/v1", tags=["Données de référence"])


@data_router.get(
    "/risks",
    response_model=RisksResponse,
    summary="Consulter les patterns de risque",
    description=(
        "Retourne les patterns de risque connus filtrés par secteur, stade et criticité. "
        "Utile pour explorer les risques d'un secteur avant une analyse complète."
    ),
)
async def get_risks(
    sector: str | None = Query(
        default=None,
        description="Secteur à filtrer (ex: 'marketplace', 'saas', 'fintech', 'agritech').",
        examples=["marketplace"],
    ),
    stage: str | None = Query(
        default=None,
        description="Stade à filtrer (ex: 'pre-seed', 'seed', 'series-a').",
    ),
    criticality: str | None = Query(
        default=None,
        description="Niveau de criticité : 'critical', 'high', 'medium', 'low'.",
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=50,
        description="Nombre maximum de résultats.",
    ),
) -> RisksResponse:
    """
    Liste des patterns de risque filtrés. Requête directe PostgreSQL.
    """
    try:
        raw_risks = queries.get_risk_patterns(
            sector=sector,
            stage=stage,
            criticality=criticality,
            limit=limit,
        )
    except Exception as e:
        logger.error("Erreur get_risks : %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur base de données : {str(e)}",
        )

    risks = [
        RiskItem(
            name=r.get("pattern_name", ""),
            criticality=r.get("criticality", ""),
            explanation=r.get("simple_explain", ""),
            warning_signs=r.get("warning_signals", ""),
            mitigation=r.get("mitigation_simple", ""),
            time_to_impact=r.get("time_to_impact"),
        )
        for r in raw_risks
    ]

    return RisksResponse(
        count=len(risks),
        sector=sector,
        stage=stage,
        risks=risks,
    )


@data_router.get(
    "/benchmarks",
    response_model=BenchmarksResponse,
    summary="Consulter les benchmarks sectoriels",
    description=(
        "Retourne les métriques de référence (médiane, bon, excellent, alerte) "
        "pour un secteur et un stade donnés. Permet de situer une startup "
        "par rapport aux standards du marché."
    ),
)
async def get_benchmarks(
    sector: str = Query(
        ...,
        description="Secteur (ex: 'saas', 'marketplace', 'fintech', 'agritech').",
        examples=["saas"],
    ),
    stage: str = Query(
        ...,
        description="Stade (ex: 'pre-seed', 'seed', 'series-a').",
        examples=["seed"],
    ),
) -> BenchmarksResponse:
    """
    Benchmarks sectoriels pour une combinaison secteur × stade.
    """
    try:
        raw = queries.get_benchmarks(sector=sector, stage=stage)
    except Exception as e:
        logger.error("Erreur get_benchmarks : %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur base de données : {str(e)}",
        )

    if not raw:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Aucun benchmark trouvé pour sector='{sector}', stage='{stage}'. "
                f"Secteurs disponibles : saas, marketplace, fintech, agritech, edtech, healthtech."
            ),
        )

    benchmarks = [
        BenchmarkItem(
            metric_name=b.get("metric_name", ""),
            value_median=b.get("value_median"),
            value_good=b.get("value_good"),
            value_excellent=b.get("value_excellent"),
            value_warning=b.get("value_warning"),
            unit=b.get("unit", ""),
            context=b.get("context", ""),
            interpretation_good=b.get("interpretation_good"),
            interpretation_bad=b.get("interpretation_bad"),
        )
        for b in raw
    ]

    return BenchmarksResponse(
        sector=sector,
        stage=stage,
        count=len(benchmarks),
        benchmarks=benchmarks,
    )


@data_router.get(
    "/evaluate",
    response_model=EvaluationResponse,
    summary="Évaluer une métrique",
    description=(
        "Compare une métrique d'une startup aux benchmarks sectoriels et retourne "
        "un jugement qualitatif : excellent, bon, médian, ou en zone d'alerte."
    ),
)
async def evaluate_metric(
    sector: str = Query(..., description="Secteur de la startup."),
    stage:  str = Query(..., description="Stade de la startup."),
    metric: str = Query(..., description="Nom de la métrique (ex: 'churn_monthly', 'nps')."),
    value:  float = Query(..., description="Valeur observée chez la startup."),
) -> EvaluationResponse:
    """
    Évalue une métrique par rapport aux benchmarks du secteur.
    """
    try:
        result = queries.evaluate_metric(
            sector=sector,
            stage=stage,
            metric_name=metric,
            value=value,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    level = result["level"]
    benchmark_raw = result.get("benchmark")

    benchmark = None
    if benchmark_raw:
        benchmark = BenchmarkItem(
            metric_name=benchmark_raw.get("metric_name", metric),
            value_median=benchmark_raw.get("value_median"),
            value_good=benchmark_raw.get("value_good"),
            value_excellent=benchmark_raw.get("value_excellent"),
            value_warning=benchmark_raw.get("value_warning"),
            unit=benchmark_raw.get("unit", ""),
            context=benchmark_raw.get("context", ""),
            interpretation_good=benchmark_raw.get("interpretation_good"),
            interpretation_bad=benchmark_raw.get("interpretation_bad"),
        )

    # Interprétation lisible selon le niveau
    interpretations = {
        "excellent": f"Votre {metric} de {value} est excellent — dans le top quartile du secteur {sector} en {stage}.",
        "good":      f"Votre {metric} de {value} est bon — au-dessus de la médiane sectorielle.",
        "median":    f"Votre {metric} de {value} est dans la médiane du secteur {sector} en {stage}. Correct, mais améliorable.",
        "warning":   f"Votre {metric} de {value} est en zone d'alerte — en dessous des standards du secteur {sector} en {stage}.",
        "unknown":   f"Aucun benchmark disponible pour {metric} en {sector}/{stage}.",
    }

    return EvaluationResponse(
        metric_name=metric,
        value=value,
        level=level,
        benchmark=benchmark,
        interpretation=interpretations.get(level, ""),
    )


@data_router.get(
    "/investment-criteria",
    summary="Critères d'évaluation par profil investisseur",
    description=(
        "Retourne les critères d'évaluation d'investissement pour un profil "
        "et un stade donnés, classés par importance (critical → important → nice-to-have)."
    ),
)
async def get_investment_criteria(
    investor_profile: str = Query(
        ...,
        description="Profil : 'angel', 'vc', 'impact', 'strategic'.",
        examples=["angel"],
    ),
    stage: str = Query(
        ...,
        description="Stade de la startup.",
        examples=["pre-seed"],
    ),
) -> dict[str, Any]:
    """Critères d'investissement depuis PostgreSQL."""
    try:
        criteria = queries.get_investment_criteria(
            investor_profile=investor_profile,
            stage=stage,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    if not criteria:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Aucun critère trouvé pour investor_profile='{investor_profile}', "
                f"stage='{stage}'."
            ),
        )

    return {"investor_profile": investor_profile, "stage": stage, "criteria": criteria}


# =============================================================================
# ROUTER 3 — SYSTÈME
# =============================================================================

system_router = APIRouter(tags=["Système"])


@system_router.get(
    "/health",
    response_model=HealthResponse,
    summary="Santé de l'API",
    description="Vérifie que l'API, le modèle et la base de données sont opérationnels.",
)
async def health() -> HealthResponse:
    """
    Health check complet.
    Utilisé par les orchestrateurs (Docker, Kubernetes, Airflow)
    pour vérifier que le service est prêt à recevoir des requêtes.
    """
    # Vérification base de données
    db_status = db_health_check()

    # Vérification modèle
    model_loaded = (
        _pipeline_instance is not None
        and _pipeline_instance.is_loaded
    )

    # Statut global
    if db_status.get("status") == "ok" and model_loaded:
        overall = "ok"
    elif db_status.get("status") == "ok" and not model_loaded:
        overall = "degraded"  # base OK mais modèle pas encore chargé
    else:
        overall = "error"

    return HealthResponse(
        status=overall,
        model_loaded=model_loaded,
        database=db_status,
        version="1.0.0",
    )


@system_router.get(
    "/",
    summary="Racine de l'API",
    include_in_schema=False,
)
async def root() -> dict[str, str]:
    return {
        "name":    "LFM Lean Startup API",
        "version": "1.0.0",
        "docs":    "/docs",
        "health":  "/health",
    }
