"""
llm_service.py — AI Translation Layer (MODULE 2)

Handles all LLM interactions:
  - Translating natural language queries into structured JSON intents
  - Generating human-readable AI commentary on container data
  - Keyword-based fallback when LLM is unavailable

PUBLIC API IS UNCHANGED — all callers (agent_loop.py, app.py) work as before.

Provider is now selected via LLM_PROVIDER env var (default: ollama).
Provider switching is handled by services/providers.py.

Classes:
    LLMTranslator  — primary AI translation and commentary class
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Optional
from loguru import logger

from utils.parser import parse_intent
from services.providers import build_provider, LLMProvider


# ---------------------------------------------------------------------------
# Load prompts
# ---------------------------------------------------------------------------

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _load_system_prompt() -> str:
    path = _PROMPTS_DIR / "system_prompt.txt"
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning("system_prompt.txt not found — using inline fallback")
        return (
            "You are a Docker monitoring assistant. "
            "Convert user queries into JSON with keys: action, duration, "
            "container_name, intent, filters. "
            "action must be one of: running, restarting, exited, unhealthy, "
            "all, logs, inspect, stats, stopped, paused."
        )


_SYSTEM_PROMPT = _load_system_prompt()

_SUMMARY_PROMPT_TEMPLATE = """You are a helpful DevOps assistant. Analyze the following Docker container data and provide a brief, actionable summary.

Container data:
{container_json}

Respond ONLY with a JSON object in this exact format:
{{
  "summary": "<one sentence summary>",
  "explanation": "<beginner-friendly explanation in 2-3 sentences>",
  "recommendation": "<concrete action the user should take>"
}}

