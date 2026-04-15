"""
Finance Content Agent Team
==========================
Agent 1: Ideation & Strategy  → Tavily Search API + Claude (synthesis)
Agent 2: Script Writer         → OpenAI (gpt-5.4-mini by default)
Agent 3: Script Analyst        → Claude claude-sonnet-4-20250514
Agent 4: Script Refiner        → Claude claude-sonnet-4-20250514

Data flows sequentially; Agent 3 can trigger a rewrite loop back to Agent 2.
"""

import os
import json
import time
import requests
import anthropic
from openai import OpenAI
from dataclasses import dataclass, field
from typing import Optional, Callable

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Data contracts passed between agents
# ---------------------------------------------------------------------------

@dataclass
class ContentIdea:
    rank: int
    topic: str
    hook_angle: str
    reasoning: str          # backed by competitor + trend signals
    trend_signal: str

@dataclass
class Script:
    topic: str
    hook: str               # first 3 seconds
    body: str               # value / story
    cta: str                # what viewer does next
    full_script: str        # combined ready-to-shoot text

@dataclass
class ScriptAnalysis:
    topic: str
    hook_score: int         # 0-10
    retention_score: int
    clarity_score: int
    cta_score: int
    platform_fit_score: int
    total_score: int
    grade: str              # A/B/C/D
    needs_full_rewrite: bool
    specific_feedback: str
    strengths: str
    tribe_predictive_note: str  # TRIBE v2 inspired predictive quality note

@dataclass
class AgentOutput:
    """Single context object passed through the entire pipeline."""
    niche: str
    competitors: list[str]
    ideas: list[ContentIdea] = field(default_factory=list)
    scripts: list[Script] = field(default_factory=list)
    analyses: list[ScriptAnalysis] = field(default_factory=list)
    final_scripts: list[Script] = field(default_factory=list)
    rewrite_count: int = 0
    agent_logs: list[str] = field(default_factory=list)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _claude(system: str, user: str, model: str = "claude-sonnet-4-20250514") -> str:
    """Single Claude call. Returns response text."""
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return msg.content[0].text


def _openai_chat(system: str, user: str, model: Optional[str] = None) -> str:
    """Single OpenAI chat completion (Agent 2 script writing). Returns response text."""
    model = model or os.environ.get("OPENAI_MODEL", "gpt-5.4-mini")
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = client.chat.completions.create(
        model=model,
        max_completion_tokens=4096,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    text = resp.choices[0].message.content
    return (text or "").strip()


def _tavily_search(query: str) -> str:
    """
    Real web search via Tavily Search API.
    Returns concatenated content from top search results.
    """
    api_key = os.environ.get("TAVILY_API_KEY", "")
    if not api_key:
        return f"[Tavily API key not set — using Claude knowledge for: {query}]"

    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "advanced",
        "max_results": 6,
        "include_answer": True,
        "include_raw_content": False,
    }

    try:
        r = requests.post(
            "https://api.tavily.com/search",
            json=payload,
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()

        # Build a rich context string from answer + result snippets
        parts = []
        if data.get("answer"):
            parts.append(f"SUMMARY: {data['answer']}")
        for result in data.get("results", []):
            title = result.get("title", "")
            content = result.get("content", "")
            url = result.get("url", "")
            if content:
                parts.append(f"SOURCE [{title}] ({url}):\n{content}")

        return "\n\n".join(parts) if parts else "[No results found]"
    except Exception as e:
        return f"[Tavily error: {e}. Falling back to Claude knowledge.]"


def _parse_json_from_response(text: str) -> dict | list:
    """Safely extract JSON from Claude's response."""
    # Strip markdown fences if present
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])
    return json.loads(text)


# ---------------------------------------------------------------------------
# AGENT 1 — Ideation & Strategy (Tavily for real signals)
# ---------------------------------------------------------------------------

