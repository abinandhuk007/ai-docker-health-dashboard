"""
app.py — Docker Assistant
Professional SaaS light-theme dashboard.
All backend logic (Docker SDK, LLM, agent loop) is UNCHANGED.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st
from loguru import logger

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from services.agent_loop import AgentExecutor, AgentResult
from services.db_service import DatabaseService
from services.intent_engine import LLMAction


# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Docker Assistant",
    page_icon="🐳",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─────────────────────────────────────────────────────────────────────────────
# CSS — Professional SaaS light theme
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>

/* ── GLOBAL ─────────────────────────────────────────────────────────────── */
html, body, .stApp {
    background-color: #F8FAFC !important;
    color: #0F172A !important;
    font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI",
                 Roboto, "Helvetica Neue", Arial, sans-serif !important;
}
.block-container {
    padding-top: 1.8rem !important;
    padding-bottom: 3rem !important;
    max-width: 1320px;
}

/* ── STREAMLIT TOOLBAR ───────────────────────────────────────────────────── */
header[data-testid="stHeader"] { display: none !important; }

/* ── SIDEBAR ─────────────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background-color: #EEF2FF !important;
    border-right: 1.5px solid #CBD5E1 !important;
}
section[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.2rem !important;
}
section[data-testid="stSidebar"] * { color: #0F172A !important; }
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] .stMarkdown span { color: #475569 !important; }
section[data-testid="stSidebar"] .section-label   { color: #4F46E5 !important; }
section[data-testid="stSidebar"] hr               { border-color: #C7D2FE !important; }

/* Sidebar sample-query buttons */
section[data-testid="stSidebar"] .stButton > button {
    background: #FFFFFF !important;
    border: 1px solid #C7D2FE !important;
    color: #3730A3 !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    text-align: left !important;
    justify-content: flex-start !important;
    padding: 7px 12px !important;
    border-radius: 8px !important;
    box-shadow: 0 1px 2px rgba(79,70,229,0.06) !important;
    transition: all 0.15s ease !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: #E0E7FF !important;
    border-color: #4F46E5 !important;
    color: #3730A3 !important;
}

/* ── TYPOGRAPHY ──────────────────────────────────────────────────────────── */
h1, h2, h3, h4, h5, h6 { color: #0F172A !important; font-weight: 700 !important; }
p, li    { color: #475569 !important; }
label    { color: #475569 !important; }
.stMarkdown p { color: #475569 !important; }

/* ── KPI METRIC CARDS ────────────────────────────────────────────────────── */
[data-testid="metric-container"] {
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 16px !important;
    padding: 22px 24px !important;
    box-shadow: 0 1px 3px rgba(15,23,42,0.06),
                0 4px 12px rgba(15,23,42,0.04) !important;
    transition: box-shadow 0.2s ease, transform 0.2s ease !important;
}
[data-testid="metric-container"]:hover {
    box-shadow: 0 4px 20px rgba(37,99,235,0.10),
                0 1px 4px rgba(15,23,42,0.06) !important;
    transform: translateY(-2px) !important;
}
[data-testid="metric-container"] label {
    color: #64748B !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.07em !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #0F172A !important;
    font-size: 2.25rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.02em !important;
}
[data-testid="stMetricDelta"] { font-size: 0.78rem !important; }

/* ── SEARCH / TEXT INPUT ─────────────────────────────────────────────────── */
.stTextInput > div > div > input {
    background: #FFFFFF !important;
    border: 1.5px solid #CBD5E1 !important;
    border-radius: 12px !important;
    color: #0F172A !important;
    font-size: 1rem !important;
    padding: 14px 18px !important;
    height: 52px !important;
    box-shadow: 0 1px 3px rgba(15,23,42,0.06) !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
.stTextInput > div > div > input:focus {
    border-color: #2563EB !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.12) !important;
    outline: none !important;
}
.stTextInput > div > div > input::placeholder { color: #94A3B8 !important; }

/* ── BUTTONS ─────────────────────────────────────────────────────────────── */
.stButton > button {
    background: #FFFFFF !important;
    border: 1.5px solid #E2E8F0 !important;
    color: #475569 !important;
    border-radius: 10px !important;
    font-weight: 500 !important;
    font-size: 0.875rem !important;
    transition: all 0.15s ease !important;
    box-shadow: 0 1px 2px rgba(15,23,42,0.05) !important;
}
.stButton > button:hover {
    border-color: #2563EB !important;
    color: #2563EB !important;
    background: #EFF6FF !important;
}
.stButton > button[kind="primary"] {
    background: #2563EB !important;
    border-color: #2563EB !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
    height: 52px !important;
    font-size: 0.95rem !important;
    border-radius: 12px !important;
    box-shadow: 0 2px 8px rgba(37,99,235,0.25) !important;
}
.stButton > button[kind="primary"]:hover {
    background: #1D4ED8 !important;
    border-color: #1D4ED8 !important;
    box-shadow: 0 4px 14px rgba(37,99,235,0.30) !important;
}

/* ── TABS ────────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background: #F1F5F9 !important;
    border-radius: 10px !important;
    padding: 4px !important;
    border: 1px solid #E2E8F0 !important;
    gap: 2px !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 7px !important;
    color: #64748B !important;
    font-weight: 500 !important;
    padding: 7px 22px !important;
    font-size: 0.875rem !important;
}
.stTabs [aria-selected="true"] {
    background: #FFFFFF !important;
    color: #0F172A !important;
    font-weight: 600 !important;
    box-shadow: 0 1px 4px rgba(15,23,42,0.08) !important;
}

/* ── DATAFRAME / TABLE ───────────────────────────────────────────────────── */
.stDataFrame {
    border-radius: 12px !important;
    overflow: hidden !important;
    border: 1px solid #E2E8F0 !important;
    box-shadow: 0 1px 4px rgba(15,23,42,0.05) !important;
}
[data-testid="stDataFrame"]        { background: #FFFFFF !important; border-radius: 12px !important; }
[data-testid="stDataFrame"] > div  { background: #FFFFFF !important; }
[data-testid="stDataFrame"] iframe { background: #FFFFFF !important; }
.stDataFrame thead tr th {
    background-color: #F1F5F9 !important;
    color: #0F172A !important;
    font-weight: 600 !important;
    font-size: 0.78rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    border-bottom: 2px solid #E2E8F0 !important;
}
.stDataFrame tbody tr td {
    background-color: #FFFFFF !important;
    color: #0F172A !important;
    font-size: 0.875rem !important;
    border-bottom: 1px solid #F1F5F9 !important;
}
.stDataFrame tbody tr:nth-child(even) td { background-color: #F8FAFC !important; }
.stDataFrame tbody tr:hover td           { background-color: #EFF6FF !important; }

/* ── EXPANDER ────────────────────────────────────────────────────────────── */
.streamlit-expanderHeader {
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 8px !important;
    color: #475569 !important;
    font-size: 0.875rem !important;
}
.streamlit-expanderContent {
    background: #F8FAFC !important;
    border: 1px solid #E2E8F0 !important;
    border-top: none !important;
    border-radius: 0 0 8px 8px !important;
}

/* ── SELECT / DROPDOWN ───────────────────────────────────────────────────── */
.stSelectbox > div > div {
    background: #FFFFFF !important;
    border: 1.5px solid #CBD5E1 !important;
    border-radius: 8px !important;
    color: #0F172A !important;
}
.stSelectbox > div > div:focus-within {
    border-color: #2563EB !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.12) !important;
}

/* ── TOGGLE ──────────────────────────────────────────────────────────────── */
.stCheckbox > label { color: #0F172A !important; }
.stToggle > label   { color: #0F172A !important; }

/* ── DIVIDER ─────────────────────────────────────────────────────────────── */
hr { border-color: #E2E8F0 !important; margin: 14px 0 !important; }

/* ── CODE BLOCKS ─────────────────────────────────────────────────────────── */
.stCode, code, pre {
    background: #F1F5F9 !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 8px !important;
    color: #1E40AF !important;
}

/* ── ALERTS ──────────────────────────────────────────────────────────────── */
.stAlert { border-radius: 10px !important; }
[data-testid="stInfoMessage"]    { background: #EFF6FF !important; border-color: #2563EB !important; }
[data-testid="stWarningMessage"] { background: #FFFBEB !important; border-color: #F59E0B !important; }
[data-testid="stErrorMessage"]   { background: #FEF2F2 !important; border-color: #EF4444 !important; }

/* ── CAPTION ─────────────────────────────────────────────────────────────── */
.stCaption, caption { color: #94A3B8 !important; font-size: 0.78rem !important; }

/* ── SPINNER ─────────────────────────────────────────────────────────────── */
.stSpinner > div { color: #2563EB !important; }

/* ═══════════════════════════════════════════════════════════════════════════
   CUSTOM COMPONENT STYLES
   ═══════════════════════════════════════════════════════════════════════════ */

/* Section label */
.section-label {
    font-size: 0.7rem;
    font-weight: 700;
    color: #94A3B8;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    margin-bottom: 8px;
    margin-top: 2px;
    display: flex;
    align-items: center;
    gap: 5px;
}

/* AI intent chips */
.intent-chip {
    display: inline-block;
    background: #EFF6FF;
    color: #2563EB;
    border: 1px solid #BFDBFE;
    border-radius: 8px;
    padding: 5px 14px;
    font-size: 0.82rem;
    font-weight: 600;
    font-family: "JetBrains Mono", "Fira Code", monospace;
    margin: 3px 4px 3px 0;
}
.intent-row { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 4px; }

/* AI Summary card */
.ai-card {
    background: #FFFFFF;
    border: 1px solid #DBEAFE;
    border-left: 4px solid #2563EB;
    border-radius: 12px;
    padding: 20px 24px;
    margin: 4px 0 16px 0;
    box-shadow: 0 1px 4px rgba(37,99,235,0.07), 0 4px 16px rgba(37,99,235,0.04);
}
.ai-card .ai-title {
    color: #1E40AF;
    font-size: 0.8rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    gap: 6px;
}
.ai-card .ai-summary   { color: #0F172A; font-weight: 600; font-size: 0.95rem; margin-bottom: 6px; line-height: 1.5; }
.ai-card .ai-explain   { color: #475569; font-size: 0.875rem; line-height: 1.65; margin-bottom: 8px; }
.ai-card .ai-recommend { color: #2563EB; font-size: 0.875rem; font-weight: 500; }

/* LLM Action + JSON — equal-height aligned grid */
.llm-action-grid {
    display: grid;
    grid-template-columns: 1fr 2fr;
    gap: 16px;
    align-items: stretch;
    margin-top: 4px;
}
.llm-action-badge {
    background: #FAFAFA;
    border: 1.5px solid #E2E8F0;
    border-radius: 12px;
    padding: 24px 20px;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 160px;
    box-shadow: 0 1px 3px rgba(15,23,42,0.05);
}
.llm-action-json {
    background: #FFFFFF;
    border: 1.5px solid #E2E8F0;
    border-radius: 12px;
    padding: 18px 20px;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    min-height: 160px;
    box-shadow: 0 1px 3px rgba(15,23,42,0.05);
}

/* Step trace */
.step-trace {
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 14px 18px;
    font-family: "JetBrains Mono", "Fira Code", "Courier New", monospace;
    font-size: 0.8rem;
    color: #64748B;
    line-height: 1.9;
}
.step-trace .ok { color: #16A34A; font-weight: 600; }

/* Auto-refresh pill */
.refresh-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #DCFCE7;
    border: 1px solid #BBF7D0;
    border-radius: 20px;
    padding: 4px 12px;
    color: #15803D;
    font-size: 0.75rem;
    font-weight: 600;
}
.refresh-dot {
    width: 7px; height: 7px;
    background: #22C55E;
    border-radius: 50%;
    animation: pulse-green 1.4s infinite;
}
@keyframes pulse-green {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%       { opacity: 0.35; transform: scale(0.8); }
}

/* Demo banner */
.demo-banner {
    background: #FFFBEB;
    border: 1px solid #FDE68A;
    border-radius: 8px;
    padding: 8px 14px;
    color: #92400E;
    font-size: 0.82rem;
    margin-top: 8px;
}

/* Empty state */
.empty-state { text-align: center; padding: 80px 20px; }
.empty-state .icon { font-size: 3.5rem; margin-bottom: 16px; }
.empty-state h3 { color: #0F172A; font-size: 1.2rem; font-weight: 700; margin-bottom: 8px; }
.empty-state p  { color: #64748B; font-size: 0.9rem; }

</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────────────────────

def _init_state() -> None:
    defaults = {
        "result":           None,
        "history":          [],
        "agent_ready":      False,
        "prefill_query":    "",
        "auto_run_query":   "",
        "auto_refresh":     False,
        "refresh_interval": 30,
        "last_refresh_ts":  0.0,
        "last_query":       "",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ─────────────────────────────────────────────────────────────────────────────
# Service singletons — UNCHANGED
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def get_executor() -> AgentExecutor:
    return AgentExecutor()

@st.cache_resource(show_spinner=False)
def get_db() -> DatabaseService:
    return DatabaseService()


# ─────────────────────────────────────────────────────────────────────────────
# DashboardRenderer — UI only
# ─────────────────────────────────────────────────────────────────────────────

class DashboardRenderer:
    STATUS_EMOJI = {
        "running": "🟢", "restarting": "🟡", "exited": "🔴",
        "stopped": "🔴", "paused": "🟣", "unknown": "⚪",
    }
    HEALTH_EMOJI = {
        "healthy": "✅", "unhealthy": "❌", "starting": "⏳", "unknown": "❓",
    }

    # ── KPI metric cards ─────────────────────────────────────────────────────

    def render_metric_cards(self, containers: list[dict]) -> None:
        total      = len(containers)
        running    = sum(1 for c in containers if c.get("status") == "running")
        restarting = sum(1 for c in containers if c.get("status") == "restarting")
        unhealthy  = sum(
            1 for c in containers
            if c.get("health") == "unhealthy" or c.get("status") == "restarting"
        )
        exited = sum(1 for c in containers if c.get("status") == "exited")

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("📦 Total Containers", total)
        c2.metric("▶️ Running",          running)
        c3.metric("⏹ Exited",            exited,
                  delta=f"-{exited}" if exited else None, delta_color="inverse")
        c4.metric("🔄 Restarting",       restarting,
                  delta=f"+{restarting}" if restarting else None, delta_color="inverse")
        c5.metric("❗ Unhealthy",        unhealthy,
                  delta=f"+{unhealthy}" if unhealthy else None, delta_color="inverse")

    # ── Intent chips (redesigned) ─────────────────────────────────────────────

    def render_intent_info(
        self, intent: dict, retried: bool, retry_action: str | None
    ) -> None:
        action    = intent.get("action", "?")
        intent_t  = intent.get("intent", "?")
        dur       = intent.get("duration")
        name      = intent.get("container_name")
        dur_str   = f"{dur}m" if dur else "any"
        name_str  = name or "any"

        chips = [
            f"action: {action}",
            f"intent: {intent_t}",
            f"duration: {dur_str}",
            f"container: {name_str}",
        ]
        chips_html = "".join(f"<span class='intent-chip'>{c}</span>" for c in chips)

        badge = ""
        if retried and retry_action:
            badge = (
                f"<span style='margin-left:8px; background:#FEF3C7; color:#B45309; "
                f"border:1px solid #FDE68A; border-radius:8px; padding:5px 12px; "
                f"font-size:0.78rem; font-weight:600;'>"
                f"⟳ Retried → {retry_action}</span>"
            )
        elif intent.get("_source") == "keyword_fallback":
            badge = (
                "<span style='margin-left:8px; background:#F1F5F9; color:#64748B; "
                "border:1px solid #E2E8F0; border-radius:8px; padding:5px 12px; "
                "font-size:0.78rem; font-weight:500;'>"
                "ℹ️ Keyword fallback</span>"
            )

        st.markdown(
            f"<div class='intent-row'>{chips_html}{badge}</div>",
            unsafe_allow_html=True,
        )

    # ── LLM Action Output (fixed alignment) ──────────────────────────────────

    def render_llm_action_box(self, llm_action: "LLMAction") -> None:
        import json as _json

        ACTION_COLOUR = {
            "list_containers":   "#2563EB", "container_logs":    "#7C3AED",
            "inspect_container": "#0891B2", "memory_usage":      "#D97706",
            "cpu_usage":         "#EA580C", "restart_container": "#DC2626",
            "stop_container":    "#DC2626", "container_stats":   "#059669",
            "unknown":           "#64748B",
        }
        ACTION_DESC = {
            "list_containers":   "List / filter containers by status",
            "container_logs":    "Retrieve container log output",
            "inspect_container": "Inspect container metadata",
            "memory_usage":      "Show memory resource usage",
            "cpu_usage":         "Show CPU resource usage",
            "restart_container": "Restart a container",
            "stop_container":    "Stop a container",
            "container_stats":   "Show container resource stats",
            "unknown":           "Query could not be mapped",
        }

        colour    = ACTION_COLOUR.get(llm_action.action, "#64748B")
        desc      = ACTION_DESC.get(llm_action.action, "")
        src_label = (
            llm_action.source if llm_action.source != "keyword_fallback"
            else "Keyword Fallback"
        )
        json_str  = _json.dumps(llm_action.to_display_dict(), indent=2)

        col_left, col_right = st.columns([1, 2], gap="medium")

        with col_left:
            st.markdown(
                f"""
                <div style="background:{colour}08; border:1.5px solid {colour}30;
                    border-top:3px solid {colour}; border-radius:12px;
                    padding:24px 20px; text-align:center;
                    box-shadow:0 1px 4px rgba(15,23,42,0.05);">
                    <div style="font-size:0.65rem; font-weight:700; color:{colour};
                                text-transform:uppercase; letter-spacing:.1em;
                                margin-bottom:10px;">Docker Action</div>
                    <div style="font-size:1.1rem; font-weight:800; color:{colour};
                                font-family:monospace; margin-bottom:10px;
                                letter-spacing:-0.01em;">{llm_action.action}</div>
                    <div style="font-size:0.76rem; color:#64748B; line-height:1.5;
                                margin-bottom:12px;">{desc}</div>
                    <div style="font-size:0.68rem; color:#94A3B8;">via {src_label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col_right:
            st.markdown(
                "<div style='font-size:0.65rem; font-weight:700; color:#94A3B8; "
                "text-transform:uppercase; letter-spacing:.09em; margin-bottom:6px;'>"
                "⬡ Translated JSON</div>",
                unsafe_allow_html=True,
            )
            st.code(json_str, language="json")

            detail_parts = []
            if llm_action.filter and llm_action.action == "list_containers":
                detail_parts.append(f"**Filter:** `{llm_action.filter}`")
            if llm_action.container:
                detail_parts.append(f"**Container:** `{llm_action.container}`")
            if llm_action.duration:
                detail_parts.append(f"**Duration:** `{llm_action.duration} min`")
            if detail_parts:
                st.caption("  ·  ".join(detail_parts))

        if llm_action.action == "unknown":
            st.warning("⚠️ Query not recognised. Try: 'show unhealthy containers'.")

    # ── Container table ───────────────────────────────────────────────────────

    def render_container_table(self, containers: list[dict]) -> None:
        if not containers:
            st.info("No containers match the current query.")
            return

        df = pd.DataFrame(containers)
        display_cols = {
            "name": "Container", "status": "Status", "health": "Health",
            "image": "Image", "uptime": "Uptime", "restart_count": "Restarts",
            "ports": "Ports", "cpu_percent": "CPU %", "mem_mb": "Mem (MB)",
        }
        existing   = {k: v for k, v in display_cols.items() if k in df.columns}
        df_display = df[list(existing.keys())].rename(columns=existing)

        if "CPU %" in df_display.columns:
            df_display["CPU %"] = df_display["CPU %"].apply(lambda x: f"{x:.2f}")
        if "Mem (MB)" in df_display.columns:
            df_display["Mem (MB)"] = df_display["Mem (MB)"].apply(lambda x: f"{x:.2f}")

        if "Status" in df_display.columns:
            df_display["Status"] = df_display["Status"].apply(
                lambda s: f"{self.STATUS_EMOJI.get(s, '⚪')} {s}"
            )
        if "Health" in df_display.columns:
            df_display["Health"] = df_display["Health"].apply(
                lambda h: f"{self.HEALTH_EMOJI.get(h, '❓')} {h}"
            )

        def row_style(row: pd.Series):
            s = str(row.get("Status", ""))
            if "restarting" in s: return ["background-color:#FFFBEB"] * len(row)
            if "exited" in s or "stopped" in s: return ["background-color:#FEF2F2"] * len(row)
            return [""] * len(row)

        st.dataframe(
            df_display.style.apply(row_style, axis=1),
            use_container_width=True,
            height=min(420, 60 + len(df_display) * 40),
        )

    # ── Status chart ──────────────────────────────────────────────────────────

    def render_status_chart(self, containers: list[dict]) -> None:
        if not containers:
            return
        try:
            import plotly.express as px
            df = pd.DataFrame(containers)
            sc = df["status"].value_counts().reset_index()
            sc.columns = ["Status", "Count"]
            colour_map = {
                "running": "#22C55E", "restarting": "#F59E0B", "exited": "#EF4444",
                "paused": "#8B5CF6", "stopped": "#EF4444", "unknown": "#94A3B8",
            }
            fig = px.pie(sc, values="Count", names="Status",
                         color="Status", color_discrete_map=colour_map, hole=0.55)
            fig.update_traces(
                textposition="outside", textinfo="label+percent",
                textfont_color="#475569",
                marker=dict(line=dict(color="#FFFFFF", width=2)),
            )
            fig.update_layout(
                title=dict(text="Container Status Distribution",
                           font=dict(color="#0F172A", size=14), x=0.5),
                paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
                font=dict(color="#475569"),
                legend=dict(font=dict(color="#475569"), bgcolor="rgba(0,0,0,0)"),
                margin=dict(t=50, b=10, l=10, r=10), height=320,
            )
            st.markdown(
                "<div style='background:#FFFFFF; border:1px solid #E2E8F0; "
                "border-radius:12px; padding:8px; box-shadow:0 1px 4px rgba(15,23,42,0.05);'>",
                unsafe_allow_html=True,
            )
            st.plotly_chart(fig, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
        except ImportError:
            st.bar_chart(pd.DataFrame(containers)["status"].value_counts())

    # ── AI Summary ────────────────────────────────────────────────────────────

    def render_ai_summary(self, summary: dict[str, str], provider: str) -> None:
        if not summary:
            return
        st.markdown(
            f"""
            <div class="ai-card">
                <div class="ai-title">🤖 AI Summary
                    <span style="font-size:0.68rem; color:#94A3B8;
                                 font-weight:400;">via {provider}</span>
                </div>
                <div class="ai-summary">{summary.get('summary', '')}</div>
                <div class="ai-explain">{summary.get('explanation', '')}</div>
                <div class="ai-recommend">💡 {summary.get('recommendation', '')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ── Agent step trace ──────────────────────────────────────────────────────

    def render_step_trace(self, steps: list[str], elapsed_ms: float) -> None:
        with st.expander("🔍 Agent Loop Trace", expanded=False):
            lines = "\n".join(f'  <span class="ok">✓</span> {s}' for s in steps)
            st.markdown(
                f"<div class='step-trace'>{lines}"
                f"\n\n  <span style='color:#94A3B8;'>⏱ Completed in "
                f"{elapsed_ms:.0f} ms</span></div>",
                unsafe_allow_html=True,
            )

    # ── Log viewer ────────────────────────────────────────────────────────────

    def render_logs(self, logs: str) -> None:
        if not logs:
            return
        st.markdown(
            "<div style='background:#FFFFFF; border:1px solid #E2E8F0; "
            "border-radius:12px; padding:20px; "
            "box-shadow:0 1px 4px rgba(15,23,42,0.05); margin-bottom:16px;'>",
            unsafe_allow_html=True,
        )
        st.subheader("📋 Container Logs")
        st.code(logs, language="bash")
        st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────

def render_sidebar(executor: AgentExecutor, db: DatabaseService) -> None:
    with st.sidebar:

        # ── Branding ─────────────────────────────────────────────────────────
        st.markdown(
            """
            <div style="padding:6px 0 18px 0; border-bottom:1.5px solid #C7D2FE;
                        margin-bottom:18px;">
                <div style="display:flex; align-items:center; gap:12px;">
                    <div style="background:#EEF2FF; border:2px solid #C7D2FE;
                                border-radius:14px; width:48px; height:48px;
                                display:flex; align-items:center;
                                justify-content:center; font-size:1.5rem;
                                flex-shrink:0;">🐳</div>
                    <div>
                        <div style="font-size:1.35rem; font-weight:800;
                                    color:#1E1B4B; letter-spacing:-0.03em;
                                    line-height:1.15;">Docker Assistant</div>
                        <div style="font-size:0.72rem; color:#6366F1;
                                    font-weight:500; margin-top:3px;
                                    letter-spacing:0.01em;">
                            AI-powered container monitoring
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── System Status ─────────────────────────────────────────────────────
        llm        = executor._llm
        docker_svc = executor._docker
        llm_ok     = llm.is_available
        docker_ok  = not docker_svc.is_demo

        st.markdown("<div class='section-label'>⚙️ System Status</div>",
                    unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        for col, label, ok, short in [
            (c1, "LLM",    llm_ok,    llm.provider_name[:12]),
            (c2, "Docker", docker_ok, "Live" if docker_ok else "Demo"),
        ]:
            colour = "#15803D" if ok else "#B45309"
            bg     = "#DCFCE7" if ok else "#FEF3C7"
            border = "#86EFAC" if ok else "#FDE68A"
            icon   = "✅" if ok else ("⚠️" if label == "LLM" else "🎭")
            with col:
                st.markdown(
                    f"<div style='background:{bg}; border:1px solid {border}; "
                    f"border-radius:10px; padding:10px 8px; text-align:center; "
                    f"box-shadow:0 1px 3px rgba(15,23,42,0.06);'>"
                    f"<div style='font-size:0.6rem; color:{colour}; font-weight:700; "
                    f"text-transform:uppercase; letter-spacing:.07em;'>{label}</div>"
                    f"<div style='color:{colour}; font-weight:700; font-size:0.76rem; "
                    f"margin-top:3px; white-space:nowrap;'>{icon} {short}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        if not llm_ok and os.getenv("LLM_PROVIDER", "").lower() == "ollama":
            st.warning(
                "Ollama not running.\n\n"
                "```\nollama serve\nollama pull llama3\n```\n"
                "Keyword fallback is active.", icon="🦙",
            )
        if docker_svc.is_demo:
            st.markdown(
                "<div class='demo-banner'>🎭 <strong>Demo Mode</strong><br>"
                "Start Docker Desktop for live data.</div>",
                unsafe_allow_html=True,
            )

        st.divider()

        # ── Auto Refresh ──────────────────────────────────────────────────────
        st.markdown("<div class='section-label'>🔄 Auto Refresh</div>",
                    unsafe_allow_html=True)

        auto_refresh = st.toggle(
            "Enable Auto Refresh",
            value=st.session_state["auto_refresh"],
            key="auto_refresh_toggle",
        )
        st.session_state["auto_refresh"] = auto_refresh

        if auto_refresh:
            interval = st.selectbox(
                "Interval",
                options=[10, 30, 60],
                index=[10, 30, 60].index(st.session_state["refresh_interval"]),
                format_func=lambda x: f"{x} seconds",
                key="refresh_interval_select",
                label_visibility="collapsed",
            )
            st.session_state["refresh_interval"] = interval
            st.markdown(
                f"<div class='refresh-pill'><div class='refresh-dot'></div>"
                f"Refreshing every {interval}s</div>",
                unsafe_allow_html=True,
            )
        else:
            st.caption("Auto refresh is off.")

        st.divider()

        # ── Sample Queries ────────────────────────────────────────────────────
        st.markdown("<div class='section-label'>💡 Sample Queries</div>",
                    unsafe_allow_html=True)

        for q in [
            "Show all containers",
            "Which containers are restarting?",
            "Show unhealthy services",
            "What crashed in the last hour?",
            "Show running containers",
            "Show logs for nginx",
            "Which containers exited recently?",
        ]:
            if st.button(q, key=f"sample_{q}", use_container_width=True):
                st.session_state["auto_run_query"] = q
                st.session_state["prefill_query"]  = q
                st.session_state["last_query"]     = q
                st.rerun()

        st.divider()

        # ── Recent Queries ────────────────────────────────────────────────────
        st.markdown("<div class='section-label'>📜 Recent Queries</div>",
                    unsafe_allow_html=True)

        history = st.session_state.get("history", [])
        if history:
            for item in reversed(history[-8:]):
                st.markdown(
                    f"<div style='font-size:0.76rem; color:#475569; padding:4px 0; "
                    f"border-bottom:1px solid #E0E7FF; line-height:1.4;'>"
                    f"<span style='background:#E0E7FF; color:#3730A3; "
                    f"border-radius:4px; padding:1px 6px; font-size:0.68rem; "
                    f"font-weight:700; font-family:monospace;'>{item['action']}</span> "
                    f"<span style='color:#0F172A;'>{item['query'][:34]}…</span> "
                    f"<span style='color:#94A3B8;'>({item['count']})</span></div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No queries yet.")

        if db.is_available:
            db_history = db.get_recent_history(5)
            if db_history:
                st.divider()
                st.markdown("<div class='section-label'>🗄️ DB History</div>",
                            unsafe_allow_html=True)
                for row in db_history:
                    st.caption(
                        f"[{row['action']}] {row['query'][:32]}… "
                        f"({row['result_count']} results)"
                    )


# ─────────────────────────────────────────────────────────────────────────────
# Auto-refresh helper — UNCHANGED logic
# ─────────────────────────────────────────────────────────────────────────────

def _should_auto_refresh() -> bool:
    if not st.session_state.get("auto_refresh", False):
        return False
    if not st.session_state.get("last_query", ""):
        return False
    interval = st.session_state.get("refresh_interval", 30)
    elapsed  = time.time() - st.session_state.get("last_refresh_ts", 0.0)
    return elapsed >= interval


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    _init_state()
    executor = get_executor()
    db       = get_db()
    renderer = DashboardRenderer()

    render_sidebar(executor, db)

    # ── Top header bar ────────────────────────────────────────────────────────
    refresh_active = st.session_state.get("auto_refresh", False)

    # Auto-refresh pill shown inline above search bar (no header bar)
    if refresh_active:
        st.markdown(
            "<div style='margin-bottom:8px;'>"
            "<span class='refresh-pill'>"
            "<span class='refresh-dot'></span>Auto Refresh ON</span>"
            "</div>",
            unsafe_allow_html=True,
        )

    # ── Search bar + Ask button ───────────────────────────────────────────────
    prefill = st.session_state.get("prefill_query", "")
    if prefill and st.session_state.get("query_input", "") != prefill:
        st.session_state["query_input"] = prefill

    col_input, col_btn = st.columns([5, 1])
    with col_input:
        query = st.text_input(
            label="Ask",
            placeholder='Ask about your containers — e.g. "show restarting containers"',
            label_visibility="collapsed",
            key="query_input",
        )
    with col_btn:
        ask_clicked = st.button("🔍 Ask", type="primary", use_container_width=True)

    # ── Execute agent loop — UNCHANGED ───────────────────────────────────────
    auto_query      = st.session_state.pop("auto_run_query", "")
    refresh_trigger = _should_auto_refresh()

    if auto_query.strip():
        run_query = auto_query.strip()
    elif ask_clicked and query.strip():
        run_query = query.strip()
    elif refresh_trigger:
        run_query = st.session_state.get("last_query", "")
    else:
        run_query = ""

    if run_query:
        st.session_state["prefill_query"]   = ""
        st.session_state["last_query"]      = run_query
        st.session_state["last_refresh_ts"] = time.time()

        with st.spinner("🤖 Agent thinking…"):
            result: AgentResult = executor.run(run_query)

        st.session_state["result"] = result

        if result and not result.error:
            db.save_query(
                query=result.query,
                action=result.intent.get("action", ""),
                intent_tag=result.intent.get("intent", ""),
                result_count=len(result.containers),
                retried=result.retried,
                elapsed_ms=result.elapsed_ms,
                summary=result.summary.get("summary", ""),
            )
            st.session_state["history"].append({
                "query":  result.query,
                "action": result.intent.get("action", ""),
                "count":  len(result.containers),
            })

    # ── Auto-refresh countdown ────────────────────────────────────────────────
    if st.session_state.get("auto_refresh") and st.session_state.get("last_query"):
        interval  = st.session_state.get("refresh_interval", 30)
        elapsed   = time.time() - st.session_state.get("last_refresh_ts", 0.0)
        remaining = max(0, int(interval - elapsed))
        st.markdown(
            f"<div style='font-size:0.75rem; color:#94A3B8; margin:6px 0 12px 0;'>"
            f"🔄 Next refresh in <strong style='color:#2563EB;'>{remaining}s</strong>"
            f" &nbsp;(interval: {interval}s)</div>",
            unsafe_allow_html=True,
        )
        if remaining == 0:
            st.rerun()

    # ── Results ───────────────────────────────────────────────────────────────
    result: AgentResult | None = st.session_state.get("result")

    if result is None:
        st.markdown(
            """<div class="empty-state">
                <div class="icon">🐳</div>
                <h3>Ready to monitor your Docker environment</h3>
                <p>Type a natural language question above or pick a sample query
                   from the sidebar.</p>
            </div>""",
            unsafe_allow_html=True,
        )
        return

    if result.error:
        st.error(f"❌ {result.error}")
        return

    # ── AI Understood ─────────────────────────────────────────────────────────
    st.markdown(
        "<div class='section-label' style='margin-top:4px;'>🧠 AI Understood</div>",
        unsafe_allow_html=True,
    )
    renderer.render_intent_info(result.intent, result.retried, result.retry_action)

    # ── LLM Action Output ─────────────────────────────────────────────────────
    if result.llm_action:
        st.markdown(
            "<hr style='border:none;border-top:1px solid #E2E8F0;margin:16px 0;'>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='section-label'>🤖 LLM Action Output</div>",
            unsafe_allow_html=True,
        )
        renderer.render_llm_action_box(result.llm_action)

    st.markdown(
        "<hr style='border:none;border-top:2px solid #E2E8F0;margin:20px 0;'>",
        unsafe_allow_html=True,
    )

    # ── KPI cards ─────────────────────────────────────────────────────────────
    if result.containers:
        renderer.render_metric_cards(result.containers)
        st.markdown(
            "<hr style='border:none;border-top:1px solid #E2E8F0;margin:20px 0;'>",
            unsafe_allow_html=True,
        )

    # ── AI Summary ────────────────────────────────────────────────────────────
    if result.summary:
        renderer.render_ai_summary(result.summary, executor._llm.provider_name)

    # ── Logs ──────────────────────────────────────────────────────────────────
    if result.logs:
        renderer.render_logs(result.logs)

    # ── Table + Chart tabs ────────────────────────────────────────────────────
    if result.containers:
        tab_table, tab_chart = st.tabs(["📊 Container Table", "🥧 Status Chart"])
        with tab_table:
            renderer.render_container_table(result.containers)
        with tab_chart:
            renderer.render_status_chart(result.containers)
    elif not result.logs:
        st.info("No containers matched the query. Try a different question.")

    # ── Agent trace ───────────────────────────────────────────────────────────
    if result.steps:
        st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
        renderer.render_step_trace(result.steps, result.elapsed_ms)

    # ── Demo notice ───────────────────────────────────────────────────────────
    if result.demo_mode:
        st.caption("🎭 Showing demo data — start Docker Desktop to see live containers.")


if __name__ == "__main__":
    main()
