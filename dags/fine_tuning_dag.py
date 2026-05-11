"""
dags/fine_tuning_dag.py
========================
Airflow DAG that orchestrates remote GPU fine-tuning.

Local Docker services keep the control plane:
- Airflow triggers and monitors the job.
- DVC versions and distributes datasets.
- MLflow receives metrics and artifacts.
- PostgreSQL remains the local knowledge database.

The actual LoRA/SFT training runs on a GPU machine reachable over SSH
(Colab through ngrok, a cloud VM, or a workstation).
"""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from airflow.decorators import dag, task
from airflow.exceptions import AirflowFailException
from airflow.models import Variable
from airflow.operators.empty import EmptyOperator
from airflow.utils.trigger_rule import TriggerRule


logger = logging.getLogger(__name__)

PROJECT_ROOT = Path("/opt/airflow")
MAX_ACCEPTABLE_EVAL_LOSS = 2.5

DEFAULT_ARGS = {
    "owner": "lfm-team",
    "retries": 0,
    "execution_timeout": timedelta(hours=8),
    "email_on_failure": False,
}


def _required_variable(name: str, help_text: str) -> str:
    value = Variable.get(name, default_var="").strip()
    if not value:
        raise AirflowFailException(
            f"Variable Airflow manquante: {name}. {help_text}"
        )
    return value


