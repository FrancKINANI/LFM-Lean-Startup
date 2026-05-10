"""
src/inference/tool_executor.py
==============================
Interception et exécution des tool calls générés par LFM2.5.

Rôle dans le pipeline d'inférence :
    model génère du texte
        → tool_executor détecte les tool calls
        → extrait et valide les paramètres
        → exécute la requête SQL sur PostgreSQL
        → formate le résultat pour le retourner au modèle
        → le modèle génère la réponse finale

Format natif LFM2.5 :
    Les tool calls sont encapsulés entre deux tokens spéciaux :
        <|tool_call_start|>[query_postgresql(sql="SELECT ...")]<|tool_call_end|>

    La réponse est injectée dans le contexte avec le rôle "tool".

Ce module est le point de liaison critique entre le LLM et PostgreSQL.
Il doit être robuste, sécurisé et informatif en cas d'erreur.
"""

import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

import psycopg2

from src.database.client import execute_safe_tool_query

logger = logging.getLogger(__name__)

# =============================================================================
# TOKENS NATIFS LFM2.5
# =============================================================================

TOOL_CALL_START = "<|tool_call_start|>"
TOOL_CALL_END   = "<|tool_call_end|>"

# Pattern regex pour extraire le contenu entre les tokens
_TOOL_CALL_PATTERN = re.compile(
    re.escape(TOOL_CALL_START) + r"(.*?)" + re.escape(TOOL_CALL_END),
    re.DOTALL,
)

# Pattern pour extraire le nom de la fonction et ses arguments
# Supporte : query_postgresql(sql="SELECT ...")
_FUNCTION_PATTERN = re.compile(
    r'(\w+)\s*\(\s*sql\s*=\s*["\']?(.*?)["\']?\s*\)\s*$',
    re.DOTALL,
)


# =============================================================================
# STRUCTURES DE DONNÉES
# =============================================================================

@dataclass
class ToolCall:
    """Représente un appel d'outil extrait de la sortie du modèle."""
    function_name: str
    sql: str
    raw: str  # texte brut original entre les tokens


@dataclass
class ToolResult:
    """Résultat d'un tool call, prêt à être injecté dans le contexte du modèle."""
    success: bool
    data: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    row_count: int = 0
    execution_time_ms: float = 0.0

    def to_model_message(self) -> dict[str, str]:
        """
        Formate le résultat au format message attendu par LFM2.5.
        Ce message est injecté dans la conversation avec role="tool".
        """
        if self.success:
            content = json.dumps({
                "status": "success",
                "row_count": self.row_count,
                "execution_time_ms": round(self.execution_time_ms, 2),
                "data": self.data,
            }, ensure_ascii=False, indent=2)
        else:
            content = json.dumps({
                "status": "error",
                "error": self.error,
            }, ensure_ascii=False)

        return {"role": "tool", "content": content}


# =============================================================================
# REGISTRE DES OUTILS DISPONIBLES
# =============================================================================

# Seuls les outils listés ici peuvent être appelés.
# Clé = nom de la fonction que le modèle appelle
# Valeur = description utilisée dans le system prompt
AVAILABLE_TOOLS: dict[str, dict[str, Any]] = {
    "query_postgresql": {
        "name": "query_postgresql",
        "description": (
            "Interroge la base de données PostgreSQL contenant des cas de startups, "
            "des patterns de risque connus, des benchmarks sectoriels, des concepts "
            "Lean Startup et des critères d'investissement. "
            "Retourne les données structurées nécessaires pour enrichir l'analyse."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": (
                        "Requête SQL SELECT à exécuter. "
                        "Tables disponibles : startups, pivot_cases, risk_patterns, "
                        "sector_benchmarks, lean_concepts, investment_criteria. "
                        "Vues disponibles : v_critical_risks, v_benchmarks_with_context, "
                        "v_startups_with_pivot_count."
                    ),
                }
            },
            "required": ["sql"],
        },
    }
}


def build_tools_system_prompt() -> str:
    """
    Génère la section "List of tools" du system prompt au format LFM2.5.
    À injecter dans le system message lors de chaque appel d'inférence.

    Returns:
        Chaîne formatée prête à être ajoutée au system prompt.
    """
    tools_json = json.dumps(list(AVAILABLE_TOOLS.values()), ensure_ascii=False)
    return f"List of tools: {tools_json}"


