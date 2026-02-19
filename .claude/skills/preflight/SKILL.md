---
name: preflight
description: Run the pre-push deployment checklist before pushing to Railway/Vercel.
allowed-tools: Bash, Read, Grep, Glob
---

Run the AEGIS pre-push checklist. Do NOT push — just validate readiness.

Steps:
1. **Check for uncommitted changes:** `git status` — warn if there are unstaged files that should be committed.
2. **Check imports:** For every route module imported in `boundstate_aegis/api/aegis_api.py`, verify the module exists and its imports resolve. Run: `python -c "from boundstate_aegis.api.aegis_api import app"` using `D:/BoundState/.venv/Scripts/python.exe`.
3. **Start server smoke test:** Start the server on port 8002, hit `/health`, then shut it down. Use a timeout so it doesn't hang.
4. **Check dependencies:** Look for any `import` statements in recently modified files that reference packages not in `pyproject.toml`. Flag anything suspicious.
5. **Check data files:** Verify that any data files referenced in code exist inside the `boundstate_aegis/` package directory (not project root).

Report results as a clear pass/fail checklist. If anything fails, explain what needs fixing before push.
