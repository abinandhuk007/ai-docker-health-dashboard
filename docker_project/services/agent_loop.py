"""
agent_loop.py — Agent Loop Implementation (MODULE 3)

Implements the 5-step agent loop that orchestrates intent parsing,
Docker execution, result validation, retry logic, and response generation.

Step 1: Understand request    → LLMTranslator.translate()
Step 2: Call Docker tool      → DockerService.*
Step 3: Inspect results       → validate length and relevance
Step 4: Retry if needed       → alternative action via LLM suggestion
Step 5: Generate response     → LLMTranslator.generate_summary()

Classes:
    AgentResult     — dataclass holding the complete agent output
    AgentExecutor   — orchestrates the full agent loop
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional
from loguru import logger

from services.docker_service import DockerService
from services.llm_service import LLMTranslator
from services.intent_engine import get_intent_engine, llm_action_to_intent
from utils.validators import validate_query, validate_intent, validate_docker_results


# ---------------------------------------------------------------------------
# AgentResult — structured output from the agent loop
# ---------------------------------------------------------------------------

@dataclass
class AgentResult:
    """
    Holds the complete output of one agent loop execution.

    Attributes:
        query           : Original user query.
        intent          : Validated intent dict from LLM/parser.
        containers      : Final list of container dicts.
        summary         : AI-generated summary dict (summary/explanation/recommendation).
        logs            : Log text (populated when action == "logs").
        steps           : List of step labels executed (for transparency display).
        retried         : True if the agent needed to retry with a different action.
        retry_action    : The action used on retry (if any).
        error           : Error message if the loop failed.
        elapsed_ms      : Total wall-clock time for the loop.
        demo_mode       : True when Docker is running against demo data.
    """
    query: str = ""
    intent: dict[str, Any] = field(default_factory=dict)
    containers: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, str] = field(default_factory=dict)
    logs: str = ""
    steps: list[str] = field(default_factory=list)
    retried: bool = False
    retry_action: Optional[str] = None
    error: Optional[str] = None
    elapsed_ms: float = 0.0
    demo_mode: bool = False
    llm_action: Optional[Any] = None   # LLMAction from intent_engine (new schema)


# ---------------------------------------------------------------------------
# AgentExecutor
# ---------------------------------------------------------------------------

class AgentExecutor:
    """
    Orchestrates the 5-step agent loop for Docker monitoring queries.

    Usage:
        executor = AgentExecutor()
        result = executor.run("show me restarting containers")
    """

    # Maximum number of retry attempts
    MAX_RETRIES = 2

    def __init__(
        self,
        docker_service: Optional[DockerService] = None,
        llm_translator: Optional[LLMTranslator] = None,
    ) -> None:
        self._docker = docker_service or DockerService()
        self._llm = llm_translator or LLMTranslator()
        logger.info(
            f"AgentExecutor ready | Docker={'demo' if self._docker.is_demo else 'live'} "
            f"| LLM={self._llm.provider_name}"
        )

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(self, query: str) -> AgentResult:
        """
        Execute the full agent loop for a user query.

        Args:
            query: Raw natural language query from the UI.

        Returns:
            AgentResult with all populated fields.
        """
        result = AgentResult(query=query, demo_mode=self._docker.is_demo)
        t_start = time.perf_counter()

        try:
            # ── STEP 1: Understand request ──────────────────────────
            result.steps.append("Step 1: Parsing intent")
            logger.info(f"AgentExecutor STEP 1 — query: '{query}'")

            validate_query(query)  # raises ValueError on bad input

            # New strict JSON intent engine
            _engine = get_intent_engine()
            llm_action = _engine.parse(query)
            result.llm_action = llm_action

            # Bridge to legacy intent dict for Docker dispatch (unchanged)
            intent = llm_action_to_intent(llm_action)
            validate_intent(intent)
            result.intent = intent
            logger.info(f"AgentExecutor STEP 1 — intent: {intent}")

            # ── STEP 2: Call Docker tool ─────────────────────────────
            result.steps.append(f"Step 2: Executing Docker action '{intent['action']}'")
            logger.info(f"AgentExecutor STEP 2 — action: {intent['action']}")

            containers, logs = self._execute_docker(intent)
            result.logs = logs

            validate_docker_results(containers)

            # ── STEP 3: Inspect results ──────────────────────────────
            result.steps.append(f"Step 3: Inspecting {len(containers)} result(s)")
            logger.info(f"AgentExecutor STEP 3 — got {len(containers)} container(s)")

            # ── STEP 4: Retry if needed ──────────────────────────────
            if not containers and intent["action"] not in ("logs", "exited", "restarting", "unhealthy"):
                containers, result = self._retry_loop(query, intent, result)

            result.containers = containers

            # ── STEP 5: Generate response ────────────────────────────
            result.steps.append("Step 5: Generating AI summary")
            logger.info("AgentExecutor STEP 5 — generating summary")

            result.summary = self._llm.generate_summary(containers)

        except ValueError as ve:
            result.error = str(ve)
            logger.warning(f"AgentExecutor: validation error — {ve}")
        except Exception as exc:
            result.error = f"Unexpected error: {exc}"
            logger.exception(f"AgentExecutor: unhandled exception — {exc}")

        result.elapsed_ms = (time.perf_counter() - t_start) * 1000
        logger.info(f"AgentExecutor done in {result.elapsed_ms:.0f}ms")
        return result

    # ------------------------------------------------------------------
    # Docker dispatch
    # ------------------------------------------------------------------

    def _execute_docker(
        self, intent: dict[str, Any]
    ) -> tuple[list[dict], str]:
        """
        Dispatch the intent to the appropriate DockerService method.

        Returns:
            Tuple of (container_list, log_text).
        """
        action = intent["action"]
        duration = intent.get("duration")
        name = intent.get("container_name")
        logs = ""

        dispatch: dict[str, Any] = {
            "all":        lambda: self._docker.list_all(),
            "running":    lambda: self._docker.list_running(),
            "restarting": lambda: self._docker.list_restarting(duration),
            "exited":     lambda: self._docker.list_exited(duration),
            "stopped":    lambda: self._docker.list_stopped(),
            "paused":     lambda: self._docker.list_paused(),
            "unhealthy":  lambda: self._docker.list_unhealthy(),
            "logs":       lambda: [],  # handled below
            "inspect":    lambda: [self._docker.inspect_container(name)] if name else self._docker.list_all(),
            "stats":      lambda: self._docker.list_all(),
        }

        if action == "logs":
            if not name:
                # If no container specified, return all containers + ask user to pick
                containers = self._docker.list_all()
                logs = "Please specify a container name to view logs."
            else:
                containers = []
                logs = self._docker.get_logs(name)
            return containers, logs

        fetcher = dispatch.get(action, dispatch["all"])
        containers = fetcher()
        return containers, logs

    # ------------------------------------------------------------------
    # Retry logic
    # ------------------------------------------------------------------

    def _retry_loop(
        self,
        original_query: str,
        intent: dict[str, Any],
        result: AgentResult,
    ) -> tuple[list[dict], AgentResult]:
        """
        Attempt up to MAX_RETRIES alternative actions when initial results are empty.

        Returns:
            Updated (containers, result) tuple.
        """
        for attempt in range(1, self.MAX_RETRIES + 1):
            result.steps.append(
                f"Step 4: No results — retry attempt {attempt}/{self.MAX_RETRIES}"
            )
            logger.info(
                f"AgentExecutor STEP 4 — empty results, retry {attempt}"
            )

            # Ask LLM for a better action
            alt_action = self._llm.suggest_retry_action(
                intent["action"], original_query
            )

            if alt_action == intent["action"]:
                # LLM suggested the same action — try "all" as final fallback
                alt_action = "all"

            logger.info(f"AgentExecutor STEP 4 — retry with action '{alt_action}'")
            result.steps.append(f"Step 4: Retrying with action '{alt_action}'")

            retry_intent = {**intent, "action": alt_action}
            containers, _ = self._execute_docker(retry_intent)

            if containers:
                result.retried = True
                result.retry_action = alt_action
                result.steps.append(
                    f"Step 4: Retry succeeded — {len(containers)} result(s) with '{alt_action}'"
                )
                return containers, result

        # All retries exhausted — return empty
        result.steps.append("Step 4: All retries exhausted — returning empty result")
        return [], result
