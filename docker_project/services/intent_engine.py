"""
intent_engine.py — Strict JSON Intent Engine

Translates plain English Docker queries into structured JSON action objects.
Now uses the provider abstraction (services/providers.py) so switching
between Ollama / Gemini / Groq is a one-line env-var change.

PUBLIC API UNCHANGED:
    IntentEngine.parse(query)     → LLMAction
    llm_action_to_intent(action)  → legacy intent dict
    get_intent_engine()           → shared singleton
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Optional
from loguru import logger

from services.providers import build_provider, LLMProvider


# ---------------------------------------------------------------------------
# Supported action / filter enums
# ---------------------------------------------------------------------------

VALID_ACTIONS = {
    "list_containers", "container_logs", "inspect_container",
    "memory_usage", "cpu_usage", "restart_container",
    "stop_container", "container_stats", "unknown",
}

VALID_FILTERS = {
    "all", "running", "exited", "restarting",
    "unhealthy", "paused", "stopped",
}


# ---------------------------------------------------------------------------
# Strict JSON-only system prompt
# ---------------------------------------------------------------------------

_INTENT_SYSTEM_PROMPT = """\
You are a Docker intent parser. Your ONLY job is to convert a user's natural language query into a structured JSON action object.

RULES:
1. Respond with ONLY a single JSON object — no explanations, no prose, no markdown.
2. Choose the action from this exact list:
   - list_containers   → list/show/find containers
   - container_logs    → show logs for a container
   - inspect_container → details/info about a container
   - memory_usage      → memory stats
   - cpu_usage         → CPU stats
   - restart_container → restart a container
   - stop_container    → stop a container
   - container_stats   → general resource stats
   - unknown           → if you cannot map the query to any action

OUTPUT SCHEMA:
{"action": "<action>", "filter": "<all|running|exited|restarting|unhealthy|paused|stopped>", "container": "<name or null>", "duration": <minutes or null>}

FIELD RULES:
- "filter" is ONLY used with list_containers. Omit for other actions.
- "container" is the exact container name if mentioned, else null.
- "duration" is time in minutes if mentioned (e.g. "last 2 hours" = 120), else null.
- Never add extra fields. Never generate shell commands.

EXAMPLES:
User: show all containers
{"action": "list_containers", "filter": "all", "container": null, "duration": null}

User: which containers are restarting?
{"action": "list_containers", "filter": "restarting", "container": null, "duration": null}

User: show unhealthy services
{"action": "list_containers", "filter": "unhealthy", "container": null, "duration": null}

User: what crashed in the last hour?
{"action": "list_containers", "filter": "exited", "container": null, "duration": 60}

User: show logs for nginx
{"action": "container_logs", "container": "nginx", "duration": null}

User: show memory usage
{"action": "memory_usage", "container": null, "duration": null}

User: restart redis
{"action": "restart_container", "container": "redis", "duration": null}

User: inspect the postgres container
{"action": "inspect_container", "container": "postgres", "duration": null}

