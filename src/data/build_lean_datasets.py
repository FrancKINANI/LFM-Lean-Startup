"""
src/data/build_lean_datasets.py
================================
Build a supervised fine-tuning dataset for LFM2.5-350M.

The canonical dataset keeps full chat messages plus audit metadata. The Liquid
format converts each conversation to a single `text` field consumed by TRL
SFTTrainer.
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from sklearn.model_selection import train_test_split

try:
    from src.inference.tool_executor import TOOL_CALL_END, TOOL_CALL_START
except ImportError:  # pragma: no cover - useful when the file is run directly.
    TOOL_CALL_START = "<|tool_call_start|>"
    TOOL_CALL_END = "<|tool_call_end|>"


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_FULL = PROJECT_ROOT / "data" / "source" / "full_dataset.jsonl"
OUTPUT_SPLITS = PROJECT_ROOT / "data" / "splits"
OUTPUT_LIQUID = PROJECT_ROOT / "data" / "liquid"

RANDOM_SEED = 42
TOTAL_EXAMPLES = 5200
HARD_EVAL_EXAMPLES = 250
TOOL_USE_RATIO = 0.35


LABELS = ["Green Flag", "Red Flag", "Mixed"]
SEVERITIES = ["Mineur", "Majeur", "Fatal", "Non applicable"]
DIFFICULTIES = ["Explicite", "Implicite", "Ambigu", "Mixte"]
CATEGORIES = [
    "diagnostic_complet",
    "identification_des_dangers",
    "evaluation_investissement",
    "simplification_concept",
]

SECTORS = [
    "SaaS B2B",
    "Marketplace",
    "Fintech",
    "Healthtech",
    "Edtech",
    "Agritech",
    "E-commerce",
    "Deeptech",
    "Web3",
    "Cleantech",
    "Proptech",
    "Adtech",
    "Insurtech",
    "Logistique",
    "Foodtech",
]
STAGES = ["Idéation", "Pre-Seed", "Seed", "Series A", "Post-Pivot"]
INVESTOR_PROFILES = ["angel", "vc", "impact", "strategic", "entrepreneur"]
REGIONS = ["France", "Afrique subsaharienne", "Maroc", "USA", "Europe", "Asie du Sud-Est"]


RISK_SIGNALS = [
    {
        "name": "CAC supérieur à la LTV",
        "principle": "Unit economics avant croissance",
        "severity": "Fatal",
        "explicit": "le CAC dépasse la LTV depuis trois cohortes",
        "implicit": "chaque nouveau client coûte plus cher que ce qu'il rapporte sur sa durée de vie estimée",
        "why": "scaler augmenterait les pertes au lieu de valider le modèle économique",
        "sql_slug": "unit_economics",
    },
    {
        "name": "Rétention faible",
        "principle": "Build-Measure-Learn",
        "severity": "Majeur",
        "explicit": "la rétention à 30 jours reste sous 12 %",
        "implicit": "les utilisateurs essaient le produit puis disparaissent après la première semaine",
        "why": "l'équipe apprend moins de la valeur réelle que de l'acquisition initiale",
        "sql_slug": "retention",
    },
    {
        "name": "TAM trop petit",
        "principle": "Validation du marché",
        "severity": "Majeur",
        "explicit": "le marché adressable réaliste est inférieur à 80 M EUR",
        "implicit": "la niche est très engagée mais trop étroite pour soutenir une sortie VC",
        "why": "le potentiel de croissance ne correspond pas à une trajectoire venture-scale",
        "sql_slug": "market_size",
    },
    {
        "name": "Solution avant problème",
        "principle": "Customer Discovery",
        "severity": "Majeur",
        "explicit": "l'équipe a construit six mois sans entretiens clients",
        "implicit": "la roadmap est très détaillée mais la douleur client reste floue",
        "why": "le produit optimise une hypothèse non validée",
        "sql_slug": "customer_discovery",
    },
    {
        "name": "Vanity metrics",
        "principle": "Métriques actionnables",
        "severity": "Mineur",
        "explicit": "le pitch met surtout en avant les impressions et les inscriptions gratuites",
        "implicit": "les chiffres progressent dans le deck, mais aucun indicateur ne relie usage, valeur et revenu",
        "why": "les métriques ne permettent pas de décider quoi changer",
        "sql_slug": "vanity_metrics",
    },
    {
        "name": "Dépendance client",
        "principle": "Réduction du risque systémique",
        "severity": "Majeur",
        "explicit": "un seul client représente 62 % du chiffre d'affaires",
        "implicit": "la traction vient surtout d'un grand compte qui pilote aussi la roadmap",
        "why": "la preuve de marché peut être confondue avec une relation commerciale isolée",
        "sql_slug": "customer_concentration",
    },
    {
        "name": "Burn rate non maîtrisé",
        "principle": "Runway avant scale",
        "severity": "Fatal",
        "explicit": "il reste quatre mois de runway au rythme actuel",
        "implicit": "l'équipe recrute pour accélérer alors que le revenu récurrent ne couvre presque aucune dépense",
        "why": "l'entreprise risque de manquer de temps avant d'apprendre assez",
        "sql_slug": "burn_rate",
    },
]

GREEN_SIGNALS = [
    {
        "name": "Cohortes en amélioration",
        "principle": "Apprentissage validé",
        "evidence": "les trois dernières cohortes montrent une rétention J30 en hausse de 18 % à 34 %",
        "why": "l'équipe transforme les retours clients en meilleure activation",
    },
    {
        "name": "Canal organique défendable",
        "principle": "Moteur de croissance",
        "evidence": "65 % des nouveaux clients viennent du bouche-à-oreille ou du SEO avec CAC faible",
        "why": "la croissance n'est pas uniquement achetée",
    },
    {
        "name": "Painkiller mesurable",
        "principle": "Problem-Solution Fit",
        "evidence": "les clients paient pour réduire un coût opérationnel précis de 22 %",
        "why": "la valeur est reliée à un problème urgent et quantifié",
    },
    {
        "name": "Cycle d'itération court",
        "principle": "Build-Measure-Learn",
        "evidence": "l'équipe lance une expérience client toutes les deux semaines avec critère de succès clair",
        "why": "le rythme d'apprentissage réduit le risque produit",
    },
    {
        "name": "Expansion nette positive",
        "principle": "Validation par usage répété",
        "evidence": "les comptes existants augmentent leur dépense nette de 118 % sur douze mois",
        "why": "la valeur perçue augmente après l'achat initial",
    },
]

CONCEPTS = {
    "MVP": {
        "simple_def": "version minimale qui teste une hypothèse critique avec le moins d'effort possible",
        "analogy": "une maquette testée en magasin avant de construire toute l'usine",
        "principle": "Build-Measure-Learn",
    },
    "Product-Market Fit": {
        "simple_def": "moment où un segment précis utilise, garde et recommande le produit sans poussée artificielle",
        "analogy": "une porte qui s'ouvre parce que les clients poussent eux-mêmes",
        "principle": "Validation du marché",
    },
    "Pivot": {
        "simple_def": "changement structuré d'hypothèse après apprentissage, pas un simple changement d'humeur",
        "analogy": "changer d'itinéraire après avoir lu la carte, pas jeter la voiture",
        "principle": "Apprentissage validé",
    },
    "Customer Discovery": {
        "simple_def": "processus d'entretiens et tests pour comprendre le problème avant de vendre la solution",
        "analogy": "prendre le pouls avant de prescrire un traitement",
        "principle": "Customer Discovery",
    },
    "Vanity Metrics": {
        "simple_def": "chiffres flatteurs qui ne guident pas une décision produit ou business",
        "analogy": "regarder les applaudissements au lieu des ventes récurrentes",
        "principle": "Métriques actionnables",
    },
}


@dataclass
class Message:
    role: str
    content: str


@dataclass
class Example:
    messages: list[Message]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "messages": [{"role": m.role, "content": m.content} for m in self.messages],
            "metadata": self.metadata,
        }

    def to_liquid_format(self) -> dict[str, Any]:
        return {
            "text": render_chat_text(self.messages),
            "metadata": self.metadata,
        }


SYSTEM_CORE = (
    "Tu es un analyste Lean Startup et VC. Réponds court, clair et actionnable. "
    "Cite le principe Lean Startup violé ou validé, puis donne la prochaine expérience."
)

TOOLS_SPEC = {
    "name": "query_postgresql",
    "description": (
        "Interroge PostgreSQL pour récupérer benchmarks sectoriels, patterns de risque, "
        "concepts Lean Startup et critères d'investissement."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": (
                    "Requête SELECT. Tables : startups, pivot_cases, risk_patterns, "
                    "sector_benchmarks, lean_concepts, investment_criteria."
                ),
            }
        },
        "required": ["sql"],
    },
}

SYSTEM_PROMPT_NO_TOOLS = SYSTEM_CORE
SYSTEM_PROMPT_WITH_TOOLS = f"{SYSTEM_CORE}\n\nList of tools: {json.dumps([TOOLS_SPEC], ensure_ascii=False)}"


def render_chat_text(messages: Iterable[Message]) -> str:
    parts = []
    for message in messages:
        parts.append(f"<|im_start|>{message.role}\n{message.content}<|im_end|>")
    return "\n".join(parts)


def format_tool_call(sql: str) -> str:
    payload = {"name": "query_postgresql", "parameters": {"sql": sql}}
    return f"{TOOL_CALL_START}{json.dumps(payload, ensure_ascii=False)}{TOOL_CALL_END}"


def tool_result(data: list[dict[str, Any]]) -> str:
    return json.dumps(
        {
            "status": "success",
            "row_count": len(data),
            "execution_time_ms": 8.4,
            "data": data,
        },
        ensure_ascii=False,
    )


def slug(value: str) -> str:
    return (
        value.lower()
        .replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace(" ", "_")
        .replace("-", "_")
    )


def choose_label(rng: random.Random, hard: bool) -> str:
    weights = [0.31, 0.37, 0.32] if hard else [0.36, 0.39, 0.25]
    return rng.choices(LABELS, weights=weights, k=1)[0]


def choose_difficulty(rng: random.Random, hard: bool) -> str:
    weights = [0.15, 0.40, 0.30, 0.15] if hard else [0.30, 0.38, 0.18, 0.14]
    return rng.choices(DIFFICULTIES, weights=weights, k=1)[0]


def build_metadata(
    *,
    idx: int,
    category: str,
    label: str,
    severity: str,
    difficulty: str,
    sector: str = "universal",
    stage: str = "non applicable",
    region: str = "non applicable",
    profile: str = "non applicable",
    has_tool_use: bool,
    principle: str,
    hard_eval: bool = False,
) -> dict[str, Any]:
    return {
        "example_id": f"lean-{idx:05d}",
        "category": category,
        "Label": label,
        "Severity": severity,
        "Difficulty": difficulty,
        "sector": sector,
        "stage": stage,
        "region": region,
        "investor_profile": profile,
        "has_tool_use": has_tool_use,
        "lean_principle": principle,
        "hard_eval": hard_eval,
    }


def generate_diagnostic(idx: int, rng: random.Random, tool_use: bool = False, hard: bool = False) -> Example:
    sector = rng.choice(SECTORS)
    stage = rng.choice(STAGES)
    region = rng.choice(REGIONS)
    profile = rng.choice(INVESTOR_PROFILES)
    label = choose_label(rng, hard)
    difficulty = choose_difficulty(rng, hard)
    risk = rng.choice(RISK_SIGNALS)
    strength = rng.choice(GREEN_SIGNALS)

    if label == "Green Flag":
        severity = "Non applicable"
        principle = strength["principle"]
        user_evidence = strength["evidence"]
        response = (
            f"Label: Green Flag\nSeverity: Non applicable\nDifficulty: {difficulty}\n"
            f"Analyse: signal positif. Le principe validé est {principle}: {strength['why']}. "
            f"Prochaine expérience: isoler le segment qui produit ce signal et mesurer s'il se répète sur deux nouvelles cohortes."
        )
    elif label == "Mixed":
        severity = risk["severity"]
        principle = risk["principle"]
        user_evidence = f"{strength['evidence']}, mais {risk['implicit' if difficulty in {'Implicite', 'Ambigu'} else 'explicit']}"
        response = (
            f"Label: Mixed\nSeverity: {severity}\nDifficulty: {difficulty}\n"
            f"Analyse: la traction existe, mais le risque principal reste {risk['name']}. "
            f"Principe Lean Startup concerné: {principle}. Le danger: {risk['why']}. "
            f"Prochaine expérience: tester l'hypothèse risquée avant toute dépense de scale."
        )
    else:
        severity = risk["severity"]
        principle = risk["principle"]
        user_evidence = risk["implicit" if difficulty in {"Implicite", "Ambigu"} else "explicit"]
        response = (
            f"Label: Red Flag\nSeverity: {severity}\nDifficulty: {difficulty}\n"
            f"Analyse: red flag sur {risk['name']}. Principe Lean Startup violé: {principle}. "
            f"Pourquoi: {risk['why']}. Prochaine expérience: définir un test mesurable qui invalide ou confirme ce risque en moins de 30 jours."
        )

    user = (
        f"Analyse ce projet {idx}: startup {sector} en {stage}, basée en {region}. "
        f"Contexte: {user_evidence}. Je suis {profile}."
    )
    messages = [Message("system", SYSTEM_PROMPT_WITH_TOOLS if tool_use else SYSTEM_PROMPT_NO_TOOLS), Message("user", user)]

    if tool_use:
        sql = (
            "SELECT pattern_name, criticality, simple_explain "
            f"FROM risk_patterns WHERE pattern_slug = '{risk['sql_slug']}' "
            f"OR sector = '{slug(sector)}' LIMIT 3"
        )
        messages.append(Message("assistant", format_tool_call(sql)))
        messages.append(
            Message(
                "tool",
                tool_result(
                    [
                        {
                            "pattern_name": risk["name"],
                            "criticality": severity,
                            "simple_explain": risk["why"],
                            "lean_principle": principle,
                        }
                    ]
                ),
            )
        )
    messages.append(Message("assistant", response))

    return Example(
        messages=messages,
        metadata=build_metadata(
            idx=idx,
            category="diagnostic_complet",
            label=label,
            severity=severity,
            difficulty=difficulty,
            sector=sector,
            stage=stage,
            region=region,
            profile=profile,
            has_tool_use=tool_use,
            principle=principle,
            hard_eval=hard,
        ),
    )


def generate_danger(idx: int, rng: random.Random, tool_use: bool = False, hard: bool = False) -> Example:
    sector = rng.choice(SECTORS)
    profile = rng.choice(INVESTOR_PROFILES)
    difficulty = choose_difficulty(rng, hard)
    risks = rng.sample(RISK_SIGNALS, 2)
    label = "Red Flag" if not hard or rng.random() < 0.75 else "Mixed"
    severity = "Fatal" if any(r["severity"] == "Fatal" for r in risks) else "Majeur"
    principle = risks[0]["principle"]
    evidence_mode = "implicit" if difficulty in {"Implicite", "Ambigu"} else "explicit"

    user = (
        f"Quels dangers critiques vois-tu pour une startup {sector} ? "
        f"Indices: {risks[0][evidence_mode]} ; {risks[1][evidence_mode]}. Profil: {profile}."
    )
    response = (
        f"Label: {label}\nSeverity: {severity}\nDifficulty: {difficulty}\n"
        f"Analyse: priorité au risque '{risks[0]['name']}', puis '{risks[1]['name']}'. "
        f"Principe Lean Startup violé: {principle}. "
        f"Action: formuler une hypothèse falsifiable et arrêter le scale tant que le signal n'est pas corrigé."
    )

    messages = [Message("system", SYSTEM_PROMPT_WITH_TOOLS if tool_use else SYSTEM_PROMPT_NO_TOOLS), Message("user", user)]
    if tool_use:
        sql = (
            "SELECT pattern_name, criticality, simple_explain FROM risk_patterns "
            f"WHERE pattern_slug IN ('{risks[0]['sql_slug']}', '{risks[1]['sql_slug']}') "
            "ORDER BY criticality DESC LIMIT 5"
        )
        messages.append(Message("assistant", format_tool_call(sql)))
        messages.append(
            Message(
                "tool",
                tool_result(
                    [
                        {
                            "pattern_name": risk["name"],
                            "criticality": risk["severity"],
                            "simple_explain": risk["why"],
                            "lean_principle": risk["principle"],
                        }
                        for risk in risks
                    ]
                ),
            )
        )
    messages.append(Message("assistant", response))

    return Example(
        messages=messages,
        metadata=build_metadata(
            idx=idx,
            category="identification_des_dangers",
            label=label,
            severity=severity,
            difficulty=difficulty,
            sector=sector,
            profile=profile,
            has_tool_use=tool_use,
            principle=principle,
            hard_eval=hard,
        ),
    )


def generate_investment(idx: int, rng: random.Random, tool_use: bool = False, hard: bool = False) -> Example:
    sector = rng.choice(SECTORS)
    stage = rng.choice(STAGES)
    region = rng.choice(REGIONS)
    profile = rng.choice(INVESTOR_PROFILES)
    label = choose_label(rng, hard)
    difficulty = choose_difficulty(rng, hard)
    risk = rng.choice(RISK_SIGNALS)
    strength = rng.choice(GREEN_SIGNALS)

    if label == "Green Flag":
        severity = "Non applicable"
        principle = strength["principle"]
        thesis = f"{strength['evidence']} et la demande vient d'un segment client précis"
        response = (
            f"Label: Green Flag\nSeverity: Non applicable\nDifficulty: {difficulty}\n"
            f"Analyse: investissable sous réserve de due diligence. Principe validé: {principle}. "
            f"À vérifier: répétabilité du canal, marge brute et qualité des cohortes."
        )
    elif label == "Mixed":
        severity = risk["severity"]
        principle = risk["principle"]
        thesis = f"{strength['evidence']}, mais {risk['implicit' if difficulty != 'Explicite' else 'explicit']}"
        response = (
            f"Label: Mixed\nSeverity: {severity}\nDifficulty: {difficulty}\n"
            f"Analyse: dossier intéressant mais pas encore évident pour {profile}. "
            f"Principe à vérifier: {principle}. Condition d'investissement: prouver que le risque ne détruit pas les unit economics."
        )
    else:
        severity = risk["severity"]
        principle = risk["principle"]
        thesis = risk["implicit" if difficulty != "Explicite" else "explicit"]
        response = (
            f"Label: Red Flag\nSeverity: {severity}\nDifficulty: {difficulty}\n"
            f"Analyse: ne pas investir maintenant. Principe Lean Startup violé: {principle}. "
            f"La startup doit produire une preuve d'apprentissage validé avant de lever plus de capital."
        )

    user = (
        f"Dossier {idx}: startup {sector} en {stage}, région {region}. "
        f"Thèse: {thesis}. Dois-je investir comme {profile} ?"
    )
    messages = [Message("system", SYSTEM_PROMPT_WITH_TOOLS if tool_use else SYSTEM_PROMPT_NO_TOOLS), Message("user", user)]

    if tool_use:
        sql = (
            "SELECT criterion_name, weight, simple_rule FROM investment_criteria "
            f"WHERE investor_profile = '{profile}' AND stage = '{slug(stage)}' LIMIT 4"
        )
        messages.append(Message("assistant", format_tool_call(sql)))
        messages.append(
            Message(
                "tool",
                tool_result(
                    [
                        {
                            "criterion_name": "cohort_retention",
                            "weight": "critical" if severity == "Fatal" else "important",
                            "simple_rule": "ne pas financer le scale sans rétention ou unit economics prouvés",
                        },
                        {
                            "criterion_name": "learning_velocity",
                            "weight": "important",
                            "simple_rule": "chaque cycle doit produire une décision produit ou go-to-market",
                        },
                    ]
                ),
            )
        )
    messages.append(Message("assistant", response))

    return Example(
        messages=messages,
        metadata=build_metadata(
            idx=idx,
            category="evaluation_investissement",
            label=label,
            severity=severity,
            difficulty=difficulty,
            sector=sector,
            stage=stage,
            region=region,
            profile=profile,
            has_tool_use=tool_use,
            principle=principle,
            hard_eval=hard,
        ),
    )


def generate_simplification(idx: int, rng: random.Random, tool_use: bool = False, hard: bool = False) -> Example:
    concept_name, concept = rng.choice(list(CONCEPTS.items()))
    profile = rng.choice(INVESTOR_PROFILES)
    difficulty = "Explicite" if not hard else rng.choice(["Explicite", "Implicite"])
    label = "Green Flag"
    severity = "Non applicable"
    principle = concept["principle"]

    context = rng.choice(
        [
            "préparer un comité d'investissement",
            "briefer une équipe fondatrice junior",
            "relire un deck trop technique",
            "former un analyste VC débutant",
            "expliquer la notion à un client pilote",
        ]
    )
    user_variants = [
        f"Cas {idx}: explique-moi {concept_name} simplement pour {context}. Je suis {profile}.",
        f"Cas {idx}: dans {context}, comment expliquer {concept_name} sans jargon ?",
        f"Cas {idx}: je confonds {concept_name} avec une simple feature pendant {context}. Peux-tu clarifier ?",
    ]
    user = rng.choice(user_variants)
    response = (
        f"Label: Green Flag\nSeverity: Non applicable\nDifficulty: {difficulty}\n"
        f"Analyse: {concept_name} signifie {concept['simple_def']}. "
        f"Principe Lean Startup validé: {principle}. Image simple: {concept['analogy']}."
    )

    messages = [Message("system", SYSTEM_PROMPT_WITH_TOOLS if tool_use else SYSTEM_PROMPT_NO_TOOLS), Message("user", user)]
    if tool_use:
        safe_concept = concept_name.replace("'", "''")
        sql = (
            "SELECT concept_name, simple_def, analogy, lean_principle "
            f"FROM lean_concepts WHERE concept_name ILIKE '%{safe_concept}%' LIMIT 1"
        )
        messages.append(Message("assistant", format_tool_call(sql)))
        messages.append(
            Message(
                "tool",
                tool_result(
                    [
                        {
                            "concept_name": concept_name,
                            "simple_def": concept["simple_def"],
                            "analogy": concept["analogy"],
                            "lean_principle": principle,
                        }
                    ]
                ),
            )
        )
    messages.append(Message("assistant", response))

    return Example(
        messages=messages,
        metadata=build_metadata(
            idx=idx,
            category="simplification_concept",
            label=label,
            severity=severity,
            difficulty=difficulty,
            profile=profile,
            has_tool_use=tool_use,
            principle=principle,
            hard_eval=hard,
        ),
    )


GENERATORS = {
    "diagnostic_complet": generate_diagnostic,
    "identification_des_dangers": generate_danger,
    "evaluation_investissement": generate_investment,
    "simplification_concept": generate_simplification,
}


def generate_all_examples(
    total_examples: int = TOTAL_EXAMPLES,
    seed: int = RANDOM_SEED,
    hard_eval: bool = False,
) -> list[Example]:
    rng = random.Random(seed)
    counts = {
        "diagnostic_complet": int(total_examples * 0.32),
        "identification_des_dangers": int(total_examples * 0.25),
        "evaluation_investissement": int(total_examples * 0.28),
        "simplification_concept": total_examples
        - int(total_examples * 0.32)
        - int(total_examples * 0.25)
        - int(total_examples * 0.28),
    }

    examples: list[Example] = []
    idx = 0
    for category, count in counts.items():
        generator = GENERATORS[category]
        for _ in range(count):
            tool_use = rng.random() < TOOL_USE_RATIO
            examples.append(generator(idx, rng, tool_use=tool_use, hard=hard_eval))
            idx += 1

    rng.shuffle(examples)
    return examples


def stratification_key(example: Example) -> str:
    meta = example.metadata
    return "|".join(
        [
            meta.get("category", "unknown"),
            meta.get("Label", "unknown"),
            meta.get("Difficulty", "unknown"),
            "tool" if meta.get("has_tool_use") else "no_tool",
        ]
    )


def split_dataset(
    examples: list[Example],
    seed: int = RANDOM_SEED,
) -> tuple[list[Example], list[Example], list[Example]]:
    keys = [stratification_key(ex) for ex in examples]
    train, temp, _, temp_keys = train_test_split(
        examples,
        keys,
        test_size=0.2,
        random_state=seed,
        stratify=keys,
    )
    val, test = train_test_split(
        temp,
        test_size=0.5,
        random_state=seed,
        stratify=temp_keys,
    )
    return train, val, test


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    logger.info("Building Lean Startup SFT dataset...")
    examples = generate_all_examples()
    train, val, test = split_dataset(examples)
    hard_eval = generate_all_examples(HARD_EVAL_EXAMPLES, seed=RANDOM_SEED + 99, hard_eval=True)

    write_jsonl(OUTPUT_FULL, (ex.to_dict() for ex in examples))
    for name, data in [("train", train), ("val", val), ("test", test), ("hard_eval", hard_eval)]:
        write_jsonl(OUTPUT_SPLITS / f"{name}.jsonl", (ex.to_dict() for ex in data))

    for name, data in [("train", train), ("val", val), ("test", test), ("hard_eval", hard_eval)]:
        write_jsonl(OUTPUT_LIQUID / f"{name}_liquid.jsonl", (ex.to_liquid_format() for ex in data))

    logger.info("Dataset built: %d canonical examples + %d hard-eval examples.", len(examples), len(hard_eval))
    logger.info("Splits: train=%d, val=%d, test=%d", len(train), len(val), len(test))


if __name__ == "__main__":
    main()
