import pytest
import sys
from unittest.mock import patch, MagicMock

# Mock des bibliothèques lourdes pour éviter de devoir installer PyTorch/Transformers juste pour les tests unitaires
sys.modules['torch'] = MagicMock()
sys.modules['transformers'] = MagicMock()
sys.modules['peft'] = MagicMock()

import src.inference.pipeline

@pytest.fixture
def mock_pipeline():
    # On mocke le modèle LFM et la base de données pour ne pas faire d'inférence coûteuse durant les tests
    with patch('src.inference.pipeline.LFMAnalyst') as MockLFM:
        with patch('src.inference.pipeline.ToolExecutor') as MockTool:
            from src.inference.pipeline import LeanStartupAnalystPipeline
            pipeline = LeanStartupAnalystPipeline(model_id="mock", adapter_path=None)
            yield pipeline

def test_pipeline_initialization(mock_pipeline):
    assert mock_pipeline is not None
    assert mock_pipeline.max_iterations == 3

def test_extract_tool_call(mock_pipeline):
    response_with_tool = '<|tool_call_start|>[get_benchmarks(sector="SaaS B2B", stage="Seed")]<|tool_call_end|>'
    tool_name, args = mock_pipeline._extract_tool_call(response_with_tool)
    
    assert tool_name == "get_benchmarks"
    assert "sector" in args
    assert args["sector"] == "SaaS B2B"
    assert "stage" in args
    assert args["stage"] == "Seed"

def test_extract_no_tool_call(mock_pipeline):
    response_without_tool = "Voici mon analyse complète et structurée."
    tool_name, args = mock_pipeline._extract_tool_call(response_without_tool)
    
    assert tool_name is None
    assert args is None
