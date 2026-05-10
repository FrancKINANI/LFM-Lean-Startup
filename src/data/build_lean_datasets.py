"""
src/data/build_lean_datasets.py
================================
Génère le dataset de fine-tuning SFT pour LFM2.5-350M.
Combine la structure robuste du script utilisateur avec l'expansion synthétique 
pour un volume et une diversité maximum.
"""

import json
import logging
import os
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from sklearn.model_selection import train_test_split

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Racine du projet
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Chemins de sortie
OUTPUT_FULL     = PROJECT_ROOT / "data" / "source" / "full_dataset.jsonl"
OUTPUT_SPLITS   = PROJECT_ROOT / "data" / "splits"
OUTPUT_LIQUID   = PROJECT_ROOT / "data" / "liquid"

# Configuration
RANDOM_SEED = 42
TOTAL_EXAMPLES = 4000
TOOL_USE_RATIO = 0.35

# --- Data Pools for Expansion ---
SECTORS = ["SaaS B2B", "Marketplace", "Fintech", "Healthtech", "Edtech", "Agritech", "E-commerce", "Deeptech", "Web3", "CleanTech", "Proptech", "Adtech", "Insurtech", "Logitech", "Foodtech"]
STAGES = ["Seed", "Pre-Seed", "Series A", "Series B", "Ideation", "MVP Ready", "Post-Pivot"]
INVESTOR_PROFILES = ["angel", "vc", "impact", "strategic", "entrepreneur"]
REGIONS = ["France", "Afrique Subsaharienne", "Maroc", "USA", "Europe", "Asie du Sud-Est"]

PROBLEMS = [
    "faible rétention (retention rate < 10%)", "coût d'acquisition trop élevé (CAC > LTV)", 
    "marché trop petit (TAM < 100M€)", "manque de product-market fit (PMF)", 
    "burn rate explosif", "concurrence féroce (incumbents dominants)",
    "équipe sans profil technique (no-code fragile)", "modèle économique flou", 
    "dépendance à un seul client (> 50% du CA)", "vitesse d'itération trop lente"
]
STRENGTHS = [
    "forte traction organique (> 30% MoM)", "technologie propriétaire défendable (brevet/IP)", 
    "équipe expérimentée (ex-founders)", "marché en hypercroissance (> 20% CAGR)", 
    "excellente rétention (net revenue retention > 120%)", "coûts d'acquisition faibles (SEO/Viral)", 
    "preuve de concept validée avec des clients payants (LoI/Pilot)", "partenariats stratégiques signés"
]

# =============================================================================
# STRUCTURES DE DONNÉES (User's robust classes)
# =============================================================================

@dataclass
class Message:
    role: str     # "system" | "user" | "assistant" | "tool"
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

# =============================================================================
# SYSTEM PROMPTS
# =============================================================================

SYSTEM_PROMPT_WITH_TOOLS = """Tu es un analyste Lean Startup expert. Tu évalues les opportunités d'investissement et identifies les dangers critiques pour les startups.

Ton rôle :
- Analyser les informations fournies sur une startup en texte libre
- Identifier les risques critiques de manière claire et accessible
- Évaluer l'opportunité d'investissement selon le profil de l'interlocuteur
- Rendre accessible ce que les whitepapers et documents techniques rendent opaque
- T'appuyer sur des données réelles (benchmarks, cas similaires) via tes outils

Ton style :
- Clair, structuré, sans jargon inutile
- Exigeant sur les faits, bienveillant sur la forme
- Adapté à l'interlocuteur (investisseur ou entrepreneur)

List of tools: [{"name": "query_postgresql", "description": "Interroge la base de données PostgreSQL contenant des cas de startups, des patterns de risque connus, des benchmarks sectoriels, des concepts Lean Startup et des critères d'investissement.", "parameters": {"type": "object", "properties": {"sql": {"type": "string", "description": "Requête SQL SELECT à exécuter. Tables : startups, pivot_cases, risk_patterns, sector_benchmarks, lean_concepts, investment_criteria."}}, "required": ["sql"]}}]"""

SYSTEM_PROMPT_NO_TOOLS = """Tu es un analyste Lean Startup expert. Tu identifies les forces, faiblesses et dangers d'un projet de manière claire et structurée."""

