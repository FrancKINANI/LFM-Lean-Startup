import json
import pytest
from src.inference.tool_executor import ToolExecutor

def test_tool_executor_initialization():
    executor = ToolExecutor()
    assert "get_benchmarks" in executor.available_tools
    assert "query_postgresql" in executor.available_tools
    assert "get_risk_patterns" in executor.available_tools

def test_tool_execution_unknown_tool():
    executor = ToolExecutor()
    result = executor.execute("fake_tool_that_does_not_exist", {"arg": "value"})
    res_dict = json.loads(result)
    assert "error" in res_dict
    assert "not defined" in res_dict["error"]
