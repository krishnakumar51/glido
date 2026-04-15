"""
Finance Content Agent Team — Streamlit UI
==========================================
Clean, professional interface for the 4-agent content pipeline.
"""

import os
import time

import streamlit as st
from dotenv import load_dotenv

# Load .env before importing agents (so subprocess-style usage also sees cwd-based env)
load_dotenv()

from agents import AgentOutput


def _env_or_input(sidebar_value: str, env_name: str) -> str:
    """Prefer non-empty sidebar input; otherwise use value from environment."""
    s = (sidebar_value or "").strip()
    if s:
        return s
    return (os.environ.get(env_name) or "").strip()

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Finance Content Agent Team",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "anthropic_key" not in st.session_state:
    st.session_state.anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
if "openai_key" not in st.session_state:
    st.session_state.openai_key = os.environ.get("OPENAI_API_KEY", "")
if "tavily_key" not in st.session_state:
    st.session_state.tavily_key = os.environ.get("TAVILY_API_KEY", "")

# ---------------------------------------------------------------------------
# Custom CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        text-align: center;
    }
    .agent-card {
        border: 1px solid #2d2d2d;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        background: #0e1117;
    }
    .score-badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.85rem;
    }
    .grade-a { background: #1a472a; color: #69db7c; }
    .grade-b { background: #1a3a47; color: #4fc3f7; }
    .grade-c { background: #47371a; color: #ffd43b; }
    .grade-d { background: #47231a; color: #ff6b6b; }
    .script-box {
        background: #1a1a2e;
        border-left: 4px solid #4fc3f7;
        border-radius: 0 8px 8px 0;
        padding: 1.2rem;
        font-family: 'Courier New', monospace;
        line-height: 1.7;
        white-space: pre-wrap;
    }
    .final-script-box {
        background: #0d2818;
        border-left: 4px solid #69db7c;
        border-radius: 0 8px 8px 0;
        padding: 1.2rem;
        font-family: 'Courier New', monospace;
        line-height: 1.7;
        white-space: pre-wrap;
    }
    .metric-row {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.markdown("""
<div class="main-header">
    <h1 style="color: white; margin: 0; font-size: 2rem;">🤖 Finance Content Agent Team</h1>
    <p style="color: #a0a0b0; margin: 0.5rem 0 0 0;">
        4 AI Agents · Strategy → Script → Analyze → Refine → Publish-Ready Output
    </p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Sidebar — Inputs & API Keys
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Configuration")

    st.subheader("🔑 API Keys")
    anthropic_key = st.text_input(
        "Anthropic API Key",
        type="password",
        key="anthropic_key",
        placeholder="sk-ant-...",
        help="Agents 1 (strategy synthesis), 3 (analyst), 4 (refiner). Seeded from .env.",
    )
    openai_key = st.text_input(
        "OpenAI API Key",
        type="password",
        key="openai_key",
        placeholder="sk-...",
        help="Agent 2 (script writer). Model: OPENAI_MODEL in .env (default gpt-5.4-mini).",
    )
    tavily_key = st.text_input(
        "Tavily API Key",
        type="password",
        key="tavily_key",
        placeholder="tvly-...",
        help="Agent 1 web search. Seeded from .env on first load; leave blank for Claude-only fallback.",
    )

    st.divider()
    st.subheader("🎯 Content Settings")

    niche = st.text_input(
        "Content Niche",
        value="Finance",
        help="e.g. Finance, Personal Finance, Crypto, Stock Market"
    )

    competitors_raw = st.text_area(
        "Competitor Handles (one per line)",
        value="@the_dailydecode\n@financialfreedomguy\n@humphreytalks\n@graham_stephan",
        height=120,
        help="Instagram handles to analyze"
    )

    max_rewrites = st.slider(
        "Max Rewrite Loops",
        min_value=0,
        max_value=2,
        value=1,
        help="If Agent 3 flags a script as weak, loop back to Agent 2 (max times)"
    )

    st.divider()
    st.markdown("""
    **Agent Stack:**
    - 🔍 **Agent 1** → Tavily + Claude (ideas)
    - ✍️ **Agent 2** → OpenAI (gpt-5.4-mini default)
    - 🔬 **Agent 3** → Claude Sonnet
    - 🔧 **Agent 4** → Claude Sonnet
    """)

# ---------------------------------------------------------------------------
# Validate and Run
# ---------------------------------------------------------------------------
competitors = [c.strip() for c in competitors_raw.strip().split("\n") if c.strip()]

col1, col2, col3 = st.columns([2, 1, 2])
with col2:
    run_button = st.button("🚀 Run Pipeline", type="primary", use_container_width=True)

if run_button:
    anthropic_effective = _env_or_input(anthropic_key, "ANTHROPIC_API_KEY")
    openai_effective = _env_or_input(openai_key, "OPENAI_API_KEY")
    tavily_effective = _env_or_input(tavily_key, "TAVILY_API_KEY")

    # Validation
    if not anthropic_effective:
        st.error("❌ Anthropic API key is required (sidebar or ANTHROPIC_API_KEY in .env).")
        st.stop()
    if not openai_effective:
        st.error("❌ OpenAI API key is required for Agent 2 (sidebar or OPENAI_API_KEY in .env).")
        st.stop()
    if not niche:
        st.error("❌ Please enter a niche.")
        st.stop()
    if len(competitors) < 2:
        st.error("❌ Please enter at least 2 competitors.")
        st.stop()

    # Sync into os.environ for agents.py
    os.environ["ANTHROPIC_API_KEY"] = anthropic_effective
    os.environ["OPENAI_API_KEY"] = openai_effective
    if tavily_effective:
        os.environ["TAVILY_API_KEY"] = tavily_effective
    else:
        os.environ.pop("TAVILY_API_KEY", None)

    # ---------------------------------------------------------------------------
    # Live pipeline execution with streaming logs
    # ---------------------------------------------------------------------------
    st.markdown("---")
    st.subheader("📡 Live Pipeline")

    log_placeholder = st.empty()
    logs = []

    def log(msg: str):
        logs.append(msg)
        log_placeholder.code("\n".join(logs[-30:]), language=None)

    progress_bar = st.progress(0, text="Starting pipeline...")

    start_time = time.time()

    try:
        # Agent 1
        progress_bar.progress(10, "🔍 Agent 1: Researching...")
        state = None

        from agents import (
            AgentOutput,
            agent1_strategy,
            agent2_script_writer,
            agent3_analyst,
            agent4_refiner,
        )

        state = AgentOutput(niche=niche, competitors=competitors)
        state = agent1_strategy(state, log)
        progress_bar.progress(30, "✍️ Agent 2: Writing scripts...")

        state = agent2_script_writer(state, log)
        progress_bar.progress(55, "🔬 Agent 3: Analyzing scripts...")

        state = agent3_analyst(state, log)
        progress_bar.progress(70, "🔄 Checking for rewrites...")

        # Rewrite loop
        rewrite_loops = 0
        weak_scripts = [a for a in state.analyses if a.needs_full_rewrite]

        while weak_scripts and rewrite_loops < max_rewrites:
            rewrite_loops += 1
            state.rewrite_count += 1
            log(f"🔄 REWRITE LOOP {rewrite_loops}: {len(weak_scripts)} scripts sent back...")

            weak_topics = {a.topic for a in weak_scripts}
            ideas_to_rewrite = [i for i in state.ideas if i.topic in weak_topics]

            state = agent2_script_writer(state, log, ideas_to_write=ideas_to_rewrite)

            # Re-analyze rewritten scripts only; keep analyses for all other topics
            orig_scripts = state.scripts
            preserved_analyses = [a for a in state.analyses if a.topic not in weak_topics]
            state.scripts = [s for s in state.scripts if s.topic in weak_topics]
            state = agent3_analyst(state, log)
            state.analyses = preserved_analyses + state.analyses
            state.analyses.sort(key=lambda a: a.total_score, reverse=True)
            state.scripts = orig_scripts
            weak_scripts = [a for a in state.analyses if a.needs_full_rewrite]

        progress_bar.progress(85, "🔧 Agent 4: Final refinement...")
        state = agent4_refiner(state, log)
        progress_bar.progress(100, "✅ Pipeline complete!")

        elapsed = time.time() - start_time
        log(f"\n⏱ Total time: {elapsed:.1f}s")

    except Exception as e:
        st.error(f"❌ Pipeline error: {e}")
        st.exception(e)
        st.stop()

    # ---------------------------------------------------------------------------
    # Results Display
    # ---------------------------------------------------------------------------
    st.markdown("---")

    elapsed_str = f"{time.time() - start_time:.1f}s"
    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Ideas Generated", len(state.ideas))
    col_b.metric("Scripts Written", len(state.scripts))
    col_c.metric("Rewrite Loops", state.rewrite_count)
    col_d.metric("Run Time", elapsed_str)

    # -----------------------------------------------------------------------
    # TAB LAYOUT
    # -----------------------------------------------------------------------
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🎯 Strategy (Agent 1)",
        "📝 Scripts (Agent 2)",
        "🔬 Analysis (Agent 3)",
        "✅ Final Scripts (Agent 4)",
        "📌 Finalised Scripts",
    ])

    # --- TAB 1: Ideas ---
    with tab1:
        st.subheader("Top 5 Content Ideas for This Week")
        for idea in state.ideas:
            with st.expander(f"#{idea.rank} — {idea.topic}", expanded=(idea.rank == 1)):
                st.markdown(f"**🎣 Hook Angle:** {idea.hook_angle}")
                st.markdown(f"**📈 Trend Signal:** {idea.trend_signal}")
                st.markdown(f"**🧠 Why This Works Now:**")
                st.info(idea.reasoning)

    # --- TAB 2: Original Scripts ---
    with tab2:
        st.subheader("Scripts Written by Agent 2")
        for script in state.scripts:
            with st.expander(f"📄 {script.topic}"):
                col_h, col_b_col, col_c_col = st.columns(3)
                with col_h:
                    st.markdown("**🎣 Hook (0-3 sec)**")
                    st.write(script.hook)
                with col_b_col:
                    st.markdown("**📖 Body**")
                    st.write(script.body)
                with col_c_col:
                    st.markdown("**👉 CTA**")
                    st.write(script.cta)
                st.markdown("**📜 Full Script**")
                st.markdown(f'<div class="script-box">{script.full_script}</div>', unsafe_allow_html=True)

    # --- TAB 3: Analysis ---
    with tab3:
        st.subheader("Script Scores & Analyst Feedback (TRIBE v2 Inspired)")
        st.caption(f"{len(state.analyses)} script(s) analyzed — scores after any rewrite loops.")

        for analysis in state.analyses:
            grade_class = {
                "A": "grade-a", "B": "grade-b", "C": "grade-c", "D": "grade-d"
            }.get(analysis.grade, "grade-c")

            header = f"{'⚠️' if analysis.needs_full_rewrite else '✅'} {analysis.topic} — {analysis.total_score}/50"
            with st.expander(header, expanded=False):
                # Score breakdown
                cols = st.columns(5)
                cols[0].metric("Hook", f"{analysis.hook_score}/10")
                cols[1].metric("Retention", f"{analysis.retention_score}/10")
                cols[2].metric("Clarity", f"{analysis.clarity_score}/10")
                cols[3].metric("CTA", f"{analysis.cta_score}/10")
                cols[4].metric("Platform Fit", f"{analysis.platform_fit_score}/10")

                st.markdown(f"""
                <span class="score-badge {grade_class}">Grade {analysis.grade} — {analysis.total_score}/50</span>
                {'<span style="color:#ff6b6b; margin-left:1rem;">⚠️ FLAGGED FOR REWRITE</span>' if analysis.needs_full_rewrite else ''}
                """, unsafe_allow_html=True)

                col_left, col_right = st.columns(2)
                with col_left:
                    st.markdown("**💪 Strengths**")
                    st.success(analysis.strengths)
                with col_right:
                    st.markdown("**🔧 What to Fix**")
                    st.error(analysis.specific_feedback)

                st.markdown("**🔮 TRIBE Predictive Note**")
                st.info(analysis.tribe_predictive_note)

    # --- TAB 4: Final Scripts (Agent 4 detail) ---
    with tab4:
        st.subheader("✅ Publish-Ready Final Scripts (Agent 4)")
        st.caption("Per-topic polish from Agent 4 using analyst feedback. Expand each card below.")

        if not state.final_scripts:
            st.warning("No final scripts generated. Check pipeline logs.")
        else:
            for i, script in enumerate(state.final_scripts, 1):
                # Find analysis for this script
                analysis = next((a for a in state.analyses if a.topic == script.topic), None)
                score_str = f"| Score: {analysis.total_score}/50 ({analysis.grade})" if analysis else ""

                with st.expander(f"🎬 Script {i}: {script.topic} {score_str}", expanded=(i == 1)):
                    col1_f, col2_f = st.columns([1, 2])
                    with col1_f:
                        st.markdown("**🎣 Hook**")
                        st.write(script.hook)
                        st.markdown("**👉 CTA**")
                        st.write(script.cta)
                    with col2_f:
                        st.markdown("**📖 Body**")
                        st.write(script.body)

                    st.markdown("**📜 Full Script (Copy & Shoot)**")
                    st.markdown(f'<div class="final-script-box">{script.full_script}</div>', unsafe_allow_html=True)

                    # Copy button simulation
                    st.code(script.full_script, language=None)

    # --- TAB 5: All finalised scripts (single overview) ---
    with tab5:
        st.subheader("📌 Finalised scripts — full output")
        st.caption(
            "Every script Agent 4 produced for this run, in one scroll. "
            "Same content as the Agent 4 tab, laid out for batch review or screen recording."
        )
        if not state.final_scripts:
            st.warning("No final scripts generated. Check pipeline logs.")
        else:
            st.success(f"{len(state.final_scripts)} publish-ready script(s).")
            for i, script in enumerate(state.final_scripts, 1):
                analysis = next((a for a in state.analyses if a.topic == script.topic), None)
                score_md = (
                    f"**Score:** {analysis.total_score}/50 (Grade {analysis.grade})"
                    if analysis
                    else ""
                )
                st.markdown(f"#### {i}. {script.topic}")
                if score_md:
                    st.markdown(score_md)
                st.markdown(f'<div class="final-script-box">{script.full_script}</div>', unsafe_allow_html=True)
                st.code(script.full_script, language=None)
                if i < len(state.final_scripts):
                    st.divider()

    # Agent logs at bottom
    with st.expander("📋 Full Agent Communication Logs"):
        for entry in state.agent_logs:
            st.text(f"• {entry}")
        st.code("\n".join(logs), language=None)

# ---------------------------------------------------------------------------
# Footer when not running
# ---------------------------------------------------------------------------
else:
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown("""
        **🔍 Agent 1 — Strategy**
        
        Uses Tavily Search API for real competitor analysis + trend research. Ranks top 5 ideas backed by live data.
        """)
    with col2:
        st.markdown("""
        **✍️ Agent 2 — Writer (OpenAI)**
        
        Uses OpenAI (default gpt-5.4-mini) to turn ranked ideas into Hook → Body → CTA Reel scripts. Native platform tone.
        """)
    with col3:
        st.markdown("""
        **🔬 Agent 3 — Analyst**
        
        TRIBE v2 inspired scoring: Hook, Retention, Clarity, CTA, Platform Fit. Flags weak scripts for rewrite.
        """)
    with col4:
        st.markdown("""
        **🔧 Agent 4 — Refiner**
        
        Takes specific critique, fixes every flagged issue, delivers publish-ready final scripts.
        """)