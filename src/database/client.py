"""
src/database/client.py
======================
Couche de connexion PostgreSQL.

Responsabilités :
- Gérer le pool de connexions (thread-safe)
- Lire la configuration depuis les variables d'environnement
- Fournir un context manager propre pour chaque opération
- Exposer une interface unique utilisée par queries.py et tool_executor.py

Dépendances :
    pip install psycopg2-binary python-dotenv
"""

import os
import logging
from contextlib import contextmanager
from typing import Any, Generator

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# Toutes les valeurs viennent des variables d'environnement (.env)
# Voir .env.example à la racine du projet
# =============================================================================

class DatabaseConfig:
    """
    Centralise la configuration de connexion.
    Toutes les valeurs ont des defaults sécurisés pour le développement local.
    """
    host:     str = os.getenv("POSTGRES_HOST",     "localhost")
    port:     int = int(os.getenv("POSTGRES_PORT", "5432"))
    database: str = os.getenv("POSTGRES_DB",       "lfm_lean_startup")
    user:     str = os.getenv("POSTGRES_USER",     "postgres")
    password: str = os.getenv("POSTGRES_PASSWORD", "")

    pool_min: int = int(os.getenv("POSTGRES_POOL_MIN", "2"))
    pool_max: int = int(os.getenv("POSTGRES_POOL_MAX", "10"))

    @classmethod
    def dsn(cls) -> str:
        return (
            f"host={cls.host} "
            f"port={cls.port} "
            f"dbname={cls.database} "
            f"user={cls.user} "
            f"password={cls.password}"
        )


# =============================================================================
# POOL DE CONNEXIONS — Singleton thread-safe
# ThreadedConnectionPool est requis car Airflow exécute les tâches
# dans des threads parallèles
# =============================================================================

class _ConnectionPool:
    _instance: "psycopg2.pool.ThreadedConnectionPool | None" = None

    @classmethod
    def get(cls) -> "psycopg2.pool.ThreadedConnectionPool":
        """Retourne le pool, l'initialise si nécessaire (lazy init)."""
        if cls._instance is None:
            cls._initialize()
        return cls._instance  # type: ignore[return-value]

    @classmethod
    def _initialize(cls) -> None:
        try:
            cls._instance = psycopg2.pool.ThreadedConnectionPool(
                minconn=DatabaseConfig.pool_min,
                maxconn=DatabaseConfig.pool_max,
                dsn=DatabaseConfig.dsn(),
            )
            logger.info(
                "Pool PostgreSQL initialisé — %s:%s/%s (pool: %d-%d)",
                DatabaseConfig.host,
                DatabaseConfig.port,
                DatabaseConfig.database,
                DatabaseConfig.pool_min,
                DatabaseConfig.pool_max,
            )
        except psycopg2.OperationalError as e:
            logger.error("Impossible de se connecter à PostgreSQL : %s", e)
            raise

    @classmethod
    def close(cls) -> None:
        """Ferme toutes les connexions. Appeler en fin de processus."""
        if cls._instance is not None:
            cls._instance.closeall()
            cls._instance = None
            logger.info("Pool PostgreSQL fermé.")


# =============================================================================
# INTERFACE PUBLIQUE
# =============================================================================

@contextmanager
def get_connection() -> Generator[psycopg2.extensions.connection, None, None]:
    """
    Context manager qui emprunte une connexion du pool et la restitue
    proprement — commit si succès, rollback si exception.

    Usage :
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    """
    connection = _ConnectionPool.get().getconn()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        _ConnectionPool.get().putconn(connection)


def execute_query(
    sql: str,
    params: tuple | None = None,
    fetch: str = "all",
) -> list[dict[str, Any]] | dict[str, Any] | None:
    """
    Exécute une requête SQL et retourne les résultats sous forme de dicts.

    RealDictCursor retourne {colonne: valeur} plutôt que des tuples —
    format directement utilisable par le LLM dans ses tool results.

    Args:
        sql    : Requête SQL à exécuter.
        params : Paramètres positionnels (%s). Toujours utiliser des params
                 plutôt que la f-string pour éviter les injections SQL.
        fetch  : "all"  → liste de tous les résultats
                 "one"  → premier résultat uniquement
                 "none" → pas de résultat (INSERT, UPDATE, DELETE)

    Returns:
        list[dict] | dict | None selon le mode fetch.

    Example :
        rows = execute_query(
            "SELECT * FROM risk_patterns WHERE sector = %s AND stage = %s",
            params=("marketplace", "pre-seed"),
            fetch="all"
        )
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            try:
                cur.execute(sql, params)
                logger.debug("SQL exécuté : %s | params : %s", sql[:120], params)

                if fetch == "all":
                    return [dict(row) for row in cur.fetchall()]
                elif fetch == "one":
                    row = cur.fetchone()
                    return dict(row) if row else None
                else:
                    return None

            except psycopg2.Error as e:
                logger.error(
                    "Erreur SQL : %s\nRequête : %s\nParams : %s",
                    e, sql, params
                )
                raise


def execute_safe_tool_query(
    sql: str,
    max_rows: int = 20,
) -> list[dict[str, Any]]:
    """
    Version sécurisée d'execute_query pour les tool calls générés par le LLM.

    Trois protections ajoutées par rapport à execute_query() :

    1. WHITELIST SELECT uniquement : refuse toute requête INSERT/UPDATE/DELETE/DROP.
       Un LLM peut générer n'importe quel SQL — on ne lui fait pas confiance
       aveuglément sur les opérations d'écriture.

    2. LIMITE AUTOMATIQUE : injecte LIMIT max_rows si absent.
       Empêche le LLM de dumper toute la table par accident.

    3. AUDIT LOG : logue toutes les requêtes du modèle pour traçabilité.

    Args:
        sql      : Requête SQL générée par le LLM.
        max_rows : Nombre maximum de lignes (défaut : 20).

    Raises:
        ValueError si la requête n'est pas un SELECT ou WITH.
    """
    normalized = sql.strip().upper()

    # Protection 1 : SELECT/WITH uniquement
    if not (normalized.startswith("SELECT") or normalized.startswith("WITH")):
        raise ValueError(
            f"Seules les requêtes SELECT sont autorisées via le tool use. "
            f"Requête reçue : {sql[:100]}"
        )

    # Protection 2 : injection automatique de la limite
    if "LIMIT" not in normalized:
        sql = f"{sql.rstrip(';')} LIMIT {max_rows}"

    # Protection 3 : audit
    logger.info("[TOOL_CALL] %s", sql[:300])

    return execute_query(sql, fetch="all")  # type: ignore[return-value]


def health_check() -> dict[str, Any]:
    """
    Vérifie la connectivité à la base.
    Utilisé par les DAGs Airflow avant chaque exécution.

    Returns:
        {"status": "ok", "database": "...", "version": "..."}
        {"status": "error", "message": "..."}
    """
    try:
        result = execute_query(
            "SELECT version(), current_database() AS database",
            fetch="one"
        )
        return {
            "status": "ok",
            "database": result["database"],   # type: ignore[index]
            "version": result["version"],     # type: ignore[index]
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}