#!/usr/bin/env python3
"""
Human-in-the-loop gate layer for recursive resolver outputs.
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from boundstate_aegis.config import MONITOR_DATA_DIR


class GateStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    DISMISSED = "DISMISSED"


class GateId(str, Enum):
    HITL_1 = "HITL-1"
    HITL_2 = "HITL-2"


REVIEW_ACTIONS = {"confirm", "override", "add_context", "dismiss", "escalate"}
APPROVAL_ACTIONS = {"approve", "edit", "reclassify", "hold"}
JUSTIFICATION_REQUIRED = {"override", "dismiss", "reclassify", "edit"}


@dataclass
class GateRecord:
    gate_id: str
    resolution_id: str
    action: str
    analyst_id: str
    timestamp: str
    justification: str
    previous_value: Dict[str, Any]
    new_value: Dict[str, Any]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(payload: Any) -> str:
    return sha256(_stable_json(payload).encode("utf-8")).hexdigest()


class HITLGateStore:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        configured_path = os.getenv("AEGIS_RESOLVER_HITL_DB_PATH", "").strip()
        default_path = Path(configured_path) if configured_path else (MONITOR_DATA_DIR / "resolver_hitl.db")
        self.db_path = Path(db_path or default_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS resolver_resolutions (
                    resolution_id TEXT PRIMARY KEY,
                    gate_status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    human_review_required INTEGER NOT NULL DEFAULT 0,
                    warnings_json TEXT NOT NULL,
                    created_by TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS resolver_gate_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    resolution_id TEXT NOT NULL,
                    gate_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    analyst_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    justification TEXT,
                    previous_value_json TEXT NOT NULL,
                    new_value_json TEXT NOT NULL,
                    prev_chain_hash TEXT,
                    chain_hash TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_resolver_gate_events_resolution_id "
                "ON resolver_gate_events(resolution_id, event_id DESC)"
            )
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS trg_resolver_gate_events_no_update
                BEFORE UPDATE ON resolver_gate_events
                BEGIN
                    SELECT RAISE(ABORT, 'resolver_gate_events is append-only');
                END;
                """
            )
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS trg_resolver_gate_events_no_delete
                BEFORE DELETE ON resolver_gate_events
                BEGIN
                    SELECT RAISE(ABORT, 'resolver_gate_events is append-only');
                END;
                """
            )

    def _last_chain_hash(self, conn: sqlite3.Connection, resolution_id: str) -> Optional[str]:
        row = conn.execute(
            "SELECT chain_hash FROM resolver_gate_events WHERE resolution_id = ? ORDER BY event_id DESC LIMIT 1",
            (resolution_id,),
        ).fetchone()
        return str(row["chain_hash"]) if row else None

    def _append_gate_event(
        self,
        conn: sqlite3.Connection,
        *,
        record: GateRecord,
    ) -> str:
        prev = self._last_chain_hash(conn, record.resolution_id)
        chain_material = {
            "resolution_id": record.resolution_id,
            "gate_id": record.gate_id,
            "action": record.action,
            "analyst_id": record.analyst_id,
            "timestamp": record.timestamp,
            "justification": record.justification,
            "previous_value": record.previous_value,
            "new_value": record.new_value,
            "prev_chain_hash": prev or "",
        }
        chain_hash = _hash(chain_material)
        conn.execute(
            """
            INSERT INTO resolver_gate_events(
                resolution_id, gate_id, action, analyst_id, timestamp, justification,
                previous_value_json, new_value_json, prev_chain_hash, chain_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.resolution_id,
                record.gate_id,
                record.action,
                record.analyst_id,
                record.timestamp,
                record.justification,
                _stable_json(record.previous_value),
                _stable_json(record.new_value),
                prev,
                chain_hash,
            ),
        )
        return chain_hash

    @staticmethod
    def _conservative_defaults(payload: Dict[str, Any]) -> Tuple[Dict[str, Any], bool, List[str]]:
        result = json.loads(json.dumps(payload))
        warnings: List[str] = []
        human_review_required = False

        # Low-confidence degradation path requires human review.
        nodes = ((result.get("degradation_tree") or {}).get("nodes") or [])
        if any(float((n or {}).get("cumulative_confidence") or 0.0) < 0.5 for n in nodes):
            warnings.append(
                "AEGIS identified a potential degradation product but evidence is limited. "
                "Your expertise would help assess this pathway."
            )
            human_review_required = True

        # Class-level-only exposure should be explicitly reviewed.
        direct = result.get("direct_exposure") or []
        class_exp = result.get("class_exposure") or []
        if not direct and class_exp:
            warnings.append("Class-level exposure only; confirm applicability to this specific product.")
            human_review_required = True

        # Critical flags always require human review.
        for flag in result.get("threat_flags") or []:
            if str(flag.get("severity") or "").upper() == "CRITICAL":
                flag["human_review_required"] = True
                human_review_required = True

            # Unknown destruction capability defaults to gap.
            if str(flag.get("flag_type") or "") == "DESTRUCTION_TECH_GAP":
                detail = str(flag.get("detail") or "").lower()
                if "no confirmed capability" in detail or "no known" in detail:
                    warnings.append(
                        "No confirmed capability identified. Override if internal R&D data exists."
                    )
                    human_review_required = True

        result.setdefault("metadata", {})
        result["metadata"]["human_review_required"] = human_review_required
        return result, human_review_required, list(dict.fromkeys(warnings))

    def create_resolution(self, payload: Dict[str, Any], *, created_by: str) -> Dict[str, Any]:
        normalized, human_review_required, warnings = self._conservative_defaults(payload)
        resolution_id = f"res_{uuid4().hex[:12]}"
        now = _utc_now()
        content_hash = _hash(normalized)
        status = GateStatus.PENDING_REVIEW.value

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO resolver_resolutions(
                    resolution_id, gate_status, payload_json, content_hash,
                    human_review_required, warnings_json, created_by, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    resolution_id,
                    status,
                    _stable_json(normalized),
                    content_hash,
                    1 if human_review_required else 0,
                    _stable_json(warnings),
                    created_by,
                    now,
                    now,
                ),
            )
            self._append_gate_event(
                conn,
                record=GateRecord(
                    gate_id=GateId.HITL_1.value,
                    resolution_id=resolution_id,
                    action="queued",
                    analyst_id=created_by,
                    timestamp=now,
                    justification="auto-created",
                    previous_value={},
                    new_value={"gate_status": status},
                ),
            )

        return {
            "resolution_id": resolution_id,
            "gate_status": status,
            "human_review_required": human_review_required,
            "warnings": warnings,
            "result": normalized,
        }

    def _load_resolution_row(self, conn: sqlite3.Connection, resolution_id: str) -> sqlite3.Row:
        row = conn.execute(
            "SELECT * FROM resolver_resolutions WHERE resolution_id = ?",
            (resolution_id,),
        ).fetchone()
        if not row:
            raise KeyError(f"Resolution not found: {resolution_id}")
        return row

    def get_resolution(self, resolution_id: str) -> Dict[str, Any]:
        with self._connect() as conn:
            row = self._load_resolution_row(conn, resolution_id)
        return {
            "resolution_id": str(row["resolution_id"]),
            "gate_status": str(row["gate_status"]),
            "human_review_required": bool(row["human_review_required"]),
            "warnings": json.loads(str(row["warnings_json"])),
            "result": json.loads(str(row["payload_json"])),
        }

    def list_pending(self, *, limit: int = 100) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT resolution_id, gate_status, human_review_required, warnings_json, payload_json, created_at, updated_at
                FROM resolver_resolutions
                WHERE gate_status IN (?, ?)
                ORDER BY updated_at ASC
                LIMIT ?
                """,
                (GateStatus.PENDING_REVIEW.value, GateStatus.PENDING_APPROVAL.value, int(limit)),
            ).fetchall()

        out: List[Dict[str, Any]] = []
        for row in rows:
            payload = json.loads(str(row["payload_json"]))
            out.append(
                {
                    "resolution_id": str(row["resolution_id"]),
                    "gate_status": str(row["gate_status"]),
                    "human_review_required": bool(row["human_review_required"]),
                    "warnings": json.loads(str(row["warnings_json"])),
                    "created_at": str(row["created_at"]),
                    "updated_at": str(row["updated_at"]),
                    "summary": {
                        "compound": ((payload.get("query_compound") or {}).get("preferred_name")),
                        "critical_flags": len(
                            [f for f in (payload.get("threat_flags") or []) if str(f.get("severity") or "").upper() == "CRITICAL"]
                        ),
                    },
                }
            )
        return out

    def _validate_action(self, *, gate_id: str, action: str, justification: str) -> None:
        if gate_id == GateId.HITL_1.value:
            allowed = REVIEW_ACTIONS
        elif gate_id == GateId.HITL_2.value:
            allowed = APPROVAL_ACTIONS
        else:
            raise ValueError(f"Unknown gate id: {gate_id}")
        if action not in allowed:
            raise ValueError(f"Action '{action}' is not allowed for gate {gate_id}")
        if action in JUSTIFICATION_REQUIRED and not justification.strip():
            raise ValueError(f"Justification required for action '{action}'")

    def _next_status(self, *, current: str, gate_id: str, action: str) -> str:
        if gate_id == GateId.HITL_1.value:
            if current != GateStatus.PENDING_REVIEW.value:
                raise ValueError("HITL-1 actions require PENDING_REVIEW status")
            if action == "dismiss":
                return GateStatus.DISMISSED.value
            if action in {"confirm", "escalate"}:
                return GateStatus.PENDING_APPROVAL.value
            return GateStatus.PENDING_REVIEW.value

        if gate_id == GateId.HITL_2.value:
            if current != GateStatus.PENDING_APPROVAL.value:
                raise ValueError("HITL-2 actions require PENDING_APPROVAL status")
            if action == "hold":
                return GateStatus.PENDING_APPROVAL.value
            return GateStatus.APPROVED.value

        raise ValueError(f"Unknown gate id: {gate_id}")

    def apply_gate_action(
        self,
        *,
        gate_id: str,
        resolution_id: str,
        action: str,
        analyst_id: str,
        justification: str = "",
        previous_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self._validate_action(gate_id=gate_id, action=action, justification=justification)
        previous_value = previous_value or {}
        new_value = new_value or {}

        with self._connect() as conn:
            row = self._load_resolution_row(conn, resolution_id)
            current_status = str(row["gate_status"])
            payload = json.loads(str(row["payload_json"]))
            next_status = self._next_status(current=current_status, gate_id=gate_id, action=action)

            # Keep immutable engine output; reviewer actions are tracked in metadata annotations.
            annotations = ((payload.get("metadata") or {}).get("hitl_annotations") or [])
            annotations.append(
                {
                    "gate_id": gate_id,
                    "action": action,
                    "analyst_id": analyst_id,
                    "timestamp": _utc_now(),
                    "justification": justification,
                    "previous_value": previous_value,
                    "new_value": new_value,
                }
            )
            payload.setdefault("metadata", {})
            payload["metadata"]["hitl_annotations"] = annotations
            payload["metadata"]["gate_status"] = next_status

            now = _utc_now()
            conn.execute(
                """
                UPDATE resolver_resolutions
                SET gate_status = ?, payload_json = ?, content_hash = ?, updated_at = ?
                WHERE resolution_id = ?
                """,
                (next_status, _stable_json(payload), _hash(payload), now, resolution_id),
            )
            self._append_gate_event(
                conn,
                record=GateRecord(
                    gate_id=gate_id,
                    resolution_id=resolution_id,
                    action=action,
                    analyst_id=analyst_id,
                    timestamp=now,
                    justification=justification,
                    previous_value=previous_value,
                    new_value=new_value,
                ),
            )

        return self.get_resolution(resolution_id)

    def list_gate_history(self, resolution_id: str, *, limit: int = 100) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT event_id, resolution_id, gate_id, action, analyst_id, timestamp, justification,
                       previous_value_json, new_value_json, prev_chain_hash, chain_hash
                FROM resolver_gate_events
                WHERE resolution_id = ?
                ORDER BY event_id DESC
                LIMIT ?
                """,
                (resolution_id, int(limit)),
            ).fetchall()

        out: List[Dict[str, Any]] = []
        for row in rows:
            out.append(
                {
                    "event_id": int(row["event_id"]),
                    "resolution_id": str(row["resolution_id"]),
                    "gate_id": str(row["gate_id"]),
                    "action": str(row["action"]),
                    "analyst_id": str(row["analyst_id"]),
                    "timestamp": str(row["timestamp"]),
                    "justification": str(row["justification"] or ""),
                    "previous_value": json.loads(str(row["previous_value_json"])),
                    "new_value": json.loads(str(row["new_value_json"])),
                    "prev_chain_hash": row["prev_chain_hash"],
                    "chain_hash": str(row["chain_hash"]),
                }
            )
        return out
