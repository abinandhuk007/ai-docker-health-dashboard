"""
providers.py — LLM Provider Abstraction Layer

Defines a clean base class and three concrete providers:
    LLMProvider       — abstract base (interface)
    OllamaProvider    — local Ollama  (DEFAULT, free, no API key)
    GeminiProvider    — Google Gemini (free tier, needs API key)
    GroqProvider      — Groq cloud    (free tier, needs API key)

Usage:
    from services.providers import build_provider
    provider = build_provider()          # reads LLM_PROVIDER env var
    text = provider.chat(system, user)   # unified call interface
    ok   = provider.is_ready             # True when usable

Architecture contract:
    - provider.chat(system_prompt, user_message) -> str
    - provider.complete(prompt)                  -> str  (no system prompt)
    - provider.is_ready                          -> bool
    - provider.name                              -> str  (display label)

All providers fall back gracefully — they set is_ready=False instead of
raising, so callers can detect unavailability and use keyword fallback.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any, Optional
from loguru import logger


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class LLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    @property
    @abstractmethod
    def is_ready(self) -> bool:
        """True when the provider is initialised and usable."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name for display."""

    @abstractmethod
    def chat(self, system_prompt: str, user_message: str) -> str:
        """
        Send a chat-style request.

        Args:
            system_prompt: Instruction context for the model.
            user_message:  The user's input.

        Returns:
            Raw model response text.
        """

    def complete(self, prompt: str) -> str:
        """
        Single-turn completion (no system prompt).
        Default implementation delegates to chat() with an empty system prompt.
        Providers may override for efficiency.
        """
        return self.chat("", prompt)


# ---------------------------------------------------------------------------
# Ollama Provider  (DEFAULT — local, free, no API key)
# ---------------------------------------------------------------------------

class OllamaProvider(LLMProvider):
    """
    Runs a local Ollama model.  No API key required.
    Communicates via the official `ollama` Python package which talks to
    the Ollama daemon on http://localhost:11434 by default.

    Supported models: llama3, mistral, qwen2.5, gemma, phi3, …
    Install:  https://ollama.com  then  `ollama pull llama3`
    """

    def __init__(self) -> None:
        self._model = os.getenv("OLLAMA_MODEL", "llama3")
        self._host  = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self._client: Any = None
        self._ready = False
        self._init()

    def _init(self) -> None:
        try:
            import ollama as _ollama  # type: ignore
            # Try constructing a client with explicit host (ollama >= 0.2)
            try:
                self._client = _ollama.Client(host=self._host)
            except Exception:
                # Older ollama package — use module-level functions
                self._client = _ollama

            # Ping: list models to confirm daemon is reachable
            models_resp = self._client.list()
            available = []
            # Handle both dict and object response styles
            if hasattr(models_resp, "models"):
                available = [m.model for m in models_resp.models]
            elif isinstance(models_resp, dict):
                available = [m.get("name", "") for m in models_resp.get("models", [])]

            if available:
                # Use requested model if available, else first available
                if self._model not in available and not any(
                    self._model in m for m in available
                ):
                    logger.warning(
                        f"OllamaProvider: model '{self._model}' not found locally. "
                        f"Available: {available}. Pull it with: ollama pull {self._model}"
                    )
                    # Still mark ready — model may be pulled on first use
                self._ready = True
                logger.info(
                    f"OllamaProvider: ready  model={self._model}  "
                    f"host={self._host}  available={available}"
                )
            else:
                logger.warning(
                    f"OllamaProvider: daemon reachable but no models found. "
                    f"Run: ollama pull {self._model}"
                )
                self._ready = True  # daemon is up, model just not pulled yet

        except Exception as exc:
            logger.warning(
                f"OllamaProvider: cannot connect to Ollama daemon at {self._host} — {exc}\n"
                f"  Install Ollama from https://ollama.com and run: ollama pull {self._model}"
            )
            self._ready = False

    @property
    def is_ready(self) -> bool:
        return self._ready

    @property
    def name(self) -> str:
        return f"Ollama ({self._model})"

    def chat(self, system_prompt: str, user_message: str) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_message})

        response = self._client.chat(
            model=self._model,
            messages=messages,
            options={"temperature": 0.0},
        )
        # Handle both object and dict response
        if hasattr(response, "message"):
            return response.message.content
        return response["message"]["content"]

    def complete(self, prompt: str) -> str:
        response = self._client.generate(
            model=self._model,
            prompt=prompt,
            options={"temperature": 0.1},
        )
        if hasattr(response, "response"):
            return response.response
        return response.get("response", "")


