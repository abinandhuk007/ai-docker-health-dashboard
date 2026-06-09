# Prompt Engineering Notes — DockerMind AI Monitor

## Overview
This document captures all prompt design decisions, templates, and rationale
used throughout the Docker Monitoring Web Application.

---

## 1. System Prompt (Translation Layer)

**File:** `prompts/system_prompt.txt`
**Used in:** `services/llm_service.py → LLMTranslator.translate()`

### Purpose
Convert free-text user queries into a structured JSON intent that the agent
loop and Docker service can act on.

### Design Decisions
- **JSON-only output rule** prevents prompt injection from being executed
  as shell commands. The LLM cannot cause harm because it can only emit a
  controlled schema.
- **Strict enum for `action`** keeps the downstream code simple and
  avoids hallucinated action types.
- **`duration` always in minutes** normalizes time expressions ("2 hours" → 120)
  so the Docker SDK filter code doesn't need time-unit logic.
- **Few-shot examples** (5 examples) cover the most common query patterns:
  list-all, restarting, logs, unhealthy, and crashed/exited.

### Template
```
System: <contents of system_prompt.txt>
User:   <raw user query>
```

---

## 2. Summary / Commentary Prompt

**Used in:** `services/llm_service.py → LLMTranslator.generate_summary()`

### Purpose
Take the structured Docker data (container list, statuses, restart counts)
and produce three levels of human-readable commentary:
1. One-sentence executive summary
2. Beginner-friendly explanation
3. Recommended action

### Template
```
You are a helpful DevOps assistant. Analyze the following Docker container 
data and provide a brief, actionable summary.

Container data:
{container_json}

Respond ONLY with a JSON object in this exact format:
{
  "summary": "<one sentence summary>",
  "explanation": "<beginner-friendly explanation in 2-3 sentences>",
  "recommendation": "<concrete action the user should take>"
}

Rules:
- Be specific about container names and counts
- If all containers are healthy, say so clearly
- Highlight any containers that need attention
- Keep the tone professional but approachable
```

### Design Decisions
- Requesting JSON output (not prose) makes parsing deterministic.
- Three-tier structure (summary/explanation/recommendation) covers both
  expert and novice users simultaneously.
- Injecting real container data keeps the AI grounded — less hallucination.

---

## 3. Agent Loop Prompts

**Used in:** `services/agent_loop.py → AgentExecutor`

### 3a. Retry Reasoning Prompt
When the first Docker query returns zero results, the agent asks the LLM
to suggest an alternative filter.

```
The following Docker query returned no results:
  Action: {action}, Duration: {duration} minutes

The user originally asked: "{original_query}"

Suggest ONE alternative action from this list that might find relevant
containers: [all, running, exited, restarting, unhealthy, stopped]

Respond with ONLY the action word, nothing else.
```

**Rationale:** Keeps the retry path deterministic — LLM returns a single
token, easy to validate, no parsing required.

### 3b. Result Inspection Prompt
After getting Docker results, the agent checks if they adequately answer
the user's question.

```
User asked: "{original_query}"
Docker returned {count} container(s).
Intent was: {intent}

Does this result adequately answer the user's question?
Reply with exactly: YES or NO
```

**Rationale:** Binary YES/NO answer avoids parsing complexity while still
using AI judgment to decide whether a retry is needed.

---

## 4. Fallback Handling

When the LLM is unavailable or returns malformed JSON, the system falls back
to a keyword-based rule engine in `utils/parser.py`:

| Keyword(s) in query     | Mapped action   |
|-------------------------|-----------------|
| restart / restarting    | restarting      |
| crash / exit / exited   | exited          |
| unhealthy / sick        | unhealthy       |
| log / logs              | logs            |
| running / active        | running         |
| stop / stopped / paused | stopped         |
| all / list / show       | all             |

This ensures the app remains functional even without an API key.

---

## 5. Prompt Injection Prevention

All user input passes through `utils/validators.py` before reaching the LLM:
- Maximum 500 characters
- Regex scan for dangerous patterns (rm -rf, eval, subprocess, etc.)
- The system prompt explicitly instructs the LLM to output JSON only
- JSON schema is validated with Pydantic before use

---

## 6. Token Budget

| Prompt type        | Approx. input tokens | Approx. output tokens |
|--------------------|----------------------|-----------------------|
| Translation        | 600–900              | 50–80                 |
| Summary            | 400–800              | 150–250               |
| Retry reasoning    | 100–150              | 5–10                  |
| Result inspection  | 80–120               | 3–5                   |

All well within Gemini Flash free tier (1M tokens/min) and Groq free tier.

---

## 7. Model Selection Notes

| Provider  | Model               | Notes                          |
|-----------|---------------------|--------------------------------|
| Gemini    | gemini-1.5-flash    | Recommended — fast, free tier  |
| Groq      | llama3-8b-8192      | Alternative — very low latency |
| Ollama    | llama3 (local)      | Fully offline option           |

Switch provider via `LLM_PROVIDER` environment variable.
