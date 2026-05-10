"""
dags/build_dataset_dag.py
==========================
DAG Airflow : Construction et validation du dataset SFT.

Déclenchement :
    - Manuel (bouton "Trigger DAG" dans l'UI Airflow)
    - Ou planifié (schedule="0 2 * * 0" = chaque dimanche à 2h)

Flux des tâches :
    check_database_health
            ↓
    build_dataset                (src/data/build_lean_datasets.py)
            ↓
    report_metrics               (src/data/report_dataset_metrics.py)
            ↓
    validate_dataset_quality     (vérifie le rapport — bloque si trop de warnings)
            ↓
    push_to_dvc_remote           (git add + dvc push → Google Drive)
            ↓
    notify_completion

XCom utilisés :
    build_dataset       → validate_dataset_quality : statistiques du dataset
    report_metrics      → validate_dataset_quality : nombre de warnings
    validate_dataset_quality → notify_completion   : résumé de validation
"""

import json
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from airflow.decorators import dag, task
from airflow.exceptions import AirflowFailException, AirflowSkipException
from airflow.models import Variable
from airflow.operators.empty import EmptyOperator
from airflow.utils.trigger_rule import TriggerRule

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION DU DAG
# =============================================================================

PROJECT_ROOT = Path("/opt/airflow")

DEFAULT_ARGS = {
    "owner":            "lfm-team",
    "retries":          1,
    "retry_delay":      timedelta(minutes=5),
    "execution_timeout": timedelta(minutes=30),
    "email_on_failure": False,
    "email_on_retry":   False,
}


# =============================================================================
# DAG
# =============================================================================

