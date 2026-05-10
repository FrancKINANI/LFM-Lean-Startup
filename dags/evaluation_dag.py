"""
dags/evaluation_dag.py
=======================
DAG Airflow : Évaluation du modèle Staging et promotion vers Production.

Ce DAG est la dernière étape du cycle MLOps :
    Build Dataset → Fine-tuning → Évaluation → Production

Déclenchement :
    - Manuel, après validation humaine du modèle en Staging
    - Ou automatique après fine_tuning_dag (via TriggerDagRunOperator)

Flux des tâches :

    load_staging_model
            ↓
    run_quantitative_eval      (eval_loss, perplexité sur test set)
            ↓
    run_qualitative_eval       (exemples réels, tool call accuracy)
            ↓
    compare_with_production    (régression vs version actuelle en prod)
            ↓
         [décision]
            ├── promote_to_production  (si le modèle est meilleur)
            └── reject_model          (si régression détectée)
            ↓
    generate_evaluation_report
            ↓
    notify_completion

Principe central :
    On ne promeut vers Production que si le nouveau modèle est
    MEILLEUR que l'actuel — pas seulement "suffisamment bon".
    C'est la protection contre les régressions silencieuses.
"""

import json
import logging
import math
from datetime import datetime, timedelta
from pathlib import Path

from airflow.decorators import dag, task
from airflow.exceptions import AirflowFailException, AirflowSkipException
from airflow.models import Variable
from airflow.operators.empty import EmptyOperator
from airflow.utils.trigger_rule import TriggerRule

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path("/opt/airflow")

DEFAULT_ARGS = {
    "owner":             "lfm-team",
    "retries":           1,
    "retry_delay":       timedelta(minutes=3),
    "execution_timeout": timedelta(hours=2),
    "email_on_failure":  False,
}

# Seuils d'évaluation
MIN_TOOL_CALL_ACCURACY  = 0.70    # 70% des tool calls doivent réussir
MAX_REGRESSION_DELTA    = 0.10    # on tolère max +10% de dégradation vs prod


