"""
src/data/report_dataset_metrics.py
====================================
Étape 2 du pipeline DVC : analyse et validation du dataset généré.

Lit full_dataset.jsonl et produit DATASET_METRICS_REPORT.md.
Ce fichier est marqué cache: false dans dvc.yaml — il est
toujours recalculé pour refléter l'état réel du dataset.

Vérifie :
    - Volume et distribution par catégorie
    - Proportion tool use vs sans tool use
    - Longueur moyenne des conversations
    - Cohérence des métadonnées
    - Alertes si déséquilibres détectés

Appel via DVC :
    dvc repro report_metrics

Appel direct :
    python src/data/report_dataset_metrics.py
"""

import json
import logging
from collections import Counter, defaultdict
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

PROJECT_ROOT  = Path(__file__).resolve().parents[2]
INPUT_DATASET = PROJECT_ROOT / "data" / "source" / "full_dataset.jsonl"
OUTPUT_REPORT = PROJECT_ROOT / "src" / "data"/ "reports" / "DATASET_METRICS_REPORT.md"


# =============================================================================
# ANALYSE
# =============================================================================

def load_dataset(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset introuvable : {path}\n"
            f"Lancer d'abord : python src/data/build_lean_datasets.py"
        )
    examples = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if line:
                try:
                    examples.append(json.loads(line))
                except json.JSONDecodeError as e:
                    logger.warning("Ligne %d invalide : %s", i, e)
    return examples


def compute_metrics(examples: list[dict]) -> dict:
    """Calcule toutes les métriques d'analyse du dataset."""
    total = len(examples)
    if total == 0:
        return {"error": "Dataset vide"}

    # Distribution par catégorie
    categories = Counter(
        ex.get("metadata", {}).get("category", "unknown")
        for ex in examples
    )

    # Distribution par secteur
    sectors = Counter(
        ex.get("metadata", {}).get("sector", "unknown")
        for ex in examples
    )

    # Distribution par profil investisseur
    investor_profiles = Counter(
        ex.get("metadata", {}).get("investor_profile", "unknown")
        for ex in examples
    )

    # Proportion tool use
    tool_use_count = sum(
        1 for ex in examples
        if ex.get("metadata", {}).get("has_tool_use", False)
    )

    # Analyse des longueurs de conversation
    message_counts = []
    total_chars = []
    for ex in examples:
        msgs = ex.get("messages", [])
        message_counts.append(len(msgs))
        total_chars.append(sum(len(m.get("content", "")) for m in msgs))

    avg_messages = sum(message_counts) / total if total else 0
    avg_chars    = sum(total_chars) / total if total else 0
    min_chars    = min(total_chars) if total_chars else 0
    max_chars    = max(total_chars) if total_chars else 0

    # Validation des métadonnées
    missing_metadata = []
    required_fields = ["category", "has_tool_use"]
    for i, ex in enumerate(examples):
        meta = ex.get("metadata", {})
        for field in required_fields:
            if field not in meta:
                missing_metadata.append(f"Exemple {i+1} : champ '{field}' manquant")

    # Détection des déséquilibres
    warnings = []
    if total > 0:
        for cat, count in categories.items():
            ratio = count / total
            if ratio < 0.10:
                warnings.append(
                    f"Catégorie '{cat}' sous-représentée : {count}/{total} ({ratio:.0%})"
                )
            if ratio > 0.60:
                warnings.append(
                    f"Catégorie '{cat}' sur-représentée : {count}/{total} ({ratio:.0%})"
                )

        tool_ratio = tool_use_count / total
        if tool_ratio < 0.30:
            warnings.append(
                f"Trop peu d'exemples avec tool use : {tool_use_count}/{total} ({tool_ratio:.0%}). "
                f"Recommandé : > 30%."
            )
        if tool_ratio > 0.80:
            warnings.append(
                f"Trop d'exemples avec tool use : {tool_use_count}/{total} ({tool_ratio:.0%}). "
                f"Le modèle doit aussi apprendre à répondre sans outils."
            )

    return {
        "total": total,
        "categories": dict(categories),
        "sectors": dict(sectors),
        "investor_profiles": dict(investor_profiles),
        "tool_use_count": tool_use_count,
        "tool_use_ratio": tool_use_count / total if total else 0,
        "avg_messages_per_example": round(avg_messages, 1),
        "avg_chars_per_example": round(avg_chars),
        "min_chars": min_chars,
        "max_chars": max_chars,
        "missing_metadata": missing_metadata,
        "warnings": warnings,
    }


# =============================================================================
# RAPPORT
# =============================================================================

