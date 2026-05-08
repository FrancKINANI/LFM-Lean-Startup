import json
from pathlib import Path
from collections import Counter

def main():
    """Analyse le dataset et génère un rapport de métriques en Markdown."""
    root = Path(__file__).parent.parent.parent
    source_file = root / "data" / "source" / "full_dataset.jsonl"
    report_file = root / "src" / "data" / "reports" / "metrics_lean.md"
    
    if not source_file.exists():
        print(f"Error: {source_file} not found.")
        return

    examples = []
    with open(source_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                examples.append(json.loads(line))
                
    total_count = len(examples)
    if total_count == 0:
        print("Dataset is empty.")
        return

    categories = [ex.get("category", "unknown") for ex in examples]
    cat_counts = Counter(categories)
    
    # Calculate stats
    msg_lengths = []
    for ex in examples:
        content_len = sum(len(m["content"]) for m in ex["messages"])
        msg_lengths.append(content_len)
        
    avg_len = sum(msg_lengths) / total_count
    
    # Generate Markdown Report
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("# 📊 Rapport de Métriques du Dataset\n\n")
        f.write(f"**Nombre total d'exemples :** {total_count}\n\n")
        
        f.write("## 🗂️ Distribution par Catégorie\n\n")
        f.write("| Catégorie | Nombre | Pourcentage |\n")
        f.write("| :--- | :---: | :---: |\n")
        # Tri par nombre décroissant
        for cat, count in cat_counts.most_common():
            pct = (count / total_count) * 100
            f.write(f"| {cat.capitalize()} | {count} | {pct:.1f}% |\n")
        
        f.write("\n## 📏 Statistiques de Contenu\n\n")
        f.write(f"- **Longueur moyenne des messages (caractères) :** {avg_len:.1f}\n")
        f.write(f"- **Exemple le plus court :** {min(msg_lengths)} caractères\n")
        f.write(f"- **Exemple le plus long :** {max(msg_lengths)} caractères\n")
        
        f.write("\n## 🧪 Échantillon (Dernier message assistant)\n\n")
        sample = examples[0]
        f.write(f"**Catégorie :** {sample['category']}\n\n")
        f.write("```text\n")
        f.write(sample["messages"][-1]["content"])
        f.write("\n```\n")

    print(f"Metrics report generated: {report_file}")

if __name__ == "__main__":
    main()
