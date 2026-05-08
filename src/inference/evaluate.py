import os
import json
import yaml
import logging
from pathlib import Path
from src.inference.pipeline import LeanStartupAnalystPipeline
import mlflow

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def evaluate():
    """
    Évalue le modèle entraîné sur le jeu de données de test.
    Génère des prédictions et les enregistre dans MLflow pour inspection.
    """
    # 1. Chargement de la configuration d'inférence
    config_path = Path("configs/inference_config.yaml")
    if not config_path.exists():
        logger.error(f"Fichier de configuration manquant : {config_path}")
        return

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 2. Chemin du dataset de test
    test_path = Path("data/splits/test.jsonl")
    if not test_path.exists():
        logger.error(f"Dataset de test manquant : {test_path}")
        return

    # 3. Initialisation du pipeline
    logger.info("Chargement du modèle pour évaluation...")
    pipeline = LeanStartupAnalystPipeline(
        model_id=config["model"]["base_model_id"],
        adapter_path=config["model"]["adapter_path"]
    )

    # 4. Configuration MLflow
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
    mlflow.set_experiment("LFM-Lean-Startup-Evaluation")

    results = []
    
    with mlflow.start_run(run_name="LFM-350M-Test-Sample"):
        logger.info("Début de la génération sur l'échantillon de test...")
        
        with open(test_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            # On évalue sur un petit échantillon pour gagner du temps
            sample = lines[:10]
            
            for i, line in enumerate(sample):
                data = json.loads(line)
                # Récupération du prompt utilisateur (dernier message 'user')
                user_msg = next(m["content"] for m in reversed(data["messages"]) if m["role"] == "user")
                expected = next(m["content"] for m in reversed(data["messages"]) if m["role"] == "assistant")
                
                logger.info(f"Test {i+1}/{len(sample)} en cours...")
                prediction = pipeline.run(user_msg)
                
                results.append({
                    "id": i,
                    "prompt": user_msg,
                    "expected": expected,
                    "prediction": prediction
                })

        # Sauvegarde et log des résultats
        output_file = "evaluation_report.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        mlflow.log_artifact(output_file)
        logger.info(f"Évaluation terminée. Résultats enregistrés dans MLflow sous : {output_file}")

if __name__ == "__main__":
    evaluate()
