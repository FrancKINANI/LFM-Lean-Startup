import json
import os
from pathlib import Path
from sklearn.model_selection import train_test_split

def generate_examples():
    """Génère des exemples synthétiques pour l'analyste Lean Startup."""
    examples = []
    
    # Category 1: Diagnostic complet (35%)
    diag_examples = [
        {
            "category": "diagnostic",
            "messages": [
                {"role": "system", "content": "Tu es un analyste Lean Startup expert. Tu identifies les forces, faiblesses et dangers d'un projet."},
                {"role": "user", "content": "Analyse du projet : 'FreshDrop', une application de livraison de produits locaux en 30 minutes. 500 utilisateurs actifs, panier moyen 25€. L'équipe veut lever 2M€ pour acheter une flotte de camions électriques."},
                {"role": "assistant", "content": "## Analyse de FreshDrop\n\n### Forces\n- **Traction initiale** : 500 utilisateurs actifs avec un panier moyen correct (25€).\n- **Alignement marché** : Demande pour le local et l'écologie.\n\n### Faiblesses\n- **Modèle Asset-Heavy** : L'achat d'une flotte de camions est risqué au stade early-stage.\n- **Logistique complexe** : La promesse des 30 minutes est difficile à tenir sans micro-hubs coûteux.\n\n### Dangers\n- **Brûlure de cash (Burn rate)** : L'investissement massif dans le matériel peut tuer la startup avant le Product-Market Fit.\n- **Unité de rentabilité (Unit Economics)** : Risque de perte sur chaque livraison à cause des coûts opérationnels."}
            ]
        },
        {
            "category": "diagnostic",
            "messages": [
                {"role": "system", "content": "Tu es un analyste Lean Startup expert. Tu identifies les forces, faiblesses et dangers d'un projet."},
                {"role": "user", "content": "Projet : 'EduAI', plateforme de tutorat IA pour lycéens. 2000 inscrits, mais seulement 50 utilisent l'outil plus d'une fois par semaine. L'équipe se concentre sur l'ajout de nouvelles fonctionnalités de gamification."},
                {"role": "assistant", "content": "## Analyse de EduAI\n\n### Forces\n- **Acquisition** : Bonne capacité à attirer des inscrits (2000).\n- **Secteur porteur** : L'IA dans l'éducation est en pleine explosion.\n\n### Faiblesses\n- **Rétention (Engagement)** : Très faible (2.5%). Le produit ne semble pas encore indispensable.\n- **Focus éparpillé** : Ajouter de la gamification avant d'avoir résolu le problème de valeur fondamentale est une erreur classique.\n\n### Dangers\n- **Produit 'Leaky Bucket'** : Vous dépensez de l'énergie pour remplir un seau percé. Sans rétention, la croissance est impossible.\n- **Solution en quête de problème** : L'IA est peut-être un gadget ici plutôt qu'une solution à un vrai 'pain point'."}
            ]
        }
    ]
    
    # Category 2: Identification des dangers (25%)
    danger_examples = [
        {
            "category": "dangers",
            "messages": [
                {"role": "system", "content": "Tu es un expert en gestion de risques Lean Startup. Liste les dangers critiques simplement."},
                {"role": "user", "content": "Quels sont les risques pour un SaaS B2B qui a beaucoup d'utilisateurs gratuits mais aucun payant après 6 mois ?"},
                {"role": "assistant", "content": "Voici les dangers critiques :\n1. **Vanity Metrics** : Vos 1000 utilisateurs gratuits vous donnent l'illusion du succès, mais ils ne valident pas la valeur économique.\n2. **Manque de Willingness-to-Pay** : Votre produit est peut-être 'nice to have' mais pas 'must have'.\n3. **Pivot tardif** : Vous risquez d'épuiser vos ressources sur la mauvaise cible."}
            ]
        },
        {
            "category": "dangers",
            "messages": [
                {"role": "system", "content": "Tu es un expert en gestion de risques Lean Startup. Liste les dangers critiques simplement."},
                {"role": "user", "content": "On a une équipe de 10 développeurs qui travaillent sur le produit depuis 1 an sans avoir montré une seule version à un client potentiel. On attend que tout soit parfait."},
                {"role": "assistant", "content": "C'est une situation de **danger extrême** :\n1. **Effet Tunnel** : Vous construisez quelque chose dont personne ne veut peut-être.\n2. **Coût d'opportunité** : Un an de salaire pour 10 personnes sans validation est un gaspillage immense.\n3. **Peur du feedback** : L'attente de la perfection cache souvent une peur de confronter la réalité du marché."}
            ]
        }
    ]
    
    # Category 3: Évaluation d'investissement (25%)
    invest_examples = [
        {
            "category": "investissement",
            "messages": [
                {"role": "system", "content": "Tu es un investisseur VC. Donne une recommandation go/no-go argumentée."},
                {"role": "user", "content": "Dossier : Marketplace de NFT pour l'immobilier. Équipe de 2 développeurs. Pas encore de clients. Demandent 500k€."},
                {"role": "assistant", "content": "### Recommandation : NO-GO\n\n**Arguments :**\n- **Marché saturé/descendant** : Le secteur NFT immobilier manque de clarté réglementaire et de demande réelle actuellement.\n- **Manque de validation** : Investir 500k€ sans une seule transaction ou lettre d'intention (LOI) est prématuré.\n- **Risque d'exécution** : L'équipe est purement technique, il manque un profil business/legal indispensable pour l'immobilier."}
            ]
        },
        {
            "category": "investissement",
            "messages": [
                {"role": "system", "content": "Tu es un investisseur VC. Donne une recommandation go/no-go argumentée."},
                {"role": "user", "content": "Startup 'CleanClean' : Service de nettoyage écologique pour bureaux. MRR de 15k€, croissance de 20% mois sur mois. Cherchent 200k€ pour recruter des commerciaux."},
                {"role": "assistant", "content": "### Recommandation : GO (Sous conditions)\n\n**Arguments :**\n- **Traction réelle** : Le MRR de 15k€ prouve qu'il y a un marché et une volonté de payer.\n- **Croissance saine** : 20% MoM est excellent pour un service de ce type.\n- **Utilisation des fonds** : Le recrutement de commerciaux pour scaler un modèle qui fonctionne est un usage logique du capital."}
            ]
        }
    ]
    
    # Category 4: Simplification de concept (15%)
    simple_examples = [
        {
            "category": "simplification",
            "messages": [
                {"role": "system", "content": "Tu es un mentor Lean Startup. Explique les concepts sans jargon."},
                {"role": "user", "content": "C'est quoi un 'Pivot' ?"},
                {"role": "assistant", "content": "Un **Pivot**, c'est comme changer de direction tout en gardant un pied ancré dans ce que vous avez appris. \n\nCe n'est pas un aveu d'échec, c'est une **correction de trajectoire**. Par exemple, vous réalisez que votre logiciel n'intéresse pas les grandes entreprises, mais que les petites associations l'adorent. Vous pivotez pour vous concentrer uniquement sur les associations."}
            ]
        },
        {
            "category": "simplification",
            "messages": [
                {"role": "system", "content": "Tu es un mentor Lean Startup. Explique les concepts sans jargon."},
                {"role": "user", "content": "Explique-moi le MVP (Minimum Viable Product)."},
                {"role": "assistant", "content": "Le **MVP**, c'est la version la plus simple de votre produit qui permet de commencer à apprendre. \n\nSi vous voulez construire une voiture, votre MVP n'est pas une roue, c'est une trottinette. Pourquoi ? Parce que la trottinette vous permet déjà de vous déplacer (la valeur principale) et de voir si les gens veulent vraiment aller d'un point A à un point B."}
            ]
        }
    ]

    # Mix and scale (for demo purposes we create 100 examples by repetition with shuffle)
    all_templates = diag_examples * 18 + danger_examples * 12 + invest_examples * 12 + simple_examples * 8
    # Total ~ 50 examples, adjusted to respect the percentages
    
    return all_templates

