from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
import os

# Configuration par défaut
default_args = {
    'owner': 'Justin',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0, # L'entraînement est coûteux, on évite les reprises automatiques sans analyse
}

# Définition du DAG de fine-tuning
with DAG(
    'lfm_lean_startup_fine_tuning',
    default_args=default_args,
    description='Lancement du fine-tuning LoRA pour l\'analyste Lean Startup',
    schedule_interval=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=['nlp', 'fine-tuning', 'mlflow', 'lean-startup'],
) as dag:

    # Récupération du dossier du projet
    PROJECT_DIR = os.environ.get('PROJECT_DIR', '/home/franck/Documents/01_Cours/Data/IA/Projets/efm/NLP/LFM-Lean-Startup-Project')
    
    # Commande pour lancer l'entraînement via le script Python dédié
    train_command = f"cd {PROJECT_DIR} && source venv/bin/activate && python src/inference/train.py"

    training_task = BashOperator(
        task_id='execute_lora_training',
        bash_command=train_command,
        executable='/bin/bash',
        # On définit des variables d'environnement utiles pour le script
        env={
            **os.environ,
            'PYTHONPATH': f"{PROJECT_DIR}:{os.environ.get('PYTHONPATH', '')}",
        }
    )

    training_task
