"""
src/api/schemas.py
==================
Modèles Pydantic pour la validation des entrées et sorties de l'API.

Deux rôles :
    - Validation et documentation automatique (FastAPI génère le schéma
      OpenAPI à partir de ces modèles)
    - Contrat explicite entre le client et l'API — chaque champ a un type,
      une description, et une valeur d'exemple

Convention de nommage :
    - *Request : corps d'une requête entrante (POST)
    - *Response : corps d'une réponse sortante
    - *Item     : élément d'une liste dans une réponse
"""

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


# =============================================================================
# ÉNUMÉRATIONS
# =============================================================================

class InvestorProfile(str, Enum):
    angel       = "angel"
    vc          = "vc"
    impact      = "impact"
    strategic   = "strategic"
    entrepreneur = "entrepreneur"
    both        = "both"


class StartupStage(str, Enum):
    idea     = "idea"
    pre_seed = "pre-seed"
    seed     = "seed"
    series_a = "series-a"
    series_b = "series-b"
    growth   = "growth"


# =============================================================================
# REQUÊTES
# =============================================================================

class AnalyzeRequest(BaseModel):
    """
    Requête d'analyse d'une startup en texte libre.
    C'est le point d'entrée principal de l'API.
    """
    description: str = Field(
        ...,
        min_length=50,
        max_length=5000,
        description=(
            "Description libre de la startup à analyser. "
            "Inclure : secteur, stade, équipe, traction actuelle, "
            "modèle économique, et ce que vous cherchez comme retour."
        ),
        examples=[
            "Notre startup connecte des artisans locaux avec des particuliers "
            "en Afrique subsaharienne via une app mobile. Équipe de 3 personnes. "
            "120 artisans inscrits, 8 transactions en 2 mois. "
            "On cherche 50 000$ pour l'acquisition."
        ],
    )

    investor_profile: InvestorProfile = Field(
        default=InvestorProfile.both,
        description=(
            "Profil de l'interlocuteur. Adapte le niveau de détail "
            "et le vocabulaire de l'analyse."
        ),
    )

    conversation_history: list[dict[str, str]] = Field(
        default_factory=list,
        description=(
            "Historique de la conversation pour les échanges multi-tour. "
            "Format : liste de {'role': 'user'|'assistant', 'content': '...'}."
        ),
    )

    class Config:
        json_schema_extra = {
            "example": {
                "description": (
                    "On développe un SaaS de gestion des congés pour les PME "
                    "de 10 à 100 employés. Lancé il y a 6 mois, 45 clients à "
                    "49€/mois, churn de 8% par mois. Équipe de 4 personnes. "
                    "On veut lever 300K€ pour recruter 2 commerciaux."
                ),
                "investor_profile": "vc",
                "conversation_history": [],
            }
        }


class ConceptRequest(BaseModel):
    """Requête d'explication d'un concept Lean Startup."""
    concept_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Nom du concept à expliquer (ex: 'MVP', 'churn', 'pivot').",
        examples=["unit economics", "product-market fit", "burn rate"],
    )

    detail_level: str = Field(
        default="simple",
        description=(
            "'simple' : explication accessible sans jargon. "
            "'technical' : définition complète avec formules."
        ),
        pattern="^(simple|technical)$",
    )


# =============================================================================
# RÉPONSES
# =============================================================================

class RiskItem(BaseModel):
    """Un risque identifié dans l'analyse."""
    name:          str
    criticality:   str   # "critical" | "high" | "medium" | "low"
    explanation:   str   # explication simple
    warning_signs: str
    mitigation:    str
    time_to_impact: str | None = None


class AnalyzeResponse(BaseModel):
    """
    Réponse complète d'une analyse de startup.
    """
    analysis: str = Field(
        ...,
        description="Analyse complète en texte structuré (Markdown).",
    )

    # Métadonnées du pipeline pour la traçabilité
    tool_calls_made:       int  = Field(default=0,  description="Nombre d'appels PostgreSQL effectués.")
    tool_calls_successful: int  = Field(default=0,  description="Nombre d'appels PostgreSQL réussis.")
    data_sources_used:     list[str] = Field(default_factory=list, description="Tables PostgreSQL consultées.")
    model_version:         str | None = Field(default=None, description="Version du modèle utilisé.")
    error:                 str | None = Field(default=None, description="Message d'erreur si applicable.")

    class Config:
        json_schema_extra = {
            "example": {
                "analysis": "## Analyse de votre marketplace\n\n**Signal d'alarme...**",
                "tool_calls_made": 2,
                "tool_calls_successful": 2,
                "data_sources_used": ["risk_patterns", "sector_benchmarks"],
                "model_version": "lfm25-lean-startup/v3",
                "error": None,
            }
        }


class ConceptResponse(BaseModel):
    """Réponse d'explication d'un concept."""
    concept_name:   str
    found:          bool
    simple_def:     str | None = None
    technical_def:  str | None = None
    analogy:        str | None = None
    example:        str | None = None
    related_risks:  str | None = None
    source:         str | None = None


class RisksResponse(BaseModel):
    """Liste de patterns de risque filtrés."""
    count:    int
    sector:   str | None
    stage:    str | None
    risks:    list[RiskItem]


class BenchmarkItem(BaseModel):
    """Un benchmark sectoriel."""
    metric_name:        str
    value_median:       float | None
    value_good:         float | None
    value_excellent:    float | None
    value_warning:      float | None
    unit:               str
    context:            str
    interpretation_good: str | None = None
    interpretation_bad:  str | None = None


class BenchmarksResponse(BaseModel):
    """Benchmarks sectoriels pour un secteur et stade donnés."""
    sector:     str
    stage:      str
    count:      int
    benchmarks: list[BenchmarkItem]


class EvaluationResponse(BaseModel):
    """Évaluation d'une métrique par rapport aux benchmarks."""
    metric_name: str
    value:       float
    level:       str        # "excellent" | "good" | "median" | "warning" | "unknown"
    benchmark:   BenchmarkItem | None = None
    interpretation: str | None = None


class HealthResponse(BaseModel):
    """Statut de santé de l'API et de ses dépendances."""
    status:         str         # "ok" | "degraded" | "error"
    model_loaded:   bool
    database:       dict[str, Any]
    version:        str
