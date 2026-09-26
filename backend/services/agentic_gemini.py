"""
Agentic upgrade for _ask_gemini.

Key improvements over the original:
  1. REFLECT — on bad output, the agent explains what was wrong back to Gemini
  2. VALIDATE — schema checks run before returning, not just JSON parsing
  3. TRIAGE  — different retry strategies per error type (server vs bad output)
  4. OBSERVE — structured logging for every attempt (audit trail, not just prints)
  5. TOOL SCHEMA — callers declare the shape they expect; agent enforces it
"""
import os, asyncio, json, logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from google import genai
from google.genai import types
from google.genai.errors import ServerError

logger = logging.getLogger(__name__)


# ── Gemini client setup ────────────────────────────────────────────────────────
_client = None

def get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _client

MODEL = "gemma-4-31b-it" #"gemini-2.5-flash" "gemini-3.1-flash-lite-preview" "gemma-4-31b-it"


# ── 1. Error taxonomy ─────────────────────────────────────────────────────────
# Agentic systems triage failures rather than treating all errors the same.
# This drives different retry strategies below.

class GeminiFailure(Enum):
    SERVER_ERROR   = "server_error"    # 5xx — retry with backoff, nothing to fix
    EMPTY_RESPONSE = "empty_response"  # model returned nothing — retry, maybe temp↑
    INVALID_JSON   = "invalid_json"    # parse failed — reflect + ask again
    SCHEMA_INVALID = "schema_invalid"  # JSON ok but shape is wrong — reflect + ask again
    EXHAUSTED      = "exhausted"       # all retries failed


# ── 2. Attempt record (the agent's working memory per call) ───────────────────
# Passed forward across retries so each attempt knows what the previous one did.

@dataclass
class AttemptRecord:
    attempt:      int
    failure_type: GeminiFailure | None = None
    raw_text:     str                  = ""
    error_detail: str                  = ""


# ── 3. Schema validator ───────────────────────────────────────────────────────
# Callers describe what they expect; the agent enforces it before returning.
# This is the "check" step in Observe → Act → Check → Loop.

@dataclass
class OutputSchema:
    """Declare the shape the caller expects from Gemini."""
    root_type:       type                      = dict   # dict or list
    required_keys:   list[str]                 = field(default_factory=list)
    list_item_keys:  list[str]                 = field(default_factory=list)  # if root is list
    min_list_length: int                       = 0
    custom_check:    Any                       = None   # callable(data) -> str | None (error msg)


def _validate(data: Any, schema: OutputSchema) -> str | None:
    """
    Returns an error description string if validation fails, else None.
    The error string is fed back to Gemini as reflection context on retry.
    """
    if not isinstance(data, schema.root_type):
        return (
            f"Expected root type {schema.root_type.__name__} "
            f"but got {type(data).__name__}."
        )

    if schema.root_type is dict:
        missing = [k for k in schema.required_keys if k not in data]
        if missing:
            return f"Missing required keys: {missing}. Keys present: {list(data.keys())}."

    if schema.root_type is list:
        if len(data) < schema.min_list_length:
            return (
                f"List has {len(data)} items but at least "
                f"{schema.min_list_length} are required."
            )
        if schema.list_item_keys:
            for i, item in enumerate(data):
                missing = [k for k in schema.list_item_keys if k not in item]
                if missing:
                    return f"Item [{i}] missing keys: {missing}."

    if schema.custom_check:
        return schema.custom_check(data)

    return None  # all good


# ── 4. Reflection prompt builder ──────────────────────────────────────────────
# When output is wrong, don't just retry the same prompt
# Tell Gemini exactly what was wrong
# Core of the agentic loop

def _build_reflection_prompt(
    original_prompt: str,
    history: list[AttemptRecord],
) -> str:
    last = history[-1]
    problem = {
        GeminiFailure.INVALID_JSON:   f"Your previous response could not be parsed as JSON.\nRaw output was:\n{last.raw_text[:600]}",
        GeminiFailure.SCHEMA_INVALID: f"Your previous response had the wrong structure.\nProblem: {last.error_detail}\nRaw output was:\n{last.raw_text[:600]}",
        GeminiFailure.EMPTY_RESPONSE: "Your previous response was empty.",
    }.get(last.failure_type, "Your previous response failed.")

    return (
        f"{original_prompt}\n\n"
        f"---\n"
        f"REFLECTION: Attempt {last.attempt} failed.\n"
        f"{problem}\n"
        f"Please correct the issue and return ONLY valid JSON matching the schema above.\n"
        f"Do not include any explanation or markdown — raw JSON only."
    )


# ── 5. Temperature escalation ─────────────────────────────────────────────────
# If the model keeps returning the same broken output, raise temperature slightly
# to encourage a different generation path.

def _escalate_temperature(base: float, attempt: int, failure: GeminiFailure) -> float:
    if failure in (GeminiFailure.INVALID_JSON, GeminiFailure.SCHEMA_INVALID):
        return min(base + (attempt - 1) * 0.05, 1.0)  # nudge up on bad output
    return base  # keep stable for server errors


