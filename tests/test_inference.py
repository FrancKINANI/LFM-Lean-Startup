"""
tests/test_inference.py
========================
Tests d'intégration pour src/inference/pipeline.py.

Stratégie :
    - Mock du modèle LFM2.5 (évite de charger 700Mo de poids en test)
    - Tests du flux pipeline complet (prompt → tool call → réponse)
    - Tests des cas limites (modèle non chargé, max rounds, erreurs)
    - Tests du nettoyage de la sortie du modèle

Important : ces tests ne chargent JAMAIS le vrai modèle.
Le modèle est remplacé par un MagicMock qui simule des réponses
prédéfinies selon le scénario testé.

Lancer :
    pytest tests/test_inference.py -v
    pytest tests/test_inference.py -v -k "test_pipeline"
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.inference.pipeline import (
    AnalysisRequest,
    AnalysisResponse,
    LeanStartupPipeline,
    PipelineConfig,
    build_system_prompt,
)
from src.inference.tool_executor import TOOL_CALL_END, TOOL_CALL_START


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def pipeline_config():
    """Configuration minimale pour les tests."""
    return PipelineConfig(
        model_path="models/test-model",
        max_new_tokens_first=128,
        max_new_tokens_final=256,
        max_tool_call_rounds=3,
    )


@pytest.fixture
def mock_pipeline(pipeline_config):
    """
    Pipeline avec modèle mocké.
    Le modèle est remplacé par un MagicMock configuré dynamically
    dans chaque test via la fixture.
    """
    pipeline = LeanStartupPipeline(config=pipeline_config)

    # Remplacer le modèle par un mock
    pipeline.model = MagicMock()
    type(pipeline.model).is_loaded = PropertyMock(return_value=True)

    return pipeline


def make_tool_call_output(sql: str) -> str:
    """Crée une sortie simulée du modèle avec un tool call."""
    return f"{TOOL_CALL_START}[query_postgresql(sql=\"{sql}\")]{TOOL_CALL_END}"


def make_final_answer(text: str) -> str:
    """Crée une sortie simulée du modèle sans tool call (réponse finale)."""
    return text


# =============================================================================
# TESTS — SYSTEM PROMPT
# =============================================================================

class TestSystemPrompt:
    """Tests sur la construction du system prompt."""

    def test_system_prompt_with_tools(self):
        prompt = build_system_prompt(include_tools=True)
        assert "query_postgresql" in prompt
        assert "List of tools" in prompt

    def test_system_prompt_without_tools(self):
        prompt = build_system_prompt(include_tools=False)
        assert "query_postgresql" not in prompt

    def test_system_prompt_contains_role_definition(self):
        prompt = build_system_prompt()
        assert "analyste" in prompt.lower() or "lean startup" in prompt.lower()

    def test_system_prompt_is_non_empty(self):
        prompt = build_system_prompt()
        assert len(prompt) > 100


# =============================================================================
# TESTS — MODÈLE NON CHARGÉ
# =============================================================================

class TestUnloadedModel:
    """Tests du comportement quand le modèle n'est pas chargé."""

    def test_analyze_returns_error_when_not_loaded(self, pipeline_config):
        """pipeline.analyze() retourne une erreur si le modèle n'est pas chargé."""
        pipeline = LeanStartupPipeline(config=pipeline_config)
        # Ne pas appeler pipeline.load() — modèle non chargé

        response = pipeline.analyze(AnalysisRequest(user_input="Test"))

        assert response.success is False
        assert response.error is not None
        assert "non chargé" in response.error.lower() or "load" in response.error.lower()


# =============================================================================
# TESTS — FLUX SANS TOOL CALL
# =============================================================================