# =============================================================================
# PARSING
# =============================================================================

def detect_tool_calls(model_output: str) -> list[ToolCall]:
    """
    Détecte et extrait tous les tool calls dans la sortie du modèle.

    Un modèle peut générer plusieurs tool calls dans une même réponse
    (ex: un pour les risques, un pour les benchmarks). On les traite tous.

    Args:
        model_output : Texte complet généré par le modèle.

    Returns:
        Liste de ToolCall extraits. Vide si aucun tool call détecté.
    """
    tool_calls = []

    for match in _TOOL_CALL_PATTERN.finditer(model_output):
        raw_content = match.group(1).strip()

        # Nettoyage : le modèle peut encapsuler dans des crochets [...]
        content = raw_content.strip("[]").strip()

        parsed = _parse_function_call(content)
        if parsed:
            tool_calls.append(parsed)
        else:
            logger.warning(
                "Tool call détecté mais non parseable : %s", raw_content[:200]
            )

    return tool_calls


def _parse_function_call(content: str) -> ToolCall | None:
    """
    Parse le contenu d'un tool call en ToolCall structuré.

    Supporte les formats :
        query_postgresql(sql="SELECT ...")
        query_postgresql(sql='SELECT ...')

    Args:
        content : Texte entre les tokens, sans les crochets.

    Returns:
        ToolCall si le parsing réussit, None sinon.
    """
    # Cas 1 : format JSON {"name": ..., "parameters": {"sql": ...}}
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            name = parsed.get("name", "")
            sql  = parsed.get("parameters", {}).get("sql", "")
            if name and sql:
                return ToolCall(function_name=name, sql=sql, raw=content)
    except json.JSONDecodeError:
        pass

    # Cas 2 : format function call query_postgresql(sql="...")
    fn_match = _FUNCTION_PATTERN.match(content.strip())
    if fn_match:
        name = fn_match.group(1)
        sql  = fn_match.group(2).strip()
        if name and sql:
            return ToolCall(function_name=name, sql=sql, raw=content)

    # Cas 3 : recherche du SQL directement si le format est non-standard
    sql_match = re.search(r'sql\s*=\s*["\']?(SELECT.*?)["\']?\s*$', content, re.DOTALL | re.IGNORECASE)
    if sql_match:
        sql = sql_match.group(1).strip()
        return ToolCall(function_name="query_postgresql", sql=sql, raw=content)

    return None


def has_tool_call(model_output: str) -> bool:
    """Retourne True si la sortie contient au moins un tool call."""
    return TOOL_CALL_START in model_output


def split_text_and_tool_calls(model_output: str) -> tuple[str, list[ToolCall]]:
    """
    Sépare le texte libre des tool calls dans la sortie du modèle.

    Utile quand le modèle génère du texte AVANT un tool call, ce qui
    est courant dans les scénarios multi-tour.

    Returns:
        (texte_avant_tool_calls, liste_de_tool_calls)
    """
    parts = _TOOL_CALL_PATTERN.split(model_output)
    text_parts = []

    for i, part in enumerate(parts):
        if i % 2 == 0:  # parties paires = texte libre
            text_parts.append(part.strip())

    text = " ".join(t for t in text_parts if t)
    tool_calls = detect_tool_calls(model_output)

    return text, tool_calls


# =============================================================================
# EXÉCUTION
# =============================================================================

