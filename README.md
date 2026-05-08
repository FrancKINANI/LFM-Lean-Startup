# Analyste Lean Startup Augmenté (LFM-Lean-Startup)

Ce projet implémente un analyste intelligent spécialisé dans la méthodologie **Lean Startup**, basé sur le modèle **LiquidAI LFM2.5-350M**. Il combine le fine-tuning supervisé (SFT) avec l'utilisation d'outils (Tool Use) pour interroger des bases de connaissances expertes.

## 🎯 La Vision

L'objectif est de construire un analyste capable de rendre accessible ce que les whitepapers techniques rendent opaque. Il ne s'adresse pas aux investisseurs institutionnels, mais aux entrepreneurs et décideurs qui ont besoin de comprendre rapidement et clairement la viabilité d'un projet.

| ENTRÉE | SORTIE |
| :--- | :--- |
| **Informations sur une startup** | → **Évaluation de l'opportunité** d'investissement |
| (stade, marché, équipe, modèle, traction...) | → **Identification des dangers** critiques (explication simple) |

## 🏗️ Architecture Hybride : Local + Remote (Colab)

Le projet est conçu pour fonctionner de manière hybride afin de pallier les limitations matérielles locales :

1.  **ORCHESTRATION LOCALE (PC)** :
    *   **Airflow & DVC** : Gestion du pipeline et versionnage des données.
    *   **PostgreSQL** : Base de connaissances experte.
    *   **MLflow** : Serveur de tracking centralisé pour les métriques.
    *   **FastAPI** : Couche API pour l'interface utilisateur.

2.  **EXÉCUTION DISTANTE (Google Colab / SSH)** :
    *   **Fine-Tuning (SFT)** : Entraînement LoRA utilisant les GPUs T4/A100 de Colab.
    *   **Inférence & Évaluation** : Test du modèle et génération de réponses complexes.
    *   **Synchronisation** : Les poids du modèle et les logs MLflow sont renvoyés vers les serveurs locaux ou distants via SSH.


## 📊 Structure du Dataset de Fine-tuning

Le dataset est stocké au format **ChatML** (compatible LFM2.5) dans `data/source/full_dataset.jsonl`.

### Les 4 catégories d'exemples
-   **Diagnostic complet (35%)** : Analyse structurée globale (forces, faiblesses, dangers).
-   **Identification des dangers (25%)** : Liste des risques expliqués simplement et classés par criticité.
-   **Évaluation d'investissement (25%)** : Recommandation go/no-go argumentée selon le profil investisseur.
-   **Simplification de concept (15%)** : Vulgarisation de concepts techniques Lean Startup sans jargon.

### Exemple de Tool Use (Interrogation SQL)
```json
{
  "messages": [
    {
      "role": "system",
      "content": "Tu es un analyste Lean Startup expert... List of tools: [query_postgresql]"
    },
    {
      "role": "user",
      "content": "Startup de mise en relation artisans en Afrique. 120 inscrits, 8 transactions..."
    },
    {
      "role": "assistant",
      "content": "<|tool_call_start|>[query_postgresql(sql=\"SELECT ... FROM risk_patterns WHERE sector = 'marketplace'...\")]<|tool_call_end|>"
    },
    {
      "role": "tool",
      "content": "[{\"pattern_name\": \"Cold start problem\", \"criticality\": \"critical\"...}]"
    },
    {
      "role": "assistant",
      "content": "## Analyse... Signal d'alarme : le ratio offre/demande..."
    }
  ]
}
```

## 🛠️ Stack Technique

-   **Modèle :** [LiquidAI LFM2.5-350M](https://liquid.ai/) (Architecture non-transformer ultra-performante).
-   **Base de données :** PostgreSQL (Vecteur de connaissances et patterns).
-   **Gestion de données :** DVC (Data Version Control).
-   **Orchestration :** Apache Airflow (DAGs de build, training et eval).
-   **Suivi :** MLflow (Tracking des expériences et registre de modèles).
-   **Fine-tuning & Inférence (Remote) :** Hugging Face `trl`, `peft` et `transformers` (LoRA).
-   **Connectivité :** SSH Tunneling (Colab ↔ Local).

## 📁 Structure du Projet

```text
├── configs/            # Configurations d'entraînement et d'inférence
├── dags/               # Pipelines Airflow (build_dataset, fine_tuning, evaluation)
├── data/               # Données (liquid, source, splits) - Géré par DVC
├── database/           # Schéma SQL, migrations et seeds (patterns de risque, etc.)
├── mlflow_configs/     # Configurations du serveur MLflow
├── notebooks/          # Exploration et prototypes (fine-tuning, inférence)
├── src/                # Code source (api, data, database, inference)
├── tests/              # Tests unitaires et d'intégration
├── docker-compose.yml  # Services (Airflow, Postgres, MLflow)
├── requirements.txt    # Dépendances Python
└── dvc.yaml            # Définition des étapes du pipeline DVC
```

## 🚀 Installation & Démarrage

1.  **Installation des dépendances :**
    ```bash
    source venv/bin/activate
    pip install -r requirements.txt
    ```

2.  **Lancement des services (Postgres, MLflow, Airflow) :**
    ```bash
    docker-compose up -d
    ```

## ☁️ Configuration Google Colab (Remote)

Pour préparer votre environnement Colab avant l'entraînement ou l'inférence :

1.  **Connexion SSH** (ou ouverture d'un Notebook).
2.  **Exécution du script de setup** :
    ```bash
    !bash scripts/setup_colab.sh
    ```
    *Ce script installera `torch`, `transformers`, `peft` et toutes les dépendances nécessaires au GPU.*

3.  **Peuplement de la base de données & Data :**
    ```bash
    # Initialisation de la DB (schémas et seeds)
    python src/database/seeds_runner.py
    
    # Récupération des données versionnées
    dvc pull
    ```

## 🔄 Cycle de Vie MLOps (Pipeline DVC)

Le projet utilise **DVC** pour orchestrer tout le pipeline. Pour reproduire l'intégralité du cycle (génération → metrics → training → evaluation) :

```bash
dvc repro
```

### Détail des étapes :
*   `build_datasets` (Local) : Génère 4000 exemples synthétiques au format ChatML.
*   `report_metrics` (Local) : Analyse la distribution et la qualité du dataset.
*   `train_model` (Colab) : Lance le fine-tuning LoRA sur le modèle Liquid LFM via SSH.
*   `evaluate_model` (Colab) : Évalue le modèle et logue les résultats dans le MLflow local via tunnel SSH.

## 🌐 Utilisation de l'API (FastAPI)

Pour exposer l'analyste en tant que service :

```bash
# Démarrage du serveur
python src/api/main.py
```

**Endpoint principal :** `POST /analyze`
```json
{
  "query": "Analyse le risque d'une marketplace de services B2B avec 5% de rétention."
}
```

## 🧪 Tests & Qualité

La robustesse du code et du parsing des outils est assurée par `pytest` :

```bash
PYTHONPATH=. pytest tests/ -v
```

## 📈 Monitoring (MLflow)

Toutes les expériences, métriques d'entraînement et rapports d'évaluation sont accessibles sur l'interface MLflow :
*   **URL :** `http://localhost:5000`
*   **Expériences :** `LFM-Lean-Startup-SFT` et `LFM-Lean-Startup-Evaluation`.

---
*Développé pour transformer la théorie du Lean Startup en outils d'aide à la décision actionnables.*