# =============================================================================
# GENERATORS
# =============================================================================

def format_tool_call(sql: str) -> str:
    return f'<|tool_call_start|>[query_postgresql(sql="{sql}")]<|tool_call_end|>'

def generate_diagnostic(idx, tool_use=False):
    sector = random.choice(SECTORS)
    stage = random.choice(STAGES)
    problem = random.choice(PROBLEMS)
    strength = random.choice(STRENGTHS)
    region = random.choice(REGIONS)
    profile = random.choice(INVESTOR_PROFILES)
    
    messages = []
    messages.append(Message("system", SYSTEM_PROMPT_WITH_TOOLS if tool_use else SYSTEM_PROMPT_NO_TOOLS))
    messages.append(Message("user", f"Analyse le projet {idx} : Startup {sector} en {stage} ({region}). On a une {strength} mais on galère avec une {problem}. Je suis {profile}."))
    
    if tool_use:
        sql = f"SELECT pattern_name, criticality, simple_explain FROM risk_patterns WHERE (sector = '{sector.lower()}' OR sector IS NULL) LIMIT 3"
        messages.append(Message("assistant", format_tool_call(sql)))
        
        tool_data = {"status": "success", "data": [{"pattern_name": "Market Risk", "criticality": "high", "simple_explain": f"La {problem} est un signal d'alarme."}]}
        messages.append(Message("tool", json.dumps(tool_data, ensure_ascii=False)))
        
        messages.append(Message("assistant", f"## Diagnostic de votre projet {sector}\n\nL'analyse des patterns de risque confirme que votre {problem} est un point bloquant majeur malgré votre {strength}. **Conseil** : Focalisez-vous sur la validation client avant de scaler."))
    else:
        messages.append(Message("assistant", f"### Analyse du Projet {idx}\n\n**Forces** : {strength}.\n**Faiblesses** : {problem}.\n**Verdict** : Risque élevé lié au stade {stage}. Ne pas négliger l'impact de la concurrence en {region}."))

    return Example(messages=messages, metadata={"category": "diagnostic_complet", "sector": sector, "has_tool_use": tool_use, "region": region, "investor_profile": profile})

def generate_danger(idx, tool_use=False):
    sector = random.choice(SECTORS)
    p1, p2 = random.sample(PROBLEMS, 2)
    profile = random.choice(INVESTOR_PROFILES)
    
    messages = [Message("system", SYSTEM_PROMPT_WITH_TOOLS if tool_use else SYSTEM_PROMPT_NO_TOOLS)]
    messages.append(Message("user", f"Quels sont les dangers critiques pour un projet {sector} souffrant de {p1} et {p2} ? Je suis {profile}."))
    
    if tool_use:
        sql = f"SELECT pattern_name, criticality, simple_explain FROM risk_patterns WHERE sector = '{sector.lower()}' AND criticality = 'critical'"
        messages.append(Message("assistant", format_tool_call(sql)))
        messages.append(Message("tool", json.dumps({"status": "success", "data": [{"pattern_name": "Burn Rate", "criticality": "critical", "simple_explain": "Perte de cash rapide."}]}, ensure_ascii=False)))
        messages.append(Message("assistant", f"En plus du risque de Burn Rate, vos problèmes de {p1} et {p2} sont mortels. Priorité : fixer {p1}."))
    else:
        messages.append(Message("assistant", f"Dangers identifiés pour {sector} :\n1. **{p1}** (Critique)\n2. **{p2}** (Élevé)"))
        
    return Example(messages=messages, metadata={"category": "identification_des_dangers", "sector": sector, "has_tool_use": tool_use, "investor_profile": profile})

