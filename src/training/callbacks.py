"""
src/training/callbacks.py
==========================
Callbacks MLflow pour l'intégration avec HuggingFace Trainer.

Responsabilités :
    - Logger les métriques à chaque step (loss, learning rate, perplexité)
    - Logger les artefacts en fin d'entraînement (config, tokenizer)
    - Enregistrer le modèle au Model Registry MLflow
    - Transitionner vers le bon stade (Staging / Production)

Architecture MLflow rappel :
    Tracking Server → Experiment → Run
                                    ├── params  (décisions avant training)
                                    ├── metrics (résultats après chaque step)
                                    └── artifacts (modèle, config, rapport)

Le Run est créé dans trainer.py avant le début de l'entraînement.
Les callbacks reçoivent l'objet mlflow_run pour y écrire.

Dépendances :
    pip install mlflow transformers
"""

import json
import logging
import math
import os
import tempfile
from pathlib import Path
from typing import Any

import mlflow
from transformers import TrainerCallback, TrainerControl, TrainerState, TrainingArguments

logger = logging.getLogger(__name__)


# =============================================================================
# CALLBACK PRINCIPAL — MÉTRIQUES ET ARTEFACTS
# =============================================================================

class MLflowTrainingCallback(TrainerCallback):
    """
    Callback principal qui logue les métriques d'entraînement dans MLflow.

    Connecté à un Run MLflow actif créé par trainer.py.
    Ne crée pas de Run lui-même — il écrit dans le Run existant.

    Métriques loggées :
        train/loss          : loss d'entraînement (toutes les logging_steps)
        train/learning_rate : learning rate courant
        train/perplexity    : exp(loss) — plus lisible que la loss seule
        eval/loss           : loss de validation (à chaque eval)
        eval/perplexity     : perplexité sur le val set
    """

    def __init__(self, run_id: str | None = None):
        """
        Args:
            run_id : ID du Run MLflow actif. Si None, utilise le run actif.
        """
        self.run_id = run_id
        self._step = 0

    def on_log(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        logs: dict[str, float] | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Appelé à chaque logging_steps.
        C'est ici que les métriques de training sont capturées.
        """
        if logs is None:
            return

        step = state.global_step
        metrics: dict[str, float] = {}

        # Loss d'entraînement
        if "loss" in logs:
            loss = logs["loss"]
            metrics["train/loss"] = loss
            # Perplexité = exp(loss) — plus intuitive : perplexité de 50
            # signifie que le modèle est "aussi perdu qu'entre 50 tokens"
            if loss < 10:  # éviter overflow sur des losses aberrantes
                metrics["train/perplexity"] = math.exp(loss)

        # Learning rate
        if "learning_rate" in logs:
            metrics["train/learning_rate"] = logs["learning_rate"]

        # Toute métrique supplémentaire préfixée "train/"
        for key, val in logs.items():
            if key not in ("loss", "learning_rate") and isinstance(val, (int, float)):
                metrics[f"train/{key}"] = val

        if metrics:
            mlflow.log_metrics(metrics, step=step)
            logger.debug("MLflow — step %d : %s", step, metrics)

    def on_evaluate(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        metrics: dict[str, float] | None = None,
        **kwargs: Any,
    ) -> None:
        """
        Appelé après chaque évaluation sur le val set.
        Les métriques d'évaluation sont préfixées "eval/".
        """
        if metrics is None:
            return

        step = state.global_step
        mlflow_metrics: dict[str, float] = {}

        for key, val in metrics.items():
            if not isinstance(val, (int, float)):
                continue

            # HuggingFace préfixe déjà avec "eval_"
            clean_key = key.replace("eval_", "")
            mlflow_key = f"eval/{clean_key}"
            mlflow_metrics[mlflow_key] = val

            # Perplexité d'évaluation
            if clean_key == "loss" and val < 10:
                mlflow_metrics["eval/perplexity"] = math.exp(val)

        if mlflow_metrics:
            mlflow.log_metrics(mlflow_metrics, step=step)
            eval_loss = mlflow_metrics.get("eval/loss", "N/A")
            eval_ppl  = mlflow_metrics.get("eval/perplexity", "N/A")
            logger.info(
                "Évaluation step %d — loss: %.4f | perplexité: %.2f",
                step,
                eval_loss if isinstance(eval_loss, float) else 0,
                eval_ppl  if isinstance(eval_ppl,  float) else 0,
            )

    def on_save(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        **kwargs: Any,
    ) -> None:
        """Appelé à chaque sauvegarde de checkpoint."""
        logger.debug(
            "Checkpoint sauvegardé — step %d | best: %s",
            state.global_step,
            state.best_model_checkpoint,
        )

    def on_train_end(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        **kwargs: Any,
    ) -> None:
        """
        Appelé en fin d'entraînement.
        Logue les métriques finales : best loss, nombre total de steps.
        """
        final_metrics = {
            "train/total_steps":    state.global_step,
            "train/total_epochs":   state.epoch or 0,
        }

        if state.best_metric is not None:
            final_metrics["eval/best_loss"] = state.best_metric
            if state.best_metric < 10:
                final_metrics["eval/best_perplexity"] = math.exp(state.best_metric)

        mlflow.log_metrics(final_metrics, step=state.global_step)

        logger.info(
            "Entraînement terminé — %d steps | meilleure loss: %.4f",
            state.global_step,
            state.best_metric or 0,
        )


# =============================================================================
# CALLBACK D'ENREGISTREMENT DU MODÈLE
# =============================================================================

class MLflowModelRegistryCallback(TrainerCallback):
    """
    Enregistre le modèle fine-tuné dans le MLflow Model Registry
    en fin d'entraînement.

    Flux :
        1. Logue le modèle comme artefact MLflow
        2. Enregistre dans le Registry sous mlflow_model_name
        3. Crée une nouvelle version
        4. Transite vers le stade cible (Staging par défaut)

    Le Model Registry permet de :
        - Versionner les modèles fine-tunés
        - Promouvoir de Staging → Production → Archived
        - Rollback instantané vers une version précédente
    """

    def __init__(
        self,
        model_name:   str,
        target_stage: str = "Staging",
        output_dir:   str = "",
    ):
        """
        Args:
            model_name   : Nom dans le Registry MLflow (ex: "lfm25-lean-startup").
            target_stage : Stade cible après enregistrement ("Staging" | "Production").
            output_dir   : Répertoire où le modèle fine-tuné est sauvegardé.
        """
        self.model_name   = model_name
        self.target_stage = target_stage
        self.output_dir   = output_dir

    def on_train_end(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        model=None,
        tokenizer=None,
        **kwargs: Any,
    ) -> None:
        """Enregistre le modèle dans le Registry en fin d'entraînement."""
        try:
            self._register_model(model, tokenizer, state, args)
        except Exception as e:
            # Ne pas faire échouer l'entraînement si l'enregistrement échoue
            logger.error(
                "Échec de l'enregistrement du modèle dans MLflow Registry : %s", e
            )

    def _register_model(
        self,
        model: Any,
        tokenizer: Any,
        state: TrainerState,
        args: TrainingArguments,
    ) -> None:
        """Logique d'enregistrement du modèle."""
        output_dir = self.output_dir or args.output_dir
        model_path = Path(output_dir)

        if not model_path.exists():
            logger.warning(
                "Répertoire du modèle introuvable : %s. "
                "Enregistrement dans le Registry ignoré.",
                model_path
            )
            return

        logger.info("Enregistrement du modèle dans MLflow Registry...")

        # 1. Créer un fichier de métadonnées d'entraînement
        training_meta = {
            "base_model":        "liquid-ai/LFM2.5-350M-Base",
            "fine_tuning_type":  "LoRA-SFT",
            "task":              "Lean Startup Analysis",
            "best_eval_loss":    state.best_metric,
            "total_steps":       state.global_step,
            "best_checkpoint":   state.best_model_checkpoint,
        }

        meta_path = model_path / "training_metadata.json"
        meta_path.write_text(
            json.dumps(training_meta, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        # 2. Logger le répertoire du modèle comme artefact MLflow
        mlflow.log_artifacts(str(model_path), artifact_path="model")

        # 3. Enregistrer dans le Model Registry
        run_id = mlflow.active_run().info.run_id if mlflow.active_run() else None

        if run_id:
            model_uri = f"runs:/{run_id}/model"
            registered = mlflow.register_model(
                model_uri=model_uri,
                name=self.model_name,
            )

            logger.info(
                "Modèle enregistré : %s version %s",
                self.model_name,
                registered.version,
            )

            # 4. Transitionner vers le stade cible
            client = mlflow.tracking.MlflowClient()
            client.transition_model_version_stage(
                name=self.model_name,
                version=registered.version,
                stage=self.target_stage,
                archive_existing_versions=False,  # garder les versions précédentes
            )

            logger.info(
                "Modèle transitionné vers le stade '%s' (version %s)",
                self.target_stage,
                registered.version,
            )

            # 5. Ajouter des tags descriptifs sur la version
            client.set_model_version_tag(
                name=self.model_name,
                version=registered.version,
                key="eval_loss",
                value=str(round(state.best_metric or 0, 4)),
            )
            client.set_model_version_tag(
                name=self.model_name,
                version=registered.version,
                key="base_model",
                value="liquid-ai/LFM2.5-350M-Base",
            )
        else:
            logger.warning("Pas de Run MLflow actif — enregistrement Registry ignoré.")


# =============================================================================
# CALLBACK D'ARTEFACTS
# =============================================================================

class MLflowArtifactsCallback(TrainerCallback):
    """
    Logue des artefacts supplémentaires dans MLflow :
        - Fichier de configuration JSON complet
        - Rapport de dataset (si disponible)
        - Sample de prédictions (à chaque évaluation)
    """

    def __init__(self, config_dict: dict, dataset_report_path: str | None = None):
        """
        Args:
            config_dict          : Dict de la configuration complète (training + LoRA).
            dataset_report_path  : Chemin vers DATASET_METRICS_REPORT.md (optionnel).
        """
        self.config_dict          = config_dict
        self.dataset_report_path  = dataset_report_path

    def on_train_begin(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        **kwargs: Any,
    ) -> None:
        """Logue la configuration complète au début de l'entraînement."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(self.config_dict, f, indent=2, ensure_ascii=False)
            tmp_path = f.name

        mlflow.log_artifact(tmp_path, artifact_path="config")
        os.unlink(tmp_path)

        # Logger le rapport de dataset si disponible
        if self.dataset_report_path and Path(self.dataset_report_path).exists():
            mlflow.log_artifact(
                self.dataset_report_path,
                artifact_path="dataset"
            )
            logger.info("Rapport dataset loggé dans MLflow.")

    def on_train_end(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        **kwargs: Any,
    ) -> None:
        """Logue le résumé de l'entraînement en fin de run."""
        summary = {
            "status":           "completed",
            "total_steps":      state.global_step,
            "total_epochs":     round(state.epoch or 0, 2),
            "best_eval_loss":   round(state.best_metric or 0, 4),
            "best_checkpoint":  state.best_model_checkpoint,
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
            tmp_path = f.name

        mlflow.log_artifact(tmp_path, artifact_path="training_summary")
        os.unlink(tmp_path)
        logger.info("Résumé d'entraînement sauvegardé dans MLflow.")