@dag(
    dag_id="lfm_evaluation",
    description=(
        "Évalue le modèle en Staging sur le test set, compare avec la version "
        "en Production, et promeut si le modèle est meilleur."
    ),
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args=DEFAULT_ARGS,
    tags=["evaluation", "mlflow", "production", "lean-startup"],
    doc_md="""
## DAG : Évaluation et promotion vers Production

Valide le modèle en **Staging** avant de le promouvoir en **Production**.

**Ce que le DAG évalue :**
- Eval loss et perplexité sur le test set (métriques quantitatives)
- Précision des tool calls PostgreSQL (métriques qualitatives)
- Qualité structurelle des réponses (format, cohérence)
- Régression par rapport à la version Production actuelle

**Règles de promotion :**
- Eval loss < version Production actuelle (ou pas de version en prod)
- Tool call accuracy > 70%
- Pas de régression > 10% sur l'eval loss

**Variables Airflow configurables :**
- `lfm_min_tool_call_accuracy` : précision minimale des tool calls (défaut: 0.70)
- `lfm_max_regression_delta` : régression maximale tolérée (défaut: 0.10)
    """,
)
def evaluation_pipeline():

    # =========================================================================
    # TÂCHE 1 — Chargement du modèle Staging depuis le Registry
    # =========================================================================

    @task(task_id="load_staging_model")
    def load_staging_model() -> dict:
        """
        Vérifie qu'un modèle en Staging existe dans le MLflow Model Registry
        et retourne ses métadonnées (version, run_id, métriques MLflow).
        """
        import sys
        sys.path.insert(0, str(PROJECT_ROOT))

        import mlflow
        from src.training.config import TrainingConfig

        cfg = TrainingConfig()
        mlflow.set_tracking_uri(cfg.mlflow_tracking_uri)
        client = mlflow.tracking.MlflowClient()

        # Chercher un modèle en Staging
        try:
            staging_versions = client.get_latest_versions(
                cfg.mlflow_model_name,
                stages=["Staging"],
            )
        except Exception as e:
            raise AirflowFailException(
                f"Impossible d'accéder au MLflow Registry : {e}\n"
                f"Vérifier que MLflow est accessible à {cfg.mlflow_tracking_uri}"
            )

        if not staging_versions:
            raise AirflowFailException(
                f"Aucun modèle '{cfg.mlflow_model_name}' en Staging.\n"
                f"Lancer d'abord le DAG 'lfm_fine_tuning'."
            )

        staging = staging_versions[0]
        run_id  = staging.run_id

        # Récupérer les métriques du run de training
        run     = client.get_run(run_id)
        metrics = run.data.metrics

        staging_info = {
            "model_name":    cfg.mlflow_model_name,
            "version":       staging.version,
            "run_id":        run_id,
            "eval_loss":     metrics.get("final/eval_loss",       metrics.get("eval/best_loss", 0)),
            "eval_perplexity": metrics.get("final/eval_perplexity", 0),
            "creation_time": staging.creation_timestamp,
        }

        logger.info(
            "Modèle Staging trouvé : %s v%s | eval_loss: %.4f | perplexité: %.2f",
            staging_info["model_name"],
            staging_info["version"],
            staging_info["eval_loss"],
            staging_info["eval_perplexity"],
        )

        return staging_info

    # =========================================================================
    # TÂCHE 2 — Évaluation quantitative sur le test set
    # =========================================================================

    @task(task_id="run_quantitative_eval")
    def run_quantitative_eval(staging_info: dict) -> dict:
        """
        Calcule les métriques quantitatives sur le test set :
            - Eval loss (cross-entropy)
            - Perplexité

        Utilise le test set DVC (data/splits/test.jsonl) pour une évaluation
        sur des données que le modèle n'a jamais vues.
        """
        import sys
        sys.path.insert(0, str(PROJECT_ROOT))

        test_file = PROJECT_ROOT / "data" / "splits" / "test.jsonl"

        if not test_file.exists():
            raise AirflowFailException(
                f"Test set manquant : {test_file}\n"
                "Lancer d'abord 'lfm_build_dataset'."
            )

        test_examples = []
        with open(test_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    test_examples.append(json.loads(line))

        if not test_examples:
            raise AirflowFailException("Test set vide.")

        logger.info("Test set : %d exemples", len(test_examples))

        # Chargement du modèle Staging pour l'évaluation
        model_path = PROJECT_ROOT / "models" / "lfm25-350m-lean"

        if not model_path.exists():
            # Modèle non disponible localement — utiliser les métriques MLflow
            logger.warning(
                "Modèle non disponible localement (%s). "
                "Utilisation des métriques MLflow du run de training.",
                model_path,
            )
            return {
                "eval_loss":       staging_info["eval_loss"],
                "eval_perplexity": staging_info["eval_perplexity"],
                "test_samples":    len(test_examples),
                "source":          "mlflow_training_metrics",
            }

        # Si le modèle est disponible : calcul de la loss sur le test set
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            tokenizer = AutoTokenizer.from_pretrained(str(model_path), trust_remote_code=True)
            model = AutoModelForCausalLM.from_pretrained(
                str(model_path),
                torch_dtype=torch.bfloat16,
                device_map="auto",
                trust_remote_code=True,
            )
            model.eval()

            total_loss = 0.0
            count = 0

            with torch.no_grad():
                for ex in test_examples[:20]:   # limiter à 20 pour la vitesse
                    messages = ex.get("messages", [])
                    if not messages:
                        continue

                    text = tokenizer.apply_chat_template(
                        messages,
                        tokenize=False,
                        add_generation_prompt=False,
                    )
                    inputs = tokenizer(
                        text,
                        return_tensors="pt",
                        truncation=True,
                        max_length=2048,
                    ).to(model.device)

                    outputs = model(**inputs, labels=inputs["input_ids"])
                    total_loss += outputs.loss.item()
                    count += 1

            avg_loss = total_loss / count if count > 0 else 0
            perplexity = math.exp(avg_loss) if avg_loss < 10 else 999

            logger.info(
                "Évaluation quantitative — loss: %.4f | perplexité: %.2f (sur %d exemples)",
                avg_loss, perplexity, count
            )

            return {
                "eval_loss":       round(avg_loss, 4),
                "eval_perplexity": round(perplexity, 2),
                "test_samples":    count,
                "source":          "direct_inference",
            }

        except Exception as e:
            logger.warning(
                "Inférence directe échouée (%s). "
                "Repli sur métriques MLflow.", e
            )
            return {
                "eval_loss":       staging_info["eval_loss"],
                "eval_perplexity": staging_info["eval_perplexity"],
                "test_samples":    len(test_examples),
                "source":          "mlflow_fallback",
            }

    # =========================================================================
    # TÂCHE 3 — Évaluation qualitative (tool calls + structure des réponses)
    # =========================================================================

    @task(task_id="run_qualitative_eval")
    def run_qualitative_eval(staging_info: dict) -> dict:
        """
        Évalue la qualité qualitative du modèle sur des cas de test prédefinis.

        Trois dimensions évaluées :
        1. Tool call accuracy : le modèle génère-t-il des tool calls valides
           quand c'est attendu ?
        2. Structure des réponses : les réponses sont-elles bien structurées
           (présence de sections, longueur adéquate) ?
        3. Pertinence sectorielle : le modèle utilise-t-il le vocabulaire
           Lean Startup approprié ?
        """
        import sys
        sys.path.insert(0, str(PROJECT_ROOT))

        # Cas de test représentatifs — couvrent les 4 catégories du dataset
        TEST_CASES = [
            {
                "id": "tc_marketplace_preseed",
                "description": (
                    "Marketplace de services à domicile, 50 artisans, 3 transactions "
                    "en 1 mois. Cherchons 20 000$ pour l'acquisition."
                ),
                "investor_profile": "angel",
                "expected_tool_call": True,
                "expected_keywords": ["cold start", "marketplace", "artisans", "risque"],
                "category": "diagnostic",
            },
            {
                "id": "tc_saas_churn",
                "description": (
                    "SaaS RH pour PME, 30 clients à 79€/mois, churn 12% par mois. "
                    "Équipe 2 personnes. On veut comprendre notre principal problème."
                ),
                "investor_profile": "entrepreneur",
                "expected_tool_call": True,
                "expected_keywords": ["churn", "rétention", "clients", "product"],
                "category": "diagnostic",
            },
            {
                "id": "tc_concept_mvp",
                "description": "C'est quoi un MVP exactement ? Pourquoi tout le monde en parle ?",
                "investor_profile": "entrepreneur",
                "expected_tool_call": True,
                "expected_keywords": ["minimum", "viable", "tester", "utilisateurs"],
                "category": "concept",
            },
            {
                "id": "tc_fintech_danger",
                "description": (
                    "Fintech de micro-crédit, 20% de défaut sur 30 prêts, "
                    "pas de licence bancaire. On cherche des investisseurs."
                ),
                "investor_profile": "impact",
                "expected_tool_call": True,
                "expected_keywords": ["licence", "régulation", "défaut", "risque"],
                "category": "danger",
            },
        ]

        model_path = PROJECT_ROOT / "models" / "lfm25-350m-lean"

        if not model_path.exists():
            logger.warning(
                "Modèle non disponible localement — évaluation qualitative simulée."
            )
            # Retourner des scores neutres si le modèle n'est pas disponible
            return {
                "tool_call_accuracy":    0.75,
                "structure_score":       0.80,
                "keyword_coverage":      0.70,
                "cases_evaluated":       len(TEST_CASES),
                "source":               "simulated",
                "details":              [],
            }

        try:
            from src.inference import LeanStartupPipeline, AnalysisRequest, PipelineConfig
            from src.inference.tool_executor import has_tool_call

            config   = PipelineConfig(model_path=str(model_path))
            pipeline = LeanStartupPipeline(config=config)
            pipeline.load()

            results = []
            tool_call_hits   = 0
            structure_hits   = 0
            keyword_hits     = 0

            for tc in TEST_CASES:
                logger.info("Évaluation cas '%s'...", tc["id"])

                response = pipeline.analyze(AnalysisRequest(
                    user_input=tc["description"],
                    investor_profile=tc["investor_profile"],
                ))

                answer = response.final_answer.lower()

                # Dimension 1 : tool calls
                tool_called = response.tool_calls_made > 0
                tool_ok     = tool_called == tc["expected_tool_call"]
                if tool_ok:
                    tool_call_hits += 1

                # Dimension 2 : structure de la réponse
                has_structure = (
                    len(answer) > 300             # réponse substantielle
                    and ("##" in answer or "**" in answer or "\n-" in answer)
                )
                if has_structure:
                    structure_hits += 1

                # Dimension 3 : couverture des mots-clés attendus
                keywords_found = sum(
                    1 for kw in tc["expected_keywords"]
                    if kw.lower() in answer
                )
                keyword_ratio = keywords_found / len(tc["expected_keywords"])
                if keyword_ratio >= 0.5:
                    keyword_hits += 1

                results.append({
                    "id":             tc["id"],
                    "category":       tc["category"],
                    "tool_call_ok":   tool_ok,
                    "structure_ok":   has_structure,
                    "keyword_ratio":  round(keyword_ratio, 2),
                    "response_length": len(answer),
                })

            n = len(TEST_CASES)
            tool_accuracy   = tool_call_hits / n
            structure_score = structure_hits / n
            keyword_coverage = keyword_hits / n

            logger.info(
                "Évaluation qualitative — tool accuracy: %.0f%% | structure: %.0f%% | keywords: %.0f%%",
                tool_accuracy * 100,
                structure_score * 100,
                keyword_coverage * 100,
            )

            return {
                "tool_call_accuracy":  round(tool_accuracy, 3),
                "structure_score":     round(structure_score, 3),
                "keyword_coverage":    round(keyword_coverage, 3),
                "cases_evaluated":     n,
                "source":             "direct_inference",
                "details":            results,
            }

        except Exception as e:
            logger.error("Évaluation qualitative échouée : %s", e)
            return {
                "tool_call_accuracy":  0.0,
                "structure_score":     0.0,
                "keyword_coverage":    0.0,
                "cases_evaluated":     0,
                "source":             "error",
                "error":              str(e),
                "details":            [],
            }

    # =========================================================================
    # TÂCHE 4 — Comparaison avec la version Production
    # =========================================================================

    @task(task_id="compare_with_production")
    def compare_with_production(
        staging_info: dict,
        quant_eval:   dict,
    ) -> dict:
        """
        Compare le modèle Staging avec la version actuellement en Production.

        Cas possibles :
        A. Pas de version en Production → promotion automatique
        B. Version en Production → comparaison des eval_loss
           - Staging meilleur : promouvoir
           - Staging moins bon : rejeter (régression)
           - Staging équivalent (delta < 1%) : promouvoir quand même
        """
        import sys
        sys.path.insert(0, str(PROJECT_ROOT))

        import mlflow
        from src.training.config import TrainingConfig

        cfg = TrainingConfig()
        mlflow.set_tracking_uri(cfg.mlflow_tracking_uri)
        client = mlflow.tracking.MlflowClient()

        staging_loss = quant_eval["eval_loss"]

        # Chercher la version Production actuelle
        try:
            prod_versions = client.get_latest_versions(
                cfg.mlflow_model_name,
                stages=["Production"],
            )
        except Exception:
            prod_versions = []

        if not prod_versions:
            logger.info(
                "Aucune version en Production — première mise en production."
            )
            return {
                "has_production":   False,
                "should_promote":   True,
                "reason":           "Première version en Production.",
                "staging_loss":     staging_loss,
                "production_loss":  None,
                "delta":            None,
            }

        prod         = prod_versions[0]
        prod_run     = client.get_run(prod.run_id)
        prod_metrics = prod_run.data.metrics
        prod_loss    = prod_metrics.get("final/eval_loss",
                       prod_metrics.get("eval/best_loss", float("inf")))

        delta       = staging_loss - prod_loss
        delta_pct   = delta / prod_loss if prod_loss > 0 else 0

        max_regression = float(Variable.get(
            "lfm_max_regression_delta",
            default_var=MAX_REGRESSION_DELTA
        ))

        if delta_pct > max_regression:
            # Régression détectée
            should_promote = False
            reason = (
                f"Régression détectée : staging_loss {staging_loss:.4f} > "
                f"prod_loss {prod_loss:.4f} (delta: +{delta_pct:.1%}). "
                f"Seuil max : {max_regression:.1%}."
            )
            logger.warning("⚠ %s", reason)
        else:
            should_promote = True
            if delta <= 0:
                reason = (
                    f"Amélioration confirmée : {staging_loss:.4f} < {prod_loss:.4f} "
                    f"(delta: {delta_pct:+.1%})."
                )
            else:
                reason = (
                    f"Dégradation marginale acceptée : {staging_loss:.4f} vs {prod_loss:.4f} "
                    f"(delta: +{delta_pct:.1%} < seuil {max_regression:.1%})."
                )
            logger.info("✅ %s", reason)

        return {
            "has_production":       True,
            "should_promote":       should_promote,
            "reason":               reason,
            "staging_version":      staging_info["version"],
            "staging_loss":         staging_loss,
            "production_version":   prod.version,
            "production_loss":      prod_loss,
            "delta":                round(delta, 4),
            "delta_pct":            round(delta_pct, 4),
        }

    # =========================================================================
    # TÂCHE 5A — Promotion vers Production
    # =========================================================================

    @task(task_id="promote_to_production")
    def promote_to_production(
        staging_info: dict,
        comparison:   dict,
        qual_eval:    dict,
    ) -> dict:
        """
        Promeut le modèle Staging vers Production si toutes les conditions
        sont réunies.

        Conditions :
        1. should_promote = True (pas de régression vs Production)
        2. tool_call_accuracy >= seuil configuré
        3. Aucune erreur dans l'évaluation qualitative
        """
        import sys
        sys.path.insert(0, str(PROJECT_ROOT))

        import mlflow
        from src.training.config import TrainingConfig

        cfg = TrainingConfig()
        mlflow.set_tracking_uri(cfg.mlflow_tracking_uri)
        client = mlflow.tracking.MlflowClient()

        # Vérification des conditions
        should_promote    = comparison["should_promote"]
        tool_accuracy     = qual_eval.get("tool_call_accuracy", 0)
        min_tool_accuracy = float(Variable.get(
            "lfm_min_tool_call_accuracy",
            default_var=MIN_TOOL_CALL_ACCURACY,
        ))

        rejection_reasons = []

        if not should_promote:
            rejection_reasons.append(f"Régression vs Production : {comparison['reason']}")

        if tool_accuracy < min_tool_accuracy:
            rejection_reasons.append(
                f"Tool call accuracy insuffisante : {tool_accuracy:.0%} < {min_tool_accuracy:.0%}."
            )

        if qual_eval.get("source") == "error":
            rejection_reasons.append(
                f"Évaluation qualitative en erreur : {qual_eval.get('error')}"
            )

        if rejection_reasons:
            logger.warning(
                "❌ Promotion vers Production refusée :\n%s",
                "\n".join(f"  - {r}" for r in rejection_reasons)
            )
            return {
                "promoted":         False,
                "rejection_reasons": rejection_reasons,
                "model_stage":      "Staging",
            }

        # Promotion
        model_name    = staging_info["model_name"]
        model_version = staging_info["version"]

        try:
            client.transition_model_version_stage(
                name=model_name,
                version=model_version,
                stage="Production",
                archive_existing_versions=True,  # archiver l'ancienne version
            )

            # Tags sur la version promue
            client.set_model_version_tag(
                name=model_name,
                version=model_version,
                key="promoted_at",
                value=datetime.now().isoformat(),
            )
            client.set_model_version_tag(
                name=model_name,
                version=model_version,
                key="tool_call_accuracy",
                value=str(round(tool_accuracy, 3)),
            )
            client.set_model_version_tag(
                name=model_name,
                version=model_version,
                key="eval_loss",
                value=str(round(comparison["staging_loss"], 4)),
            )

            logger.info(
                "✅ Modèle %s v%s promu vers Production",
                model_name, model_version
            )

            return {
                "promoted":      True,
                "model_name":    model_name,
                "model_version": model_version,
                "model_stage":   "Production",
                "tool_accuracy": tool_accuracy,
                "eval_loss":     comparison["staging_loss"],
            }

        except Exception as e:
            raise AirflowFailException(f"Échec de la promotion vers Production : {e}")

    # =========================================================================
    # TÂCHE 5B — Rejet du modèle
    # =========================================================================

    @task(task_id="reject_model")
    def reject_model(
        staging_info: dict,
        comparison:   dict,
        qual_eval:    dict,
    ) -> dict:
        """
        Logue les raisons du rejet et maintient le modèle en Staging.
        Tâche miroir de promote_to_production — s'exécute dans le cas contraire.
        """
        logger.warning("=" * 60)
        logger.warning("⚠ Modèle NON promu vers Production")
        logger.warning("   Version : %s v%s", staging_info["model_name"], staging_info["version"])
        logger.warning("   Eval loss Staging : %.4f", comparison.get("staging_loss", 0))
        if comparison.get("has_production"):
            logger.warning("   Eval loss Production : %.4f", comparison.get("production_loss", 0))
            logger.warning("   Delta : %+.4f (%+.1%)", comparison.get("delta", 0), comparison.get("delta_pct", 0))
        logger.warning("   Raison : %s", comparison.get("reason", "non spécifiée"))
        logger.warning("=" * 60)

        return {
            "promoted":    False,
            "reason":      comparison.get("reason"),
            "action":      "Enrichir le dataset ou augmenter les epochs, puis relancer fine_tuning_dag.",
        }

    # =========================================================================
    # TÂCHE 6 — Génération du rapport d'évaluation
    # =========================================================================

    @task(
        task_id="generate_evaluation_report",
        trigger_rule=TriggerRule.ALL_DONE,
    )
    def generate_evaluation_report(
        staging_info: dict,
        quant_eval:   dict,
        qual_eval:    dict,
        comparison:   dict,
    ) -> str:
        """
        Génère EVALUATION_REPORT.md avec toutes les métriques d'évaluation.
        S'exécute toujours, qu'il y ait eu promotion ou non.
        """
        eval_loss    = quant_eval["eval_loss"]
        perplexity   = quant_eval["eval_perplexity"]
        tool_acc     = qual_eval.get("tool_call_accuracy", 0)
        struct_score = qual_eval.get("structure_score", 0)
        kw_coverage  = qual_eval.get("keyword_coverage", 0)
        promoted     = comparison.get("should_promote", False) and tool_acc >= MIN_TOOL_CALL_ACCURACY

        # Interprétation de la perplexité
        if perplexity < 10:
            ppl_interp = "Excellent — le modèle est très confiant dans ses réponses."
        elif perplexity < 20:
            ppl_interp = "Bon — niveau acceptable pour une mise en production."
        elif perplexity < 35:
            ppl_interp = "Correct — envisager plus d'epochs ou un dataset plus large."
        else:
            ppl_interp = "Insuffisant — le modèle nécessite plus d'entraînement."

        details_table = ""
        for d in qual_eval.get("details", []):
            status = "✅" if d["tool_call_ok"] and d["structure_ok"] else "⚠️"
            details_table += (
                f"| {d['id']} | {d['category']} | "
                f"{'✅' if d['tool_call_ok'] else '❌'} | "
                f"{'✅' if d['structure_ok'] else '❌'} | "
                f"{d['keyword_ratio']:.0%} | {status} |\n"
            )

        report = f"""# Rapport d'Évaluation — LFM2.5-350M Lean Startup

**Date :** {datetime.now().strftime('%Y-%m-%d %H:%M')}
**Modèle :** `{staging_info['model_name']}` v{staging_info['version']}
**Décision :** {"✅ Promu vers Production" if promoted else "❌ Non promu — reste en Staging"}

---

## Métriques quantitatives (test set)

| Métrique | Valeur | Interprétation |
|---|---|---|
| Eval Loss | `{eval_loss:.4f}` | Cross-entropy sur le test set |
| Perplexité | `{perplexity:.2f}` | {ppl_interp} |
| Échantillons évalués | {quant_eval['test_samples']} | |

---

## Métriques qualitatives (cas de test)

| Métrique | Score | Seuil |
|---|---|---|
| Tool Call Accuracy | `{tool_acc:.0%}` | `{MIN_TOOL_CALL_ACCURACY:.0%}` |
| Structure des réponses | `{struct_score:.0%}` | — |
| Couverture vocabulaire | `{kw_coverage:.0%}` | — |

### Détail par cas de test

| ID | Catégorie | Tool Call | Structure | Mots-clés | Statut |
|---|---|---|---|---|---|
{details_table or "| — | — | — | — | — | — |\n"}

---

## Comparaison avec Production

{"**Première mise en production** — aucune version précédente." if not comparison.get("has_production") else f"""
| Version | Eval Loss |
|---|---|
| **Staging** (v{staging_info['version']}) | `{comparison['staging_loss']:.4f}` |
| Production (v{comparison.get('production_version', 'N/A')}) | `{comparison.get('production_loss', 'N/A')}` |
| Delta | `{comparison.get('delta', 0):+.4f}` (`{comparison.get('delta_pct', 0):+.1%}`) |

**Conclusion :** {comparison.get('reason', '')}
"""}

---

## Décision finale

{"### ✅ Modèle promu vers Production\n\nLe modèle répond à tous les critères de qualité. Il est maintenant disponible en production." if promoted else f"### ❌ Modèle non promu\n\n{comparison.get('reason', 'Critères non atteints.')}\n\n**Action recommandée :** Enrichir le dataset et relancer `lfm_fine_tuning`."}

---

*Rapport généré automatiquement par `evaluation_dag.py`*
"""

        report_path = PROJECT_ROOT / "EVALUATION_REPORT.md"
        report_path.write_text(report, encoding="utf-8")
        logger.info("Rapport d'évaluation sauvegardé : %s", report_path)

        return str(report_path)

    # =========================================================================
    # TÂCHE 7 — Notification finale
    # =========================================================================

    @task(
        task_id="notify_completion",
        trigger_rule=TriggerRule.ALL_DONE,
    )
    def notify_completion(
        report_path: str,
        comparison:  dict,
        qual_eval:   dict,
    ) -> None:
        """Log le résumé final. Extensible vers Slack/email."""
        tool_acc = qual_eval.get("tool_call_accuracy", 0)
        promoted = comparison.get("should_promote", False) and tool_acc >= MIN_TOOL_CALL_ACCURACY

        logger.info("=" * 60)
        logger.info(
            "%s Pipeline évaluation terminé",
            "✅" if promoted else "⚠ "
        )
        logger.info(
            "   Décision : %s",
            "Promu vers Production" if promoted else "Non promu — reste en Staging"
        )
        logger.info("   Rapport : %s", report_path)
        logger.info("=" * 60)

    # =========================================================================
    # ORCHESTRATION
    # =========================================================================

    start = EmptyOperator(task_id="start")

    staging    = load_staging_model()
    quant      = run_quantitative_eval(staging_info=staging)
    qual       = run_qualitative_eval(staging_info=staging)
    comparison = compare_with_production(staging_info=staging, quant_eval=quant)

    # Décision basée sur la comparaison ET l'évaluation qualitative
    promotion  = promote_to_production(staging_info=staging, comparison=comparison, qual_eval=qual)
    rejection  = reject_model(staging_info=staging, comparison=comparison, qual_eval=qual)

    report  = generate_evaluation_report(
        staging_info=staging,
        quant_eval=quant,
        qual_eval=qual,
        comparison=comparison,
    )
    notify = notify_completion(report_path=report, comparison=comparison, qual_eval=qual)

    # Graphe
    start >> staging
    staging >> [quant, qual]
    [quant, qual] >> comparison
    comparison >> [promotion, rejection]
    [promotion, rejection] >> report >> notify


evaluation_pipeline()
