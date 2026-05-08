# Analyste Lean Startup Augmenté (LFM-Lean-Startup)

Ce projet implémente un analyste intelligent spécialisé dans la méthodologie **Lean Startup**, basé sur le modèle **LiquidAI LFM2.5-350M**. Il combine le fine-tuning supervisé (SFT) avec l'utilisation d'outils (Tool Use) pour interroger des bases de connaissances expertes.

## 🎯 La Vision

L'objectif est de construire un analyste capable de rendre accessible ce que les whitepapers techniques rendent opaque. Il ne s'adresse pas aux investisseurs institutionnels, mais aux entrepreneurs et décideurs qui ont besoin de comprendre rapidement et clairement la viabilité d'un projet.

| ENTRÉE | SORTIE |
| :--- | :--- |
| **Informations sur une startup** | → **Évaluation de l'opportunité** d'investissement |
| (stade, marché, équipe, modèle, traction...) | → **Identification des dangers** critiques (explication simple) |

## 🏗️ Architecture : Les trois sources de compétence

Le modèle tire sa force de trois piliers complémentaires :

1.  **FINE-TUNING (Poids du modèle)** : Apprentissage du raisonnement spécifique au domaine Lean Startup (évaluation, simplification, identification des signaux faibles).
2.  **BASE POSTGRESQL (Tool Use)** : Accès à des données factuelles : cas réels, patterns de pivot, benchmarks sectoriels et indicateurs de risque connus.
3.  **PROMPT SYSTÈME (Inférence)** : Cadre opérationnel et contexte spécifique de la startup analysée.

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
-   **Fine-tuning :** Hugging Face `trl`, `peft` et `transformers` (LoRA).

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
    pip install -r requirements.txt
    ```
2.  **Initialisation des données :**
    ```bash
    dvc pull
    ```
3.  **Lancement des services (Postgres, MLflow, Airflow) :**
    ```bash
    docker-compose up -d
    ```
4.  **Peuplement de la base de données :**
    ```bash
    python src/database/seeds_runner.py # Si script disponible, ou via migrations
    ```

---
*Développé pour transformer la théorie du Lean Startup en outils d'aide à la décision actionnables.*