class TestPipelineWithoutToolCall:
    """Tests du flux direct : prompt → réponse finale sans tool call."""

    def test_direct_response_no_tool_call(self, mock_pipeline):
        """Le pipeline retourne la réponse directement quand il n'y a pas de tool call."""
        expected_answer = "## Analyse\n\nVotre startup présente plusieurs risques."

        mock_pipeline.model.generate.return_value = make_final_answer(expected_answer)

        request = AnalysisRequest(
            user_input="Startup marketplace, 50 artisans, 5 transactions.",
            investor_profile="angel",
        )
        with patch("src.inference.pipeline.has_tool_call", return_value=False):
            response = mock_pipeline._run_pipeline(request)

        assert response.success is True
        assert response.tool_calls_made == 0
        assert expected_answer in response.final_answer

    def test_response_is_cleaned(self, mock_pipeline):
        """Les tokens spéciaux LFM2.5 sont nettoyés de la réponse finale."""
        raw_output = "<|im_start|>assistant\nVoici mon analyse.<|im_end|>"
        mock_pipeline.model.generate.return_value = raw_output

        cleaned = mock_pipeline._clean_output(raw_output)

        assert "<|im_start|>" not in cleaned
        assert "<|im_end|>" not in cleaned
        assert "Voici mon analyse." in cleaned

    def test_residual_tool_call_tokens_cleaned(self, mock_pipeline):
        """Les blocs tool call résiduels sont supprimés de la réponse."""
        residual_tc = f"{TOOL_CALL_START}[query_postgresql(sql='SELECT 1')]{TOOL_CALL_END}"
        raw = f"Texte avant. {residual_tc} Texte après."

        cleaned = mock_pipeline._clean_output(raw)

        assert TOOL_CALL_START not in cleaned
        assert TOOL_CALL_END   not in cleaned
        assert "Texte avant." in cleaned
        assert "Texte après." in cleaned


# =============================================================================
# TESTS — FLUX AVEC TOOL CALL
# =============================================================================

class TestPipelineWithToolCall:
    """Tests du flux complet avec tool calls PostgreSQL."""

    @patch("src.inference.pipeline.execute_all_tool_calls")
    def test_tool_call_increments_counter(self, mock_execute, mock_pipeline):
        """Le compteur tool_calls_made est incrémenté après chaque tool call."""
        from src.inference.tool_executor import ToolResult

        # Première génération : tool call
        # Deuxième génération : réponse finale
        tc_output    = make_tool_call_output("SELECT * FROM risk_patterns LIMIT 3")
        final_output = "## Analyse\n\nVoici les risques identifiés."

        mock_pipeline.model.generate.side_effect = [tc_output, final_output]
        mock_execute.return_value = [
            ToolResult(success=True, data=[{"pattern_name": "Cold Start"}], row_count=1)
        ]

        request = AnalysisRequest(user_input="Marketplace avec peu de transactions.")

        with patch("src.inference.pipeline.build_tool_messages") as mock_msgs:
            mock_msgs.return_value = [{"role": "tool", "content": '{"status": "success"}'}]
            response = mock_pipeline._run_pipeline(request)

        assert response.tool_calls_made >= 1

    @patch("src.inference.pipeline.execute_all_tool_calls")
    def test_tool_call_data_sources_tracked(self, mock_execute, mock_pipeline):
        """Les tables PostgreSQL consultées sont tracées dans data_sources_used."""
        from src.inference.tool_executor import ToolResult

        tc_output    = make_tool_call_output("SELECT * FROM risk_patterns LIMIT 5")
        final_output = "Réponse finale basée sur les données."

        mock_pipeline.model.generate.side_effect = [tc_output, final_output]
        mock_execute.return_value = [
            ToolResult(success=True, data=[], row_count=0)
        ]

        request = AnalysisRequest(user_input="Analyse de risques.")

        with patch("src.inference.pipeline.build_tool_messages") as mock_msgs:
            mock_msgs.return_value = [{"role": "tool", "content": '{"status": "success"}'}]
            response = mock_pipeline._run_pipeline(request)

        assert "risk_patterns" in response.data_sources_used

    @patch("src.inference.pipeline.execute_all_tool_calls")
    def test_max_rounds_prevents_infinite_loop(self, mock_execute, mock_pipeline):
        """Le pipeline s'arrête après max_tool_call_rounds rounds."""
        from src.inference.tool_executor import ToolResult

        # Le modèle génère TOUJOURS un tool call → test de la limite
        tc_output = make_tool_call_output("SELECT 1")
        mock_pipeline.model.generate.return_value = tc_output
        mock_execute.return_value = [
            ToolResult(success=True, data=[], row_count=0)
        ]

        request = AnalysisRequest(user_input="Test boucle infinie.")
        max_rounds = mock_pipeline.config.max_tool_call_rounds

        with patch("src.inference.pipeline.build_tool_messages") as mock_msgs:
            mock_msgs.return_value = [{"role": "tool", "content": "{}"}]
            # Permet au fallback de terminer
            mock_pipeline.model.generate.side_effect = (
                [tc_output] * max_rounds + ["Réponse finale de secours."]
            )
            response = mock_pipeline._run_pipeline(request)

        # Le pipeline doit avoir terminé (pas de boucle infinie)
        assert response is not None
        assert isinstance(response, AnalysisResponse)


