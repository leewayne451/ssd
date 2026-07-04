"""Thin, locked-down wrapper around the OpenAI Responses API.

Guarantees:
- store=False (no server-side retention of the request).
- No tools, no web search, no code execution, no file search.
- Strict structured output against a local JSON Schema.
- Bounded timeout, bounded retries, bounded output tokens.
- Prompt content is never logged.
- The API key is only ever read by the SDK client itself.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .config import Settings
from .schemas import SchemaValidationError


class AIRequestError(RuntimeError):
    """Raised when the model call fails or returns undecodable output."""


@dataclass(frozen=True)
class AIResult:
    data: dict[str, Any]
    model: str
    input_tokens: int | None
    output_tokens: int | None


def run_structured_request(
    model: str,
    system_prompt: str,
    user_content: str,
    schema_name: str,
    json_schema: dict[str, Any],
    settings: Settings,
) -> AIResult:
    """Make exactly one structured Responses API call and decode the JSON.

    The caller must still validate the returned data with
    schemas.validate_response(); this function only guarantees valid JSON.
    """
    from openai import OpenAI  # imported lazily; CI-only dependency

    client = OpenAI(
        timeout=settings.request_timeout_seconds,
        max_retries=settings.max_retries,
    )

    response = client.responses.create(
        model=model,
        store=False,
        max_output_tokens=settings.max_output_tokens,
        input=[
            {"role": "developer", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "schema": json_schema,
                "strict": True,
            }
        },
    )

    # A response that hit max_output_tokens (or was otherwise cut short) comes
    # back with status="incomplete" and partial JSON — fail with an actionable
    # message instead of a confusing JSONDecodeError further down.
    status = getattr(response, "status", None)
    if status == "incomplete":
        details = getattr(response, "incomplete_details", None)
        reason = getattr(details, "reason", None) or "unknown"
        usage = getattr(response, "usage", None)
        out_tokens = getattr(usage, "output_tokens", None) if usage else None
        raise AIRequestError(
            f"model response incomplete (reason: {reason}, output tokens used: "
            f"{out_tokens}, cap: {settings.max_output_tokens}) — raise "
            "AI_MAX_OUTPUT_TOKENS in the workflow env or reduce the audit scope"
        )

    raw_text = getattr(response, "output_text", "") or ""
    if not raw_text.strip():
        raise AIRequestError("model returned no output text")
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise AIRequestError(
            f"model output was not valid JSON: {exc} (response status: "
            f"{status or 'unknown'} — if this recurs, suspect truncation and "
            "raise AI_MAX_OUTPUT_TOKENS)"
        ) from exc
    if not isinstance(data, dict):
        raise SchemaValidationError("model output was not a JSON object")

    usage = getattr(response, "usage", None)
    return AIResult(
        data=data,
        model=getattr(response, "model", model) or model,
        input_tokens=getattr(usage, "input_tokens", None) if usage else None,
        output_tokens=getattr(usage, "output_tokens", None) if usage else None,
    )
