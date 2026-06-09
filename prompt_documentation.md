# Project Spec: DockerMind — Natural Language Docker Monitor

## Goal
Build a Streamlit web app where users type plain English questions
about Docker containers and get instant visual answers — no terminal needed.

## Tech Stack
- Python + Streamlit (UI)
- Anthropic Claude / Gemini / Groq (LLM)
- Docker Python SDK (container data)
- Plotly (charts)

## Architecture — 3 Phases

### Phase 1: AI Translation Core
- Text input box in Streamlit captures user query
- Pass query to LLM with this system prompt:
  "You are a Docker intent parser. Convert the user's natural language
   query into a JSON object with these fields only:
   {action: running|restarting|exited|unhealthy|all|logs,
    duration: <integer minutes or null>,
    container_name: <string or null>}
   Respond with JSON only. No explanation."
- Parse the JSON response

### Phase 2: Docker Execution Hook
- Read the action field from parsed JSON
- Route to correct Docker SDK call:
  - running    → client.containers.list(filters={"status":"running"})
  - restarting → client.containers.list(filters={"status":"restarting"})
  - exited     → client.containers.list(filters={"status":"exited"})
  - unhealthy  → client.containers.list(filters={"health":"unhealthy"})
  - all        → client.containers.list(all=True)
  - logs       → container.logs(tail=100)
- If Docker is not running, return demo/mock data

### Phase 3: Dashboard Visualization
- Display container data in st.dataframe() with colored status column
- Show KPI metric cards: Total / Running / Exited / Restarting
- Send container data back to LLM for a plain-English summary:
  "You are a DevOps assistant. In 1 sentence, summarize this container
   data for a non-technical user: {container_json}"
- Show Plotly pie/donut chart of container status distribution

## Agent Loop (Bonus)
- Step 1: Parse intent via LLM
- Step 2: Execute Docker action
- Step 3: Check if results are empty
- Step 4: If empty, ask LLM for alternative action and retry once
- Step 5: Generate final AI summary

## Fallback Rules (No API Key)
If LLM is unavailable, use keyword matching:
- "restart"   → action: restarting
- "crash/exit" → action: exited
- "unhealthy" → action: unhealthy
- "log"       → action: logs
- "all/show"  → action: all

## Security Rules
- Validate input: max 500 characters
- Block dangerous patterns: rm, eval, subprocess, os.system
- LLM must output JSON only — never shell commands

## File Structure
app.py                  # Streamlit UI
services/
  agent_loop.py         # 5-step agent loop
  llm_service.py        # LLM translation + summary
  docker_service.py     # Docker SDK calls
  providers.py          # Ollama/Gemini/Groq abstraction
utils/
  validators.py         # Input sanitisation
  parser.py             # Keyword fallback parser
prompts/
  system_prompt.txt     # Intent translation prompt
  prompt_notes.md       # Prompt documentation

## Deliverables
- Working Streamlit app
- Agent loop with retry logic
- AI summary on every query
- Demo mode when Docker is offline
- prompt_notes.md documenting all prompts
- AI_Usage_Note.md documenting AI tool usage
