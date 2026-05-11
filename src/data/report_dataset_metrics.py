"""
src/data/report_dataset_metrics.py
====================================
Validate and document the generated Lean Startup SFT dataset.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from collections import Counter
from pathlib import Path


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_DATASET = PROJECT_ROOT / "data" / "source" / "full_dataset.jsonl"
OUTPUT_REPORT = PROJECT_ROOT / "src" / "data" / "reports" / "metrics_lean.md"

REQUIRED_METADATA = [
    "category",
    "Label",
    "Severity",
    "Difficulty",
    "has_tool_use",
    "lean_principle",
]
VALID_ROLES = {"system", "user", "assistant", "tool"}
VALID_LABELS = {"Green Flag", "Red Flag", "Mixed"}
VALID_SEVERITIES = {"Mineur", "Majeur", "Fatal", "Non applicable"}
VALID_DIFFICULTIES = {"Explicite", "Implicite", "Ambigu", "Mixte"}


def load_dataset(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset introuvable : {path}\n"
            "Lancer d'abord : python src/data/build_lean_datasets.py"
        )

    examples = []
    with path.open(encoding="utf-8") as file:
        for line_no, line in enumerate(file, 1):
            line = line.strip()
            if not line:
                continue
            try:
                examples.append(json.loads(line))
            except json.JSONDecodeError as exc:
                logger.warning("Ligne %d invalide : %s", line_no, exc)
    return examples


def _assistant_final(example: dict) -> str:
    for message in reversed(example.get("messages", [])):
        if message.get("role") == "assistant":
            return message.get("content", "")
    return ""


def _normalized_user_text(example: dict) -> str:
    user_text = " ".join(
        message.get("content", "")
        for message in example.get("messages", [])
        if message.get("role") == "user"
    )
    return re.sub(r"\s+", " ", user_text.lower()).strip()


def _hash_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def compute_metrics(examples: list[dict]) -> dict:
    total = len(examples)
    if total == 0:
        return {"error": "Dataset vide", "total": 0, "warnings": ["Dataset vide"]}

    categories = Counter()
    labels = Counter()
    severities = Counter()
    difficulties = Counter()
    sectors = Counter()
    profiles = Counter()
    principles = Counter()
    role_errors = []
    metadata_errors = []
    label_response_mismatches = []
    missing_tool_messages = []
    text_hashes = Counter()
    user_hashes = Counter()
    message_counts = []
    char_counts = []

    for index, example in enumerate(examples, 1):
        metadata = example.get("metadata", {})
        messages = example.get("messages", [])
        categories[metadata.get("category", "unknown")] += 1
        labels[metadata.get("Label", "unknown")] += 1
        severities[metadata.get("Severity", "unknown")] += 1
        difficulties[metadata.get("Difficulty", "unknown")] += 1
        sectors[metadata.get("sector", "unknown")] += 1
        profiles[metadata.get("investor_profile", "unknown")] += 1
        principles[metadata.get("lean_principle", "unknown")] += 1

        text_hashes[_hash_text(json.dumps(example, ensure_ascii=False, sort_keys=True))] += 1
        user_hashes[_hash_text(_normalized_user_text(example))] += 1
        message_counts.append(len(messages))
        char_counts.append(sum(len(message.get("content", "")) for message in messages))

        for field_name in REQUIRED_METADATA:
            if field_name not in metadata:
                metadata_errors.append(f"Exemple {index}: metadata.{field_name} manquant")

        if metadata.get("Label") not in VALID_LABELS:
            metadata_errors.append(f"Exemple {index}: Label invalide")
        if metadata.get("Severity") not in VALID_SEVERITIES:
            metadata_errors.append(f"Exemple {index}: Severity invalide")
        if metadata.get("Difficulty") not in VALID_DIFFICULTIES:
            metadata_errors.append(f"Exemple {index}: Difficulty invalide")

        roles = [message.get("role") for message in messages]
        if not messages or roles[0] != "system" or roles[-1] != "assistant":
            role_errors.append(f"Exemple {index}: séquence system/.../assistant invalide")
        if "user" not in roles:
            role_errors.append(f"Exemple {index}: aucun message user")
        invalid_roles = [role for role in roles if role not in VALID_ROLES]
        if invalid_roles:
            role_errors.append(f"Exemple {index}: rôles invalides {invalid_roles}")

        has_tool = bool(metadata.get("has_tool_use"))
        if has_tool and "tool" not in roles:
            missing_tool_messages.append(f"Exemple {index}: has_tool_use=True sans message tool")
        if not has_tool and "tool" in roles:
            missing_tool_messages.append(f"Exemple {index}: message tool mais has_tool_use=False")

        final_answer = _assistant_final(example)
        expected_label = metadata.get("Label")
        if expected_label and f"Label: {expected_label}" not in final_answer:
            label_response_mismatches.append(f"Exemple {index}: label metadata/réponse incohérent")

    tool_use_count = sum(1 for ex in examples if ex.get("metadata", {}).get("has_tool_use"))
    duplicate_full = sum(count - 1 for count in text_hashes.values() if count > 1)
    duplicate_user = sum(count - 1 for count in user_hashes.values() if count > 1)
    implicit_ratio = (
        (difficulties["Implicite"] + difficulties["Ambigu"] + difficulties["Mixte"]) / total
        if total
        else 0
    )

    warnings = []
    if total < 5000:
        warnings.append(f"Volume faible pour l'objectif actuel: {total} exemples < 5000.")
    tool_ratio = tool_use_count / total
    if not 0.25 <= tool_ratio <= 0.45:
        warnings.append(f"Ratio tool use hors cible: {tool_ratio:.0%}, cible 25%-45%.")
    if implicit_ratio < 0.55:
        warnings.append(f"Part implicite/ambiguë insuffisante: {implicit_ratio:.0%}, cible >=55%.")
    if duplicate_full:
        warnings.append(f"Doublons exacts détectés: {duplicate_full}.")
    if duplicate_user / total > 0.03:
        warnings.append(f"Prompts utilisateurs trop proches: {duplicate_user}/{total}.")
    if role_errors:
        warnings.append(f"Erreurs de rôles/messages: {len(role_errors)}.")
    if metadata_errors:
        warnings.append(f"Erreurs de métadonnées: {len(metadata_errors)}.")
    if label_response_mismatches:
        warnings.append(f"Incohérences Label metadata/réponse: {len(label_response_mismatches)}.")
    if missing_tool_messages:
        warnings.append(f"Incohérences tool use: {len(missing_tool_messages)}.")

    return {
        "total": total,
        "categories": dict(categories),
        "labels": dict(labels),
        "severities": dict(severities),
        "difficulties": dict(difficulties),
        "sectors": dict(sectors),
        "investor_profiles": dict(profiles),
        "lean_principles": dict(principles),
        "tool_use_count": tool_use_count,
        "tool_use_ratio": tool_ratio,
        "implicit_ratio": implicit_ratio,
        "avg_messages_per_example": round(sum(message_counts) / total, 1),
        "avg_chars_per_example": round(sum(char_counts) / total),
        "min_chars": min(char_counts),
        "max_chars": max(char_counts),
        "duplicate_full": duplicate_full,
        "duplicate_user_prompts": duplicate_user,
        "role_errors": role_errors,
        "metadata_errors": metadata_errors,
        "label_response_mismatches": label_response_mismatches,
        "missing_tool_messages": missing_tool_messages,
        "warnings": warnings,
    }


def render_report(metrics: dict, input_path: Path) -> str:
    def distribution_table(title: str, values: dict[str, int]) -> list[str]:
        lines = [f"## {title}", "", "| Valeur | Nombre | Ratio |", "|---|---:|---:|"]
        total = metrics["total"] or 1
        for name, count in sorted(values.items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"| {name} | {count} | {count / total:.1%} |")
        lines.append("")
        return lines

    status = "OK" if not metrics.get("warnings") else "À surveiller"
    lines = [
        "# Dataset Metrics Report - LFM Lean Startup",
        "",
        f"Source: `{input_path}`",
        f"Statut: **{status}**",
        "",
        "## Vue d'ensemble",
        "",
        "| Métrique | Valeur |",
        "|---|---:|",
        f"| Total exemples | {metrics['total']} |",
        f"| Tool use | {metrics['tool_use_count']} ({metrics['tool_use_ratio']:.1%}) |",
        f"| Implicite/Ambigu/Mixte | {metrics['implicit_ratio']:.1%} |",
        f"| Messages moyens | {metrics['avg_messages_per_example']} |",
        f"| Caractères moyens | {metrics['avg_chars_per_example']} |",
        f"| Min / Max caractères | {metrics['min_chars']} / {metrics['max_chars']} |",
        f"| Doublons exacts | {metrics['duplicate_full']} |",
        f"| Prompts utilisateurs proches/exacts | {metrics['duplicate_user_prompts']} |",
        "",
    ]

    lines += distribution_table("Distribution par catégorie", metrics["categories"])
    lines += distribution_table("Distribution par Label", metrics["labels"])
    lines += distribution_table("Distribution par Severity", metrics["severities"])
    lines += distribution_table("Distribution par Difficulty", metrics["difficulties"])
    lines += distribution_table("Distribution par principe Lean", metrics["lean_principles"])
    lines += distribution_table("Distribution par secteur", metrics["sectors"])

    if metrics.get("warnings"):
        lines += ["## Avertissements", ""]
        for warning in metrics["warnings"]:
            lines.append(f"- {warning}")
        lines.append("")

    diagnostics = [
        ("Erreurs rôles/messages", metrics.get("role_errors", [])),
        ("Erreurs métadonnées", metrics.get("metadata_errors", [])),
        ("Incohérences Label", metrics.get("label_response_mismatches", [])),
        ("Incohérences tool use", metrics.get("missing_tool_messages", [])),
    ]
    for title, values in diagnostics:
        if values:
            lines += [f"## {title}", ""]
            for value in values[:20]:
                lines.append(f"- {value}")
            if len(values) > 20:
                lines.append(f"- ... et {len(values) - 20} autres")
            lines.append("")

    if not metrics.get("warnings"):
        lines += [
            "## Recommandation",
            "",
            "- Dataset validé pour un premier fine-tuning LoRA-SFT.",
            "- Garder `hard_eval` séparé pour mesurer la généralisation sur les cas ambigus.",
            "",
        ]

    lines += ["---", "", "Rapport généré par `src/data/report_dataset_metrics.py`."]
    return "\n".join(lines)


def main() -> None:
    logger.info("Chargement du dataset: %s", INPUT_DATASET)
    examples = load_dataset(INPUT_DATASET)
    metrics = compute_metrics(examples)
    report = render_report(metrics, INPUT_DATASET)
    OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_REPORT.write_text(report, encoding="utf-8")
    logger.info("Rapport sauvegardé: %s", OUTPUT_REPORT)
    if metrics.get("warnings"):
        for warning in metrics["warnings"]:
            logger.warning("%s", warning)
    else:
        logger.info("Dataset validé sans avertissement.")


if __name__ == "__main__":
    main()
