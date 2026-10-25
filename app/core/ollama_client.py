
import httpx

from app.core.config import Settings, get_settings


class OllamaError(Exception):
    """A recoverable Ollama integration error."""


class OllamaClient:
    def __init__(
        self,
        settings: Settings | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.settings = settings or get_settings()
        self.transport = transport

    
    async def chat_turn(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> dict:
        url = (
            self.settings.ollama_base_url.rstrip("/")
            + "/api/chat"
        )

        payload = {
            "model": self.settings.ollama_model,
            "messages": messages,
            "stream": False,
            "think": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 512,
            },
        }

        if tools is not None:
            payload["tools"] = tools

        try:
            async with httpx.AsyncClient(
                timeout=self.settings.ollama_timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.post(
                    url,
                    json=payload,
                )
                response.raise_for_status()

            result = response.json()

            if not isinstance(result, dict):
                raise OllamaError(
                    "Invalid Ollama response."
                )

            message = result.get("message")

            if not isinstance(message, dict):
                raise OllamaError(
                    "Ollama response has no message."
                )

            content = message.get("content")
            tool_calls = message.get("tool_calls")

            if content is not None and not isinstance(content, str):
                raise OllamaError(
                    "Invalid Ollama message content."
                )

            if tool_calls is not None and not isinstance(
                tool_calls, list
            ):
                raise OllamaError(
                    "Invalid Ollama tool calls."
                )

            if not (content or tool_calls):
                raise OllamaError(
                    "Ollama returned an empty response."
                )

            return message

        except httpx.TimeoutException as exc:
            raise OllamaError(
                "Ollama timed out."
            ) from exc

        except httpx.RequestError as exc:
            raise OllamaError(
                "Cannot connect to Ollama."
            ) from exc

        except httpx.HTTPStatusError as exc:
            raise OllamaError(
                f"Ollama HTTP {exc.response.status_code}."
            ) from exc

        except ValueError as exc:
            raise OllamaError(
                "Ollama returned invalid JSON."
            ) from exc

    async def chat(
        self,
        messages: list[dict],
    ) -> str:
        message = await self.chat_turn(messages)

        content = message.get("content", "")

        if not content or not content.strip():
            raise OllamaError(
                "Ollama returned an empty response."
            )

        return content.strip()

        try:
            async with httpx.AsyncClient(
                timeout=self.settings.ollama_timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.post(
                    url,
                    json=payload,
                )
                response.raise_for_status()

            result = response.json()

            if not isinstance(result, dict):
                raise OllamaError(
                    "Ollama returned an invalid response."
                )

            message = result.get("message")

            if not isinstance(message, dict):
                raise OllamaError(
                    "Ollama response has no message."
                )

            content = message.get("content")

            if not isinstance(content, str) or not content.strip():
                raise OllamaError(
                    "Ollama returned an empty response."
                )

            return content.strip()

        except httpx.TimeoutException as exc:
            raise OllamaError(
                "Ollama timed out. Try a shorter task."
            ) from exc

        except httpx.RequestError as exc:
            raise OllamaError(
                "Cannot connect to Ollama. "
                "Check that Ollama is running."
            ) from exc

        except httpx.HTTPStatusError as exc:
            raise OllamaError(
                "Ollama rejected the request "
                f"(HTTP {exc.response.status_code}). "
                "Check the model name and Ollama logs."
            ) from exc

        except ValueError as exc:
            raise OllamaError(
                "Ollama returned invalid JSON."
            ) from exc