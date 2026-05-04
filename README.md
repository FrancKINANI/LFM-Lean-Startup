# LFM-Lean-Startup: Fine-tuning LiquidAI LFM2.5-350M

Ce projet implémente un pipeline complet de fine-tuning supervisé (SFT) pour le modèle **LiquidAI LFM2.5-350M-Base**, optimisé pour des cas d'usage de type "Lean Startup". Il utilise une architecture moderne combinant la gestion de données versionnée, l'orchestration de workflows et le suivi d'expériences.

## 🚀 Vue d'ensemble

L'objectif est d'adapter le modèle de base `LFM2.5-350M` via une stratégie **LoRA + TRL** pour répondre à des instructions spécifiques. Le projet est structuré pour être industrialisable (MLOps ready).

### Stack Technique
- **Modèle :** LiquidAI LFM2.5-350M-Base (architecture non-transformer performante).
- **Gestion de données :** [DVC](https://dvc.org/) (Data Version Control).
- **Suivi d'expériences :** [MLflow](https://mlflow.org/) (Metrics, Params, Models).
- **Orchestration :** [Apache Airflow](https://airflow.apache.org/) (Pipelines d'entraînement et d'évaluation).
- **Framework de Fine-tuning :** Hugging Face `trl`, `peft` et `transformers`.

## 📁 Structure du Projet

```text
├── dags/               # Pipelines d'orchestration Airflow
├── data/               # Données (versionnées par DVC, ignorées par Git)
├── notebooks/          # Exploration et prototypes de fine-tuning
├── src/                # Code source modulaire (entraînement, preprocessing)
├── mlflow_configs/     # Configurations pour le serveur MLflow
├── data.dvc            # Pointeur DVC pour les données
└── dvc.yaml            # Définition des étapes du pipeline DVC
```

## 🛠️ Installation

1. **Cloner le projet :**
   ```bash
   git clone https://github.com/FrancKINANI/LFM-Lean-Startup.git
   cd LFM-Lean-Startup
   ```

2. **Environnement virtuel :**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   pip install -r requirements.txt
   ```

3. **Récupérer les données (DVC) :**
   *(Note : Pour l'instant configuré en local)*
   ```bash
   dvc pull
   ```

## 🔄 Workflow MLOps

### 1. Gestion des Données (DVC)
Le dossier `data/` est géré par DVC. Pour ajouter de nouvelles données :
```bash
dvc add data/
git add data.dvc .gitignore
git commit -m "Update dataset"
```

### 2. Expérimentation (MLflow)
Toutes les sessions de fine-tuning loguent automatiquement :
- Les hyperparamètres (learning rate, rank LoRA, etc.)
- Les courbes de perte (loss) et les métriques d'évaluation.
- Les artefacts du modèle final.

### 3. Orchestration (Airflow)
Les DAGs dans `/dags` permettent d'automatiser :
- Le prétraitement des fichiers `.jsonl`.
- Le déclenchement de l'entraînement.
- L'évaluation comparative sur le dataset `liquid_hard_eval.jsonl`.

## 📝 Fine-tuning
Le processus principal suit la stratégie `LoRA` recommandée par LiquidAI pour le modèle 350M, permettant un entraînement efficace même sur des ressources GPU limitées.

---
*Développé dans le cadre du projet LFM-Lean-Startup.*
