import json
import os
import random
from pathlib import Path
from sklearn.model_selection import train_test_split

# --- Données pour générer des variations ---
sectors = ["SaaS B2B", "Marketplace", "Fintech", "Healthtech", "Edtech", "Agritech", "E-commerce", "Deeptech", "Web3", "CleanTech"]
stages = ["Seed", "Pre-Seed", "Series A", "Series B", "Ideation"]
metrics = ["MRR", "ARR", "CAC", "LTV", "Churn", "NPS", "DAU/MAU", "Burn Rate"]
problems = [
    "faible rétention", "coût d'acquisition trop élevé (CAC)", "marché trop petit (TAM)",
    "manque de product-market fit", "burn rate explosif", "concurrence féroce",
    "équipe sans profil technique", "modèle économique flou", "dépendance à un seul client"
]
strengths = [
    "forte traction organique", "technologie propriétaire défendable", "équipe expérimentée",
    "marché en hypercroissance", "excellente rétention (net revenue retention > 120%)",
    "coûts d'acquisition faibles", "preuve de concept validée avec des clients payants"
]

def generate_diagnostic(idx):
    sector = random.choice(sectors)
    stage = random.choice(stages)
    users = random.randint(100, 10000)
    mrr = random.randint(1000, 100000)
    problem = random.choice(problems)
    strength = random.choice(strengths)
    
    return {
        "category": "diagnostic",
        "messages": [
            {"role": "system", "content": "Tu es un analyste Lean Startup expert. Tu identifies les forces, faiblesses et dangers d'un projet."},
            {"role": "user", "content": f"Analyse le projet {idx} : Startup {sector} en {stage}. {users} utilisateurs actifs, MRR de {mrr}€. Le CEO signale une {problem} mais met en avant une {strength}."},
            {"role": "assistant", "content": f"## Analyse du Projet {idx}\n\n### Forces\n- **Avantage compétitif** : La {strength} est un excellent signal à ce stade ({stage}).\n- **Traction financière** : Un MRR de {mrr}€ prouve qu'il y a une volonté de payer dans ce secteur {sector}.\n\n### Faiblesses\n- **Point de friction** : La {problem} est inquiétante. Cela indique un problème potentiel au niveau du produit ou du ciblage.\n\n### Dangers\n- **Risque d'épuisement (Burnout/Cash)** : Si la {problem} n'est pas résolue rapidement, vous risquez de gaspiller votre trésorerie (Burn Rate) en essayant de forcer la croissance (Leaky Bucket). Focalisez-vous sur la résolution de ce point avant de chercher à acquérir de nouveaux utilisateurs."}
        ]
    }

def generate_danger(idx):
    sector = random.choice(sectors)
    problem1 = random.choice(problems)
    problem2 = random.choice(problems)
    
    return {
        "category": "dangers",
        "messages": [
            {"role": "system", "content": "Tu es un expert en gestion de risques Lean Startup. Liste les dangers critiques simplement."},
            {"role": "user", "content": f"Quels sont les risques pour un projet {sector} qui souffre de {problem1} et de {problem2} ?"},
            {"role": "assistant", "content": f"Voici les dangers critiques pour ce projet {sector} :\n\n1. **Risque mortel (Fatal)** : La {problem1} est souvent le signe d'une mauvaise adéquation produit-marché (Product-Market Fit). Si les utilisateurs ne restent pas ou coûtent trop cher, le modèle s'effondre.\n2. **Vulnérabilité systémique** : La {problem2} aggrave la situation. Vous risquez d'être à court de trésorerie avant d'avoir pu itérer.\n3. **Pivot nécessaire** : Il faut arrêter d'investir dans la croissance (Scale) et revenir à la phase de découverte client (Customer Discovery) pour corriger ces failles fondamentales."}
        ]
    }

def generate_investment(idx):
    sector = random.choice(sectors)
    stage = random.choice(stages)
    mrr = random.randint(0, 500000)
    ask = random.randint(100000, 5000000)
    
    if mrr > 100000 and ask < 2000000:
        decision = "GO (Très favorable)"
        arg = f"Le ratio levée ({ask}€) sur traction (MRR {mrr}€) est excellent. La startup est très efficiente (capital efficient)."
    elif mrr < 5000 and ask > 1000000:
        decision = "NO-GO (Trop risqué)"
        arg = f"Lever {ask}€ avec seulement {mrr}€ de MRR est déraisonnable au stade {stage}. Le risque de dilution et d'exécution est trop grand. Ils doivent prouver la traction d'abord."
    else:
        decision = "MAYBE (Besoin d'approfondir)"
        arg = f"Les métriques sont dans la moyenne (MRR {mrr}€ pour une levée de {ask}€). Le succès dépendra de l'équipe et de la taille réelle du marché {sector}."

    return {
        "category": "investissement",
        "messages": [
            {"role": "system", "content": "Tu es un investisseur VC. Donne une recommandation go/no-go argumentée."},
            {"role": "user", "content": f"Dossier {idx} : Startup {sector} en {stage}. MRR actuel de {mrr}€. Ils demandent une levée de {ask}€."},
            {"role": "assistant", "content": f"### Recommandation : {decision}\n\n**Arguments :**\n- **Analyse Financière** : {arg}\n- **Stade d'investissement** : En {stage}, on s'attend à une dynamique spécifique. Ici, les chiffres montrent une trajectoire claire.\n- **Conclusion** : Concentrez votre due diligence sur la capacité de l'équipe à exécuter le plan avec ces fonds."}
        ]
    }

