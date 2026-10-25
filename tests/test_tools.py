
import pytest

from app.tools.registry import execute_tool


def test_calculator():
    result = execute_tool(
        "calculate",
        {"expression": "125 * 24"},
    )

    assert result["result"] == 3000


def test_calculator_parentheses():
    result = execute_tool(
        "calculate",
        {"expression": "(10 + 5) * 2"},
    )

    assert result["result"] == 30


def test_calculator_rejects_code():
    with pytest.raises(ValueError):
        execute_tool(
            "calculate",
            {
                "expression": "__import__('os').getcwd()"
            },
        )


def test_unknown_tool_rejected():
    with pytest.raises(
        ValueError,
        match="not permitted",
    ):
        execute_tool("delete_files", {})


def test_glossary():
    result = execute_tool(
        "lookup_concept",
        {"concept": "rag"},
    )

    assert result["found"] is True
    assert "Retrieval" in result["definition"]


def test_extra_arguments_rejected():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        execute_tool(
            "calculate",
            {
                "expression": "1+1",
                "command": "delete",
            },
        )