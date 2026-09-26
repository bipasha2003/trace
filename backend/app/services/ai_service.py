"""
TRACE - The AI service layer (CORE.md §2, §2.1)

One way to call the model: `complete(ai, Schema, system, user)` sends the prompt in
JSON mode, parses the reply into `Schema`, and on a parse or validation failure
hands the errors back to the model and asks again. Nothing unvalidated leaves here.

Credentials and the model come from `.env` only (`OPENAI_API_KEY`, `OPENAI_MODEL`,
`OPENAI_BASE_URL`) — fixed by whoever runs the server; no Admin screen changes them
(user decision 2026-09-26). Never from a call site. Tests pass a fake client with the same
`chat_json` method; no test reaches a real model.
"""

import json
import logging

from pydantic import BaseModel, ValidationError
from app.exceptions import TraceException
from app.config import get_settings

logger = logging.getLogger("trace.ai")

MAX_RETRIES = 2


class AINotConfigured(TraceException):
    def __init__(self):
        super().__init__(
            status_code=503,
            detail="AI is not configured. Set OPENAI_API_KEY in .env.",
        )


class AIOutputInvalid(Exception):
    """The model kept returning output that does not match the schema."""

    def __init__(self, schema: str, errors: str):
        super().__init__(f"The AI returned invalid {schema} after {MAX_RETRIES + 1} attempts: {errors}")


class AIClient:
    """The real model, through the OpenAI SDK (any OpenAI-compatible base URL)."""

    def __init__(self, api_key: str, model: str, base_url: str | None = None):
        from openai import AsyncOpenAI

        self.model = model
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url or None, timeout=120)

    async def chat_json(self, messages: list[dict], schema_name: str) -> str:
        response = await self._client.chat.completions.create(
            model=self.model, messages=messages, response_format={"type": "json_object"},
        )
        return response.choices[0].message.content or ""


def ai_configured() -> bool:
    return bool(get_settings().OPENAI_API_KEY)


def client_from_settings() -> AIClient:
    settings = get_settings()
    if not settings.OPENAI_API_KEY:
        raise AINotConfigured()
    return AIClient(settings.OPENAI_API_KEY, settings.OPENAI_MODEL, settings.OPENAI_BASE_URL)


def _errors(exc: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(p) for p in e['loc']) or 'root'}: {e['msg']}" for e in exc.errors()[:10]
    )


async def complete(ai, schema: type[BaseModel], system: str, user: str,
                   context: dict | None = None) -> BaseModel:
    """Ask, validate against `schema`, retry with the errors; raise AIOutputInvalid if it never fits."""
    messages = [
        {"role": "system", "content": (
            f"{system}\n\nReply with a single JSON object that validates against this JSON Schema. "
            f"No prose outside the JSON.\n{json.dumps(schema.model_json_schema())}"
        )},
        {"role": "user", "content": user},
    ]
    last = ""
    for attempt in range(MAX_RETRIES + 1):
        raw = await ai.chat_json(messages, schema.__name__)
        try:
            return schema.model_validate_json(raw, context=context)
        except ValidationError as exc:
            last = _errors(exc)
            logger.warning("[ai] %s attempt %d invalid: %s", schema.__name__, attempt + 1, last)
            messages += [
                {"role": "assistant", "content": raw},
                {"role": "user", "content": f"That JSON is invalid: {last}. Return the corrected JSON object only."},
            ]
    raise AIOutputInvalid(schema.__name__, last)
