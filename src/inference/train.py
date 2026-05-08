import os
import yaml
import logging
from pathlib import Path
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import LoraConfig, get_peft_model
from trl import SFTTrainer, SFTConfig
import mlflow
from dotenv import load_dotenv

# Chargement des variables d'environnement (.env)
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def train():
    """
    Lance le processus de fine-tuning LoRA basé sur la configuration YAML.
    Intègre le tracking MLflow pour les métriques et les artefacts.
    """
    # 1. Chargement de la configuration
    config_path = Path("configs/training_config.yaml")
    if not config_path.exists():
        logger.error(f"Fichier de configuration manquant : {config_path}")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 2. Configuration MLflow
    mlflow_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    mlflow.set_tracking_uri(mlflow_uri)
    mlflow.set_experiment("LFM-Lean-Startup-SFT")

    logger.info(f"MLflow Tracking URI : {mlflow_uri}")

    # 3. Chargement des datasets
    logger.info("Chargement des datasets...")
    dataset = load_dataset("json", data_files={
        "train": config["train_path"],
        "eval": config["eval_path"]
    })

    # 4. Chargement du modèle et du tokenizer
    model_id = config["model_id"]
    logger.info(f"Chargement du modèle de base : {model_id}")
    
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype="auto", # Utilise bf16/fp16 si possible
        device_map="auto",
        trust_remote_code=True
    )

    # 5. Configuration LoRA
    logger.info("Configuration de LoRA...")
    lora_config = LoraConfig(**config["lora_args"])
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # 6. Configuration de l'entraînement (TRL)
    logger.info("Préparation du SFTTrainer...")
    sft_config = SFTConfig(
        output_dir=config["output_dir"],
        **config["training_args"]
    )

    trainer = SFTTrainer(
        model=model,
        args=sft_config,
        train_dataset=dataset["train"],
        eval_dataset=dataset["eval"],
        tokenizer=tokenizer,
        dataset_text_field="messages", # Le format ChatML est géré par TRL si spécifié
    )

    # 7. Entraînement
    logger.info("Début de l'entraînement...")
    with mlflow.start_run(run_name="LFM-350M-Lean-Startup"):
        # Log des paramètres de config dans MLflow
        mlflow.log_params(config["training_args"])
        mlflow.log_params(config["lora_args"])
        
        trainer.train()
        
        # Sauvegarde finale
        logger.info(f"Sauvegarde du modèle dans {config['output_dir']}...")
        trainer.save_model(config["output_dir"])
        tokenizer.save_pretrained(config["output_dir"])
        
        # Log de l'adaptateur dans MLflow
        mlflow.log_artifacts(config["output_dir"], artifact_path="model_adapter")

    logger.info("Entraînement terminé avec succès.")

if __name__ == "__main__":
    train()
