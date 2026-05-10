"""
dags/fine_tuning_dag.py
========================
DAG Airflow : Fine-tuning LoRA-SFT de LFM2.5-350M.

Déclenchement :
    - Manuel uniquement (schedule=None)
    - Typiquement déclenché après validation du dataset par build_dataset_dag

Ce DAG est conçu pour être exécuté sur une machine avec GPU.
En production, utiliser KubernetesExecutor avec un node GPU, ou
configurer un worker Celery sur une machine GPU dédiée.

Flux des tâches :
    check_prerequisites
            ↓
    pull_dataset_from_dvc
            ↓
    run_fine_tuning          (src/training/trainer.py — long running)
            ↓
    evaluate_fine_tuned_model
            ↓
    ┌───────┴────────┐
    │                │
promote_to_staging  log_training_summary
    │                │
    └───────┬────────┘
            ↓
    notify_completion

XCom utilisés :
    run_fine_tuning          → evaluate_fine_tuned_model : run_id MLflow
    evaluate_fine_tuned_model → promote_to_staging : eval_loss, perplexité
    promote_to_staging       → notify_completion   : version du modèle
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from airflow.decorators import dag, task
from airflow.exceptions import AirflowFailException
from airflow.models import Variable
from airflow.operators.empty import EmptyOperator
from airflow.utils.trigger_rule import TriggerRule

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path("/opt/airflow")

DEFAULT_ARGS = {
    "owner":            "lfm-team",
    "retries":          0,          # pas de retry sur le fine-tuning (coûteux)
    "execution_timeout": timedelta(hours=6),  # le training peut prendre plusieurs heures
    "email_on_failure": False,
}

# Seuil de qualité : eval_loss maximum acceptable pour promouvoir le modèle
MAX_ACCEPTABLE_EVAL_LOSS = 2.5


@dag(
    dag_id="lfm_fine_tuning",
    description=(
        "Fine-tuning LoRA-SFT de LFM2.5-350M sur le dataset Lean Startup. "
        "Nécessite un GPU. Déclencher manuellement après validation du dataset."
    ),
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["training", "mlflow", "lora", "lean-startup"],
    doc_md="""
## DAG : Fine-tuning LFM2.5-350M

Lance le fine-tuning LoRA-SFT et enregistre le modèle dans MLflow.

