#!/usr/bin/env python3
"""
In-memory bounded session store for AEGIS chat.
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import List
from uuid import uuid4

from boundstate_aegis.models.chat_models import ChatTurn

_MAX_HISTORY_MESSAGES = 10
_MAX_SESSIONS = 500
_TTL_SECONDS = 30 * 60


class ChatSessionStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: "OrderedDict[str, dict[str, object]]" = OrderedDict()

    def _prune_locked(self) -> None:
        now = time.time()
        expired = [
            session_id
            for session_id, row in self._sessions.items()
            if (now - float(row.get("last_access", now))) > _TTL_SECONDS
        ]
        for session_id in expired:
            self._sessions.pop(session_id, None)
        while len(self._sessions) > _MAX_SESSIONS:
            self._sessions.popitem(last=False)

    def touch(self, session_id: str | None) -> str:
        with self._lock:
            current = session_id or f"chat-{uuid4().hex[:12]}"
            row = self._sessions.get(current)
            if row is None:
                row = {"history": [], "last_access": time.time()}
                self._sessions[current] = row
            else:
                row["last_access"] = time.time()
                self._sessions.move_to_end(current)
            self._prune_locked()
            return current

    def history(self, session_id: str) -> List[ChatTurn]:
        with self._lock:
            row = self._sessions.get(session_id)
            if row is None:
                return []
            row["last_access"] = time.time()
            self._sessions.move_to_end(session_id)
            history = row.get("history", [])
            return list(history) if isinstance(history, list) else []

    def append(self, session_id: str, user_text: str, assistant_text: str) -> None:
        with self._lock:
            row = self._sessions.setdefault(session_id, {"history": [], "last_access": time.time()})
            history = row.get("history", [])
            if not isinstance(history, list):
                history = []
            history.extend([
                ChatTurn(role="user", content=user_text),
                ChatTurn(role="assistant", content=assistant_text),
            ])
            row["history"] = history[-_MAX_HISTORY_MESSAGES:]
            row["last_access"] = time.time()
            self._sessions.move_to_end(session_id)
            self._prune_locked()


STORE = ChatSessionStore()