# ── 6. Retry delay strategy ───────────────────────────────────────────────────
# Server errors need longer backoff; logic errors can retry faster.

async def _wait(attempt: int, failure: GeminiFailure | None) -> None:
    if failure == GeminiFailure.SERVER_ERROR:
        delay = 2 ** attempt          # exponential: 2s, 4s, 8s ...
    else:
        delay = attempt               # linear: 1s, 2s, 3s ...
    await asyncio.sleep(delay)


# ── 7. The agentic _ask_gemini ────────────────────────────────────────────────

MAX_RETRIES = 4

async def _ask_gemini(
    prompt: str,
    temperature: float = 0.7,
    schema: OutputSchema | None = None,
    client = None,
) -> dict | list | None:
    """
    Agentic Gemini caller with:
      - Reflection loop: feeds failure context back into the next prompt
      - Schema validation: checks structure before returning
      - Triage: different retry strategies per error type
      - Escalation: temperature nudge when output keeps failing
      - Structured logging: full attempt history for observability

    Args:
        prompt:      The base prompt to send.
        temperature: Starting temperature (escalated on repeated logic failures).
        schema:      Optional OutputSchema. If provided, response is validated
                     before returning; failures trigger a reflection retry.
        client:      Gemini client instance (uses module-level default if None).

    Returns:
        Parsed dict or list on success, None after all retries exhausted.
    """

    history: list[AttemptRecord] = []
    current_prompt = prompt

    for attempt in range(1, MAX_RETRIES + 1):
        record = AttemptRecord(attempt=attempt)
        current_temp = _escalate_temperature(
            temperature, attempt,
            history[-1].failure_type if history else None,
        )

        # ── Act ───────────────────────────────────────────────────────────────
        try:
            response = get_client().models.generate_content(
                model=MODEL,
                contents=current_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=current_temp,
                ),
            )

            # ── Observe: empty? ───────────────────────────────────────────────
            if not response or not response.text:
                record.failure_type = GeminiFailure.EMPTY_RESPONSE
                record.error_detail = "Model returned empty response."
                logger.warning(
                    "Gemini empty response",
                    extra={"attempt": attempt, "model": MODEL},
                )
                history.append(record)
                if attempt < MAX_RETRIES:
                    await _wait(attempt, record.failure_type)
                continue

            record.raw_text = response.text.strip()

            # ── Observe: valid JSON? ───────────────────────────────────────────
            try:
                data = json.loads(record.raw_text)
            except json.JSONDecodeError as e:
                record.failure_type = GeminiFailure.INVALID_JSON
                record.error_detail = str(e)
                logger.warning(
                    "Gemini invalid JSON",
                    extra={"attempt": attempt, "error": str(e),
                           "raw_preview": record.raw_text[:200]},
                )
                history.append(record)
                if attempt < MAX_RETRIES:
                    # REFLECT: tell Gemini what broke
                    current_prompt = _build_reflection_prompt(prompt, history)
                    await _wait(attempt, record.failure_type)
                continue

            # ── Observe: correct schema? ───────────────────────────────────────
            if schema is not None:
                validation_error = _validate(data, schema)

                if validation_error:
                    record.failure_type = GeminiFailure.SCHEMA_INVALID
                    record.error_detail = validation_error

                    logger.warning(
                        "Gemini schema invalid",
                        extra={"attempt": attempt, "error": validation_error},
                    )

                    history.append(record)
                    
                    if attempt < MAX_RETRIES:
                        # REFLECT: tell Gemini the specific structural problem
                        current_prompt = _build_reflection_prompt(prompt, history)
                        await _wait(attempt, record.failure_type)
                    
                    continue

            # ── Success ───────────────────────────────────────────────────────
            logger.info(
                "Gemini success",
                extra={"attempt": attempt, "temperature": current_temp},
            )
            return data

        except ServerError as e:
            record.failure_type = GeminiFailure.SERVER_ERROR
            record.error_detail = str(e)
            logger.error(
                "Gemini server error",
                extra={"attempt": attempt, "error": str(e)},
            )
            history.append(record)
            if attempt < MAX_RETRIES:
                await _wait(attempt, record.failure_type)  # longer backoff for 5xx

        except Exception as e:
            record.failure_type = GeminiFailure.SERVER_ERROR
            record.error_detail = str(e)
            logger.error(
                "Gemini unexpected error",
                extra={"attempt": attempt, "error": str(e)},
            )
            history.append(record)
            if attempt < MAX_RETRIES:
                await _wait(attempt, record.failure_type)

    # ── Exhausted ─────────────────────────────────────────────────────────────
    failure_summary = [
        {"attempt": r.attempt, "type": r.failure_type.value if r.failure_type else "unknown"}
        for r in history
    ]
    logger.error(
        "Gemini exhausted all retries",
        extra={"failures": failure_summary, "model": MODEL},
    )
    return None
