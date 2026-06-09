"""
parser.py — Intent parser utilities for Docker Monitor
Provides JSON extraction and structured intent parsing helpers.
"""

import json
import re
from typing import Any, Optional
from loguru import logger


# ---------------------------------------------------------------------------
# Supported action types that the AI layer can return
# ---------------------------------------------------------------------------
VALID_ACTIONS = {
    "running",
    "restarting",
    "exited",
    "unhealthy",
    "all",
    "logs",
    "inspect",
    "stats",
    "stopped",
    "paused",
}

# Default intent schema used as a fallback
DEFAULT_INTENT: dict[str, Any] = {
    "action": "all",
    "duration": None,
    "container_name": None,
    "intent": "monitor",
    "filters": {},
}


class IntentParser:
    """
    Parses raw LLM output into a validated intent dictionary.

    The LLM is expected to return a JSON block like:
        { "action": "restarting", "duration": 60, "intent": "monitor" }
    This class handles extraction from markdown fences, validation,
    and fallback when the LLM response is malformed.
    """

    def __init__(self) -> None:
        self._json_fence_re = re.compile(
            r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE
        )
        self._bare_json_re = re.compile(r"\{[\s\S]*\}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, raw: str) -> dict[str, Any]:
        """
        Extract and validate a JSON intent from a raw LLM response string.

        Args:
            raw: The raw string returned by the LLM.

        Returns:
            A validated intent dict.  Falls back to DEFAULT_INTENT on error.
        """
        extracted = self._extract_json(raw)
        if extracted is None:
            logger.warning("IntentParser: no JSON found in LLM output; using default")
            return DEFAULT_INTENT.copy()

        return self._validate(extracted)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_json(self, text: str) -> Optional[dict]:
        """Try to pull a JSON object out of arbitrary text."""
        # 1. Look inside markdown code fences first
        fence_match = self._json_fence_re.search(text)
        if fence_match:
            candidate = fence_match.group(1).strip()
        else:
            # 2. Fall back to first bare { … } block
            bare_match = self._bare_json_re.search(text)
            if bare_match:
                candidate = bare_match.group(0)
            else:
                return None

        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            logger.warning(f"IntentParser: JSON decode error — {exc}")
            return None

    def _validate(self, data: dict) -> dict[str, Any]:
        """
        Validate and normalise the extracted intent dict.

        Unknown or missing fields are replaced with safe defaults.
        """
        intent: dict[str, Any] = DEFAULT_INTENT.copy()

        # action
        action = str(data.get("action", "all")).lower().strip()
        intent["action"] = action if action in VALID_ACTIONS else "all"

        # duration (minutes)
        raw_duration = data.get("duration")
        if raw_duration is not None:
            try:
                duration = int(raw_duration)
                intent["duration"] = max(1, min(duration, 10080))  # 1 min – 7 days
            except (ValueError, TypeError):
                logger.warning(
                    f"IntentParser: invalid duration '{raw_duration}'; ignoring"
                )

        # container_name
        name = data.get("container_name") or data.get("name")
        if name and isinstance(name, str):
            intent["container_name"] = name.strip()

        # intent tag
        raw_intent = str(data.get("intent", "monitor")).lower()
        intent["intent"] = raw_intent if raw_intent in {"monitor", "debug", "health"} else "monitor"

        # extra filters (pass-through dict)
        filters = data.get("filters")
        if isinstance(filters, dict):
            intent["filters"] = filters

        logger.debug(f"IntentParser validated intent: {intent}")
        return intent


# Module-level singleton for convenience
_parser_instance: Optional[IntentParser] = None


def get_parser() -> IntentParser:
    """Return a shared IntentParser instance."""
    global _parser_instance
    if _parser_instance is None:
        _parser_instance = IntentParser()
    return _parser_instance


def parse_intent(raw: str) -> dict[str, Any]:
    """Convenience function — parse raw LLM text into a validated intent."""
    return get_parser().parse(raw)
