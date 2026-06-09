"""
troubleshoot.py — AI Troubleshooting Insights (Enhancement Only)

Adds a lightweight severity + priority analysis layer on top of already-
retrieved Docker container data.  This module is purely additive — it does
NOT touch the query flow, Gemini intent parser, Docker SDK, or existing UI.

Public API (only two things app.py needs):
    build_insights(containers)  -> TroubleshootReport | None
    render_insights(report)     -> renders Streamlit widgets
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Severity levels
# ---------------------------------------------------------------------------

SEVERITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}

SEVERITY_COLOUR = {
    "Critical": "#ef4444",   # red
    "High":     "#f97316",   # orange
    "Medium":   "#eab308",   # yellow
    "Low":      "#22c55e",   # green
}

SEVERITY_EMOJI = {
    "Critical": "🔴",
    "High":     "🟠",
    "Medium":   "🟡",
    "Low":      "🟢",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ContainerInsight:
    """Insight record for a single container."""
    name: str
    status: str
    severity: str                        # Critical / High / Medium / Low
    why: str                             # Why this status matters
    possible_cause: str                  # Likely root causes
    recommended_action: str             # Concrete next step
    priority_score: int = 0             # Lower = higher priority (for sorting)


@dataclass
class TroubleshootReport:
    """Full troubleshooting report for a result set."""
    insights: list[ContainerInsight] = field(default_factory=list)
    overall_severity: str = "Low"
    priority_container: Optional[ContainerInsight] = None

    @property
    def has_issues(self) -> bool:
        return any(i.severity in ("Critical", "High", "Medium") for i in self.insights)


# ---------------------------------------------------------------------------
# Severity rules
# ---------------------------------------------------------------------------

def _score_container(c: dict[str, Any]) -> tuple[str, int]:
    """
    Assign a severity level and numeric priority score to a container dict.

    Returns:
        (severity_label, priority_score)  — lower score = higher priority
    """
    status = c.get("status", "unknown").lower()
    health = c.get("health", "unknown").lower()
    restarts = int(c.get("restart_count", 0) or 0)

    # Critical — container is crash-looping or repeatedly failing
    if status == "restarting" and restarts >= 5:
        return "Critical", 0
    if status == "restarting":
        return "Critical", 1

    # High — container exited (crashed) or is flagged unhealthy
    if status == "exited":
        return "High", 2
    if health == "unhealthy":
        return "High", 3

    # Medium — health check still starting, or many restarts while running
    if health == "starting":
        return "Medium", 4
    if status == "running" and restarts >= 3:
        return "Medium", 5

    # Low — paused, or running fine
    if status == "paused":
        return "Low", 6

    return "Low", 10


def _build_insight(c: dict[str, Any]) -> ContainerInsight:
    """Build a ContainerInsight for one container dict."""
    status   = c.get("status", "unknown").lower()
    health   = c.get("health", "unknown").lower()
    restarts = int(c.get("restart_count", 0) or 0)
    name     = c.get("name", "unknown")
    image    = c.get("image", "unknown")

    severity, score = _score_container(c)

    # ── Why ──────────────────────────────────────────────────────────
    if status == "restarting":
        why = (
            f"'{name}' is caught in a restart loop "
            f"({'repeated' if restarts >= 5 else 'active'} restarts: {restarts}). "
            "The service is likely unavailable to other containers right now."
        )
    elif status == "exited":
        why = (
            f"'{name}' has stopped unexpectedly. "
            "An exited container means the process inside it terminated, "
            "which could indicate a crash, OOM kill, or a missing dependency."
        )
    elif health == "unhealthy":
        why = (
            f"'{name}' is running but its health check is failing. "
            "The container process is alive but not responding correctly — "
            "requests to this service may be failing silently."
        )
    elif health == "starting":
        why = (
            f"'{name}' health check has not passed yet. "
            "It may still be booting, or the health check endpoint is not ready."
        )
    elif restarts >= 3:
        why = (
            f"'{name}' has restarted {restarts} times even though it is currently running. "
            "This suggests intermittent failures that have been auto-recovered."
        )
    else:
        why = f"'{name}' is running normally with no detected issues."

    # ── Possible cause ────────────────────────────────────────────────
    if status == "restarting":
        possible_cause = (
            "Missing environment variable or secret · Port already in use · "
            "Out-of-memory (OOM) kill · Dependency service not ready · "
            f"Bug or panic inside image '{image}'"
        )
    elif status == "exited":
        possible_cause = (
            "Application crash (non-zero exit code) · OOM kill by Docker · "
            "Missing config file or volume mount · "
            "Dependent service (DB, cache) unreachable"
        )
    elif health in ("unhealthy", "starting"):
        possible_cause = (
            "Health check endpoint returning 5xx or timing out · "
            "Application still initialising · "
            "Wrong health check path configured in Dockerfile"
        )
    elif restarts >= 3:
        possible_cause = (
            "Intermittent network or dependency issue · "
            "Resource limit (CPU/memory) being hit periodically · "
            "Background job crashing on certain inputs"
        )
    else:
        possible_cause = "No anomalies detected."

    # ── Recommended action ────────────────────────────────────────────
    if status == "restarting":
        recommended_action = (
            f"Run `docker logs {name}` to read the crash output. "
            "Look for the last error line before each restart. "
            "Then run `docker inspect {name}` to verify env vars and mounts."
        )
    elif status == "exited":
        recommended_action = (
            f"Run `docker logs {name}` to see why the container stopped. "
            "Check the exit code with `docker inspect {name} --format '{{{{.State.ExitCode}}}}'`. "
            "Exit code 137 = OOM kill; exit code 1 = application error."
        )
    elif health in ("unhealthy", "starting"):
        recommended_action = (
            f"Run `docker inspect {name}` and check the Health section. "
            "View recent health check output with "
            f"`docker inspect {name} --format '{{{{json .State.Health}}}}'`."
        )
    elif restarts >= 3:
        recommended_action = (
            f"Monitor with `docker stats {name}` to check memory/CPU. "
            f"Review logs with `docker logs --tail 50 {name}`."
        )
    else:
        recommended_action = "No action needed. Continue monitoring."

    return ContainerInsight(
        name=name,
        status=status,
        severity=severity,
        why=why,
        possible_cause=possible_cause,
        recommended_action=recommended_action,
        priority_score=score,
    )


# ---------------------------------------------------------------------------
# Public builder
# ---------------------------------------------------------------------------

def build_insights(containers: list[dict[str, Any]]) -> Optional[TroubleshootReport]:
    """
    Build a TroubleshootReport from a list of container dicts.

    Args:
        containers: List already returned by DockerService / AgentResult.

    Returns:
        TroubleshootReport, or None if the list is empty.
    """
    if not containers:
        return None

    insights = [_build_insight(c) for c in containers]

    # Sort: most severe / highest priority first
    insights.sort(key=lambda i: (SEVERITY_ORDER[i.severity], i.priority_score))

    # Overall severity = worst single container
    overall = insights[0].severity if insights else "Low"

    # Priority container = first non-Low insight, else first overall
    priority = next(
        (i for i in insights if i.severity != "Low"),
        insights[0],
    )

    return TroubleshootReport(
        insights=insights,
        overall_severity=overall,
        priority_container=priority,
    )


# ---------------------------------------------------------------------------
# Public renderer  (Streamlit — imported lazily to keep module testable)
# ---------------------------------------------------------------------------

def render_insights(report: TroubleshootReport) -> None:
    """
    Render the AI Troubleshooting Insights section in Streamlit.
    Call this AFTER the existing AI summary block in app.py.

    Args:
        report: TroubleshootReport from build_insights().
    """
    import streamlit as st  # lazy import — keeps module usable outside Streamlit

    st.divider()
    st.markdown("### 🔧 AI Troubleshooting Insights")

    # ── Overall severity badge ────────────────────────────────────────
    sev   = report.overall_severity
    colour = SEVERITY_COLOUR[sev]
    emoji  = SEVERITY_EMOJI[sev]

    col_sev, col_pri = st.columns([1, 2])

    with col_sev:
        st.markdown(
            f"""
            <div style="
                background:{colour}22;
                border:1px solid {colour};
                border-radius:8px;
                padding:12px 16px;
                text-align:center;
            ">
                <div style="font-size:1.6rem;">{emoji}</div>
                <div style="color:{colour}; font-weight:700; font-size:1rem;">
                    Overall Severity
                </div>
                <div style="color:{colour}; font-size:1.4rem; font-weight:800;">
                    {sev}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_pri:
        p = report.priority_container
        if p:
            p_colour = SEVERITY_COLOUR[p.severity]
            st.markdown(
                f"""
                <div style="
                    background:#1e293b;
                    border-left:4px solid {p_colour};
                    border-radius:8px;
                    padding:12px 16px;
                ">
                    <div style="color:#94a3b8; font-size:0.78rem; font-weight:600;
                                text-transform:uppercase; letter-spacing:.05em;">
                        Highest Priority Container
                    </div>
                    <div style="color:#f1f5f9; font-size:1.1rem; font-weight:700;
                                margin:4px 0;">
                        🐳 {p.name}
                    </div>
                    <div style="color:{p_colour}; font-size:0.85rem;">
                        {SEVERITY_EMOJI[p.severity]} {p.severity} &nbsp;·&nbsp;
                        Status: <code style="color:#e2e8f0;">{p.status}</code>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Per-container insight cards ───────────────────────────────────
    # Show all non-Low first; put healthy containers in a collapsed expander
    problem_insights  = [i for i in report.insights if i.severity != "Low"]
    healthy_insights  = [i for i in report.insights if i.severity == "Low"]

    for insight in problem_insights:
        _render_insight_card(st, insight)

    if healthy_insights:
        with st.expander(f"🟢 {len(healthy_insights)} healthy container(s) — no action needed"):
            for insight in healthy_insights:
                st.markdown(
                    f"**{insight.name}** — {insight.why}",
                )


def _render_insight_card(st: Any, insight: ContainerInsight) -> None:
    """Render a single container insight as a styled card."""
    colour = SEVERITY_COLOUR[insight.severity]
    emoji  = SEVERITY_EMOJI[insight.severity]

    st.markdown(
        f"""
        <div style="
            background:#0f172a;
            border:1px solid {colour}55;
            border-left:4px solid {colour};
            border-radius:8px;
            padding:14px 18px;
            margin-bottom:10px;
        ">
            <div style="display:flex; justify-content:space-between; align-items:center;
                        margin-bottom:8px;">
                <span style="color:#f1f5f9; font-weight:700; font-size:1rem;">
                    🐳 {insight.name}
                </span>
                <span style="
                    background:{colour}33;
                    color:{colour};
                    border:1px solid {colour};
                    border-radius:12px;
                    padding:2px 10px;
                    font-size:0.78rem;
                    font-weight:700;
                ">
                    {emoji} {insight.severity}
                </span>
            </div>
            <p style="color:#94a3b8; margin:4px 0; font-size:0.88rem;">
                <strong style="color:#cbd5e1;">Why this matters:</strong>
                {insight.why}
            </p>
            <p style="color:#94a3b8; margin:4px 0; font-size:0.88rem;">
                <strong style="color:#cbd5e1;">Possible cause:</strong>
                {insight.possible_cause}
            </p>
            <p style="color:#94a3b8; margin:4px 0; font-size:0.88rem;">
                <strong style="color:#22c55e;">▶ Recommended action:</strong>
                {insight.recommended_action}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