def generate_investment(idx, tool_use=False):
    sector = random.choice(SECTORS)
    stage = random.choice(STAGES)
    profile = random.choice(INVESTOR_PROFILES)
    
    messages = [Message("system", SYSTEM_PROMPT_WITH_TOOLS if tool_use else SYSTEM_PROMPT_NO_TOOLS)]
    messages.append(Message("user", f"Dossier {idx} : Startup {sector} en {stage}. Devrais-je investir en tant que {profile} ?"))
    
    if tool_use:
        sql = f"SELECT criterion_name, weight FROM investment_criteria WHERE investor_profile = '{profile}' AND stage = '{stage.lower()}'"
        messages.append(Message("assistant", format_tool_call(sql)))
        messages.append(Message("tool", json.dumps({"status": "success", "data": [{"criterion_name": "Retention", "weight": "critical"}]}, ensure_ascii=False)))
        messages.append(Message("assistant", f"En tant que {profile}, le critère de Rétention est éliminatoire. Vérifiez les chiffres avant d'investir."))
    else:
        messages.append(Message("assistant", f"Verdict {profile} : Recommandation neutre. Le stade {stage} nécessite plus de preuves de traction."))
        
    return Example(messages=messages, metadata={"category": "evaluation_investissement", "sector": sector, "has_tool_use": tool_use, "investor_profile": profile})

def generate_simplification(idx, tool_use=False):
    concepts = ["Pivot", "MVP", "Product-Market Fit", "Customer Discovery", "Vanity Metrics"]
    concept = random.choice(concepts)
    profile = random.choice(INVESTOR_PROFILES)
    
    messages = [Message("system", SYSTEM_PROMPT_WITH_TOOLS if tool_use else SYSTEM_PROMPT_NO_TOOLS)]
    messages.append(Message("user", f"Explique moi '{concept}' simplement. Je suis {profile}."))
    
    if tool_use:
        sql = f"SELECT simple_def, analogy FROM lean_concepts WHERE concept_name ILIKE '%{concept}%'"
        messages.append(Message("assistant", format_tool_call(sql)))
        messages.append(Message("tool", json.dumps({"status": "success", "data": [{"simple_def": "Def", "analogy": "Analog"}]}, ensure_ascii=False)))
        messages.append(Message("assistant", f"Le concept de {concept} c'est comme... [Analog]. En gros : Def."))
    else:
        messages.append(Message("assistant", f"**{concept}** : C'est comme tester l'eau avant de plonger."))
        
    return Example(messages=messages, metadata={"category": "simplification_concept", "has_tool_use": tool_use, "investor_profile": profile, "sector": "universal"})

# =============================================================================
# MAIN LOGIC
# =============================================================================

def main():
    logger.info("Génération du Master Dataset SFT...")
    random.seed(RANDOM_SEED)
    
    examples = []
    counts = {
        "diagnostic_complet": int(TOTAL_EXAMPLES * 0.35),
        "identification_des_dangers": int(TOTAL_EXAMPLES * 0.25),
        "evaluation_investissement": int(TOTAL_EXAMPLES * 0.25),
        "simplification_concept": int(TOTAL_EXAMPLES * 0.15)
    }
    
    generators = {
        "diagnostic_complet": generate_diagnostic,
        "identification_des_dangers": generate_danger,
        "evaluation_investissement": generate_investment,
        "simplification_concept": generate_simplification
    }
    
    for cat, count in counts.items():
        for i in range(count):
            tool_use = random.random() < TOOL_USE_RATIO
            examples.append(generators[cat](i, tool_use))
            
    random.shuffle(examples)
    
    # Save Full
    OUTPUT_FULL.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FULL, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex.to_dict(), ensure_ascii=False) + "\n")
            
    # Splits
    train_ex, temp_ex = train_test_split(examples, test_size=0.2, random_state=RANDOM_SEED)
    val_ex, test_ex = train_test_split(temp_ex, test_size=0.5, random_state=RANDOM_SEED)
    
    for name, data in [("train", train_ex), ("val", val_ex), ("test", test_ex)]:
        path = OUTPUT_SPLITS / f"{name}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for ex in data:
                f.write(json.dumps(ex.to_dict(), ensure_ascii=False) + "\n")
                
    # Liquid format
    OUTPUT_LIQUID.mkdir(parents=True, exist_ok=True)
    for name, data in [("train", train_ex), ("val", val_ex)]:
        path = OUTPUT_LIQUID / f"{name}_liquid.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for ex in data:
                f.write(json.dumps({"messages": [m.__dict__ for m in ex.messages]}, ensure_ascii=False) + "\n")
            
    logger.info(f"Dataset construit : {len(examples)} exemples.")
    logger.info(f"Splits: Train={len(train_ex)}, Val={len(val_ex)}, Test={len(test_ex)}")

if __name__ == "__main__":
    main()