User: show cpu usage for api-server
{"action": "cpu_usage", "container": "api-server", "duration": null}
"""

_INTENT_USER_TEMPLATE = "User: {query}"


# ---------------------------------------------------------------------------
# LLMAction dataclass  (unchanged from before)
# ---------------------------------------------------------------------------

@dataclass
class LLMAction:
    """Structured intent produced by the intent engine."""
    action:    str            = "unknown"
    filter:    str            = "all"
    container: Optional[str] = None
    duration:  Optional[int] = None
    raw_json:  str            = ""
    source:    str            = "keyword_fallback"

    def to_display_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"action": self.action}
        if self.action == "list_containers":
            d["filter"] = self.filter
        if self.container:
            d["container"] = self.container
        if self.duration is not None:
            d["duration"] = self.duration
        return d


# ---------------------------------------------------------------------------
# Keyword fallback  (unchanged)
# ---------------------------------------------------------------------------

_KEYWORD_ACTION_MAP = [
    (["restar"],                              "list_containers",   "restarting"),
    (["crash", "exit", "exited", "died"],     "list_containers",   "exited"),
    (["unhealthy", "sick", "health"],         "list_containers",   "unhealthy"),
    (["log", "logs", "output"],              "container_logs",    "all"),
    (["run", "running", "active"],           "list_containers",   "running"),
    (["stop", "stopped", "pause", "paused"], "list_containers",   "stopped"),
    (["mem", "memory"],                       "memory_usage",      "all"),
    (["cpu"],                                 "cpu_usage",         "all"),
    (["stat", "resource"],                    "container_stats",   "all"),
    (["inspect", "detail", "info"],          "inspect_container", "all"),
    (["restart"],                             "restart_container", "all"),
    (["all", "list", "show", "container"],   "list_containers",   "all"),
]


def _keyword_fallback(query: str) -> LLMAction:
    q = query.lower()
    action, flt = "list_containers", "all"
    for keywords, mapped_action, mapped_filter in _KEYWORD_ACTION_MAP:
        if any(kw in q for kw in keywords):
            action, flt = mapped_action, mapped_filter
            break

    duration: Optional[int] = None
    if m := re.search(r"(\d+)\s*hour", q):
        duration = int(m.group(1)) * 60
    elif m := re.search(r"(\d+)\s*min", q):
        duration = int(m.group(1))

    container: Optional[str] = None
    if m := re.search(r"(?:for|of|named?|container)\s+([a-zA-Z0-9_\-]+)", q):
        container = m.group(1)

    return LLMAction(
        action=action, filter=flt,
        container=container, duration=duration,
        raw_json=json.dumps({"action": action, "filter": flt,
                              "container": container, "duration": duration}),
        source="keyword_fallback",
    )


# ---------------------------------------------------------------------------
# IntentEngine  — now uses provider abstraction
# ---------------------------------------------------------------------------

class IntentEngine:
    """
    Strict JSON-only intent translator backed by any LLMProvider.
    Default provider is Ollama (local, free, no API key).
    Gracefully falls back to keyword rules when provider is unavailable.
    """

    def __init__(self) -> None:
        # Build provider with the intent system prompt
        self._provider: LLMProvider = build_provider(
            system_prompt=_INTENT_SYSTEM_PROMPT
        )
        logger.info(
            f"IntentEngine: provider={self._provider.name}  "
            f"ready={self._provider.is_ready}"
        )

    @property
    def provider_name(self) -> str:
        return self._provider.name if self._provider.is_ready else "keyword_fallback"

    def parse(self, query: str) -> LLMAction:
        """Translate a natural language query into a structured LLMAction."""
        if not self._provider.is_ready:
            logger.debug("IntentEngine: provider not ready — keyword fallback")
            return _keyword_fallback(query)

        user_msg = _INTENT_USER_TEMPLATE.format(query=query)
        try:
            raw = self._provider.chat(_INTENT_SYSTEM_PROMPT, user_msg)
            action = self._parse_response(raw)
            action.source = self._provider.name
            logger.info(f"IntentEngine parsed: {action.to_display_dict()}")
            return action
        except Exception as exc:
            logger.warning(f"IntentEngine.parse failed ({exc}) — keyword fallback")
            return _keyword_fallback(query)

    @staticmethod
    def _parse_response(raw: str) -> LLMAction:
        """Extract and validate JSON from raw LLM response."""
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.IGNORECASE)
        candidate = fence.group(1).strip() if fence else raw.strip()
        brace = re.search(r"\{[\s\S]*?\}", candidate)
        if brace:
            candidate = brace.group(0)

        data = json.loads(candidate)

        action = str(data.get("action", "unknown")).lower().strip()
        if action not in VALID_ACTIONS:
            action = "unknown"

        flt = str(data.get("filter", "all")).lower().strip()
        if flt not in VALID_FILTERS:
            flt = "all"

        container = data.get("container")
        if container:
            container = str(container).strip() or None

        duration = data.get("duration")
        if duration is not None:
            try:
                duration = max(1, int(duration))
            except (TypeError, ValueError):
                duration = None

        return LLMAction(
            action=action, filter=flt,
            container=container, duration=duration,
            raw_json=json.dumps(data),
        )


# ---------------------------------------------------------------------------
# Bridge: LLMAction → legacy intent dict  (unchanged)
# ---------------------------------------------------------------------------

_ACTION_BRIDGE: dict[str, str] = {
    "list_containers":   None,
    "container_logs":    "logs",
    "inspect_container": "inspect",
    "memory_usage":      "stats",
    "cpu_usage":         "stats",
    "container_stats":   "stats",
    "restart_container": "running",
    "stop_container":    "stopped",
    "unknown":           "all",
}

_FILTER_BRIDGE: dict[str, str] = {
    "all":        "all",
    "running":    "running",
    "exited":     "exited",
    "restarting": "restarting",
    "unhealthy":  "unhealthy",
    "paused":     "paused",
    "stopped":    "stopped",
}


def llm_action_to_intent(action: LLMAction) -> dict[str, Any]:
    """Convert LLMAction → legacy intent dict for AgentExecutor."""
    if action.action == "list_containers":
        legacy_action = _FILTER_BRIDGE.get(action.filter, "all")
    else:
        legacy_action = _ACTION_BRIDGE.get(action.action, "all")

    return {
        "action":         legacy_action,
        "duration":       action.duration,
        "container_name": action.container,
        "intent":         "monitor",
        "filters":        {},
        "_source":        action.source,
        "_llm_action":    action,
    }


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_engine_instance: Optional[IntentEngine] = None


def get_intent_engine() -> IntentEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = IntentEngine()
    return _engine_instance