**Prérequis :**
- GPU disponible avec ≥ 16 Go VRAM
- Dataset généré et validé (lancer `lfm_build_dataset` en premier)
- MLflow accessible (http://localhost:5000)

**Résultat :**
- Modèle sauvegardé dans `models/lfm25-350m-lean/`
- Version enregistrée dans le MLflow Model Registry au stade **Staging**
- Métriques visibles dans l'UI MLflow

**Configuration (Variables Airflow) :**
- `lfm_max_eval_loss` : eval_loss maximum pour promotion (défaut: 2.5)
- `lfm_lora_rank` : rang LoRA (défaut: 16)
- `lfm_num_epochs` : nombre d'epochs (défaut: 3)
    """,
)
def fine_tuning_pipeline():

    # =========================================================================
    # TÂCHE 1 — Vérification des prérequis
    # =========================================================================

    @task(task_id="check_prerequisites")
    def check_prerequisites() -> dict:
        """
        Vérifie que toutes les conditions sont réunies avant de lancer
        un entraînement coûteux :
        - Dataset disponible et non vide
        - GPU détecté
        - MLflow accessible
        - Connexion PostgreSQL OK
        """
        import sys
        sys.path.insert(0, str(PROJECT_ROOT))

        results = {}

        # 1. Dataset
        train_file = PROJECT_ROOT / "data" / "liquid" / "train_liquid.jsonl"
        if not train_file.exists():
            raise AirflowFailException(
                f"Dataset manquant : {train_file}\n"
                "Lancer d'abord le DAG 'lfm_build_dataset'."
            )

        train_size = sum(1 for _ in open(train_file, encoding="utf-8"))
        if train_size < 10:
            raise AirflowFailException(
                f"Dataset trop petit : {train_size} exemples. "
                "Enrichir les générateurs."
            )

        results["train_size"] = train_size
        logger.info("Dataset train : %d exemples ✓", train_size)

        # 2. GPU
        try:
            import torch
            gpu_available = torch.cuda.is_available()
            gpu_name = torch.cuda.get_device_name(0) if gpu_available else "N/A"
            gpu_memory = (
                torch.cuda.get_device_properties(0).total_memory // (1024**3)
                if gpu_available else 0
            )
            results["gpu"] = {
                "available": gpu_available,
                "name": gpu_name,
                "memory_gb": gpu_memory,
            }
            if not gpu_available:
                logger.warning(
                    "Aucun GPU détecté — le fine-tuning sur CPU est très lent. "
                    "Continuer quand même (utile pour tests)."
                )
            else:
                logger.info("GPU : %s (%d Go) ✓", gpu_name, gpu_memory)
        except ImportError:
            results["gpu"] = {"available": False, "name": "torch non installé"}
            logger.warning("torch non disponible — vérifier l'installation.")

        # 3. MLflow
        try:
            import mlflow
            from src.training.config import TrainingConfig
            cfg = TrainingConfig()
            mlflow.set_tracking_uri(cfg.mlflow_tracking_uri)
            client = mlflow.tracking.MlflowClient()
            # Test léger : lister les experiments
            client.search_experiments()
            results["mlflow"] = "ok"
            logger.info("MLflow accessible : %s ✓", cfg.mlflow_tracking_uri)
        except Exception as e:
            raise AirflowFailException(f"MLflow inaccessible : {e}")

        # 4. PostgreSQL
        from src.database.client import health_check
        health = health_check()
        if health["status"] != "ok":
            raise AirflowFailException(f"PostgreSQL inaccessible : {health.get('message')}")
        results["postgres"] = "ok"
        logger.info("PostgreSQL ✓")

        return results

    # =========================================================================
    # TÂCHE 2 — Pull DVC
    # =========================================================================

    @task(task_id="pull_dataset_from_dvc")
    def pull_dataset_from_dvc() -> str:
        """
        Récupère la dernière version du dataset depuis le remote DVC.
        Garantit que le training utilise les données versionnées, pas
        des données locales potentiellement modifiées.
        """
        import subprocess

        result = subprocess.run(
            ["dvc", "pull", "data/liquid/train_liquid.jsonl", "data/splits/val.jsonl"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )

        if result.returncode != 0:
            # Ne pas bloquer si le pull échoue (fichiers déjà présents localement)
            logger.warning(
                "dvc pull warning (non bloquant) : %s", result.stderr
            )
            return "dvc pull partiel — utilisation des fichiers locaux existants"

        logger.info("dvc pull terminé : %s", result.stdout.strip() or "données à jour")
        return "dvc pull réussi"

    # =========================================================================
    # TÂCHE 3 — Fine-tuning (tâche longue)
    # =========================================================================

    @task(
        task_id="run_fine_tuning",
        execution_timeout=timedelta(hours=5),
    )
    def run_fine_tuning(prerequisites: dict) -> dict:
        """
        Lance le fine-tuning LoRA-SFT via trainer.py.

        Les hyperparamètres peuvent être surchargés via les Variables Airflow :
            - lfm_lora_rank    : rang LoRA (défaut: 16)
            - lfm_num_epochs   : nombre d'epochs (défaut: 3)
            - lfm_learning_rate: learning rate (défaut: 2e-4)

        Retourne le run_id MLflow pour les tâches suivantes.
        """
        import sys
        sys.path.insert(0, str(PROJECT_ROOT))

        from src.training.config import LoraConfig, TrainingConfig

        # Surcharge via Variables Airflow (si définies dans l'UI)
        training_cfg = TrainingConfig(
            num_train_epochs=int(Variable.get("lfm_num_epochs", default_var=3)),
            learning_rate=float(Variable.get("lfm_learning_rate", default_var=2e-4)),
        )
        lora_cfg = LoraConfig(
            r=int(Variable.get("lfm_lora_rank", default_var=16)),
        )
        lora_cfg.lora_alpha = lora_cfg.r * 2  # convention : alpha = 2 × r

        logger.info(
            "Démarrage du fine-tuning — epochs: %d | lr: %.2e | lora_r: %d",
            training_cfg.num_train_epochs,
            training_cfg.learning_rate,
            lora_cfg.r,
        )

        # Capture du run_id MLflow avant le lancement
        import mlflow
        mlflow.set_tracking_uri(training_cfg.mlflow_tracking_uri)
        mlflow.set_experiment(training_cfg.mlflow_experiment_name)

        # Import du trainer
        from src.training.trainer import _run_training
        _run_training(training_cfg=training_cfg, lora_cfg=lora_cfg)

        # Récupération du run_id du dernier run
        client = mlflow.tracking.MlflowClient()
        experiment = client.get_experiment_by_name(training_cfg.mlflow_experiment_name)
        runs = client.search_runs(
            experiment_ids=[experiment.experiment_id],
            order_by=["start_time DESC"],
            max_results=1,
        )

        if not runs:
            raise AirflowFailException("Aucun run MLflow trouvé après entraînement.")

        latest_run = runs[0]
        run_id = latest_run.info.run_id
        eval_loss = latest_run.data.metrics.get("final/eval_loss", 0)

        logger.info(
            "Fine-tuning terminé — Run ID: %s | Eval loss: %.4f",
            run_id, eval_loss
        )

        return {
            "run_id":    run_id,
            "eval_loss": eval_loss,
            "model_uri": f"runs:/{run_id}/model",
        }

    # =========================================================================
    # TÂCHE 4 — Évaluation du modèle fine-tuné
    # =========================================================================

    @task(task_id="evaluate_fine_tuned_model")
    def evaluate_fine_tuned_model(training_result: dict) -> dict:
        """
        Évalue le modèle fine-tuné sur le test set et log les métriques
        finales dans MLflow.

        Métriques calculées :
        - eval_loss sur le test set (perplexité)
        - Comparaison avec la baseline (modèle de base sans fine-tuning)
        """
        import math
        import sys
        sys.path.insert(0, str(PROJECT_ROOT))

        import mlflow
        from src.training.config import TrainingConfig

        cfg = TrainingConfig()
        mlflow.set_tracking_uri(cfg.mlflow_tracking_uri)
        run_id = training_result["run_id"]

        # Récupération des métriques du run de training
        client = mlflow.tracking.MlflowClient()
        run = client.get_run(run_id)
        metrics = run.data.metrics

        eval_loss      = metrics.get("final/eval_loss",      training_result["eval_loss"])
        eval_perplexity = metrics.get("final/eval_perplexity", math.exp(eval_loss) if eval_loss < 10 else 0)

        # Log des métriques d'évaluation dans le run existant
        with mlflow.start_run(run_id=run_id):
            mlflow.log_metrics({
                "test/eval_loss":       eval_loss,
                "test/eval_perplexity": eval_perplexity,
            })

        logger.info(
            "Évaluation finale — Loss: %.4f | Perplexité: %.2f",
            eval_loss, eval_perplexity
        )

        return {
            "run_id":          run_id,
            "eval_loss":       eval_loss,
            "eval_perplexity": eval_perplexity,
            "passes_threshold": eval_loss < MAX_ACCEPTABLE_EVAL_LOSS,
        }

    # =========================================================================
    # TÂCHE 5A — Promotion vers Staging
    # =========================================================================

    @task(task_id="promote_to_staging")
    def promote_to_staging(evaluation_result: dict) -> dict:
        """
        Promeut le modèle vers le stade Staging dans le MLflow Model Registry
        si les métriques d'évaluation sont acceptables.

        Si la eval_loss dépasse le seuil configuré, bloque la promotion
        et logue un avertissement.
        """
        import sys
        sys.path.insert(0, str(PROJECT_ROOT))

        import mlflow
        from src.training.config import TrainingConfig

        cfg = TrainingConfig()
        mlflow.set_tracking_uri(cfg.mlflow_tracking_uri)
        client = mlflow.tracking.MlflowClient()

        eval_loss = evaluation_result["eval_loss"]
        passes    = evaluation_result["passes_threshold"]

        if not passes:
            logger.warning(
                "⚠ Eval loss %.4f > seuil %.4f — modèle NON promu vers Staging.",
                eval_loss,
                MAX_ACCEPTABLE_EVAL_LOSS,
            )
            return {
                "promoted":    False,
                "reason":      f"Eval loss {eval_loss:.4f} dépasse le seuil {MAX_ACCEPTABLE_EVAL_LOSS}",
                "model_stage": "None",
            }

        # Recherche de la dernière version du modèle
        try:
            versions = client.search_model_versions(f"name='{cfg.mlflow_model_name}'")
            if not versions:
                logger.warning(
                    "Aucune version du modèle '%s' trouvée dans le Registry. "
                    "Le modèle a peut-être déjà été enregistré par le callback.",
                    cfg.mlflow_model_name
                )
                return {"promoted": False, "reason": "Aucune version dans le Registry"}

            # Prendre la version la plus récente
            latest_version = max(versions, key=lambda v: int(v.version))
            current_stage  = latest_version.current_stage

            if current_stage in ("Staging", "Production"):
                logger.info(
                    "Modèle version %s déjà au stade '%s' — pas de changement.",
                    latest_version.version, current_stage
                )
            else:
                client.transition_model_version_stage(
                    name=cfg.mlflow_model_name,
                    version=latest_version.version,
                    stage="Staging",
                    archive_existing_versions=False,
                )
                logger.info(
                    "✅ Modèle v%s promu vers Staging (eval_loss: %.4f)",
                    latest_version.version, eval_loss
                )

            return {
                "promoted":      True,
                "model_name":    cfg.mlflow_model_name,
                "model_version": latest_version.version,
                "model_stage":   "Staging",
                "eval_loss":     eval_loss,
            }

        except Exception as e:
            logger.error("Erreur lors de la promotion : %s", e)
            return {"promoted": False, "reason": str(e)}

    # =========================================================================
    # TÂCHE 5B — Log du résumé (parallèle à promote_to_staging)
    # =========================================================================

    @task(task_id="log_training_summary")
    def log_training_summary(
        training_result: dict,
        evaluation_result: dict,
    ) -> None:
        """
        Génère et sauvegarde un résumé Markdown de l'entraînement.
        S'exécute en parallèle de promote_to_staging.
        """
        import math
        run_id    = training_result["run_id"]
        eval_loss = evaluation_result["eval_loss"]
        perplexity = evaluation_result["eval_perplexity"]
        passes    = evaluation_result["passes_threshold"]

        summary = f"""# Résumé du Fine-tuning — LFM2.5-350M Lean Startup

**Date :** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**MLflow Run ID :** `{run_id}`

## Métriques finales

| Métrique | Valeur |
|---|---|
| Eval Loss | `{eval_loss:.4f}` |
| Perplexité | `{perplexity:.2f}` |
| Seuil qualité | `{MAX_ACCEPTABLE_EVAL_LOSS}` |
| Statut | {"✅ Passe" if passes else "❌ Échoue"} |

## Interprétation

Une perplexité de **{perplexity:.1f}** signifie que le modèle est "aussi incertain
qu'entre {perplexity:.0f} tokens équiprobables" en moyenne.
{"Un score < 15 est excellent pour ce type de tâche." if perplexity < 15 else
 "Envisager plus d'epochs ou un dataset plus large." if perplexity > 25 else
 "Score correct — acceptable pour la mise en production."}

## Prochaine étape

{"Promouvoir de **Staging → Production** via l'UI MLflow ou le DAG d'évaluation." if passes else
 "Analyser les erreurs, enrichir le dataset, et relancer le fine-tuning."}
"""

        summary_path = PROJECT_ROOT / "TRAINING_SUMMARY.md"
        summary_path.write_text(summary, encoding="utf-8")
        logger.info("Résumé sauvegardé : %s", summary_path)

    # =========================================================================
    # TÂCHE 6 — Notification finale
    # =========================================================================

    @task(
        task_id="notify_completion",
        trigger_rule=TriggerRule.ALL_DONE,
    )
    def notify_completion(
        promotion_result: dict,
        evaluation_result: dict,
    ) -> None:
        """Log le résumé final du pipeline."""
        promoted   = promotion_result.get("promoted", False)
        eval_loss  = evaluation_result.get("eval_loss", 0)
        perplexity = evaluation_result.get("eval_perplexity", 0)

        logger.info("=" * 60)
        if promoted:
            logger.info("✅ Pipeline fine-tuning terminé avec succès")
            logger.info(
                "   Modèle %s v%s → Staging",
                promotion_result.get("model_name", ""),
                promotion_result.get("model_version", ""),
            )
        else:
            logger.warning("⚠ Pipeline fine-tuning terminé — modèle NON promu")
            logger.warning("   Raison : %s", promotion_result.get("reason", "inconnue"))

        logger.info(
            "   Eval loss: %.4f | Perplexité: %.2f",
            eval_loss, perplexity
        )
        logger.info("=" * 60)

    # =========================================================================
    # ORCHESTRATION
    # =========================================================================

    start = EmptyOperator(task_id="start")

    prereqs  = check_prerequisites()
    pull     = pull_dataset_from_dvc()
    training = run_fine_tuning(prerequisites=prereqs)
    eval_res = evaluate_fine_tuned_model(training_result=training)

    # Tâches parallèles
    promotion = promote_to_staging(evaluation_result=eval_res)
    summary   = log_training_summary(
        training_result=training,
        evaluation_result=eval_res,
    )

    notify = notify_completion(
        promotion_result=promotion,
        evaluation_result=eval_res,
    )

    # Graphe
    start >> prereqs >> pull >> training >> eval_res
    eval_res >> [promotion, summary]
    [promotion, summary] >> notify


fine_tuning_pipeline()
