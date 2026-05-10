"""
src/training/trainer.py
========================
Pipeline de fine-tuning SFT complet pour LFM2.5-350M.

Flux d'exécution :
    1. Initialiser MLflow (Experiment + Run)
    2. Logger tous les hyperparamètres (params = décisions AVANT training)
    3. Charger le modèle de base et configurer LoRA (PEFT)
    4. Charger les datasets train et val
    5. Lancer le SFTTrainer (TRL) avec les callbacks MLflow
    6. Évaluer sur le val set
    7. Enregistrer le modèle dans le MLflow Registry
    8. Fermer le Run MLflow

Distinction params vs metrics (rappel fondamental MLflow) :
    params  = ce qu'on DÉCIDE avant : learning_rate, lora_rank, num_epochs
    metrics = ce qu'on OBSERVE après : eval_loss, perplexity, training_steps

Dépendances :
    pip install transformers trl peft accelerate datasets mlflow torch
"""

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# =============================================================================
# GUARD : vérifier les dépendances avant import lourd
# =============================================================================

def _check_dependencies() -> None:
    missing = []
    for pkg in ["torch", "transformers", "trl", "peft", "mlflow", "datasets"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        logger.error(
            "Dépendances manquantes : %s\n"
            "Installer avec : pip install %s",
            missing, " ".join(missing)
        )
        sys.exit(1)


# =============================================================================
# IMPORTS LOURDS (après le guard)
# =============================================================================

def _run_training(
    training_cfg=None,
    lora_cfg=None,
) -> None:
    """
    Corps principal du fine-tuning. Importé séparément pour permettre
    les tests sans charger torch au module level.
    """
    import math
    import torch
    import mlflow
    import mlflow.pytorch
    from datasets import load_dataset
    from peft import LoraConfig as PeftLoraConfig, get_peft_model, TaskType
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        TrainingArguments,
    )
    from trl import SFTTrainer, SFTConfig

    from src.training.config import LoraConfig, TrainingConfig
    from src.training.callbacks import (
        MLflowTrainingCallback,
        MLflowModelRegistryCallback,
        MLflowArtifactsCallback,
    )

    # Valeurs par défaut si non fournies
    if training_cfg is None:
        training_cfg = TrainingConfig()
    if lora_cfg is None:
        lora_cfg = LoraConfig()

    PROJECT_ROOT = Path(__file__).resolve().parents[2]

    # =========================================================================
    # 1. INITIALISATION MLFLOW
    # =========================================================================

    mlflow.set_tracking_uri(training_cfg.mlflow_tracking_uri)
    mlflow.set_experiment(training_cfg.mlflow_experiment_name)

    logger.info(
        "MLflow — Experiment : '%s' | Tracking URI : %s",
        training_cfg.mlflow_experiment_name,
        training_cfg.mlflow_tracking_uri,
    )

    with mlflow.start_run(run_name="LoRA-SFT") as run:
        run_id = run.info.run_id
        logger.info("MLflow Run démarré : %s", run_id)

        # =====================================================================
        # 2. LOGGER LES PARAMS (décisions AVANT entraînement)
        # =====================================================================

        # Params d'entraînement
        mlflow.log_params(training_cfg.log_params_dict())

        # Params LoRA (loggés séparément — clés distinctes)
        mlflow.log_params({
            "lora_r":               lora_cfg.r,
            "lora_alpha":           lora_cfg.lora_alpha,
            "lora_dropout":         lora_cfg.lora_dropout,
            "lora_target_modules":  ",".join(lora_cfg.target_modules),
            "lora_bias":            lora_cfg.bias,
        })

        # Tag pour filtrage rapide dans l'UI MLflow
        mlflow.set_tags({
            "model_type":   "causal_lm",
            "architecture": "LFM2.5-350M",
            "method":       "LoRA-SFT",
            "task":         "lean_startup_analysis",
            "framework":    "TRL+PEFT",
        })

        logger.info("Hyperparamètres loggés dans MLflow.")

        # =====================================================================
        # 3. CHARGEMENT DU TOKENIZER
        # =====================================================================

        logger.info("Chargement du tokenizer : %s", training_cfg.base_model_id)
        tokenizer = AutoTokenizer.from_pretrained(
            training_cfg.base_model_id,
            trust_remote_code=True,
        )

        # LFM2.5 peut nécessiter la définition du pad token
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
            logger.info("pad_token défini sur eos_token : %s", tokenizer.eos_token)

        # =====================================================================
        # 4. CHARGEMENT DU MODÈLE DE BASE
        # =====================================================================

        logger.info("Chargement du modèle de base : %s", training_cfg.base_model_id)

        model = AutoModelForCausalLM.from_pretrained(
            training_cfg.base_model_id,
            torch_dtype=torch.bfloat16 if training_cfg.bf16 else torch.float16,
            device_map="auto",
            trust_remote_code=True,
        )

        # Gradient checkpointing avant PEFT (requis pour économiser la VRAM)
        if training_cfg.gradient_checkpointing:
            model.gradient_checkpointing_enable()
            model.config.use_cache = False  # incompatible avec grad checkpointing

        # =====================================================================
        # 5. CONFIGURATION LORA (PEFT)
        # =====================================================================

        logger.info(
            "Configuration LoRA — rank: %d | alpha: %d | modules: %s",
            lora_cfg.r, lora_cfg.lora_alpha, lora_cfg.target_modules
        )

        peft_config = PeftLoraConfig(
            r=                  lora_cfg.r,
            lora_alpha=         lora_cfg.lora_alpha,
            lora_dropout=       lora_cfg.lora_dropout,
            bias=               lora_cfg.bias,
            task_type=          TaskType.CAUSAL_LM,
            target_modules=     lora_cfg.target_modules,
            modules_to_save=    lora_cfg.modules_to_save,
        )

        model = get_peft_model(model, peft_config)

        # Logger le nombre de paramètres entraînables
        trainable, total = model.get_nb_trainable_parameters()
        trainable_ratio = trainable / total if total > 0 else 0

        mlflow.log_params({
            "trainable_params":       trainable,
            "total_params":           total,
            "trainable_params_ratio": round(trainable_ratio, 4),
        })

        logger.info(
            "Paramètres entraînables : %d / %d (%.2f%%)",
            trainable, total, trainable_ratio * 100
        )

        # =====================================================================
        # 6. CHARGEMENT DES DATASETS
        # =====================================================================

        logger.info("Chargement des données...")

        train_dataset = load_dataset(
            "json",
            data_files=training_cfg.train_file,
            split="train",
        )
        val_dataset = load_dataset(
            "json",
            data_files=training_cfg.val_file,
            split="train",  # HuggingFace lit tout en "train" depuis JSON
        )

        mlflow.log_params({
            "train_samples": len(train_dataset),
            "val_samples":   len(val_dataset),
            "train_file":    Path(training_cfg.train_file).name,
        })

        logger.info(
            "Données chargées — train: %d | val: %d",
            len(train_dataset), len(val_dataset)
        )

        # =====================================================================
        # 7. TRAINING ARGUMENTS
        # =====================================================================

        training_args = SFTConfig(
            **training_cfg.to_hf_training_args(),
            max_seq_length=training_cfg.max_seq_length,
            dataset_text_field=training_cfg.dataset_field,
            packing=False,  # pas de packing : conversations de longueurs variables
        )

        # =====================================================================
        # 8. CALLBACKS MLFLOW
        # =====================================================================

        dataset_report = str(PROJECT_ROOT / "DATASET_METRICS_REPORT.md")
        config_dict = {
            "training": training_cfg.log_params_dict(),
            "lora": {
                "r": lora_cfg.r,
                "alpha": lora_cfg.lora_alpha,
                "dropout": lora_cfg.lora_dropout,
                "target_modules": lora_cfg.target_modules,
            },
        }

        callbacks = [
            MLflowTrainingCallback(run_id=run_id),
            MLflowArtifactsCallback(
                config_dict=config_dict,
                dataset_report_path=dataset_report,
            ),
        ]

        # Callback d'enregistrement au Registry (si activé)
        if training_cfg.auto_register_model:
            callbacks.append(
                MLflowModelRegistryCallback(
                    model_name=   training_cfg.mlflow_model_name,
                    target_stage= training_cfg.register_to_stage,
                    output_dir=   training_cfg.output_dir,
                )
            )

        # =====================================================================
        # 9. ENTRAÎNEMENT
        # =====================================================================

        logger.info("=" * 60)
        logger.info("Début de l'entraînement SFT")
        logger.info("  Epochs           : %d", training_cfg.num_train_epochs)
        logger.info("  Learning rate    : %.2e", training_cfg.learning_rate)
        logger.info("  Batch effectif   : %d",
                    training_cfg.per_device_train_batch_size *
                    training_cfg.gradient_accumulation_steps)
        logger.info("  Steps estimés    : ~%d",
                    math.ceil(len(train_dataset) / (
                        training_cfg.per_device_train_batch_size *
                        training_cfg.gradient_accumulation_steps
                    )) * training_cfg.num_train_epochs)
        logger.info("=" * 60)

        trainer = SFTTrainer(
            model=          model,
            tokenizer=      tokenizer,
            args=           training_args,
            train_dataset=  train_dataset,
            eval_dataset=   val_dataset,
            callbacks=      callbacks,
        )

        train_result = trainer.train()

        # =====================================================================
        # 10. MÉTRIQUES FINALES
        # =====================================================================

        logger.info("Évaluation finale sur le val set...")
        eval_metrics = trainer.evaluate()

        final_eval_loss = eval_metrics.get("eval_loss", 0)
        mlflow.log_metrics({
            "final/eval_loss":       final_eval_loss,
            "final/eval_perplexity": math.exp(final_eval_loss) if final_eval_loss < 10 else 0,
            "final/train_loss":      train_result.training_loss,
            "final/total_steps":     train_result.global_step,
        })

        # =====================================================================
        # 11. SAUVEGARDE DU MODÈLE FINAL
        # =====================================================================

        logger.info("Sauvegarde du modèle final : %s", training_cfg.output_dir)
        trainer.save_model(training_cfg.output_dir)
        tokenizer.save_pretrained(training_cfg.output_dir)

        logger.info("=" * 60)
        logger.info("Fine-tuning terminé avec succès !")
        logger.info("  Eval loss finale  : %.4f", final_eval_loss)
        logger.info("  Perplexité finale : %.2f", math.exp(final_eval_loss) if final_eval_loss < 10 else 0)
        logger.info("  Modèle sauvegardé : %s", training_cfg.output_dir)
        logger.info("  MLflow Run ID     : %s", run_id)
        logger.info("=" * 60)


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================

def main() -> None:
    """
    Lance le fine-tuning avec la configuration par défaut.
    Pour une configuration personnalisée, modifier les dataclasses
    dans config.py ou passer des arguments CLI.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )

    _check_dependencies()

    from src.training.config import LoraConfig, TrainingConfig

    training_cfg = TrainingConfig()
    lora_cfg     = LoraConfig()

    _run_training(training_cfg=training_cfg, lora_cfg=lora_cfg)


if __name__ == "__main__":
    main()
