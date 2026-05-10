# LFM Lean Startup — Analyste IA pour Startups

Fine-tuning de **LFM2.5-350M** (LiquidAI) pour analyser des startups en langage naturel, identifier les risques critiques et évaluer les opportunités d'investissement — en rendant accessible ce que les whitepapers rendent opaque.

---

## Ce que fait ce projet

Un utilisateur décrit sa startup en texte libre. Le modèle :

1. **Identifie les risques critiques** (Cold Start Problem, churn élevé, unit economics négatifs...)
2. **Évalue l'opportunité d'investissement** selon le profil (angel, VC, impact, entrepreneur)
3. **Explique simplement** les concepts Lean Startup tirés de whitepapers techniques
4. **S'appuie sur des données réelles** via des tool calls PostgreSQL (benchmarks sectoriels, cas similaires, patterns de risque)

```
Utilisateur → texte libre
      ↓
LFM2.5-350M fine-tuné (LoRA-SFT)
      ↓
Tool call PostgreSQL (benchmarks, risques, cas similaires)
      ↓
Réponse claire, structurée, adaptée à l'interlocuteur
```

---

## Stack technique

| Couche | Technologie |
|---|---|
| Modèle de base | LiquidAI LFM2.5-350M-Base |
| Fine-tuning | LoRA + TRL SFTTrainer |
| Versioning données | DVC + Google Drive |
| Tracking expériences | MLflow |
| Orchestration | Apache Airflow |
| Base de données | PostgreSQL |
| API | FastAPI |
| Infrastructure locale | Docker Compose |

---

## Démarrage rapide

### Prérequis

- Python 3.11+
- Docker & Docker Compose
- GPU avec ≥ 16 Go VRAM (pour le fine-tuning)
- Compte Google Drive (pour le remote DVC)

### 1. Cloner et configurer l'environnement

```bash
git clone https://github.com/FrancKINANI/LFM-Lean-Startup.git
cd LFM-Lean-Startup

python -m venv .venv
source .venv/bin/activate        # Linux/Mac
# .venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

### 2. Configurer les variables d'environnement

```bash
cp .env.example .env
# Éditer .env avec vos valeurs (PostgreSQL, MLflow, etc.)
```

### 3. Lancer l'infrastructure locale

```bash
# PostgreSQL + MLflow + Airflow
docker-compose up -d postgres mlflow

# Initialiser Airflow (une seule fois)
docker-compose up airflow-init

# Lancer Airflow
docker-compose up -d airflow-webserver airflow-scheduler
```

Services disponibles :
- **Airflow UI** : http://localhost:8080 (admin/admin)
- **MLflow UI** : http://localhost:5000
- **PostgreSQL** : localhost:5433

### 4. Initialiser la base de données

```bash
# Le schéma et les seeds s'exécutent automatiquement au premier démarrage de PostgreSQL
# Vérifier :
psql -h localhost -U postgres -d lfm_lean_startup -c "\dt"
```

### 5. Configurer DVC avec Google Drive

```bash
dvc remote add -d gdrive gdrive://<VOTRE_FOLDER_ID>
dvc remote modify gdrive gdrive_use_service_account false
```

---

## Pipeline MLOps complet

Le pipeline est orchestré par trois DAGs Airflow, à exécuter dans l'ordre :

### DAG 1 — Construction du dataset

```
Airflow UI → DAGs → lfm_build_dataset → Trigger DAG
```

Ou en direct :
```bash
python src/data/build_lean_datasets.py
python src/data/report_dataset_metrics.py
```

Produit :
- `data/source/full_dataset.jsonl` — dataset canonique
- `data/splits/` — train / val / test
- `data/liquid/` — format TRL
- `DATASET_METRICS_REPORT.md` — rapport de qualité

### DAG 2 — Fine-tuning

```
Airflow UI → DAGs → lfm_fine_tuning → Trigger DAG
```

Ou en direct :
```bash
python src/training/trainer.py
```

Produit :
- `models/lfm25-350m-lean/` — modèle fine-tuné
- Run MLflow avec toutes les métriques et artefacts
- Modèle enregistré dans le Registry au stade **Staging**

### DAG 3 — Évaluation et promotion

```
Airflow UI → DAGs → lfm_evaluation → Trigger DAG
```

Évalue le modèle Staging et le promeut vers **Production** si :
- Pas de régression vs la version précédente (delta eval_loss < 10%)
- Tool call accuracy ≥ 70%

---

## Utilisation de l'API

### Démarrer l'API (après fine-tuning)

```bash
# Avec le modèle disponible
uvicorn src.api.main:app --host 0.0.0.0 --port 8000