def agent1_strategy(state: AgentOutput, log: Callable) -> AgentOutput:
    log("🔍 Agent 1: Researching competitors and trends via Tavily...")

    competitors_str = ", ".join(state.competitors)

    # Real web research queries
    competitor_query = (
        f"Analyze Instagram finance creators: {competitors_str}. "
        "What content formats (Reels topics, hooks, posting cadence) are performing best for them right now in April 2026? "
        "Include engagement patterns and top-performing content themes."
    )
    competitor_data = _tavily_search(competitor_query)
    log(f"  ✓ Competitor research complete ({len(competitor_data)} chars)")
    time.sleep(1)

    trending_query = (
        "What are the top 5 trending finance/money topics on Instagram and social media in April 2026? "
        "Include: stock market news, personal finance trends, crypto, recession fears, interest rates. "
        "What is audience sentiment right now?"
    )
    trend_data = _tavily_search(trending_query)
    log(f"  ✓ Trend research complete ({len(trend_data)} chars)")
    time.sleep(1)

    # Now let Claude synthesize and rank
    system = """You are a senior content strategist specializing in finance content for Instagram.
Your job is to synthesize real research data into ranked content ideas.
You MUST output valid JSON only — no preamble, no markdown fences, just raw JSON."""

    user = f"""
NICHE: {state.niche}
COMPETITORS ANALYZED: {competitors_str}

COMPETITOR RESEARCH DATA (from live web search):
{competitor_data}

TRENDING TOPICS DATA (from live web search):
{trend_data}

Based on this REAL data, generate the Top 5 content ideas for this week.
Each idea must be grounded in the research above — not generic.

Output a JSON array of exactly 5 objects with these fields:
- rank (1-5, 1 = highest priority)
- topic (clear topic name)
- hook_angle (the specific angle/twist that makes this unique)
- reasoning (why this will perform RIGHT NOW — cite competitor patterns + trend signals from the data)
- trend_signal (specific signal from the research that backs this up)

Example structure:
[
  {{
    "rank": 1,
    "topic": "...",
    "hook_angle": "...",
    "reasoning": "...",
    "trend_signal": "..."
  }}
]
"""

    raw = _claude(system, user)
    log("  ✓ Claude synthesized top 5 ideas")

    try:
        ideas_data = _parse_json_from_response(raw)
        state.ideas = [ContentIdea(**d) for d in ideas_data]
    except Exception as e:
        log(f"  ⚠ JSON parse error: {e}. Retrying with explicit prompt...")
        # Retry once
        raw2 = _claude(system, user + "\n\nIMPORTANT: Output ONLY the JSON array, nothing else.")
        ideas_data = _parse_json_from_response(raw2)
        state.ideas = [ContentIdea(**d) for d in ideas_data]

    state.agent_logs.append(f"Agent 1 complete: {len(state.ideas)} ideas generated")
    log(f"✅ Agent 1 done — {len(state.ideas)} ideas ranked")
    return state


# ---------------------------------------------------------------------------
# AGENT 2 — Script Writer
# ---------------------------------------------------------------------------

def agent2_script_writer(state: AgentOutput, log: Callable, ideas_to_write: Optional[list[ContentIdea]] = None) -> AgentOutput:
    omodel = os.environ.get("OPENAI_MODEL", "gpt-5.4-mini")
    log(f"✍️  Agent 2: Writing scripts (OpenAI {omodel}) for top ideas...")

    # Use provided ideas (for rewrites) or all ideas from Agent 1
    ideas = ideas_to_write or state.ideas

    system = """You are a top-tier Instagram Reels scriptwriter for finance content.
You write scripts that feel NATIVE to the platform — punchy, fast, relatable.
NOT like a blog post. NOT corporate. Like a smart friend talking money.
You MUST output valid JSON only — no preamble, no markdown fences."""

    new_scripts = []
    for idea in ideas:
        user = f"""
Write a complete Instagram Reel script for this topic:

TOPIC: {idea.topic}
HOOK ANGLE: {idea.hook_angle}
STRATEGIC REASONING: {idea.reasoning}
TREND SIGNAL: {idea.trend_signal}

Requirements:
- Total duration: 45-75 seconds when spoken
- Hook: First 3 seconds — MUST stop the scroll. A bold statement, shocking stat, or direct challenge.
- Body: The value/story. Use short punchy sentences. Max 2-3 ideas. No fluff.
- CTA: Clear, specific action the viewer takes next (follow, save, comment a word, etc.)
- Tone: Conversational, confident, slightly edgy — like @the_dailydecode
- NO "Hey guys", NO "Welcome back", NO slow intros

Output a JSON object with these fields:
- topic (same as input)
- hook (just the hook line — 1-2 sentences max)  
- body (the main content — broken into short punchy paragraphs)
- cta (the call to action line)
- full_script (hook + body + cta formatted as one continuous ready-to-shoot script with [PAUSE] markers)
"""
        raw = _openai_chat(system, user)
        try:
            script_data = _parse_json_from_response(raw)
            new_scripts.append(Script(**script_data))
            log(f"  ✓ Script written: '{idea.topic[:50]}...'")
        except Exception as e:
            log(f"  ⚠ Script parse error for '{idea.topic}': {e}. Retrying...")
            try:
                raw2 = _openai_chat(
                    system,
                    user + "\n\nIMPORTANT: Output ONLY valid JSON with the requested fields — no markdown, no extra text.",
                )
                script_data = _parse_json_from_response(raw2)
                new_scripts.append(Script(**script_data))
                log(f"  ✓ Script written (retry): '{idea.topic[:50]}...'")
            except Exception:
                raw_final = raw
                new_scripts.append(Script(
                    topic=idea.topic,
                    hook="[Parse error — regenerate]",
                    body=raw_final[:500],
                    cta="Follow for more.",
                    full_script=raw_final,
                ))

    # If rewriting specific scripts, replace them; otherwise set all
    if ideas_to_write:
        # Replace only the rewritten ones by topic
        rewrite_topics = {i.topic for i in ideas_to_write}
        state.scripts = [s for s in state.scripts if s.topic not in rewrite_topics]
        state.scripts.extend(new_scripts)
    else:
        state.scripts = new_scripts

    state.agent_logs.append(f"Agent 2 complete: {len(new_scripts)} scripts written")
    log(f"✅ Agent 2 done — {len(new_scripts)} scripts ready")
    return state