def generate_simplification(idx):
    concept = random.choice(["Pivot", "MVP (Minimum Viable Product)", "Product-Market Fit", "Customer Discovery", "Vanity Metrics", "CAC (Coût d'Acquisition Client)", "LTV (Lifetime Value)"])
    analogy = ""
    
    if "MVP" in concept:
        analogy = "Si vous voulez construire une voiture, votre MVP n'est pas une roue, c'est un skateboard. Il vous permet déjà de vous déplacer et de voir si les gens en ont besoin."
    elif "Pivot" in concept:
        analogy = "Un pivot, c'est comme utiliser le GPS : vous changez d'itinéraire parce qu'il y a des bouchons, mais votre destination finale reste la même."
    elif "Vanity Metrics" in concept:
        analogy = "C'est comme avoir beaucoup de followers sur Instagram mais personne qui achète vos produits. Ça flatte l'ego, mais ça ne paie pas les factures."
    else:
        analogy = f"Imaginez que {concept} est comme la fondation d'une maison. Sans elle, tout ce que vous construirez par la suite s'effondrera à la première difficulté."

    return {
        "category": "simplification",
        "messages": [
            {"role": "system", "content": "Tu es un mentor Lean Startup. Explique les concepts sans jargon."},
            {"role": "user", "content": f"Peux-tu m'expliquer ce qu'est le concept de '{concept}' simplement ?"},
            {"role": "assistant", "content": f"Bien sûr ! Le concept de **{concept}** est fondamental mais très simple à comprendre.\n\n**Explication simple :**\nIl s'agit d'une approche pour valider rapidement si ce que vous faites a de la valeur, sans gaspiller de temps ou d'argent.\n\n**Analogie :**\n{analogy}\n\nL'objectif est d'apprendre vite et de s'adapter à la réalité du terrain."}
        ]
    }

def generate_dataset(num_examples=3500): # 3500 pour assurer environ 1000+ par set selon la demande
    """Génère un large dataset synthétique."""
    examples = []
    
    # Ratios: 35% diag, 25% danger, 25% invest, 15% simple
    for i in range(int(num_examples * 0.35)):
        examples.append(generate_diagnostic(i))
        
    for i in range(int(num_examples * 0.25)):
        examples.append(generate_danger(i))
        
    for i in range(int(num_examples * 0.25)):
        examples.append(generate_investment(i))
        
    for i in range(int(num_examples * 0.15)):
        examples.append(generate_simplification(i))
        
    # Mélanger le dataset
    random.seed(42)
    random.shuffle(examples)
    
    return examples

def main():
    root = Path(__file__).parent.parent.parent
    data_dir = root / "data"
    source_dir = data_dir / "source"
    splits_dir = data_dir / "splits"
    liquid_dir = data_dir / "liquid"
    
    for d in [source_dir, splits_dir, liquid_dir]:
        d.mkdir(parents=True, exist_ok=True)
        
    print("Génération du dataset enrichi en cours...")
    # Génère 4000 exemples pour être large
    examples = generate_dataset(4000)
    
    # Save source
    full_path = source_dir / "full_dataset.jsonl"
    with open(full_path, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
            
    # L'utilisateur a demandé au moins 1000 lignes pour train, eval, test.
    # On a 4000 lignes, on peut faire un split 2000 train / 1000 eval / 1000 test
    # 50% train, 25% eval, 25% test
    train_data, temp_data = train_test_split(examples, test_size=0.5, random_state=42)
    val_data, test_data = train_test_split(temp_data, test_size=0.5, random_state=42)
    
    for name, data in [("train", train_data), ("eval", val_data), ("test", test_data)]:
        path = splits_dir / f"{name}.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for ex in data:
                f.write(json.dumps(ex, ensure_ascii=False) + "\n")
                
        # Format for Liquid (just the messages)
        liquid_path = liquid_dir / f"liquid_{name}.jsonl"
        with open(liquid_path, "w", encoding="utf-8") as f:
            for ex in data:
                f.write(json.dumps({"messages": ex["messages"]}, ensure_ascii=False) + "\n")
                
    print(f"Dataset construit avec succès !")
    print(f"- Total: {len(examples)} exemples")
    print(f"- Train: {len(train_data)} exemples")
    print(f"- Eval : {len(val_data)} exemples")
    print(f"- Test : {len(test_data)} exemples")

if __name__ == "__main__":
    main()
