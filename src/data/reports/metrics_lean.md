# Dataset Metrics Report - LFM Lean Startup

Source: `/home/franck/Documents/01_Cours/Data/IA/Projets/efm/NLP/LFM-Lean-Startup-Project/data/source/full_dataset.jsonl`
Statut: **OK**

## Vue d'ensemble

| Métrique | Valeur |
|---|---:|
| Total exemples | 5200 |
| Tool use | 1849 (35.6%) |
| Implicite/Ambigu/Mixte | 59.9% |
| Messages moyens | 3.7 |
| Caractères moyens | 999 |
| Min / Max caractères | 522 / 1896 |
| Doublons exacts | 0 |
| Prompts utilisateurs proches/exacts | 113 |

## Distribution par catégorie

| Valeur | Nombre | Ratio |
|---|---:|---:|
| diagnostic_complet | 1664 | 32.0% |
| evaluation_investissement | 1456 | 28.0% |
| identification_des_dangers | 1300 | 25.0% |
| simplification_concept | 780 | 15.0% |

## Distribution par Label

| Valeur | Nombre | Ratio |
|---|---:|---:|
| Red Flag | 2505 | 48.2% |
| Green Flag | 1923 | 37.0% |
| Mixed | 772 | 14.8% |

## Distribution par Severity

| Valeur | Nombre | Ratio |
|---|---:|---:|
| Non applicable | 1923 | 37.0% |
| Majeur | 1792 | 34.5% |
| Fatal | 1223 | 23.5% |
| Mineur | 262 | 5.0% |

## Distribution par Difficulty

| Valeur | Nombre | Ratio |
|---|---:|---:|
| Explicite | 2087 | 40.1% |
| Implicite | 1657 | 31.9% |
| Ambigu | 799 | 15.4% |
| Mixte | 657 | 12.6% |

## Distribution par principe Lean

| Valeur | Nombre | Ratio |
|---|---:|---:|
| Build-Measure-Learn | 851 | 16.4% |
| Customer Discovery | 667 | 12.8% |
| Métriques actionnables | 644 | 12.4% |
| Validation du marché | 611 | 11.8% |
| Réduction du risque systémique | 477 | 9.2% |
| Runway avant scale | 447 | 8.6% |
| Unit economics avant croissance | 446 | 8.6% |
| Apprentissage validé | 394 | 7.6% |
| Validation par usage répété | 251 | 4.8% |
| Problem-Solution Fit | 210 | 4.0% |
| Moteur de croissance | 202 | 3.9% |

## Distribution par secteur

| Valeur | Nombre | Ratio |
|---|---:|---:|
| universal | 780 | 15.0% |
| Fintech | 331 | 6.4% |
| Insurtech | 325 | 6.2% |
| E-commerce | 311 | 6.0% |
| Marketplace | 309 | 5.9% |
| Agritech | 307 | 5.9% |
| Cleantech | 305 | 5.9% |
| Adtech | 296 | 5.7% |
| Logistique | 296 | 5.7% |
| Proptech | 290 | 5.6% |
| Edtech | 288 | 5.5% |
| Web3 | 282 | 5.4% |
| SaaS B2B | 277 | 5.3% |
| Foodtech | 274 | 5.3% |
| Deeptech | 271 | 5.2% |
| Healthtech | 258 | 5.0% |

## Recommandation

- Dataset validé pour un premier fine-tuning LoRA-SFT.
- Garder `hard_eval` séparé pour mesurer la généralisation sur les cas ambigus.

---

Rapport généré par `src/data/report_dataset_metrics.py`.