@dag(
    dag_id="lfm_fine_tuning",
    description=(
        "Déclenche le fine-tuning LoRA-SFT sur une machine GPU distante "
        "et suit le run dans MLflow Docker."
    ),
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["training", "remote-gpu", "mlflow", "lora", "lean-startup"],
    doc_md="""
## DAG : Fine-tuning distant LFM2.5-350M

Ce DAG ne lance pas `torch` dans Docker local. Il orchestre un entraînement sur
une machine GPU distante via SSH, puis lit les métriques dans MLflow.

### Services locaux Docker
- Airflow : `http://localhost:8080`
- MLflow : `http://localhost:5000`
- PostgreSQL : `localhost:5433` côté host, `postgres:5432` côté containers

### Variables Airflow obligatoires
- `lfm_remote_ssh_host` : host SSH distant ou host ngrok
- `lfm_remote_ssh_user` : utilisateur SSH distant
- `lfm_remote_mlflow_tracking_uri` : URI MLflow accessible depuis la machine distante

### Variables Airflow optionnelles
- `lfm_remote_ssh_port` : port SSH, défaut `22`
- `lfm_remote_ssh_key_path` : clé privée dans le container Airflow, défaut `/opt/airflow/.ssh/id_rsa`
- `lfm_remote_project_dir` : dossier projet sur la machine distante
- `lfm_remote_setup_command` : commande d'installation distante
- `lfm_remote_dvc_pull_command` : commande DVC distante
- `lfm_remote_train_command` : commande d'entraînement distante
    """,
)
def fine_tuning_pipeline():
    @task(task_id="check_local_services")
    def check_local_services() -> dict:
        """Check local Docker-side prerequisites before spending GPU time."""
        import sys

        sys.path.insert(0, str(PROJECT_ROOT))

        train_file = PROJECT_ROOT / "data" / "liquid" / "train_liquid.jsonl"
        val_file = PROJECT_ROOT / "data" / "liquid" / "val_liquid.jsonl"
        for dataset_file in [train_file, val_file]:
            if not dataset_file.exists():
                raise AirflowFailException(
                    f"Dataset manquant: {dataset_file}. Lancer `lfm_build_dataset` d'abord."
                )

        train_size = sum(1 for _ in train_file.open(encoding="utf-8"))
        if train_size < 5000 * 0.75:
            raise AirflowFailException(
                f"Train set trop petit: {train_size}. Régénérer le dataset."
            )

        try:
            import mlflow
            from src.training.config import TrainingConfig

            cfg = TrainingConfig()
            mlflow.set_tracking_uri(cfg.mlflow_tracking_uri)
            client = mlflow.tracking.MlflowClient()
            client.search_experiments()
            mlflow_status = cfg.mlflow_tracking_uri
        except Exception as exc:
            raise AirflowFailException(f"MLflow Docker inaccessible: {exc}") from exc

        try:
            from src.database.client import health_check

            health = health_check()
            if health["status"] != "ok":
                raise AirflowFailException(
                    f"PostgreSQL Docker inaccessible: {health.get('message')}"
                )
        except Exception as exc:
            raise AirflowFailException(f"PostgreSQL Docker inaccessible: {exc}") from exc

        logger.info(
            "Prérequis locaux OK — train=%d | MLflow=%s | PostgreSQL=ok",
            train_size,
            mlflow_status,
        )
        return {
            "train_size": train_size,
            "val_size": sum(1 for _ in val_file.open(encoding="utf-8")),
            "mlflow_tracking_uri": mlflow_status,
        }

    @task(task_id="build_remote_training_command")
    def build_remote_training_command(local_status: dict) -> dict:
        """Build a safe SSH command from Airflow variables."""
        del local_status

        host = _required_variable(
            "lfm_remote_ssh_host",
            "Exemple ngrok: 0.tcp.ngrok.io",
        )
        user = Variable.get("lfm_remote_ssh_user", default_var="root").strip()
        port = Variable.get("lfm_remote_ssh_port", default_var="22").strip()
        key_path = Variable.get(
            "lfm_remote_ssh_key_path",
            default_var="/opt/airflow/.ssh/id_rsa",
        ).strip()
        project_dir = Variable.get(
            "lfm_remote_project_dir",
            default_var="~/LFM-Lean-Startup-Project",
        ).strip()
        mlflow_tracking_uri = Variable.get(
            "lfm_remote_mlflow_tracking_uri",
            default_var=os.getenv("PUBLIC_MLFLOW_TRACKING_URI", ""),
        ).strip()
        if not mlflow_tracking_uri:
            raise AirflowFailException(
                "Définir `lfm_remote_mlflow_tracking_uri` avec une URL accessible "
                "depuis Colab/VM GPU, par exemple une URL ngrok vers MLflow."
            )

        if key_path and not Path(key_path).exists():
            raise AirflowFailException(
                f"Clé SSH introuvable dans le container Airflow: {key_path}. "
                "Monter `./.ssh:/opt/airflow/.ssh:ro` ou modifier `lfm_remote_ssh_key_path`."
            )

        run_token = f"airflow-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8]}"
        setup_command = Variable.get(
            "lfm_remote_setup_command",
            default_var="pip install -r scripts/remote_training_requirements.txt",
        ).strip()
        dvc_pull_command = Variable.get(
            "lfm_remote_dvc_pull_command",
            default_var=(
                "dvc pull data/liquid/train_liquid.jsonl "
                "data/liquid/val_liquid.jsonl data/splits/test.jsonl"
            ),
        ).strip()
        train_command = Variable.get(
            "lfm_remote_train_command",
            default_var="python3 src/training/trainer.py",
        ).strip()

        exports = {
            "MLFLOW_TRACKING_URI": mlflow_tracking_uri,
            "LFM_AIRFLOW_RUN_TOKEN": run_token,
            "LFM_EXECUTION_TARGET": "remote_ssh_gpu",
            "PYTHONPATH": ".",
        }
        export_command = " ".join(
            f"export {name}={shlex.quote(value)};" for name, value in exports.items()
        )
        remote_shell = (
            "set -e; "
            f"cd {shlex.quote(project_dir)}; "
            f"{export_command} "
            f"{setup_command}; "
            f"{dvc_pull_command}; "
            f"{train_command}"
        )

        ssh_command = ["ssh", "-p", str(port), "-o", "StrictHostKeyChecking=no"]
        if key_path:
            ssh_command.extend(["-i", key_path])
        ssh_command.extend([f"{user}@{host}", remote_shell])

        safe_command = shlex.join(
            part if part != key_path else "<ssh-key>" for part in ssh_command
        )
        logger.info("Commande SSH préparée: %s", safe_command)
        return {
            "ssh_command": ssh_command,
            "safe_command": safe_command,
            "run_token": run_token,
            "mlflow_tracking_uri": mlflow_tracking_uri,
        }

    @task(task_id="run_remote_fine_tuning", execution_timeout=timedelta(hours=7))
    def run_remote_fine_tuning(remote_config: dict) -> dict:
        """Run the remote command and stream logs into Airflow."""
        logger.info("Lancement du training distant: %s", remote_config["safe_command"])
        process = subprocess.Popen(
            remote_config["ssh_command"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            logger.info("[remote] %s", line.rstrip())

        return_code = process.wait()
        if return_code != 0:
            raise AirflowFailException(
                f"Fine-tuning distant échoué avec code {return_code}."
            )

        logger.info("Fine-tuning distant terminé. Token run: %s", remote_config["run_token"])
        return {
            "run_token": remote_config["run_token"],
            "mlflow_tracking_uri": remote_config["mlflow_tracking_uri"],
        }

    @task(task_id="collect_mlflow_metrics")
    def collect_mlflow_metrics(training_result: dict) -> dict:
        """Fetch the MLflow run produced by the remote trainer."""
        import sys

        sys.path.insert(0, str(PROJECT_ROOT))

        import mlflow
        from src.training.config import TrainingConfig

        cfg = TrainingConfig()
        mlflow.set_tracking_uri(cfg.mlflow_tracking_uri)
        client = mlflow.tracking.MlflowClient()
        experiment = client.get_experiment_by_name(cfg.mlflow_experiment_name)
        if experiment is None:
            raise AirflowFailException(
                f"Experiment MLflow introuvable: {cfg.mlflow_experiment_name}"
            )

        run_token = training_result["run_token"]
        runs = client.search_runs(
            experiment_ids=[experiment.experiment_id],
            filter_string=f"tags.airflow_run_token = '{run_token}'",
            order_by=["start_time DESC"],
            max_results=1,
        )
        if not runs:
            logger.warning(
                "Aucun run trouvé avec airflow_run_token=%s. Fallback sur le dernier run.",
                run_token,
            )
            runs = client.search_runs(
                experiment_ids=[experiment.experiment_id],
                order_by=["start_time DESC"],
                max_results=1,
            )
        if not runs:
            raise AirflowFailException("Aucun run MLflow trouvé après entraînement distant.")

        run = runs[0]
        eval_loss = run.data.metrics.get("final/eval_loss", 999.0)
        eval_perplexity = run.data.metrics.get("final/eval_perplexity", 0.0)
        logger.info(
            "Run MLflow collecté — run_id=%s | eval_loss=%.4f | perplexity=%.2f",
            run.info.run_id,
            eval_loss,
            eval_perplexity,
        )
        return {
            "run_id": run.info.run_id,
            "run_token": run_token,
            "eval_loss": eval_loss,
            "eval_perplexity": eval_perplexity,
            "passes_threshold": eval_loss < MAX_ACCEPTABLE_EVAL_LOSS,
        }

    @task(task_id="promote_to_staging")
    def promote_to_staging(metrics: dict) -> dict:
        """Promote the latest registered model version if metrics are acceptable."""
        import sys

        sys.path.insert(0, str(PROJECT_ROOT))

        import mlflow
        from src.training.config import TrainingConfig

        cfg = TrainingConfig()
        mlflow.set_tracking_uri(cfg.mlflow_tracking_uri)
        client = mlflow.tracking.MlflowClient()

        if not metrics["passes_threshold"]:
            return {
                "promoted": False,
                "reason": (
                    f"Eval loss {metrics['eval_loss']:.4f} dépasse le seuil "
                    f"{MAX_ACCEPTABLE_EVAL_LOSS}."
                ),
            }

        versions = client.search_model_versions(f"name='{cfg.mlflow_model_name}'")
        if not versions:
            return {
                "promoted": False,
                "reason": "Aucune version du modèle trouvée dans MLflow Registry.",
            }

        latest_version = max(versions, key=lambda version: int(version.version))
        if latest_version.current_stage not in ("Staging", "Production"):
            client.transition_model_version_stage(
                name=cfg.mlflow_model_name,
                version=latest_version.version,
                stage="Staging",
                archive_existing_versions=False,
            )

        return {
            "promoted": True,
            "model_name": cfg.mlflow_model_name,
            "model_version": latest_version.version,
            "model_stage": "Staging",
            "eval_loss": metrics["eval_loss"],
        }

    @task(task_id="log_training_summary")
    def log_training_summary(metrics: dict, promotion_result: dict) -> None:
        """Write a lightweight summary visible from the mounted project files."""
        summary_path = PROJECT_ROOT / "src" / "data" / "reports" / "remote_training_summary.md"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary = f"""# Remote Fine-tuning Summary

Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}
MLflow Run ID: `{metrics['run_id']}`
Airflow Run Token: `{metrics['run_token']}`

| Metric | Value |
|---|---:|
| Eval loss | {metrics['eval_loss']:.4f} |
| Eval perplexity | {metrics['eval_perplexity']:.2f} |
| Threshold | {MAX_ACCEPTABLE_EVAL_LOSS:.2f} |
| Passes threshold | {metrics['passes_threshold']} |

Promotion: {promotion_result}
"""
        summary_path.write_text(summary, encoding="utf-8")
        logger.info("Résumé sauvegardé: %s", summary_path)

    @task(task_id="notify_completion", trigger_rule=TriggerRule.ALL_DONE)
    def notify_completion(metrics: dict, promotion_result: dict) -> None:
        logger.info("=" * 60)
        logger.info("Pipeline fine-tuning distant terminé")
        logger.info("Run MLflow: %s", metrics.get("run_id"))
        logger.info("Eval loss: %.4f", metrics.get("eval_loss", 999.0))
        logger.info("Promotion: %s", promotion_result)
        logger.info("=" * 60)

    start = EmptyOperator(task_id="start")
    local = check_local_services()
    remote = build_remote_training_command(local)
    training = run_remote_fine_tuning(remote)
    metrics = collect_mlflow_metrics(training)
    promotion = promote_to_staging(metrics)
    summary = log_training_summary(metrics, promotion)
    notify = notify_completion(metrics, promotion)

    start >> local >> remote >> training >> metrics >> promotion
    metrics >> summary
    [promotion, summary] >> notify


fine_tuning_pipeline()
