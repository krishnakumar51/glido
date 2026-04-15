# Finance Content Agent Team

A multi-agent AI pipeline that researches, strategizes, writes, analyzes, and refines Instagram Reel scripts for finance content — end-to-end with **real web signals** and **two LLM providers** (OpenAI + Anthropic), plus Tavily for competitor/trend research.

## Architecture

```
INPUT: niche + competitor handles
         │
         ▼
┌─────────────────────────────────────────┐
│  AGENT 1 — Ideation & Strategy          │
│  Tavily Search (live web) + Claude      │
│  • Competitor + trend research          │
│  OUTPUT: Top 5 ideas + reasoning      │
└──────────────────┬──────────────────────┘
                   ▼
┌─────────────────────────────────────────┐
│  AGENT 2 — Script Writer                │
│  OpenAI (gpt-5.4-mini default)          │
│  • Native Reel scripts (Hook/Body/CTA)    │
│  OUTPUT: Full scripts per idea          │
└──────────────────┬──────────────────────┘
                   ▼
┌─────────────────────────────────────────┐
│  AGENT 3 — Script Analyst & Ranker      │
│  Claude Sonnet                          │
│  • TRIBE v2–inspired scores + feedback  │
│  OUTPUT: Ranked scores, rewrite flags   │
└──────────────┬───────────────┬──────────┘
               │               │
         Score OK          Weak script
               │               └──► rewrite loop → Agent 2
               ▼
┌─────────────────────────────────────────┐
│  AGENT 4 — Script Refiner               │
│  Claude Sonnet                          │
│  OUTPUT: Final publish-ready scripts    │
└─────────────────────────────────────────┘
```

## APIs & models

| Piece | Role | Provider |
|-------|------|----------|
| Web search | Real competitor/trend data (not hallucinated) | **Tavily** |
| Strategy JSON synthesis | Rank top 5 ideas from search context | **Anthropic** Claude `claude-sonnet-4-20250514` |
| Script writing | Scroll-stopping Reel scripts (JSON) | **OpenAI** `gpt-5.4-mini` (override via `OPENAI_MODEL`) |
| Analysis & refinement | Scores, critique, polish | **Anthropic** Claude (same model) |


## 🎥 Demo

[![Demo Loom Link](https://cdn.loom.com/sessions/thumbnails/57512b560e7848888ce71bb0cbeb9485-with-play.gif)](https://www.loom.com/share/57512b560e7848888ce71bb0cbeb9485)
## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env: ANTHROPIC_API_KEY, OPENAI_API_KEY, TAVILY_API_KEY (recommended)

streamlit run app.py
```

Keys can also be entered in the Streamlit sidebar; `.env` is loaded automatically via `python-dotenv`.

## API keys

| Key | Required | Usage |
|-----|----------|--------|
| `ANTHROPIC_API_KEY` | Yes | Agents 1 (synthesis), 3, 4 |
| `OPENAI_API_KEY` | Yes | Agent 2 (writer) |
| `TAVILY_API_KEY` | Recommended | Agent 1 live search; without it, synthesis falls back to weaker context |

Optional: `OPENAI_MODEL` (default `gpt-5.4-mini`).

## Features

- Real competitor/trend signals via Tavily
- Four specialized agents with shared context (analyst sees strategy; refiner sees critique)
- TRIBE v2–inspired scoring; optional rewrite loop for weak scripts
- Streamlit UI with live logs

## Stack

- Python 3.11+
- Streamlit
- OpenAI API (Agent 2) · Anthropic API (Agents 1, 3, 4) · Tavily Search API
- Dataclasses for pipeline state; direct SDK calls (no LangChain required)


## What worked well

Separating **four clear roles** (strategy → writer → analyst → refiner) and passing **structured context** between them—not isolated prompts—made the pipeline honest to the brief. **Tavily** grounds competitor and trend research in **live web results**, and **Claude** turns that into ranked ideas with reasoning tied to those signals. **OpenAI** drafts scripts while **Claude** scores and polishes them, which satisfies the **two LLM API** requirement and keeps critique and refinement on one consistent “editor” stack. The **TRIBE v2–inspired** rubric and **rewrite loop** for weak scripts add real deliberation instead of a single pass. **Streamlit** plus plain Python and dataclasses kept the demo easy to run and the flow easy to explain without framework magic.

## What I would improve

- **Instagram Graph API**: pull real engagement and posting signals for named handles instead of inferring performance only from public web snippets.
- **Perplexity (or similar) API**: optional second research path for answer-style synthesis on “what’s trending now” alongside Tavily’s search-style results—stronger cross-checks on strategy.
- **Parallelism**: generate or score multiple scripts concurrently to cut latency; add **persisted run folders** (Markdown exports per run) for audit and handoff.

## Hardest part

Getting **structured JSON** (ideas, scripts, analyses) to parse reliably while keeping feedback **specific and actionable**—not generic—required tight prompts, retries, and a few edge-case fixes when models drifted format. 
