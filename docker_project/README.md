# 🐳 Docker Monitor AI

> **AI-powered Docker container monitoring with natural language queries.**
> Built as a 1–2 day hackathon prototype demonstrating agent loops, LLM integration, and real-time Docker introspection.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🧠 Natural language queries | Ask "show restarting containers" in plain English |
| 🤖 Agent Loop | 5-step autonomous reasoning with retry logic |
| 🐋 Docker SDK | Real-time container monitoring via official Python SDK |
| 📊 Visual dashboard | Metrics, tables, charts via Streamlit + Plotly |
| 💬 AI Commentary | Three-tier summaries (executive / beginner / recommendation) |
| 🔄 Fallback mode | Works without LLM API key via keyword rules |
| 🎭 Demo mode | Auto-activates with sample data when Docker isn't running |
| 🗄️ Query history | Optional PostgreSQL persistence for audit/analytics |

---

## 🏗 Architecture

```
User Query
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  MODULE 1: Streamlit UI (app.py)                            │
│    - Query input  - Status cards  - Container table         │
│    - AI summary   - Agent trace   - Log viewer              │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  MODULE 3: Agent Loop (services/agent_loop.py)              │
│    Step 1: Parse intent via LLM                             │
│    Step 2: Execute Docker action                            │
│    Step 3: Inspect results                                  │
│    Step 4: Retry with alternate filter if empty             │
│    Step 5: Generate AI commentary                           │
└────────────┬────────────────────────────────────────────────┘
             │                           │
             ▼                           ▼
┌────────────────────┐     ┌─────────────────────────────────┐
│  MODULE 2: LLM     │     │  MODULE 4: Docker SDK           │
│  (llm_service.py)  │     │  (docker_service.py)            │
│                    │     │                                 │
│  • Gemini Flash    │     │  • list_all / running / exited  │
│  • Groq LLaMA 3    │     │  • list_restarting / unhealthy  │
│  • Ollama (local)  │     │  • get_logs / inspect / stats   │
│  • Keyword rules   │     │  • Demo data fallback           │
└────────────────────┘     └─────────────────────────────────┘
                                         │
                           ┌─────────────┴──────────────────┐
                           │  MODULE 5+6: Visualization     │
                           │  (DashboardRenderer in app.py) │
                           │                                │
                           │  • Metric cards                │
                           │  • Styled DataFrame            │
                           │  • Plotly pie chart            │
                           │  • AI summary card             │
                           └────────────────────────────────┘
```

---

## 📁 Project Structure

```
docker-monitor-ai/
├── app.py                    # Streamlit UI (Module 1 + 5 + 6)
├── services/
│   ├── agent_loop.py         # Agent Loop (Module 3)
│   ├── llm_service.py        # AI Translation Layer (Module 2)
│   ├── docker_service.py     # Docker Monitoring Engine (Module 4)
│   └── db_service.py         # PostgreSQL history service
├── utils/
│   ├── parser.py             # Intent JSON parser
│   └── validators.py         # Input / output validators
├── prompts/
│   ├── system_prompt.txt     # LLM system prompt
│   └── prompt_notes.md       # Prompt engineering documentation
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🚀 Quick Start

### 1. Clone / navigate to project
```bash
cd docker-monitor-ai
```

### 2. Create virtual environment
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment
```bash
copy .env.example .env   # Windows
# or
cp .env.example .env     # Mac/Linux
```

Edit `.env` and add your API key:

```dotenv
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
```

> **No API key?** The app still works using keyword-based fallback and demo Docker data.

### 5. Run the app
```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 🔑 LLM Provider Options

### Option A: Google Gemini (Recommended — free tier)
1. Go to [https://aistudio.google.com](https://aistudio.google.com)
2. Create an API key (free, no credit card)
3. Set in `.env`:
   ```
   LLM_PROVIDER=gemini
   GEMINI_API_KEY=your_key
   ```

### Option B: Groq (Extremely fast, free tier)
1. Sign up at [https://console.groq.com](https://console.groq.com)
2. Create an API key
3. Set in `.env`:
   ```
   LLM_PROVIDER=groq
   GROQ_API_KEY=your_key
   ```

### Option C: Ollama (Fully offline, no API key)
1. Install Ollama: [https://ollama.ai](https://ollama.ai)
2. Pull a model: `ollama pull llama3`
3. Set in `.env`:
   ```
   LLM_PROVIDER=ollama
   OLLAMA_MODEL=llama3
   ```

---

## 🐘 PostgreSQL Setup (Optional)

```bash
# Create database
createdb docker_monitor

# Set connection string in .env
DATABASE_URL=postgresql://postgres:password@localhost:5432/docker_monitor
```

The schema is auto-created on first run.

---

## 💬 Sample Queries

| Query | What it does |
|---|---|
| `show all containers` | Lists every container |
| `which containers are restarting?` | Finds containers in restart loop |
| `show unhealthy services` | Lists health-check failures |
| `what crashed in the last hour?` | Exited containers from last 60 min |
| `show logs for nginx` | Retrieves last 100 log lines |
| `are there any stopped containers?` | Lists stopped/paused containers |
| `show running containers` | Active containers only |

---

## 🤖 Agent Loop Explained

```
User Query: "show restarting containers from last 2 hours"
     │
     ▼ Step 1 — Parse Intent
     LLM → {"action": "restarting", "duration": 120, "intent": "debug"}
     │
     ▼ Step 2 — Execute Docker Action
     DockerService.list_restarting(duration=120)
     │
     ▼ Step 3 — Inspect Results
     0 containers found (no recent restarts)
     │
     ▼ Step 4 — Retry (automatic)
     LLM suggests: try "exited"
     DockerService.list_exited(duration=120) → 2 containers found ✓
     │
     ▼ Step 5 — Generate Response
     LLM → "Two containers exited in the past 2 hours and may need investigation."
```

---

## 🏅 Hackathon Evaluation Checklist

| Criteria | Implementation |
|---|---|
| ✅ End-to-end usability | Full working UI with error handling and demo mode |
| ✅ Service/API integration | Gemini / Groq / Ollama LLM + Docker SDK |
| ✅ Agent loop | 5-step loop with validation and retry |
| ✅ Code quality | OOP, logging, validation, exception handling |
| ✅ Documentation | Prompt notes, README, inline docstrings |
| ✅ AI capability | Translation + commentary + retry reasoning |

---

## 🛠 Classes Reference

| Class | File | Responsibility |
|---|---|---|
| `DockerService` | `services/docker_service.py` | Docker daemon interface |
| `ContainerAnalyzer` | `services/docker_service.py` | Container data enrichment |
| `LLMTranslator` | `services/llm_service.py` | NL → JSON + AI summaries |
| `AgentExecutor` | `services/agent_loop.py` | 5-step agent orchestration |
| `AgentResult` | `services/agent_loop.py` | Structured agent output |
| `DashboardRenderer` | `app.py` | All Streamlit rendering |
| `DatabaseService` | `services/db_service.py` | PostgreSQL history |
| `IntentParser` | `utils/parser.py` | JSON extraction/validation |
| `QueryValidator` | `utils/validators.py` | Input safety checks |
| `IntentValidator` | `utils/validators.py` | Intent schema validation |
| `DockerResultValidator` | `utils/validators.py` | Docker result checks |
