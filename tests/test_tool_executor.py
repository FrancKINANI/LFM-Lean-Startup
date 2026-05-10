"""
tests/test_tool_executor.py
============================
Tests unitaires pour src/inference/tool_executor.py.

Stratégie :
    - Tests de parsing : valider la détection et l'extraction des tool calls
    - Tests de sécurité : valider les protections (SELECT only, whitelist)
    - Tests de formatage : valider les messages retournés au modèle
    - Mocks PostgreSQL : aucune vraie connexion BDD dans ces tests

Lancer :
    pytest tests/test_tool_executor.py -v
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.inference.tool_executor import (
    TOOL_CALL_END,
    TOOL_CALL_START,
    ToolCall,
    ToolResult,
    build_tool_messages,
    build_tools_system_prompt,
    detect_tool_calls,
    execute_tool_call,
    format_results_for_context,
    has_tool_call,
    split_text_and_tool_calls,
)


# =============================================================================
# HELPERS DE TEST
# =============================================================================

def wrap_tool_call(content: str) -> str:
    """Encapsule du contenu dans les tokens LFM2.5."""
    return f"{TOOL_CALL_START}[{content}]{TOOL_CALL_END}"


def make_tool_call(sql: str) -> str:
    """Crée un tool call complet au format LFM2.5."""
    return wrap_tool_call(f'query_postgresql(sql="{sql}")')


# =============================================================================
# TESTS — DÉTECTION DES TOOL CALLS
# =============================================================================

class TestDetection:
    """Tests sur has_tool_call() et detect_tool_calls()."""

    def test_detects_tool_call_present(self):
        output = make_tool_call("SELECT 1")
        assert has_tool_call(output) is True

    def test_no_tool_call_in_plain_text(self):
        output = "Voici mon analyse de la startup : elle a un problème de churn."
        assert has_tool_call(output) is False

    def test_empty_string(self):
        assert has_tool_call("") is False

    def test_detects_multiple_tool_calls(self):
        output = (
            make_tool_call("SELECT * FROM risk_patterns LIMIT 5")
            + "\n"
            + make_tool_call("SELECT * FROM sector_benchmarks WHERE sector='saas'")
        )
        calls = detect_tool_calls(output)
        assert len(calls) == 2, f"Attendu 2 tool calls, détecté {len(calls)}."

    def test_detects_single_tool_call(self):
        output = make_tool_call("SELECT * FROM lean_concepts WHERE concept_name ILIKE '%MVP%'")
        calls = detect_tool_calls(output)
        assert len(calls) == 1

    def test_no_calls_in_plain_text(self):
        calls = detect_tool_calls("Pas de tool call ici.")
        assert calls == []


# =============================================================================
# TESTS — PARSING DES TOOL CALLS
# =============================================================================

class TestParsing:
    """Tests sur l'extraction des paramètres des tool calls."""

    def test_parses_function_name(self):
        output = make_tool_call("SELECT * FROM risk_patterns")
        calls = detect_tool_calls(output)
        assert calls[0].function_name == "query_postgresql"

    def test_parses_sql_parameter(self):
        sql = "SELECT * FROM risk_patterns WHERE sector = 'marketplace'"
        output = make_tool_call(sql)
        calls = detect_tool_calls(output)
        assert sql in calls[0].sql, f"SQL mal parsé : '{calls[0].sql}'"

    def test_parses_multiline_sql(self):
        sql = """SELECT pattern_name, criticality
FROM risk_patterns
WHERE sector = 'saas'
ORDER BY criticality DESC
LIMIT 5"""
        output = f"{TOOL_CALL_START}[query_postgresql(sql=\"{sql}\")]{TOOL_CALL_END}"
        calls = detect_tool_calls(output)
        assert len(calls) == 1
        assert "risk_patterns" in calls[0].sql

    def test_raw_field_preserved(self):
        """Le champ raw conserve le texte brut original."""
        sql = "SELECT 1"
        output = make_tool_call(sql)
        calls = detect_tool_calls(output)
        assert calls[0].raw is not None and len(calls[0].raw) > 0

    def test_split_text_and_tool_calls(self):
        """split_text_and_tool_calls sépare correctement le texte des tool calls."""
        text_before = "Je vais interroger la base de données."
        tc = make_tool_call("SELECT * FROM startups LIMIT 3")
        output = text_before + "\n" + tc

        text, calls = split_text_and_tool_calls(output)

        assert len(calls) == 1
        assert "Je vais interroger" in text

    def test_split_no_tool_call(self):
        """Sans tool call, le texte est retourné intact et calls est vide."""
        output = "Voici une réponse sans tool call."
        text, calls = split_text_and_tool_calls(output)
        assert calls == []
        assert "sans tool call" in text


# =============================================================================
# TESTS — SÉCURITÉ DE L'EXÉCUTION
# =============================================================================