@dag(
    dag_id="lfm_build_dataset",
    description=(
        "Construit le dataset SFT Lean Startup, génère le rapport de métriques, "
        "valide la qualité, et pousse vers le remote DVC (Google Drive)."
    ),
    schedule=None,              # déclenché manuellement
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,          # pas de runs parallèles sur le même dataset
    default_args=DEFAULT_ARGS,
    tags=["data", "dvc", "lean-startup"],
    doc_md="""
## DAG : Construction du dataset SFT

Ce DAG exécute les deux premières étapes du pipeline DVC :
1. `build_lean_datasets.py` → génère les exemples d'entraînement
2. `report_dataset_metrics.py` → valide la qualité du dataset

**Quand le lancer :**
- Après avoir ajouté de nouveaux exemples dans `build_lean_datasets.py`
- Après modification du schéma PostgreSQL (nouveaux seeds)

**Prérequis :**
- PostgreSQL disponible et alimenté (seeds exécutés)
- Remote DVC configuré (Google Drive)
    """,
)
def build_dataset_pipeline():

    # =========================================================================
    # TÂCHE 1 — Vérification de la base de données
    # =========================================================================

    @task(task_id="check_database_health")
    def check_database_health() -> dict:
        """
        Vérifie que PostgreSQL est accessible et que les tables de seeds
        sont peuplées. Bloque le pipeline si la base est vide ou inaccessible.
        """
        import sys
        sys.path.insert(0, str(PROJECT_ROOT))

        from src.database.client import health_check
        from src.database.client import execute_query

        # Vérification connectivité
        health = health_check()
        if health["status"] != "ok":
            raise AirflowFailException(
                f"PostgreSQL inaccessible : {health.get('message')}"
            )

        logger.info("PostgreSQL accessible : %s", health["database"])

        # Vérification que les seeds ont été exécutés
        counts = execute_query(
            """
            SELECT
                (SELECT COUNT(*) FROM lean_concepts)       AS concepts,
                (SELECT COUNT(*) FROM risk_patterns)       AS risks,
                (SELECT COUNT(*) FROM sector_benchmarks)   AS benchmarks,
                (SELECT COUNT(*) FROM investment_criteria) AS criteria
            """,
            fetch="one"
        )

        logger.info("Tables seeds : %s", counts)

        if not counts or any(v == 0 for v in counts.values()):
            raise AirflowFailException(
                f"Tables seeds vides — exécuter database/seeds/seeds_runner.sql.\n"
                f"État actuel : {counts}"
            )

        return {
            "database": health["database"],
            "seed_counts": dict(counts),
        }

    # =========================================================================
    # TÂCHE 2 — Construction du dataset
    # =========================================================================

    @task(task_id="build_dataset")
    def build_dataset() -> dict:
        """
        Exécute build_lean_datasets.py et retourne les statistiques
        du dataset généré via XCom.
        """
        import sys
        sys.path.insert(0, str(PROJECT_ROOT))

        # Import du script (pas subprocess — meilleure intégration et logs)
        import importlib.util

        script_path = PROJECT_ROOT / "src" / "data" / "build_lean_datasets.py"
        spec = importlib.util.spec_from_file_location("build_lean_datasets", script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Exécution
        module.main()

        # Lecture du dataset généré pour les statistiques
        full_dataset = PROJECT_ROOT / "data" / "source" / "full_dataset.jsonl"
        if not full_dataset.exists():
            raise AirflowFailException(
                f"Dataset non généré : {full_dataset} introuvable."
            )

        total = sum(1 for _ in open(full_dataset, encoding="utf-8"))

        from collections import Counter
        categories = Counter()
        tool_use_count = 0

        with open(full_dataset, encoding="utf-8") as f:
            for line in f:
                ex = json.loads(line)
                meta = ex.get("metadata", {})
                categories[meta.get("category", "unknown")] += 1
                if meta.get("has_tool_use"):
                    tool_use_count += 1

        stats = {
            "total_examples":  total,
            "categories":      dict(categories),
            "tool_use_count":  tool_use_count,
            "tool_use_ratio":  round(tool_use_count / total, 3) if total else 0,
        }

        logger.info("Dataset généré — %d exemples | %s", total, dict(categories))
        return stats

    # =========================================================================
    # TÂCHE 3 — Rapport de métriques
    # =========================================================================

    @task(task_id="report_metrics")
    def report_metrics() -> dict:
        """
        Exécute report_dataset_metrics.py et retourne le nombre
        d'avertissements détectés via XCom.
        """
        import sys
        sys.path.insert(0, str(PROJECT_ROOT))

        import importlib.util

        script_path = PROJECT_ROOT / "src" / "data" / "report_dataset_metrics.py"
        spec = importlib.util.spec_from_file_location("report_dataset_metrics", script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Exécution
        full_dataset = PROJECT_ROOT / "data" / "source" / "full_dataset.jsonl"
        examples = module.load_dataset(full_dataset)
        metrics = module.compute_metrics(examples)

        report = module.render_report(metrics, full_dataset)
        report_path = PROJECT_ROOT / "DATASET_METRICS_REPORT.md"
        report_path.write_text(report, encoding="utf-8")

        warnings = metrics.get("warnings", [])
        logger.info("Rapport généré — %d avertissement(s)", len(warnings))

        if warnings:
            for w in warnings:
                logger.warning("⚠ %s", w)

        return {
            "total":         metrics["total"],
            "warnings":      warnings,
            "warning_count": len(warnings),
        }

    # =========================================================================
    # TÂCHE 4 — Validation de la qualité du dataset
    # =========================================================================

    @task(task_id="validate_dataset_quality")
    def validate_dataset_quality(
        build_stats: dict,
        metrics_result: dict,
    ) -> dict:
        """
        Valide que le dataset est suffisamment équilibré et volumineux.

        Règles de validation :
        - Minimum 20 exemples (seuil bas pour le développement)
        - Pas plus de 3 avertissements bloquants
        - Ratio tool use entre 20% et 85%

        Bloque le pipeline (AirflowFailException) si les critères ne sont pas atteints.
        """
        total        = build_stats["total_examples"]
        tool_ratio   = build_stats["tool_use_ratio"]
        warnings     = metrics_result["warnings"]
        warning_count = metrics_result["warning_count"]

        errors = []

        # Règle 1 : volume minimum
        MIN_EXAMPLES = int(Variable.get("lfm_min_dataset_size", default_var=20))
        if total < MIN_EXAMPLES:
            errors.append(
                f"Volume insuffisant : {total} exemples < {MIN_EXAMPLES} minimum. "
                f"Enrichir les générateurs dans build_lean_datasets.py."
            )

        # Règle 2 : ratio tool use
        if tool_ratio < 0.20:
            errors.append(
                f"Ratio tool use trop bas : {tool_ratio:.0%} < 20%. "
                f"Ajouter des exemples avec tool use PostgreSQL."
            )
        if tool_ratio > 0.85:
            errors.append(
                f"Ratio tool use trop élevé : {tool_ratio:.0%} > 85%. "
                f"Ajouter des exemples sans tool use."
            )

        # Règle 3 : avertissements bloquants
        MAX_WARNINGS = int(Variable.get("lfm_max_warnings", default_var=3))
        if warning_count > MAX_WARNINGS:
            errors.append(
                f"Trop d'avertissements : {warning_count} > {MAX_WARNINGS}. "
                f"Vérifier DATASET_METRICS_REPORT.md."
            )

        if errors:
            raise AirflowFailException(
                "Validation du dataset échouée :\n" + "\n".join(f"  - {e}" for e in errors)
            )

        logger.info(
            "✅ Validation réussie — %d exemples | tool use: %.0f%% | warnings: %d",
            total, tool_ratio * 100, warning_count
        )

        return {
            "valid":         True,
            "total":         total,
            "tool_ratio":    tool_ratio,
            "warning_count": warning_count,
            "message":       f"Dataset valide : {total} exemples, {tool_ratio:.0%} tool use.",
        }

    # =========================================================================
    # TÂCHE 5 — Push DVC vers Google Drive
    # =========================================================================

    @task(task_id="push_to_dvc_remote")
    def push_to_dvc_remote(validation_result: dict) -> str:
        """
        Versionne les nouvelles données avec DVC et les pousse vers le remote.

        Étapes :
        1. dvc add data/      → génère les fichiers .dvc
        2. git add .dvc files → stage les métadonnées dans git
        3. dvc push           → uploade vers Google Drive
        """
        import subprocess

        repo_root = PROJECT_ROOT

        def run(cmd: list[str], cwd=None) -> str:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=cwd or str(repo_root),
            )
            if result.returncode != 0:
                raise AirflowFailException(
                    f"Commande échouée : {' '.join(cmd)}\n"
                    f"stderr : {result.stderr}"
                )
            return result.stdout.strip()

        # 1. DVC add
        logger.info("dvc add data/ ...")
        run(["dvc", "add", "data/source/full_dataset.jsonl"])
        run(["dvc", "add", "data/splits/"])
        run(["dvc", "add", "data/liquid/"])

        # 2. DVC push
        logger.info("dvc push ...")
        output = run(["dvc", "push"])
        logger.info("DVC push terminé : %s", output)

        return f"DVC push réussi — {validation_result['total']} exemples versionnés."

    # =========================================================================
    # TÂCHE 6 — Notification de fin
    # =========================================================================

    @task(
        task_id="notify_completion",
        trigger_rule=TriggerRule.ALL_DONE,  # s'exécute même si une tâche est skippée
    )
    def notify_completion(push_result: str, validation_result: dict) -> None:
        """
        Log le résumé de fin de pipeline.
        Peut être étendu pour envoyer un email ou une notification Slack.
        """
        logger.info("=" * 60)
        logger.info("✅ Pipeline build_dataset terminé avec succès")
        logger.info("   %s", validation_result.get("message", ""))
        logger.info("   DVC : %s", push_result)
        logger.info("=" * 60)

    # =========================================================================
    # ORCHESTRATION — DÉFINITION DU FLUX
    # =========================================================================

    # Tâche de départ (point d'ancrage visuel dans l'UI Airflow)
    start = EmptyOperator(task_id="start")

    # Exécution des tâches
    health   = check_database_health()
    stats    = build_dataset()
    metrics  = report_metrics()

    # validate_dataset_quality reçoit les XCom des deux tâches précédentes
    validation = validate_dataset_quality(
        build_stats=stats,
        metrics_result=metrics,
    )

    push   = push_to_dvc_remote(validation_result=validation)
    notify = notify_completion(
        push_result=push,
        validation_result=validation,
    )

    # Graphe de dépendances
    start >> health >> stats >> metrics >> validation >> push >> notify


# Instanciation du DAG
build_dataset_pipeline()