def execute_tool_call(tool_call: ToolCall) -> ToolResult:
    """
    Exécute un tool call et retourne le résultat.

    Trois couches de protection :
    1. Whitelist : seule query_postgresql est autorisée.
    2. execute_safe_tool_query : SELECT only + limite automatique.
    3. Try/except : toute erreur SQL est capturée et retournée proprement.

    Args:
        tool_call : ToolCall extrait de la sortie du modèle.

    Returns:
        ToolResult avec les données ou l'erreur.
    """
    # Protection 1 : vérifier que l'outil est dans le registre
    if tool_call.function_name not in AVAILABLE_TOOLS:
        logger.error(
            "Outil non autorisé appelé par le modèle : %s",
            tool_call.function_name
        )
        return ToolResult(
            success=False,
            error=f"Outil '{tool_call.function_name}' non disponible. "
                  f"Outils disponibles : {list(AVAILABLE_TOOLS.keys())}",
        )

    if not tool_call.sql:
        return ToolResult(
            success=False,
            error="Paramètre 'sql' vide ou absent dans le tool call.",
        )

    # Exécution avec mesure du temps
    start = time.perf_counter()
    try:
        rows = execute_safe_tool_query(sql=tool_call.sql)
        elapsed_ms = (time.perf_counter() - start) * 1000

        logger.info(
            "Tool call exécuté avec succès — %d ligne(s) en %.1f ms",
            len(rows), elapsed_ms
        )

        return ToolResult(
            success=True,
            data=rows,
            row_count=len(rows),
            execution_time_ms=elapsed_ms,
        )

    except ValueError as e:
        # Requête non-SELECT rejetée par execute_safe_tool_query
        logger.warning("Tool call rejeté (non-SELECT) : %s", e)
        return ToolResult(success=False, error=str(e))

    except psycopg2.Error as e:
        # Erreur SQL (table inexistante, syntaxe, etc.)
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.error("Erreur SQL dans le tool call : %s", e)
        return ToolResult(
            success=False,
            error=f"Erreur SQL : {str(e)[:300]}",
            execution_time_ms=elapsed_ms,
        )

    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.error("Erreur inattendue dans le tool call : %s", e)
        return ToolResult(
            success=False,
            error=f"Erreur interne : {str(e)[:300]}",
            execution_time_ms=elapsed_ms,
        )


def execute_all_tool_calls(tool_calls: list[ToolCall]) -> list[ToolResult]:
    """
    Exécute une liste de tool calls séquentiellement.
    Retourne un résultat par tool call, dans le même ordre.

    Args:
        tool_calls : Liste de ToolCall à exécuter.

    Returns:
        Liste de ToolResult correspondants.
    """
    results = []
    for i, tc in enumerate(tool_calls):
        logger.debug(
            "Exécution du tool call %d/%d : %s",
            i + 1, len(tool_calls), tc.sql[:100]
        )
        result = execute_tool_call(tc)
        results.append(result)
    return results


# =============================================================================
# FORMATAGE POUR LE CONTEXTE DU MODÈLE
# =============================================================================

def build_tool_messages(
    tool_calls: list[ToolCall],
    results: list[ToolResult],
) -> list[dict[str, str]]:
    """
    Construit les messages "tool" à injecter dans la conversation
    après l'exécution des tool calls.

    Ces messages sont ajoutés à l'historique de la conversation
    avant de rappeler le modèle pour la réponse finale.

    Args:
        tool_calls : Tool calls exécutés.
        results    : Résultats correspondants.

    Returns:
        Liste de messages au format {"role": "tool", "content": "..."}
    """
    messages = []
    for tool_call, result in zip(tool_calls, results):
        msg = result.to_model_message()

        # Ajout des métadonnées de traçabilité dans le contenu
        payload = json.loads(msg["content"])
        payload["_tool_call_sql"] = tool_call.sql[:200]
        msg["content"] = json.dumps(payload, ensure_ascii=False, indent=2)

        messages.append(msg)

    return messages


def format_results_for_context(results: list[ToolResult]) -> str:
    """
    Formatte les résultats de plusieurs tool calls en un bloc de texte
    lisible, pour les pipelines qui préfèrent injecter un résumé en prose
    plutôt que du JSON brut dans le contexte.

    Args:
        results : Liste de ToolResult.

    Returns:
        Texte structuré résumant les données récupérées.
    """
    if not results:
        return ""

    sections = []
    for i, result in enumerate(results, 1):
        if result.success and result.data:
            section = f"[Données récupérées {i}/{len(results)} — {result.row_count} résultat(s)]\n"
            section += json.dumps(result.data, ensure_ascii=False, indent=2)
        elif not result.success:
            section = f"[Erreur requête {i}/{len(results)}]\n{result.error}"
        else:
            section = f"[Requête {i}/{len(results)} — aucun résultat]"

        sections.append(section)

    return "\n\n".join(sections)