# ---------------------------------------------------------------------------
# Gemini Provider
# ---------------------------------------------------------------------------

class GeminiProvider(LLMProvider):
    """
    Google Gemini via the google-generativeai SDK.
    Requires GEMINI_API_KEY environment variable.
    Free tier: https://aistudio.google.com
    """

    _MODEL = "gemini-2.0-flash-lite"

    def __init__(self, system_prompt: str = "") -> None:
        self._system_prompt = system_prompt
        self._client: Any = None
        self._plain_client: Any = None   # for complete() calls
        self._ready = False
        self._init()

    def _init(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            logger.warning("GeminiProvider: GEMINI_API_KEY not set")
            return
        try:
            import google.generativeai as genai  # type: ignore
            genai.configure(api_key=api_key)
            self._client = genai.GenerativeModel(
                model_name=self._MODEL,
                system_instruction=self._system_prompt or None,
                generation_config={"temperature": 0.0, "max_output_tokens": 200},
            )
            self._plain_client = genai.GenerativeModel(
                model_name=self._MODEL,
                generation_config={"temperature": 0.1, "max_output_tokens": 500},
            )
            self._ready = True
            logger.info(f"GeminiProvider: ready  model={self._MODEL}")
        except Exception as exc:
            logger.warning(f"GeminiProvider: init failed — {exc}")

    @property
    def is_ready(self) -> bool:
        return self._ready

    @property
    def name(self) -> str:
        return f"Gemini ({self._MODEL})"

    def chat(self, system_prompt: str, user_message: str) -> str:
        # Gemini bakes system_prompt at construction; just send user message
        response = self._client.generate_content(user_message)
        return response.text

    def complete(self, prompt: str) -> str:
        response = self._plain_client.generate_content(prompt)
        return response.text


# ---------------------------------------------------------------------------
# Groq Provider
# ---------------------------------------------------------------------------

class GroqProvider(LLMProvider):
    """
    Groq cloud inference via the `groq` SDK.
    Requires GROQ_API_KEY environment variable.
    Free tier: https://console.groq.com
    """

    def __init__(self, system_prompt: str = "") -> None:
        self._system_prompt = system_prompt
        self._model = os.getenv("GROQ_MODEL", "llama3-8b-8192")
        self._client: Any = None
        self._ready = False
        self._init()

    def _init(self) -> None:
        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key:
            logger.warning("GroqProvider: GROQ_API_KEY not set")
            return
        try:
            from groq import Groq  # type: ignore
            self._client = Groq(api_key=api_key)
            self._ready = True
            logger.info(f"GroqProvider: ready  model={self._model}")
        except Exception as exc:
            logger.warning(f"GroqProvider: init failed — {exc}")

    @property
    def is_ready(self) -> bool:
        return self._ready

    @property
    def name(self) -> str:
        return f"Groq ({self._model})"

    def chat(self, system_prompt: str, user_message: str) -> str:
        messages = []
        sp = system_prompt or self._system_prompt
        if sp:
            messages.append({"role": "system", "content": sp})
        messages.append({"role": "user", "content": user_message})

        completion = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0.0,
            max_tokens=200,
        )
        return completion.choices[0].message.content

    def complete(self, prompt: str) -> str:
        completion = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=500,
        )
        return completion.choices[0].message.content


# ---------------------------------------------------------------------------
# Factory — build the right provider from env vars
# ---------------------------------------------------------------------------

def build_provider(system_prompt: str = "") -> LLMProvider:
    """
    Build and return the LLM provider specified by LLM_PROVIDER env var.

    Default is "ollama".  Falls back silently on init failure — callers
    should check provider.is_ready before use.

    Args:
        system_prompt: Optional system instruction baked into the provider
                       (used by Gemini and Groq; Ollama accepts per-call).

    Returns:
        A ready (or gracefully-degraded) LLMProvider instance.
    """
    provider_name = os.getenv("LLM_PROVIDER", "ollama").lower().strip()

    if provider_name == "ollama":
        return OllamaProvider()
    elif provider_name == "gemini":
        return GeminiProvider(system_prompt=system_prompt)
    elif provider_name == "groq":
        return GroqProvider(system_prompt=system_prompt)
    else:
        logger.warning(
            f"build_provider: unknown LLM_PROVIDER='{provider_name}', defaulting to Ollama"
        )
        return OllamaProvider()
