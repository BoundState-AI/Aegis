---
name: server
description: Start the AEGIS backend dev server on port 8002 with auto-reload.
allowed-tools: Bash
---

Start the AEGIS FastAPI backend server for local development.

1. Check if port 8002 is already in use. If so, report what's running and ask before killing it.
2. Start the server in background:
   ```
   D:/BoundState/.venv/Scripts/python.exe -m uvicorn boundstate_aegis.api.aegis_api:app --reload --port 8002
   ```
3. Wait a few seconds, then hit `http://localhost:8002/health` to confirm it's up.
4. Report the health check response and confirm the server is ready.
