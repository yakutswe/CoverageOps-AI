
from pydantic import BaseModel, ConfigDict, Field

from app.tools.calculator import calculate
from app.tools.glossary import lookup_concept


class CalculateArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expression: str = Field(min_length=1, max_length=100)


class LookupArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept: str = Field(min_length=1, max_length=80)


TOOL_MODELS = {
    "calculate": CalculateArguments,
    "lookup_concept": LookupArguments,
}

TOOL_FUNCTIONS = {
    "calculate": calculate,
    "lookup_concept": lookup_concept,
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": (
                "Calculate a basic arithmetic expression. "
                "Supports addition, subtraction, "
                "multiplication, division, and parentheses."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Arithmetic expression."
                    }
                },
                "required": ["expression"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lookup_concept",
            "description": (
                "Look up a definition of an AI agent "
                "engineering concept."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "concept": {
                        "type": "string",
                        "description": (
                            "One concept: agent, tool calling, "
                            "rag, mcp, or memory."
                        )
                    }
                },
                "required": ["concept"],
                "additionalProperties": False
            }
        }
    },
]


def execute_tool(name: str, arguments: dict) -> dict:
    if name not in TOOL_FUNCTIONS:
        raise ValueError(f"Tool not permitted: {name}")

    if not isinstance(arguments, dict):
        raise ValueError("Tool arguments must be an object.")

    validated = TOOL_MODELS[name].model_validate(arguments)

    return TOOL_FUNCTIONS[name](
        **validated.model_dump()
    )