Rules:
- Be specific about container names and counts
- If all containers are healthy, say so clearly
- Highlight any containers that need immediate attention
- Keep the tone professional but approachable
- Do NOT include any text outside the JSON object"""


# ---------------------------------------------------------------------------
# Keyword fallback (unchanged — works with zero LLM dependency)
# ---------------------------------------------------------------------------

_KEYWORD_MAP = [
    (["restar"],                               "restarting"),
    (["crash", "exit", "exited", "died", "dead", "fail"], "exited"),
    (["unhealthy", "sick", "health"],          "unhealthy"),
    (["log", "logs", "output"],               "logs"),
    (["run", "running", "active", "alive"],   "running"),
    (["stop", "stopped", "pause", "paused"],  "stopped"),
    (["stat", "resource", "cpu", "mem", "memory"], "stats"),
    (["inspect", "detail", "info"],           "inspect"),
]


def _keyword_fallback(query: str) -> dict[str, Any]:
    """Rule-based intent extraction — used when LLM is unavailable."""
    q = query.lower()
    action = "all"
    for keywords, mapped_action in _KEYWORD_MAP:
        if any(kw in q for kw in keywords):
            action = mapped_action
            break

    duration: Optional[int] = None
    hour_m = re.search(r"(\d+)\s*hour", q)
    min_m  = re.search(r"(\d+)\s*min", q)
    if hour_m:
        duration = int(hour_m.group(1)) * 60
    elif min_m:
        duration = int(min_m.group(1))

    return {
        "action": action,
        "duration": duration,
        "container_name": None,
        "intent": "monitor",
        "filters": {},
        "_source": "keyword_fallback",
    }


# ---------------------------------------------------------------------------
# LLMTranslator  — PUBLIC API UNCHANGED
# ---------------------------------------------------------------------------

class LLMTranslator:
    """
    Translates natural language queries into structured Docker intents
    and generates AI commentary on container data.

    Provider is selected via LLM_PROVIDER env var:
        "ollama"  → Local Ollama  (DEFAULT — free, no API key)
        "gemini"  → Google Gemini (free tier, needs GEMINI_API_KEY)
        "groq"    → Groq cloud    (free tier, needs GROQ_API_KEY)

    Falls back to keyword-based rules when the provider is unavailable.
    """

    def __init__(self) -> None:
        # Build the provider with the system prompt for intent translation
        self._provider: LLMProvider = build_provider(system_prompt=_SYSTEM_PROMPT)
        logger.info(
            f"LLMTranslator: provider={self._provider.name}  "
            f"ready={self._provider.is_ready}"
        )

    # ------------------------------------------------------------------
    # Public properties (same as before)
    # ------------------------------------------------------------------

    @property
    def is_available(self) -> bool:
        return self._provider.is_ready

    @property
    def provider_name(self) -> str:
        if not self._provider.is_ready:
            return "keyword fallback"
        return self._provider.name

    # ------------------------------------------------------------------
    # Public methods (same signatures as before)
    # ------------------------------------------------------------------

    def translate(self, query: str) -> dict[str, Any]:
        """
        Convert a natural language query into a structured intent dict.
        Returns a validated intent dict (see utils/parser.py for schema).
        """
        if not self._provider.is_ready:
            logger.info("LLMTranslator.translate: provider not ready — keyword fallback")
            return _keyword_fallback(query)

        try:
            raw = self._provider.chat(_SYSTEM_PROMPT, query)
            intent = parse_intent(raw)
            intent["_source"] = self._provider.name
            return intent
        except Exception as exc:
            logger.warning(f"LLMTranslator.translate: failed ({exc}) — keyword fallback")
            return _keyword_fallback(query)

    def generate_summary(self, containers: list[dict[str, Any]]) -> dict[str, str]:
        """
        Generate a three-tier AI commentary on a container result set.
        Returns dict with keys: summary, explanation, recommendation.
        """
        if not containers:
            return {
                "summary": "No containers matched the query.",
                "explanation": "The Docker engine returned zero results for the given filters.",
                "recommendation": "Try broadening your query or checking if Docker is running.",
            }

        if not self._provider.is_ready:
            return self._fallback_summary(containers)

        trimmed = [
            {
                "name":          c.get("name"),
                "status":        c.get("status"),
                "restart_count": c.get("restart_count"),
                "health":        c.get("health"),
                "uptime":        c.get("uptime"),
                "image":         c.get("image"),
            }
            for c in containers[:20]
        ]
        prompt = _SUMMARY_PROMPT_TEMPLATE.format(
            container_json=json.dumps(trimmed, indent=2)
        )

        try:
            raw = self._provider.complete(prompt)
            return self._parse_summary_response(raw)
        except Exception as exc:
            logger.warning(f"LLMTranslator.generate_summary: {exc}")
            return self._fallback_summary(containers)

    def suggest_retry_action(self, action: str, original_query: str) -> str:
        """
        Ask the LLM to suggest an alternative Docker action when results are empty.
        Returns a single action string (e.g. "running", "all").
        """
        if not self._provider.is_ready:
            return "all"

        prompt = (
            f"The Docker query for action='{action}' returned no results.\n"
            f"User originally asked: \"{original_query}\"\n"
            f"Suggest ONE alternative action from: "
            f"[all, running, exited, restarting, unhealthy, stopped]\n"
            f"Reply with ONLY the action word, nothing else."
        )
        try:
            raw = self._provider.complete(prompt).strip().lower()
            valid = {"all", "running", "exited", "restarting", "unhealthy", "stopped"}
            for token in raw.split():
                if token in valid:
                    return token
        except Exception as exc:
            logger.warning(f"suggest_retry_action: {exc}")
        return "all"

    # ------------------------------------------------------------------
    # Internal helpers (unchanged)
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_summary_response(raw: str) -> dict[str, str]:
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.IGNORECASE)
        candidate = fence.group(1).strip() if fence else raw.strip()
        brace = re.search(r"\{[\s\S]*\}", candidate)
        if brace:
            candidate = brace.group(0)
        try:
            data = json.loads(candidate)
            return {
                "summary":        data.get("summary", "Summary unavailable."),
                "explanation":    data.get("explanation", ""),
                "recommendation": data.get("recommendation", ""),
            }
        except json.JSONDecodeError:
            return {
                "summary":        raw[:200],
                "explanation":    "",
                "recommendation": "Please review the container statuses manually.",
            }

    @staticmethod
    def _fallback_summary(containers: list[dict]) -> dict[str, str]:
        total      = len(containers)
        running    = sum(1 for c in containers if c.get("status") == "running")
        restarting = sum(1 for c in containers if c.get("status") == "restarting")
        exited     = sum(1 for c in containers if c.get("status") == "exited")
        unhealthy  = sum(1 for c in containers if c.get("health") == "unhealthy")

        problems = []
        if restarting: problems.append(f"{restarting} restarting")
        if exited:     problems.append(f"{exited} exited")
        if unhealthy:  problems.append(f"{unhealthy} unhealthy")

        if problems:
            summary        = f"Found {total} container(s): {', '.join(problems)} need attention."
            recommendation = "Investigate the highlighted containers and check their logs."
        else:
            summary        = f"All {total} container(s) appear healthy."
            recommendation = "No immediate action required."

        return {
            "summary": summary,
            "explanation": (
                f"Out of {total} containers, {running} are running normally. "
                + (f"Issues detected: {', '.join(problems)}." if problems else "")
            ),
            "recommendation": recommendation,
        }
