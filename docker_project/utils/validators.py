"""
validators.py — Input validation for Docker Monitor
Validates user queries, LLM-produced intents, and Docker API results.
"""

from __future__ import annotations

import re
from typing import Any
from loguru import logger


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_QUERY_LENGTH = 500
MIN_QUERY_LENGTH = 3

# Patterns that could indicate prompt-injection or shell abuse
_DANGEROUS_PATTERNS = [
    r"rm\s+-rf",
    r"sudo",
    r"exec\s*\(",
    r"__import__",
    r"os\.system",
    r"subprocess",
    r"eval\s*\(",
    r";\s*(rm|del|format|shutdown)",
]

_DANGEROUS_RE = re.compile("|".join(_DANGEROUS_PATTERNS), re.IGNORECASE)


# ---------------------------------------------------------------------------
# Query validator
# ---------------------------------------------------------------------------

class QueryValidator:
    """
    Validates raw user-supplied queries before they are sent to the LLM.

    Raises ValueError for clearly invalid input; returns True for valid.
    """

    def validate(self, query: str) -> bool:
        """
        Check that a query is safe and well-formed.

        Args:
            query: The raw string from the Streamlit text input.

        Returns:
            True if valid.

        Raises:
            ValueError: With a human-readable message if invalid.
        """
        if not isinstance(query, str):
            raise ValueError("Query must be a string.")

        stripped = query.strip()

        if len(stripped) < MIN_QUERY_LENGTH:
            raise ValueError(
                f"Query is too short (minimum {MIN_QUERY_LENGTH} characters)."
            )

        if len(stripped) > MAX_QUERY_LENGTH:
            raise ValueError(
                f"Query is too long (maximum {MAX_QUERY_LENGTH} characters)."
            )

        if _DANGEROUS_RE.search(stripped):
            raise ValueError(
                "Query contains potentially unsafe content and was rejected."
            )

        logger.debug(f"QueryValidator: query OK — '{stripped[:80]}…'")
        return True


# ---------------------------------------------------------------------------
# Intent validator
# ---------------------------------------------------------------------------

class IntentValidator:
    """
    Validates the structured intent dict produced by the LLM / IntentParser.
    """

    REQUIRED_KEYS = {"action", "intent"}
    VALID_ACTIONS = {
        "running", "restarting", "exited", "unhealthy",
        "all", "logs", "inspect", "stats", "stopped", "paused",
    }
    VALID_INTENTS = {"monitor", "debug", "health"}

    def validate(self, intent: dict[str, Any]) -> bool:
        """
        Ensure the intent dict has the required keys and valid values.

        Args:
            intent: The dict to validate.

        Returns:
            True if valid.

        Raises:
            ValueError: With a descriptive message if invalid.
        """
        missing = self.REQUIRED_KEYS - intent.keys()
        if missing:
            raise ValueError(f"Intent dict missing required keys: {missing}")

        action = intent.get("action", "")
        if action not in self.VALID_ACTIONS:
            raise ValueError(
                f"Unknown action '{action}'. Supported: {self.VALID_ACTIONS}"
            )

        intent_tag = intent.get("intent", "")
        if intent_tag not in self.VALID_INTENTS:
            raise ValueError(
                f"Unknown intent tag '{intent_tag}'. Supported: {self.VALID_INTENTS}"
            )

        duration = intent.get("duration")
        if duration is not None:
            if not isinstance(duration, (int, float)) or duration < 0:
                raise ValueError(
                    f"Duration must be a non-negative number, got '{duration}'."
                )

        logger.debug(f"IntentValidator: intent OK — {intent}")
        return True


# ---------------------------------------------------------------------------
# Docker result validator
# ---------------------------------------------------------------------------

class DockerResultValidator:
    """
    Lightweight sanity check on results returned from the Docker service.
    """

    def validate(self, results: list[dict]) -> bool:
        """
        Check that the Docker result is a list of dicts.

        Args:
            results: The list returned by DockerService.

        Returns:
            True if valid (even if the list is empty).

        Raises:
            ValueError: If the structure is wrong.
        """
        if not isinstance(results, list):
            raise ValueError(
                f"DockerService must return a list, got {type(results).__name__}."
            )

        for i, item in enumerate(results):
            if not isinstance(item, dict):
                raise ValueError(
                    f"Result item at index {i} must be a dict, got {type(item).__name__}."
                )

        logger.debug(f"DockerResultValidator: {len(results)} item(s) OK")
        return True


# ---------------------------------------------------------------------------
# Convenience singletons
# ---------------------------------------------------------------------------

_query_validator = QueryValidator()
_intent_validator = IntentValidator()
_docker_result_validator = DockerResultValidator()


def validate_query(query: str) -> bool:
    return _query_validator.validate(query)


def validate_intent(intent: dict[str, Any]) -> bool:
    return _intent_validator.validate(intent)


def validate_docker_results(results: list[dict]) -> bool:
    return _docker_result_validator.validate(results)