# ---------------------------------------------------------------------------
# AGENT 3 — Script Analyst & Quality Ranker (TRIBE v2 inspired)
# ---------------------------------------------------------------------------

def agent3_analyst(state: AgentOutput, log: Callable) -> AgentOutput:
    log("🔬 Agent 3: Analyzing and scoring all scripts...")

    system = """You are a brutal, honest script analyst for Instagram finance content.
You score scripts on measurable criteria and give SPECIFIC, ACTIONABLE feedback.
No generic praise. No softening. Pure signal.

TRIBE v2 Inspired Scoring Framework:
- Hook Strength (0-10): Will it stop the scroll in 1.5 seconds? Is it specific/surprising?
- Retention Potential (0-10): Will viewers watch past 5 seconds? Is pacing right?
- Clarity (0-10): Is the ONE takeaway crystal clear? No confusion?
- CTA Effectiveness (0-10): Is the CTA specific, low-friction, and timely?
- Platform Fit (0-10): Does it feel native to Reels? Not a blog post read aloud?

A script scoring below 30/50 total needs a FULL REWRITE (needs_full_rewrite: true).
A script scoring 30-39 needs targeted fixes.
A script scoring 40+ is strong and goes to refinement.

You MUST output valid JSON only — no preamble, no markdown fences."""

    analyses = []
    for script in state.scripts:
        user = f"""
Analyze this Instagram Reel script for finance content:

TOPIC: {script.topic}

HOOK:
{script.hook}

BODY:
{script.body}

CTA:
{script.cta}

FULL SCRIPT:
{script.full_script}

Score this script and provide detailed analysis.

Output a JSON object with these fields:
- topic (same as input)
- hook_score (0-10 integer)
- retention_score (0-10 integer)
- clarity_score (0-10 integer)
- cta_score (0-10 integer)
- platform_fit_score (0-10 integer)
- total_score (sum of all 5 scores)
- grade (A=45-50, B=38-44, C=30-37, D=below 30)
- needs_full_rewrite (true if total_score < 30, false otherwise)
- specific_feedback (bullet-point list of EXACTLY what to fix and HOW — be surgical)
- strengths (what's actually working well — be honest)
- tribe_predictive_note (based on TRIBE v2 thinking: predict this script's likely performance pattern — will it front-load views and drop off? Will it be a slow burn saver? Will it drive comments?)
"""
        raw = _claude(system, user)
        try:
            analysis_data = _parse_json_from_response(raw)
            analysis = ScriptAnalysis(**analysis_data)
            analyses.append(analysis)
            log(f"  ✓ Scored '{script.topic[:40]}...' → {analysis.total_score}/50 ({analysis.grade}) {'⚠ REWRITE' if analysis.needs_full_rewrite else ''}")
        except Exception as e:
            log(f"  ⚠ Analysis parse error: {e}")

    # Sort by score descending
    analyses.sort(key=lambda a: a.total_score, reverse=True)
    state.analyses = analyses

    rewrite_count = sum(1 for a in analyses if a.needs_full_rewrite)
    state.agent_logs.append(f"Agent 3 complete: {len(analyses)} scripts scored, {rewrite_count} need rewrite")
    log(f"✅ Agent 3 done — {rewrite_count} scripts flagged for full rewrite")
    return state


# ---------------------------------------------------------------------------
# AGENT 4 — Script Refiner (The Closer)
# ---------------------------------------------------------------------------

