"""
src/database/queries.py
=======================
Requêtes SQL nommées et réutilisables.

Ce module est la couche entre le code applicatif (tool_executor, API)
et la base de données. Chaque fonction correspond à une question métier
précise que le modèle ou l'API peut avoir besoin de poser.

Deux types de fonctions coexistent :
    - Fonctions TYPÉES  : paramètres Python, SQL fixe, sécurisé.
      Utilisées par le code interne (training, evaluation, API).
    - Fonction RAW      : execute_safe_tool_query() du client.
      Utilisée par le tool_executor pour les requêtes libres du LLM.

Principe : toujours passer les paramètres via %s (jamais de f-string SQL)
pour éviter les injections SQL.
"""

from typing import Any
from src.database.client import execute_query


# =============================================================================
# RISK PATTERNS
# =============================================================================

def get_risk_patterns(
    sector: str | None = None,
    stage: str | None = None,
    criticality: str | None = None,
    category: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Récupère les patterns de risque filtrés par secteur, stade, criticité.

    Gère les colonnes NULLables : un risk_pattern avec sector=NULL
    s'applique à tous les secteurs — la requête l'inclut toujours
    quand un secteur est spécifié.

    Args:
        sector      : Secteur de la startup (ex: "marketplace", "saas").
                      None = pas de filtre secteur.
        stage       : Stade de la startup (ex: "pre-seed", "seed").
                      None = pas de filtre stade.
        criticality : Niveau de criticité ("critical", "high", "medium", "low").
        category    : Catégorie du risque ("market", "team", "product"...).
        limit       : Nombre maximum de résultats.

    Returns:
        Liste de patterns de risque, triés par criticité décroissante.

    Example :
        patterns = get_risk_patterns(sector="marketplace", stage="pre-seed")
    """
    conditions = []
    params: list[Any] = []

    if sector:
        # Inclure les patterns universels (sector IS NULL) ET ceux du secteur
        conditions.append("(sector = %s OR sector IS NULL)")
        params.append(sector)

    if stage:
        # Inclure les patterns universels (stage IS NULL) ET ceux du stade
        conditions.append("(stage = %s::startup_stage OR stage IS NULL)")
        params.append(stage)

    if criticality:
        conditions.append("criticality = %s::risk_criticality")
        params.append(criticality)

    if category:
        conditions.append("category = %s")
        params.append(category)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    sql = f"""
        SELECT
            id,
            pattern_name,
            sector,
            stage,
            criticality,
            category,
            simple_explain,
            warning_signals,
            mitigation_simple,
            impact_on_runway,
            time_to_impact
        FROM risk_patterns
        {where_clause}
        ORDER BY
            CASE criticality
                WHEN 'critical' THEN 1
                WHEN 'high'     THEN 2
                WHEN 'medium'   THEN 3
                WHEN 'low'      THEN 4
            END,
            -- Patterns sectoriels avant les universels
            CASE WHEN sector IS NULL THEN 1 ELSE 0 END
        LIMIT %s
    """
    params.append(limit)

    return execute_query(sql, tuple(params), fetch="all")  # type: ignore[return-value]


def get_risk_pattern_full(pattern_name: str) -> dict[str, Any] | None:
    """
    Récupère un pattern de risque complet par son nom (avec description technique).
    Utilisé quand le modèle veut approfondir un risque spécifique.
    """
    return execute_query(
        """
        SELECT *
        FROM risk_patterns
        WHERE pattern_name ILIKE %s
        LIMIT 1
        """,
        params=(f"%{pattern_name}%",),
        fetch="one",
    )


# =============================================================================
# SECTOR BENCHMARKS
# =============================================================================

def get_benchmarks(
    sector: str,
    stage: str,
    metric_name: str | None = None,
) -> list[dict[str, Any]]:
    """
    Récupère les benchmarks sectoriels pour comparer les métriques d'une startup.

    Args:
        sector      : Secteur (ex: "saas", "marketplace").
        stage       : Stade (ex: "seed", "series-a").
        metric_name : Métrique spécifique (ex: "churn_monthly"). None = toutes.

    Returns:
        Liste de benchmarks avec seuils et contexte d'interprétation.
    """
    if metric_name:
        return execute_query(
            """
            SELECT *
            FROM v_benchmarks_with_context
            WHERE sector = %s
              AND stage  = %s::startup_stage
              AND metric_name = %s
            """,
            params=(sector, stage, metric_name),
            fetch="all",
        )  # type: ignore[return-value]
    else:
        return execute_query(
            """
            SELECT *
            FROM v_benchmarks_with_context
            WHERE sector = %s
              AND stage  = %s::startup_stage
            ORDER BY metric_name
            """,
            params=(sector, stage),
            fetch="all",
        )  # type: ignore[return-value]


def evaluate_metric(
    sector: str,
    stage: str,
    metric_name: str,
    value: float,
) -> dict[str, Any]:
    """
    Évalue une métrique d'une startup par rapport aux benchmarks.
    Retourne le benchmark ET un jugement qualitatif (excellent/good/median/warning).

    Args:
        sector      : Secteur de la startup.
        stage       : Stade de la startup.
        metric_name : Nom de la métrique.
        value       : Valeur observée chez la startup.

    Returns:
        Dict avec le benchmark et le jugement : {"level": "warning", "benchmark": {...}}
    """
    benchmark = execute_query(
        """
        SELECT *
        FROM sector_benchmarks
        WHERE sector = %s
          AND stage  = %s::startup_stage
          AND metric_name = %s
        LIMIT 1
        """,
        params=(sector, stage, metric_name),
        fetch="one",
    )

    if not benchmark:
        return {"level": "unknown", "benchmark": None, "value": value}

    # Détermination du niveau : on compare selon si une valeur plus haute
    # est meilleure (ex: NPS) ou si une valeur plus basse est meilleure (ex: churn)
    # Convention : value_excellent > value_good > value_median > value_warning
    # signifie que plus c'est élevé, mieux c'est.
    # Pour les métriques inverses (churn, CAC), les seuils sont inversés dans les seeds.

    excellent = benchmark.get("value_excellent")
    good      = benchmark.get("value_good")
    median    = benchmark.get("value_median")
    warning   = benchmark.get("value_warning")

    # Détection de l'orientation (plus élevé = mieux ou plus bas = mieux)
    # On déduit l'orientation depuis la relation entre warning et excellent
    higher_is_better = (excellent or 0) > (warning or 0)

    if higher_is_better:
        if excellent is not None and value >= excellent:
            level = "excellent"
        elif good is not None and value >= good:
            level = "good"
        elif median is not None and value >= median:
            level = "median"
        else:
            level = "warning"
    else:
        if excellent is not None and value <= excellent:
            level = "excellent"
        elif good is not None and value <= good:
            level = "good"
        elif median is not None and value <= median:
            level = "median"
        else:
            level = "warning"

    return {
        "level": level,
        "value": value,
        "benchmark": dict(benchmark),
    }


# =============================================================================
# LEAN CONCEPTS
# =============================================================================

def get_lean_concept(concept_name: str) -> dict[str, Any] | None:
    """
    Récupère un concept Lean Startup par son nom ou un alias.
    Utilisé pour générer des explications accessibles.

    Args:
        concept_name : Nom complet ou partiel du concept.
    """
    return execute_query(
        """
        SELECT *
        FROM lean_concepts
        WHERE concept_name ILIKE %s
           OR %s = ANY(aliases)
        LIMIT 1
        """,
        params=(f"%{concept_name}%", concept_name),
        fetch="one",
    )


def get_concepts_by_category(category: str) -> list[dict[str, Any]]:
    """
    Récupère tous les concepts d'une catégorie donnée.
    Catégories : 'framework', 'metric', 'strategy', 'principle', 'tool'
    """
    return execute_query(
        """
        SELECT
            concept_name,
            category,
            simple_def,
            example,
            related_risks
        FROM lean_concepts
        WHERE category = %s::lean_category
        ORDER BY concept_name
        """,
        params=(category,),
        fetch="all",
    )  # type: ignore[return-value]


# =============================================================================
# INVESTMENT CRITERIA
# =============================================================================

def get_investment_criteria(
    investor_profile: str,
    stage: str,
    weight: str | None = None,
) -> list[dict[str, Any]]:
    """
    Récupère les critères d'évaluation d'investissement.

    Args:
        investor_profile : Profil de l'investisseur ("angel", "vc", "impact", "strategic").
        stage            : Stade de la startup.
        weight           : Filtre optionnel sur le poids ("critical", "important", "nice-to-have").

    Returns:
        Liste de critères avec red_flags, green_flags et explication simple.
    """
    if weight:
        return execute_query(
            """
            SELECT *
            FROM investment_criteria
            WHERE investor_profile = %s::investor_profile
              AND stage            = %s::startup_stage
              AND weight           = %s::criterion_weight
            ORDER BY
                CASE weight
                    WHEN 'critical'     THEN 1
                    WHEN 'important'    THEN 2
                    WHEN 'nice-to-have' THEN 3
                END
            """,
            params=(investor_profile, stage, weight),
            fetch="all",
        )  # type: ignore[return-value]
    else:
        return execute_query(
            """
            SELECT *
            FROM investment_criteria
            WHERE investor_profile = %s::investor_profile
              AND stage            = %s::startup_stage
            ORDER BY
                CASE weight
                    WHEN 'critical'     THEN 1
                    WHEN 'important'    THEN 2
                    WHEN 'nice-to-have' THEN 3
                END
            """,
            params=(investor_profile, stage),
            fetch="all",
        )  # type: ignore[return-value]


# =============================================================================
# STARTUPS (cas d'étude)
# =============================================================================

def get_similar_startups(
    sector: str,
    stage: str | None = None,
    outcome: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    Récupère des cas de startups similaires pour alimenter le raisonnement
    par analogie du modèle.

    Args:
        sector  : Secteur à cibler.
        stage   : Stade à cibler (optionnel).
        outcome : Filtrer par résultat ("success", "failure", "pivot"...).
        limit   : Nombre maximum de résultats.
    """
    conditions = ["s.sector = %s"]
    params: list[Any] = [sector]

    if stage:
        conditions.append("s.stage = %s::startup_stage")
        params.append(stage)

    if outcome:
        conditions.append("s.outcome = %s::startup_outcome")
        params.append(outcome)

    params.append(limit)

    sql = f"""
        SELECT
            v.name,
            v.sector,
            v.stage,
            v.region,
            v.outcome,
            v.description,
            v.pivot_count,
            v.key_learnings
        FROM v_startups_with_pivot_count v
        JOIN startups s ON s.id = v.id
        WHERE {' AND '.join(conditions)}
        ORDER BY v.pivot_count DESC, s.founding_year DESC
        LIMIT %s
    """

    return execute_query(sql, tuple(params), fetch="all")  # type: ignore[return-value]


# =============================================================================
# PIVOT CASES
# =============================================================================

def get_pivot_cases(
    pivot_type: str | None = None,
    outcome: str | None = None,
    sector: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    Récupère des cas de pivots documentés.
    Utilisé quand le modèle analyse si une startup devrait pivoter
    et veut s'appuyer sur des analogies réelles.

    Args:
        pivot_type : Type de pivot ("zoom-in", "customer-segment"...).
        outcome    : Résultat du pivot ("success", "failure").
        sector     : Secteur de la startup qui a pivoté.
        limit      : Nombre maximum de résultats.
    """
    conditions = []
    params: list[Any] = []

    if pivot_type:
        conditions.append("pc.pivot_type = %s")
        params.append(pivot_type)

    if outcome:
        conditions.append("pc.outcome = %s::startup_outcome")
        params.append(outcome)

    if sector:
        conditions.append("s.sector = %s")
        params.append(sector)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)

    sql = f"""
        SELECT
            pc.pivot_type,
            pc.trigger_signal,
            pc.before_model,
            pc.after_model,
            pc.bml_cycle_number,
            pc.outcome,
            pc.key_learnings,
            s.sector,
            s.region
        FROM pivot_cases pc
        JOIN startups s ON s.id = pc.startup_id
        {where_clause}
        ORDER BY pc.outcome DESC
        LIMIT %s
    """

    return execute_query(sql, tuple(params), fetch="all")  # type: ignore[return-value]


# =============================================================================
# REQUÊTES COMPOSITES
# Requêtes qui combinent plusieurs tables pour un diagnostic complet
# Utilisées directement par le pipeline d'inférence (pas le tool use)
# =============================================================================

def get_startup_diagnosis_context(
    sector: str,
    stage: str,
    investor_profile: str = "angel",
) -> dict[str, Any]:
    """
    Agrège tout le contexte nécessaire pour un diagnostic complet en une seule
    requête composite. Évite les appels multiples à la base depuis le pipeline.

    Retourne :
        - Les risques critiques du secteur/stade
        - Les benchmarks clés du secteur/stade
        - Les critères d'investissement du profil
        - Des exemples de startups similaires

    Args:
        sector           : Secteur de la startup analysée.
        stage            : Stade de la startup analysée.
        investor_profile : Profil de l'investisseur.

    Returns:
        Dict structuré avec les quatre sources de contexte.
    """
    return {
        "risks": get_risk_patterns(
            sector=sector,
            stage=stage,
            criticality="critical",
            limit=5,
        ),
        "benchmarks": get_benchmarks(
            sector=sector,
            stage=stage,
        ),
        "investment_criteria": get_investment_criteria(
            investor_profile=investor_profile,
            stage=stage,
            weight="critical",
        ),
        "similar_startups": get_similar_startups(
            sector=sector,
            stage=stage,
            limit=3,
        ),
    }
