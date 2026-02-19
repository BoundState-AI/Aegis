# AEGIS - CLAUDE.md

## General Behavior
- When I ask you to fix or implement something, write the code immediately. Do not enter plan mode or produce implementation plans unless I explicitly ask for a plan. Default to action.
- When I describe a bug or feature, implement the real solution using the actual data/pipeline. Never suggest adding placeholder or mock data as a substitute for running the real pipeline or fixing the real issue.
- Before modifying CSS/UI for visual issues, first verify the root cause (e.g., check image dimensions, inspect the actual asset). Never blindly iterate on CSS values more than 2 times without stepping back to diagnose.

## Project Structure

This workspace is **AEGIS** (Advanced Evidence Gathering & Intelligence System) — a PFAS risk intelligence platform.

**This repo:** `boundstate_aegis` — the primary AEGIS codebase.
- **Backend:** FastAPI (Python) in `boundstate_aegis/`
- **Frontend:** React + TypeScript + Recharts + shadcn/ui in `src/`
- **Config:** `boundstate_aegis/config.py` defines `EVIDENCE_DIR`, `DATA_DIR`, and all data paths
- **Data:** JSON/YAML evidence corpus in `boundstate_aegis/data/` and `boundstate_aegis/data/evidence/`
- **Engines:** `boundstate_aegis/engines/` (EOL certificate generator, substructure rules, etc.)
- **Knowledge:** `boundstate_aegis/knowledge/` (graph builder, graph queries, destruction queries)
- **Models:** `boundstate_aegis/models/` (Pydantic models)
- **API Routes:** `boundstate_aegis/api/routes/` (14 route modules registered in `aegis_api.py`)
- **Scripts:** `scripts/` (sentiment classification, data processing pipelines)

### Sibling repos under D:\BoundState\ (DO NOT confuse):
| Repo | Purpose | Stack |
|------|---------|-------|
| `boundstate_aegis` | **THIS REPO** - PFAS risk intelligence platform | FastAPI + React |
| `boundstate_mira` | MIRA platform frontend | React + TypeScript |
| `Mira-Backend` | MIRA platform backend | Python / FastAPI |
| `boundstate_athena` | Athena platform | Python |
| `boundstate_core` | Shared core libraries | Python |
| `gptl` | SENTINEL GPTL (General Purpose Translation Layer) | Python |
| `sentinel` | SENTINEL service | Python |
| `sentinel_dc` | SENTINEL-DC | Python |
| `mira-ui` / `mira-dev` | MIRA UI iterations | React |

**GPTL = "General Purpose Translation Layer"** — never "Grounded Precision" or any other expansion.

Always confirm which directory and repo you're working in before making changes. If a task mentions a module name, verify it exists in THIS repo before starting work.

## AEGIS Architecture Quick Reference

### Key Data Files
- `boundstate_aegis/data/evidence/pfas_fate_v2.json` — 732 aggregated pathways from 353 papers (primary data source)
- `boundstate_aegis/data/destruction_technologies.yaml` — 6 destruction technologies with Chemours IP positions
- `boundstate_aegis/data/evidence/tfa_comprehensive_evidence.yaml` — Full Chemours HFO→TFA litigation chain
- `boundstate_aegis/data/evidence/pfoa_sentiment_classified.json` — 8,221 PFOA papers with sentiment
- `boundstate_aegis/data/evidence/genx_sentiment_classified.json` — 412 GenX papers with sentiment

### Caching Pattern
All heavy data uses thread-safe double-check locking:
```python
_cache: Optional[X] = None
_lock = threading.Lock()
def _get_data():
    global _cache
    if _cache is not None: return _cache
    with _lock:
        if _cache is not None: return _cache
        _cache = load_data()
    return _cache
```
Server restart required after data file changes (caches are in-memory).

### SENTINEL System
- Litigation early warning based on publication dynamics (velocity, acceleration, jerk)
- Route: `boundstate_aegis/api/routes/sentinel_route.py`
- Frontend: `src/pages/LitigationRisk.tsx`
- Compounds with data: PFOA, GenX (backtest JSONs + classified sentiment JSONs)

### Sentiment Pipeline
- Shared module: `boundstate_aegis/sentiment.py` — rolling window, category scores, aggregation
- 6 categories: celebration, utility, detection, questioning, alarm, reckoning
- 3-year rolling window (NOT cumulative average — cumulative dilutes signal)
- Formula: `sum(year_scores) / sum(year_papers)` across window
- Per-compound scripts: `scripts/classify_pfoa_sentiment.py`, `scripts/classify_genx_sentiment.py`
- Scripts use `--aggregate-only` flag to re-process without API calls

## Deployment
- **Frontend:** Vercel (aegis.boundstate.ai)
- **Backend:** Railway.app (port 8002)
- **venv:** `D:\BoundState\.venv` (managed with `uv`, NOT pip)

### Pre-Push Checklist
Before pushing to Railway or Vercel:
1. Verify all dependencies are in pyproject.toml / requirements (use `uv pip install`)
2. Config/data files must be inside the deployed package (not project root)
3. Run a local server start to confirm it works
4. Check that new route imports don't pull in missing dependencies

## Session Retrospectives
At the end of any significant session (new feature, major fix, multi-file refactor), proactively update the auto-memory retro log:
1. **Write to** `C:\Users\Jnwil\.claude\projects\d--BoundState-boundstate-aegis\memory\session_retros.md`
2. **Format** each entry as:
   ```
   ## YYYY-MM-DD — [2-5 word summary]
   **Built:** what was accomplished
   **Wins:** what went well, clever approaches, good catches
   **Failures:** what went wrong, time wasted, wrong assumptions
   **Lessons:** concrete takeaways for next time (not vague platitudes)
   ```
3. **Keep it honest.** If you made a dumb mistake, say so. If the user caught something you missed, note it.
4. **Promote durable lessons** to `MEMORY.md` if they'll matter beyond this session.
5. **Trim** retros older than 10 sessions to keep the file useful, not archaeological.
6. **Read retros at session start** before diving into work — check if you're about to repeat a past mistake.

## Git
- Do NOT push unless explicitly asked — pushing updates the live deployment
- Main branch: `main`
