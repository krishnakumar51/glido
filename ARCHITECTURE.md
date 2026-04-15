# Architecture


## Diagram 

```
  niche + competitors
           │
           ▼
  ┌─────────────────────┐
  │ Agent 1             │  Tavily → raw web context
  │ Strategy            │  Claude → JSON → 5 × ContentIdea
  └──────────┬──────────┘
             │ ideas (rank, topic, hook_angle, reasoning, trend_signal)
             ▼
  ┌─────────────────────┐
  │ Agent 2             │  OpenAI → JSON per idea
  │ Script writer       │  Script (hook, body, cta, full_script)
  └──────────┬──────────┘
             │ scripts[]
             ▼
  ┌─────────────────────┐
  │ Agent 3             │  Claude → JSON per script
  │ Analyst             │  ScriptAnalysis (scores, feedback, needs_full_rewrite)
  └──────────┬──────────┘
             │
     weak? ──┴──► loop back to Agent 2 (same ideas/topics) up to max rewrites
             │
             ▼
  ┌─────────────────────┐
  │ Agent 4             │  Claude → final Script JSON per analysis
  │ Refiner             │
  └──────────┬──────────┘
             ▼
        final_scripts + logs
```

## What passes between agents (data contracts)

| Step | Carried forward | Purpose |
|------|-----------------|--------|
| After Agent 1 | `ContentIdea[]`: rank, topic, hook_angle, reasoning, trend_signal | Writer must align scripts with **strategy** and **trend evidence**. |
| After Agent 2 | `Script[]`: topic, hook, body, cta, full_script | Analyst scores **full script** and ties critique to the same **topic**. |
| After Agent 3 | `ScriptAnalysis[]`: five subscores, total, grade, needs_full_rewrite, specific_feedback, strengths, tribe_predictive_note | Refiner receives **exact critique** and score breakdown—not just a score. |
| After Agent 4 | `Script[]` (final_scripts) | Human-ready copy; same schema as Agent 2 for consistency. |

All of this lives on one **`AgentOutput`** object in code (`agents.py`) so the pipeline is a single **state object** threaded through functions—clear for reviewers and matches the “deliberation flow” rubric.

## External systems

| System | Role |
|--------|------|
| **Tavily** | Real competitor/trend **search** (reduces hallucinated “what’s working”). |
| **Anthropic Claude** | Agent 1 synthesis, Agent 3 analysis, Agent 4 refinement. |
| **OpenAI** | Agent 2 script generation (second LLM provider vs Anthropic). |
| **Streamlit** | UI, API key entry, live logs, results tabs. |

## Why not LangChain / LangGraph here

The workflow is a **linear chain** with one **conditional rewrite loop**—orchestration stays in plain Python for transparency, easier debugging, and a smaller dependency surface for a time-boxed MVP. See `README.md` stack section.