def main():
    # Setup paths
    root = Path(__file__).parent.parent.parent
    data_dir = root / "data"
    source_dir = data_dir / "source"
    splits_dir = data_dir / "splits"
    liquid_dir = data_dir / "liquid"
    
    for d in [source_dir, splits_dir, liquid_dir]:
        d.mkdir(parents=True, exist_ok=True)
        
    # Generate
    examples = generate_examples()
    
    # Save source
    full_path = source_dir / "full_dataset.jsonl"
    with open(full_path, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
            
    # Split (80% train, 10% eval, 10% test)
    train_data, temp_data = train_test_split(examples, test_size=0.2, random_state=42)
    val_data, test_data = train_test_split(temp_data, test_size=0.5, random_state=42)
    
    for name, data in [("train", train_data), ("eval", val_data), ("test", test_data)]:
        # Normal split
        path = splits_dir / f"{name}.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for ex in data:
                f.write(json.dumps(ex, ensure_ascii=False) + "\n")
                
        # Format for Liquid (just the messages)
        liquid_path = liquid_dir / f"liquid_{name}.jsonl"
        with open(liquid_path, "w", encoding="utf-8") as f:
            for ex in data:
                f.write(json.dumps({"messages": ex["messages"]}, ensure_ascii=False) + "\n")
                
    print(f"Dataset built successfully: {len(examples)} examples.")

if __name__ == "__main__":
    main()