def render_report(metrics: dict, input_path: Path) -> str:
    """Génère le rapport Markdown."""

    def bar(count: int, total: int, width: int = 20) -> str:
        filled = int(width * count / total) if total else 0
        return "█" * filled + "░" * (width - filled)

    total = metrics.get("total", 0)
    status = "✅ OK" if not metrics.get("warnings") else "⚠️ Attention"

    lines = [
        "# Dataset Metrics Report — LFM Lean Startup",
        "",
        f"**Source :** `{input_path}`  ",
        f"**Statut :** {status}  ",
        "",
        "---",
        "",
        "## Vue d'ensemble",
        "",
        f"| Métrique | Valeur |",
        f"|---|---|",
        f"| Total exemples | **{total}** |",
        f"| Avec tool use | {metrics['tool_use_count']} ({metrics['tool_use_ratio']:.0%}) |",
        f"| Messages moyens / exemple | {metrics['avg_messages_per_example']} |",
        f"| Caractères moyens / exemple | {metrics['avg_chars_per_example']:,} |",
        f"| Min / Max caractères | {metrics['min_chars']:,} / {metrics['max_chars']:,} |",
        "",
        "---",
        "",
        "## Distribution par catégorie",
        "",
    ]

    for cat, count in sorted(metrics["categories"].items(), key=lambda x: -x[1]):
        pct = count / total if total else 0
        lines.append(f"- **{cat}** : {count} exemples ({pct:.0%}) `{bar(count, total)}`")

    lines += [
        "",
        "## Distribution par secteur",
        "",
    ]

    for sector, count in sorted(metrics["sectors"].items(), key=lambda x: -x[1]):
        pct = count / total if total else 0
        lines.append(f"- **{sector}** : {count} ({pct:.0%})")

    lines += [
        "",
        "## Distribution par profil investisseur",
        "",
    ]

    for profile, count in sorted(metrics["investor_profiles"].items(), key=lambda x: -x[1]):
        pct = count / total if total else 0
        lines.append(f"- **{profile}** : {count} ({pct:.0%})")

    # Avertissements
    if metrics.get("warnings"):
        lines += ["", "---", "", "## ⚠️ Avertissements", ""]
        for w in metrics["warnings"]:
            lines.append(f"- {w}")

    # Métadonnées manquantes
    if metrics.get("missing_metadata"):
        lines += ["", "## ❌ Métadonnées manquantes", ""]
        for m in metrics["missing_metadata"][:10]:
            lines.append(f"- {m}")
        if len(metrics["missing_metadata"]) > 10:
            lines.append(f"- ... et {len(metrics['missing_metadata']) - 10} autres")

    # Recommandations
    lines += ["", "---", "", "## Recommandations", ""]

    if total < 200:
        lines.append(
            f"- **Volume faible ({total} exemples)** : viser 500-1000 exemples "
            f"pour un fine-tuning robuste. Enrichir les générateurs dans "
            f"`build_lean_datasets.py`."
        )

    for cat in ["diagnostic_complet", "identification_des_dangers",
                "evaluation_investissement", "simplification_concept"]:
        count = metrics["categories"].get(cat, 0)
        if count < 10:
            lines.append(
                f"- **Catégorie '{cat}'** insuffisante ({count} exemples). "
                f"Ajouter des exemples dans le générateur correspondant."
            )

    if not metrics.get("warnings") and total >= 100:
        lines.append("- Dataset équilibré et prêt pour le fine-tuning. ✅")

    lines += ["", "---", "", f"*Rapport généré par `report_dataset_metrics.py`*"]

    return "\n".join(lines)


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================

def main() -> None:
    logger.info("=" * 60)
    logger.info("LFM Lean Startup — Métriques du dataset")
    logger.info("=" * 60)

    logger.info("\n[1/3] Chargement du dataset : %s", INPUT_DATASET)
    examples = load_dataset(INPUT_DATASET)
    logger.info("  %d exemples chargés", len(examples))

    logger.info("\n[2/3] Calcul des métriques...")
    metrics = compute_metrics(examples)

    logger.info("\n[3/3] Génération du rapport : %s", OUTPUT_REPORT)
    report = render_report(metrics, INPUT_DATASET)

    OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_REPORT.write_text(report, encoding="utf-8")

    # Affichage résumé dans les logs
    logger.info("\nRésumé :")
    logger.info("  Total exemples   : %d", metrics["total"])
    logger.info("  Avec tool use    : %d (%.0f%%)",
                metrics["tool_use_count"], metrics["tool_use_ratio"] * 100)
    logger.info("  Chars moyens     : %d", metrics["avg_chars_per_example"])

    if metrics.get("warnings"):
        logger.warning("\n%d avertissement(s) :", len(metrics["warnings"]))
        for w in metrics["warnings"]:
            logger.warning("  ⚠ %s", w)
    else:
        logger.info("\n✅ Aucun avertissement — dataset équilibré")

    logger.info("\nRapport sauvegardé : %s", OUTPUT_REPORT)


if __name__ == "__main__":
    main()
