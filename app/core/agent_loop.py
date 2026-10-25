
import json
import logging
import uuid

from pydantic import ValidationError

from app.tools.registry import (
    TOOL_SCHEMAS,
    execute_tool,
)

logger = logging.getLogger(__name__)

MAX_TOOL_STEPS = 5


class AgentLoop:
    def __init__(self, client):
        self.client = client

    async def run(
        self,
        task: str,
        system_prompt: str,
    ) -> dict:
        run_id = str(uuid.uuid4())

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": task,
            },
        ]

        trace = []
        tool_steps = 0

        while True:
            # Once the budget is exhausted, tools are
            # removed from the next model request.
            available_tools = (
                TOOL_SCHEMAS
                if tool_steps < MAX_TOOL_STEPS
                else []
            )

            message = await self.client.chat_turn(
                messages=messages,
                tools=available_tools,
            )

            tool_calls = message.get("tool_calls") or []

            if not tool_calls:
                return {
                    "run_id": run_id,
                    "status": (
                        "completed"
                        if tool_steps < MAX_TOOL_STEPS
                        else "step_limit"
                    ),
                    "answer": message.get("content", ""),
                    "tool_steps": tool_steps,
                    "trace": trace,
                }

            # Save the assistant's requested tool calls.
            if len(tool_calls) > (
                MAX_TOOL_STEPS - tool_steps
            ):
                return {
                    "run_id": run_id,
                    "status": "step_limit",
                    "answer": (
                        "The model requested more tool calls "
                        "than the remaining budget allows."
                    ),
                    "tool_steps": tool_steps,
                    "trace": trace,
                }
            messages.append(message)

            for call in tool_calls:
                if tool_steps >= MAX_TOOL_STEPS:
                    return {
                        "run_id": run_id,
                        "status": "step_limit",
                        "answer": (
                            "Tool execution limit reached."
                        ),
                        "tool_steps": tool_steps,
                        "trace": trace,
                    }

                tool_steps += 1

                name = ""
                arguments = {}
                success = False

                try:
                    if not isinstance(call, dict):
                        raise ValueError(
                            "Invalid tool call format."
                        )

                    function = call.get("function")

                    if not isinstance(function, dict):
                        raise ValueError(
                            "Missing function object."
                        )

                    name = function.get("name", "")

                    raw_arguments = function.get(
                        "arguments", {}
                    )

                    if isinstance(raw_arguments, str):
                        arguments = json.loads(
                            raw_arguments
                        )
                    else:
                        arguments = raw_arguments

                    result = execute_tool(
                        name,
                        arguments,
                    )
                    success = True

                except (
                    ValueError,
                    TypeError,
                    ValidationError,
                ) as exc:
                    result = {
                        "error": str(exc)[:300],
                    }

                trace.append({
                    "step": tool_steps,
                    "tool": name,
                    "success": success,
                })

                logger.info(
                    "run_id=%s step=%d tool=%s success=%s",
                    run_id,
                    tool_steps,
                    name,
                    success,
                )

                messages.append({
                    "role": "tool",
                    "tool_name": name or "invalid_tool",
                    "content": json.dumps(result),
                })