"""
src/database
============
Couche d'accès à PostgreSQL.

Exports principaux :
    - execute_query            : requête SQL typée avec paramètres
    - execute_safe_tool_query  : requête SQL sécurisée pour les tool calls du LLM
    - health_check             : vérification de la connectivité
    - get_connection           : context manager de connexion brute
    - queries                  : module de requêtes nommées

Usage :
    from src.database import execute_safe_tool_query
    from src.database import queries
"""

from src.database.client import (
    execute_query,
    execute_safe_tool_query,
    health_check,
    get_connection,
)

__all__ = [
    "execute_query",
    "execute_safe_tool_query",
    "health_check",
    "get_connection",
]