# Documentation interactive
open http://localhost:8000/docs
```

### Analyser une startup

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Notre marketplace connecte 120 artisans à des particuliers en Afrique subsaharienne. 8 transactions en 2 mois. On cherche 50 000$.",
    "investor_profile": "angel"
  }'
```

### Consulter les risques d'un secteur

```bash
curl "http://localhost:8000/api/v1/risks?sector=marketplace&stage=pre-seed&criticality=critical"
```

### Évaluer une métrique

```bash
curl "http://localhost:8000/api/v1/evaluate?sector=saas&stage=seed&metric=churn_monthly&value=8.0"
```

---

## Structure du projet

```
LFM-Lean-Startup/
├── dags/                          # Airflow DAGs
│   ├── build_dataset_dag.py
│   ├── fine_tuning_dag.py
│   └── evaluation_dag.py
├── data/                          # Géré par DVC (ignoré par git)
│   ├── source/full_dataset.jsonl
│   ├── splits/
│   └── liquid/
├── database/
│   ├── schema.sql                 # Schéma PostgreSQL (6 tables)
│   └── seeds/                     # Données initiales
├── src/
│   ├── data/                      # Pipeline données (étapes DVC)
│   ├── database/                  # Couche PostgreSQL
│   ├── training/                  # Fine-tuning LoRA
│   ├── inference/                 # Pipeline d'inférence + tool use
│   └── api/                       # FastAPI
├── tests/                         # Tests unitaires
├── configs/                       # Configurations YAML
├── docker-compose.yml
├── dvc.yaml                       # Pipeline DVC
└── .env.example                   # Template variables d'environnement
```

---

## Tests

```bash
# Tous les tests (sans GPU ni base de données requise)
pytest tests/ -v

# Un fichier spécifique
pytest tests/test_data_pipeline.py -v
pytest tests/test_tool_executor.py -v
pytest tests/test_inference.py -v

# Avec couverture
pytest tests/ --cov=src --cov-report=term-missing
```

---

## Base de données PostgreSQL

Six tables organisées en deux groupes :

**Connaissance** (cas et patterns réels) :
- `startups` — cas documentés de startups
- `pivot_cases` — pivots avec contexte et résultats
- `risk_patterns` — patterns de risque par secteur et stade

**Référence** (calibrage et frameworks) :
- `sector_benchmarks` — métriques de référence sectorielles
- `lean_concepts` — concepts Lean Startup avec double explication
- `investment_criteria` — critères d'évaluation par profil investisseur

---

## MLflow — Suivi des expériences

```bash
# Accéder à l'UI
open http://localhost:5000

# Lister les runs via CLI
mlflow runs list --experiment-name "LFM-Lean-Startup-SFT"

# Promouvoir manuellement un modèle
python -c "
import mlflow
client = mlflow.tracking.MlflowClient('http://localhost:5000')
client.transition_model_version_stage('lfm25-lean-startup', '1', 'Production')
"
```

---

## Contribuer

1. Enrichir le dataset — ajouter des exemples dans `src/data/build_lean_datasets.py`
2. Enrichir les seeds — ajouter des risques, benchmarks ou cas dans `database/seeds/`
3. Lancer le DAG `lfm_build_dataset` pour valider
4. Lancer `pytest tests/` pour vérifier la non-régression

---

## Auteur

**Franc KINANI** — [GitHub](https://github.com/FrancKINANI)