# =============================================================================
# TESTS — ANALYSE REQUEST
# =============================================================================

class TestAnalysisRequest:
    """Tests sur la structure et validation des requêtes."""

    def test_default_investor_profile(self):
        req = AnalysisRequest(user_input="Description startup.")
        assert req.investor_profile == "both"

    def test_custom_investor_profile(self):
        req = AnalysisRequest(user_input="Description.", investor_profile="angel")
        assert req.investor_profile == "angel"

    def test_empty_conversation_history_by_default(self):
        req = AnalysisRequest(user_input="Description.")
        assert req.conversation_history == []

    def test_conversation_history_preserved(self):
        history = [
            {"role": "user",      "content": "Bonjour"},
            {"role": "assistant", "content": "Bonjour, comment puis-je aider ?"},
        ]
        req = AnalysisRequest(user_input="Suite.", conversation_history=history)
        assert len(req.conversation_history) == 2


# =============================================================================
# TESTS — PROFIL INVESTISSEUR
# =============================================================================

class TestInvestorProfile:
    """Tests sur l'adaptation au profil investisseur."""

    def test_profile_instruction_entrepreneur(self, mock_pipeline):
        instr = mock_pipeline._get_profile_instruction("entrepreneur")
        assert "entrepreneur" in instr.lower() or "actionnables" in instr.lower()

    def test_profile_instruction_angel(self, mock_pipeline):
        instr = mock_pipeline._get_profile_instruction("angel")
        assert "angel" in instr.lower() or "traction" in instr.lower()

    def test_profile_instruction_vc(self, mock_pipeline):
        instr = mock_pipeline._get_profile_instruction("vc")
        assert "vc" in instr.lower() or "métriques" in instr.lower()

    def test_profile_instruction_impact(self, mock_pipeline):
        instr = mock_pipeline._get_profile_instruction("impact")
        assert "impact" in instr.lower()

    def test_unknown_profile_returns_empty(self, mock_pipeline):
        instr = mock_pipeline._get_profile_instruction("inconnu")
        assert instr == ""

    def test_both_profile_mentions_both(self, mock_pipeline):
        instr = mock_pipeline._get_profile_instruction("both")
        assert "investisseur" in instr.lower() or "entrepreneur" in instr.lower()


# =============================================================================
# TESTS — ANALYSE RESPONSE
# =============================================================================

class TestAnalysisResponse:
    """Tests sur la structure des réponses."""

    def test_success_property_true_when_no_error(self):
        response = AnalysisResponse(final_answer="Analyse complète.")
        assert response.success is True

    def test_success_property_false_when_error(self):
        response = AnalysisResponse(final_answer="", error="Modèle non chargé.")
        assert response.success is False

    def test_default_values(self):
        response = AnalysisResponse(final_answer="Test.")
        assert response.tool_calls_made == 0
        assert response.tool_calls_successful == 0
        assert response.data_sources_used == []
        assert response.error is None


# =============================================================================
# TESTS — EXTRACTION DU NOM DE TABLE
# =============================================================================

class TestTableExtraction:
    """Tests sur _extract_table_name (helper interne du pipeline)."""

    def test_extracts_simple_table(self, mock_pipeline):
        sql = "SELECT * FROM risk_patterns WHERE criticality = 'critical'"
        table = mock_pipeline._extract_table_name(sql)
        assert table == "risk_patterns"

    def test_extracts_from_view(self, mock_pipeline):
        sql = "SELECT * FROM v_critical_risks LIMIT 5"
        table = mock_pipeline._extract_table_name(sql)
        assert table == "v_critical_risks"

    def test_returns_none_for_invalid_sql(self, mock_pipeline):
        table = mock_pipeline._extract_table_name("pas de SQL ici")
        assert table is None

    def test_case_insensitive_from(self, mock_pipeline):
        sql = "select * from lean_concepts where concept_name = 'MVP'"
        table = mock_pipeline._extract_table_name(sql)
        assert table == "lean_concepts"