def agent4_refiner(state: AgentOutput, log: Callable) -> AgentOutput:
    log("🔧 Agent 4: Refining scripts based on analyst feedback...")

    system = """You are The Closer — the final polisher who takes analyst feedback and makes scripts PERFECT.
You receive a script + specific critique and you FIX every flagged issue precisely.
Your output is the FINAL publish-ready version.
You MUST output valid JSON only — no preamble, no markdown fences."""

    final_scripts = []
    for analysis in state.analyses:
        # Find matching script
        script = next((s for s in state.scripts if s.topic == analysis.topic), None)
        if not script:
            continue

        user = f"""
ORIGINAL SCRIPT:

TOPIC: {script.topic}
HOOK: {script.hook}
BODY: {script.body}
CTA: {script.cta}
FULL SCRIPT: {script.full_script}

ANALYST FEEDBACK (Score: {analysis.total_score}/50 — Grade {analysis.grade}):

STRENGTHS (KEEP THESE):
{analysis.strengths}

SPECIFIC ISSUES TO FIX:
{analysis.specific_feedback}

WEAK SCORES:
- Hook: {analysis.hook_score}/10
- Retention: {analysis.retention_score}/10
- Clarity: {analysis.clarity_score}/10
- CTA: {analysis.cta_score}/10
- Platform Fit: {analysis.platform_fit_score}/10

PREDICTIVE NOTE (from TRIBE framework):
{analysis.tribe_predictive_note}

NOW: Rewrite this script addressing EVERY specific critique. Keep what works. Fix what doesn't.
Make it punchy, native, and scroll-stopping.

Output a JSON object with these fields:
- topic
- hook
- body
- cta
- full_script (the complete polished version with [PAUSE] markers)
"""
        raw = _claude(system, user)
        try:
            final_data = _parse_json_from_response(raw)
            final_scripts.append(Script(**final_data))
            log(f"  ✓ Refined: '{script.topic[:40]}...'")
        except Exception as e:
            log(f"  ⚠ Refine parse error: {e}")
            final_scripts.append(script)  # Use original if parse fails

    state.final_scripts = final_scripts
    state.agent_logs.append(f"Agent 4 complete: {len(final_scripts)} final scripts ready")
    log(f"✅ Agent 4 done — {len(final_scripts)} publish-ready scripts")
    return state


# ---------------------------------------------------------------------------
# ORCHESTRATOR — Wires all agents together with rewrite loop
# ---------------------------------------------------------------------------

def run_pipeline(
    niche: str,
    competitors: list[str],
    log: Callable = print,
    max_rewrite_loops: int = 1,
) -> AgentOutput:
    """
    Main orchestrator. Runs Agent1 → Agent2 → Agent3 → (rewrite loop?) → Agent4.
    Returns final AgentOutput with all intermediate data + final scripts.
    """
    state = AgentOutput(niche=niche, competitors=competitors)

    log("=" * 60)
    log(f"🚀 PIPELINE START | Niche: {niche} | Competitors: {', '.join(competitors)}")
    log("=" * 60)

    # --- Agent 1: Strategy ---
    state = agent1_strategy(state, log)
    log("")

    # --- Agent 2: Script Writing ---
    state = agent2_script_writer(state, log)
    log("")

    # --- Agent 3: Analysis ---
    state = agent3_analyst(state, log)
    log("")

    # --- Rewrite Loop (bonus feature) ---
    rewrite_loops = 0
    weak_scripts = [a for a in state.analyses if a.needs_full_rewrite]

    while weak_scripts and rewrite_loops < max_rewrite_loops:
        rewrite_loops += 1
        state.rewrite_count += 1
        log(f"🔄 REWRITE LOOP {rewrite_loops}: {len(weak_scripts)} weak scripts sent back to Agent 2...")

        # Find ideas for weak scripts
        weak_topics = {a.topic for a in weak_scripts}
        ideas_to_rewrite = [i for i in state.ideas if i.topic in weak_topics]

        state = agent2_script_writer(state, log, ideas_to_write=ideas_to_rewrite)
        log("")

        # Re-analyze only the rewritten scripts; preserve analyses for all other topics
        log("🔬 Agent 3: Re-analyzing rewritten scripts...")
        temp_scripts = state.scripts
        preserved_analyses = [a for a in state.analyses if a.topic not in weak_topics]
        state.scripts = [s for s in state.scripts if s.topic in weak_topics]
        state = agent3_analyst(state, log)
        state.analyses = preserved_analyses + state.analyses
        state.analyses.sort(key=lambda a: a.total_score, reverse=True)
        state.scripts = temp_scripts

        weak_scripts = [a for a in state.analyses if a.needs_full_rewrite]
        log("")

    # --- Agent 4: Final Refinement ---
    state = agent4_refiner(state, log)
    log("")
    log("=" * 60)
    log("🏁 PIPELINE COMPLETE")
    log("=" * 60)

    return state