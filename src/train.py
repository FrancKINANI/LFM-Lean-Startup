import mlflow
import mlflow.pytorch

# Initialisation MLflow
mlflow.set_experiment("LFM_Lean_Startup_Analysis")

with mlflow.start_run():
    # Log des paramètres LoRA
    mlflow.log_param("model_name", "LFM2.5-350M-Base")
    mlflow.log_param("lora_rank", 16)
    mlflow.log_param("dataset_size", 8860) # Volume du full_dataset[cite: 1]

    # ... Ton code de fine-tuning ...

    # Log de la perte (Loss) à chaque époque
    for epoch in range(epochs):
        mlflow.log_metric("train_loss", loss, step=epoch)
        
    # Log du modèle final
    mlflow.pytorch.log_model(model, "liquid_model_v1")