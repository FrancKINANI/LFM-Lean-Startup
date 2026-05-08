import os
import logging
from pathlib import Path
from src.database.client import get_connection

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_seeds():
    """
    Lit et exécute les fichiers SQL de seeds dans le bon ordre.
    Cette méthode est préférée à l'exécution directe du .sql via psql
    car elle permet d'utiliser les credentials définis dans le .env
    via le client Python.
    """
    root = Path(__file__).parent.parent.parent
    seeds_dir = root / "database" / "seeds"
    
    # Ordre d'exécution recommandé
    seed_files = [
        "lean_concepts.sql",
        "risk_patterns.sql",
        "sector_benchmarks.sql",
        "investment_criteria.sql"
    ]
    
    logger.info("Début de l'initialisation des données (seeds)...")
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            for seed_file in seed_files:
                path = seeds_dir / seed_file
                if not path.exists():
                    logger.warning(f"Fichier de seed manquant : {path}")
                    continue
                
                logger.info(f"Exécution de {seed_file}...")
                with open(path, "r", encoding="utf-8") as f:
                    sql_content = f.read()
                    
                try:
                    # On exécute le contenu complet du fichier
                    # Note: Les fichiers de seeds contiennent généralement des INSERT multiples
                    cur.execute(sql_content)
                    logger.info(f"✅ {seed_file} exécuté avec succès.")
                except Exception as e:
                    logger.error(f"❌ Erreur lors de l'exécution de {seed_file} : {e}")
                    conn.rollback()
                    raise e

    logger.info("============================================================")
    logger.info("Base de données initialisée avec succès.")
    logger.info("============================================================")

if __name__ == "__main__":
    run_seeds()
