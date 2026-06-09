# Prompt Documentation — DockerMind AI Monitor

## Project Overview
AI-powered Docker container monitoring dashboard (Streamlit) that converts natural language queries into Docker API calls using an LLM + agent loop.

---

## Prompts Used

### 1. Intent Translation Prompt (System Prompt)
**File:** `prompts/system_prompt.txt`  
**Used in:** `services/llm_service.py → LLMTranslator.translate()`  
**Purpose:** Converts free-text user queries into a structured JSON intent for the Docker dispatcher.

**Key Design Choices:**
- JSON-only output prevents prompt injection from becoming shell commands
- Strict `action` enum keeps downstream dispatch simple
- `duration` always in minutes (normalizes "2 hours" → 120)
- 5 few-shot examples covering: list-all, restarting, logs, unhealthy, crashed

**Schema output:**
```json
{"action": "running|restarting|exited|unhealthy|all|logs|inspect|stats|stopped|paused",
 "duration": <int minutes or null>,
 "container_name": "<name or null>",
 "intent": "monitor|debug|health",
 "filters": {}}
```

---

### 2. Intent Engine Prompt (Strict JSON Parser)
**File:** `services/intent_engine.py → _INTENT_SYSTEM_PROMPT`  
**Used in:** `IntentEngine.parse()`  
**Purpose:** Secondary, stricter parser that maps queries to a richer action schema.

**Key Design Choices:**
- Maps to fine-grained actions: `list_containers`, `container_logs`, `inspect_container`, `memory_usage`, `cpu_usage`, `restart_container`, `stop_container`, `container_stats`, `unknown`
- `filter` field only applies to `list_containers` (avoids schema pollution)
- 9 few-shot examples for broad coverage
- Falls back to keyword rules if LLM unavailable

---

### 3. Summary / Commentary Prompt
**Used in:** `services/llm_service.py → LLMTranslator.generate_summary()`  
**Purpose:** Produces three-tier human-readable commentary on Docker results.

**Template:**
```
You are a helpful DevOps assistant. Analyze the following Docker container data
and provide a brief, actionable summary.

Container data: {container_json}

Respond ONLY with a JSON object:
{
  "summary": "<one sentence summary>",
  "explanation": "<beginner-friendly explanation in 2-3 sentences>",
  "recommendation": "<concrete action the user should take>"
}
```

**Key Design Choices:**
- JSON output makes parsing deterministic
- Three-tier structure covers both expert and novice users
- Real container data injected to reduce hallucination
- Only first 20 containers sent (token control)

---

### 4. Agent Loop — Retry Reasoning Prompt
**Used in:** `services/llm_service.py → LLMTranslator.suggest_retry_action()`  
**Purpose:** When a Docker query returns zero results, asks LLM for a better action.

**Template:**
```
The Docker query for action='{action}' returned no results.
User originally asked: "{original_query}"
Suggest ONE alternative action from: [all, running, exited, restarting, unhealthy, stopped]
Reply with ONLY the action word, nothing else.
```

**Key Design Choices:** Single-token response makes parsing trivial, no regex needed.

---

### 5. Agent Loop — Result Inspection Prompt
**Used in:** `services/agent_loop.py → AgentExecutor._retry_loop()`  
**Purpose:** Checks if Docker results actually answer the user's question before retrying.

**Template:**
```
User asked: "{original_query}"
Docker returned {count} container(s).
Intent was: {intent}

Does this result adequately answer the user's question?
Reply with exactly: YES or NO
```

**Key Design Choices:** Binary YES/NO avoids parsing complexity while still using AI judgment.

---

## Fallback Strategy (No API Key Required)

When LLM is unavailable, `utils/parser.py` uses keyword matching:

| Keywords | Action |
|---|---|
| restart / restarting | restarting |
| crash / exit / exited | exited |
| unhealthy / sick | unhealthy |
| log / logs | logs |
| running / active | running |
| stop / stopped / paused | stopped |
| all / list / show | all |

---

## Security
All user input passes through `utils/validators.py` before reaching any LLM:
- Max 500 characters
- Regex scan for dangerous patterns (`rm -rf`, `eval`, `subprocess`, etc.)
- LLM instructed to output JSON only — cannot emit shell commands

---

## Token Budget

| Prompt | Input Tokens | Output Tokens |
|---|---|---|
| Translation | 600–900 | 50–80 |
| Summary | 400–800 | 150–250 |
| Retry reasoning | 100–150 | 5–10 |
| Result inspection | 80–120 | 3–5 |

All within Gemini Flash free tier (1M tokens/min) and Groq free tier.

---

## Model / Provider Config

| Provider | Model | Notes |
|---|---|---|
| Gemini | gemini-1.5-flash | Recommended — fast, free tier |
| Groq | llama3-8b-8192 | Very low latency |
| Ollama | llama3 (local) | Fully offline |

Switch via `LLM_PROVIDER` environment variable.