class TestSecurity:
    """Tests sur les protections d'execute_tool_call et execute_safe_tool_query."""

    def test_rejects_unknown_tool_name(self):
        """Un outil non dans le registre est rejeté."""
        bad_call = ToolCall(
            function_name="drop_table",
            sql="DROP TABLE startups",
            raw="",
        )
        result = execute_tool_call(bad_call)
        assert result.success is False
        assert "non disponible" in result.error.lower() or "autorisé" in result.error.lower()

    def test_rejects_empty_sql(self):
        """Un tool call avec SQL vide est rejeté."""
        bad_call = ToolCall(
            function_name="query_postgresql",
            sql="",
            raw="",
        )
        result = execute_tool_call(bad_call)
        assert result.success is False

    def test_execute_safe_tool_query_rejects_insert(self):
        """execute_safe_tool_query rejette les requêtes non-SELECT."""
        from src.database.client import execute_safe_tool_query
        with pytest.raises(ValueError, match="SELECT"):
            execute_safe_tool_query("INSERT INTO startups (name) VALUES ('test')")

    def test_execute_safe_tool_query_rejects_delete(self):
        from src.database.client import execute_safe_tool_query
        with pytest.raises(ValueError):
            execute_safe_tool_query("DELETE FROM risk_patterns")

    def test_execute_safe_tool_query_rejects_drop(self):
        from src.database.client import execute_safe_tool_query
        with pytest.raises(ValueError):
            execute_safe_tool_query("DROP TABLE startups")

    def test_execute_safe_tool_query_rejects_update(self):
        from src.database.client import execute_safe_tool_query
        with pytest.raises(ValueError):
            execute_safe_tool_query("UPDATE startups SET name='hack' WHERE 1=1")


# =============================================================================
# TESTS — EXÉCUTION AVEC MOCK POSTGRESQL
# =============================================================================

class TestExecution:
    """Tests sur execute_tool_call avec PostgreSQL mocké."""

    @patch("src.inference.tool_executor.execute_safe_tool_query")
    def test_successful_execution(self, mock_query):
        """Un tool call valide retourne un ToolResult avec success=True."""
        mock_query.return_value = [
            {"pattern_name": "Cold Start Problem", "criticality": "critical"}
        ]

        call = ToolCall(
            function_name="query_postgresql",
            sql="SELECT * FROM risk_patterns WHERE sector='marketplace'",
            raw="",
        )
        result = execute_tool_call(call)

        assert result.success is True
        assert result.row_count == 1
        assert result.data[0]["pattern_name"] == "Cold Start Problem"

    @patch("src.inference.tool_executor.execute_safe_tool_query")
    def test_empty_result_is_success(self, mock_query):
        """Un résultat vide est un succès (pas d'erreur SQL)."""
        mock_query.return_value = []

        call = ToolCall(
            function_name="query_postgresql",
            sql="SELECT * FROM startups WHERE sector='inexistant'",
            raw="",
        )
        result = execute_tool_call(call)

        assert result.success is True
        assert result.row_count == 0
        assert result.data == []

    @patch("src.inference.tool_executor.execute_safe_tool_query")
    def test_sql_error_returns_failure(self, mock_query):
        """Une erreur SQL retourne un ToolResult avec success=False."""
        import psycopg2
        mock_query.side_effect = psycopg2.Error("relation does not exist")

        call = ToolCall(
            function_name="query_postgresql",
            sql="SELECT * FROM table_inexistante",
            raw="",
        )
        result = execute_tool_call(call)

        assert result.success is False
        assert result.error is not None


# =============================================================================
# TESTS — FORMATAGE DES RÉSULTATS
# =============================================================================

class TestFormatting:
    """Tests sur le formatage des résultats pour le modèle."""

    def test_tool_result_to_model_message_success(self):
        """Un ToolResult réussi produit un message JSON valide."""
        result = ToolResult(
            success=True,
            data=[{"key": "value"}],
            row_count=1,
            execution_time_ms=12.5,
        )
        msg = result.to_model_message()

        assert msg["role"] == "tool"
        parsed = json.loads(msg["content"])
        assert parsed["status"] == "success"
        assert parsed["row_count"] == 1

    def test_tool_result_to_model_message_error(self):
        """Un ToolResult en erreur produit un message avec status=error."""
        result = ToolResult(
            success=False,
            error="Erreur SQL : table inexistante",
        )
        msg = result.to_model_message()

        parsed = json.loads(msg["content"])
        assert parsed["status"] == "error"
        assert "Erreur SQL" in parsed["error"]

    def test_build_tool_messages_count(self):
        """build_tool_messages retourne autant de messages que de tool calls."""
        calls = [
            ToolCall("query_postgresql", "SELECT 1", ""),
            ToolCall("query_postgresql", "SELECT 2", ""),
        ]
        results = [
            ToolResult(success=True, data=[], row_count=0),
            ToolResult(success=True, data=[{"x": 1}], row_count=1),
        ]
        messages = build_tool_messages(calls, results)
        assert len(messages) == 2

    def test_format_results_for_context_success(self):
        """format_results_for_context produit un texte non vide avec des données."""
        results = [
            ToolResult(success=True, data=[{"pattern": "Cold Start"}], row_count=1),
        ]
        text = format_results_for_context(results)
        assert "Cold Start" in text
        assert len(text) > 10

    def test_format_results_for_context_empty(self):
        """format_results_for_context retourne une chaîne vide si aucun résultat."""
        text = format_results_for_context([])
        assert text == ""

    def test_build_tools_system_prompt_contains_tool_name(self):
        """Le system prompt contient le nom de l'outil query_postgresql."""
        prompt = build_tools_system_prompt()
        assert "query_postgresql" in prompt

    def test_build_tools_system_prompt_is_valid_json_embedded(self):
        """La section List of tools contient du JSON valide."""
        import re
        prompt = build_tools_system_prompt()
        # Extraire le JSON après "List of tools: "
        match = re.search(r"List of tools: (\[.*\])", prompt, re.DOTALL)
        assert match, "Section 'List of tools' introuvable dans le system prompt."
        tools = json.loads(match.group(1))
        assert isinstance(tools, list) and len(tools) > 0
