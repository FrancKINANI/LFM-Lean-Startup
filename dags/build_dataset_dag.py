from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
import os

# Configuration par défaut pour les tâches
default_args = {
    'owner': 'franck',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Définition du DAG de build du dataset
with DAG(
    'lfm_lean_startup_build_dataset',
    default_args=default_args,
    description='Exécution du pipeline DVC pour la construction des datasets Lean Startup',
    schedule_interval=None, # Manuel par défaut
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=['nlp', 'dvc', 'lean-startup'],
) as dag:

    # Chemin absolu du projet (détecté dynamiquement si possible, sinon fixe)
    PROJECT_DIR = os.environ.get('PROJECT_DIR', '/home/franck/Documents/01_Cours/Data/IA/Projets/efm/NLP/LFM-Lean-Startup-Project')
    
    # Commande pour activer l'environnement virtuel et lancer DVC repro
    # On force l'utilisation de bash pour le sourcing
    repro_command = f"cd {PROJECT_DIR} && source venv/bin/activate && dvc repro"

    reproduce_pipeline = BashOperator(
        task_id='reproduce_dvc_pipeline',
        bash_command=repro_command,
        executable='/bin/bash', # Indispensable pour le 'source'
    )

    reproduce_pipeline
