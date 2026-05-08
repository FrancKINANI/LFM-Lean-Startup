from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
import os

default_args = {
    'owner': 'Justin',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'lfm_lean_startup_evaluation',
    default_args=default_args,
    description='Évaluation du modèle LFM sur le dataset de test via Pytest',
    schedule_interval=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=['nlp', 'evaluation', 'lean-startup'],
) as dag:

    PROJECT_DIR = os.environ.get('PROJECT_DIR', '/home/franck/Documents/01_Cours/Data/IA/Projets/efm/NLP/LFM-Lean-Startup-Project')
    
    # Exécution des tests Pytest qui contiennent l'évaluation d'inférence
    eval_command = f"cd {PROJECT_DIR} && source venv/bin/activate && pytest tests/ -v"

    evaluation_task = BashOperator(
        task_id='run_pytest_evaluation',
        bash_command=eval_command,
        executable='/bin/bash',
        env={
            **os.environ,
            'PYTHONPATH': f"{PROJECT_DIR}:{os.environ.get('PYTHONPATH', '')}",
        }
    )

    evaluation_task
