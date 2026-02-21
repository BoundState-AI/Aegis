#!/usr/bin/env python3
"""
Assertion governance store.

DB-backed source of truth for regulatory assertions with:
- schema validation on approval
- immutable event log
- tamper-evident hash chain
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from boundstate_aegis.config import (
    AEGIS_ASSERTION_DB_PATH,
    APAC_REGULATORY_ASSERTIONS,
    PENDING_ASSERTIONS_DIR,
    TFA_REGULATORY_ASSERTIONS,
    WESTERN_REGULATORY_ASSERTIONS,
)

logger = logging.getLogger(__name__)

REQUIRED_ASSERTION_KEYS = {
    "id",
    "assertion",
    "type",
    "compound_class",
    "confidence",
    "status",
    "dates",
    "citations",
    "context",
    "threshold_value",
    "exemptions",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stable_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _content_hash(payload: Dict[str, Any]) -> str:
    return sha256(_stable_json(payload).encode("utf-8")).hexdigest()


def _normalize_status(raw_status: Any, raw_type: Any) -> str:
    status = str(raw_status or "").strip().lower()
    typ = str(raw_type or "").strip().lower()
    token = f"{status} {typ}"
    if "enforc" in token or "enact" in token:
        return "enforced"
    if "consult" in token:
        return "consultation"
    if "adopt" in token or "final" in token:
        return "adopted"
    if "withdraw" in token:
        return "withdrawn"
    if "propos" in token or "pending" in token or "draft" in token:
        return "proposed"
    return "proposed"


@dataclass
class AssertionDecision:
    assertion_id: str
    status: str
    version: int
    content_hash: str
    chain_hash: str


class AssertionStore:
    def __init__(self, db_path: Path | str = AEGIS_ASSERTION_DB_PATH) -> None:
        self.db_path = Path(db_path)
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
                CREATE TABLE IF NOT EXISTS assertions (
                    assertion_id TEXT PRIMARY KEY,
                    region TEXT,
                    source_file TEXT,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS assertion_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    assertion_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    actor TEXT,
                    reason TEXT,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    prev_chain_hash TEXT,
                    chain_hash TEXT NOT NULL,
                    occurred_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_assertion_events_assertion_id "
                "ON assertion_events(assertion_id, event_id DESC)"
            )

    def _coerce_assertion_payload(self, payload: Dict[str, Any], *, default_compound_class: str = "PFAS_class") -> Dict[str, Any]:
        normalized = dict(payload)
        normalized["id"] = str(normalized.get("id") or "").strip()
        normalized["assertion"] = str(normalized.get("assertion") or "").strip()
        normalized["type"] = str(normalized.get("type") or "factual")
        normalized["compound_class"] = str(
            normalized.get("compound_class")
            or normalized.get("compound")
            or default_compound_class
        )
        normalized["confidence"] = float(normalized.get("confidence") or 0.7)
        normalized["status"] = _normalize_status(normalized.get("status"), normalized.get("type"))

        dates = normalized.get("dates")
        if not isinstance(dates, dict):
            dates = {}
        for key in ("proposed", "consultation_end", "finalized", "effective", "enforcement", "sunset"):
            dates.setdefault(key, None)
        # Carry through one-off date fields used by older files.
        if normalized.get("as_of_date") and not dates.get("effective"):
            dates["effective"] = str(normalized.get("as_of_date"))
        if normalized.get("effective_date") and not dates.get("effective"):
            dates["effective"] = str(normalized.get("effective_date"))
        normalized["dates"] = dates

        citations = normalized.get("citations")
        if not isinstance(citations, list):
            citations = []
        normalized["citations"] = citations

        context = normalized.get("context")
        if not isinstance(context, list):
            context = []
        # Backfill context from legacy fields where available.
        supporting = normalized.get("supporting_facts")
        if isinstance(supporting, list):
            context.extend(str(x) for x in supporting if str(x).strip())
        proposed_cls = normalized.get("proposed_classifications")
        if isinstance(proposed_cls, list):
            context.extend(str(x) for x in proposed_cls if str(x).strip())
        normalized["context"] = context

        if "threshold_value" not in normalized:
            normalized["threshold_value"] = (
                normalized.get("adi_value")
                or normalized.get("threshold")
                or None
            )
        exemptions = normalized.get("exemptions")
        if not isinstance(exemptions, list):
            exemptions = []
        normalized["exemptions"] = exemptions

        return normalized

    def validate_assertion(self, payload: Dict[str, Any]) -> None:
        missing = REQUIRED_ASSERTION_KEYS - set(payload.keys())
        if missing:
            raise ValueError(f"Assertion missing required keys: {sorted(missing)}")
        if not isinstance(payload.get("dates"), dict):
            raise ValueError("Assertion 'dates' must be an object")
        if not isinstance(payload.get("citations"), list):
            raise ValueError("Assertion 'citations' must be a list")
        if not isinstance(payload.get("context"), list):
            raise ValueError("Assertion 'context' must be a list")
        if not isinstance(payload.get("exemptions"), list):
            raise ValueError("Assertion 'exemptions' must be a list")

    def _latest_chain_hash(self, conn: sqlite3.Connection, assertion_id: str) -> Optional[str]:
        row = conn.execute(
            "SELECT chain_hash FROM assertion_events WHERE assertion_id = ? ORDER BY event_id DESC LIMIT 1",
            (assertion_id,),
        ).fetchone()
        return str(row["chain_hash"]) if row else None

    def _append_event(
        self,
        conn: sqlite3.Connection,
        *,
        assertion_id: str,
        version: int,
        action: str,
        actor: str,
        reason: str,
        status: str,
        payload: Dict[str, Any],
        content_hash: str,
    ) -> str:
        occurred_at = _utc_now()
        prev_hash = self._latest_chain_hash(conn, assertion_id)
        chain_material = _stable_json(
            {
                "assertion_id": assertion_id,
                "version": version,
                "action": action,
                "actor": actor,
                "reason": reason,
                "status": status,
                "content_hash": content_hash,
                "occurred_at": occurred_at,
                "prev_chain_hash": prev_hash or "",
            }
        )
        chain_hash = sha256(chain_material.encode("utf-8")).hexdigest()
        conn.execute(
            """
            INSERT INTO assertion_events(
                assertion_id, version, action, actor, reason, status,
                payload_json, content_hash, prev_chain_hash, chain_hash, occurred_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                assertion_id,
                version,
                action,
                actor,
                reason,
                status,
                _stable_json(payload),
                content_hash,
                prev_hash,
                chain_hash,
                occurred_at,
            ),
        )
        return chain_hash

    def upsert_assertion(
        self,
        *,
        payload: Dict[str, Any],
        status: str,
        region: str,
        source_file: str,
        actor: str,
        reason: str,
        action: str,
        record_if_unchanged: bool = False,
    ) -> AssertionDecision:
        assertion_id = str(payload.get("id") or "").strip()
        if not assertion_id:
            raise ValueError("Assertion ID is required")
        self.validate_assertion(payload)

        hash_value = _content_hash(payload)
        now = _utc_now()

        with self._connect() as conn:
            existing = conn.execute(
                "SELECT version, content_hash, status FROM assertions WHERE assertion_id = ?",
                (assertion_id,),
            ).fetchone()
            if existing:
                existing_hash = str(existing["content_hash"])
                existing_status = str(existing["status"])
                existing_version = int(existing["version"])
                if existing_hash == hash_value and existing_status == status:
                    if record_if_unchanged:
                        chain_hash = self._append_event(
                            conn,
                            assertion_id=assertion_id,
                            version=existing_version,
                            action=action,
                            actor=actor,
                            reason=reason,
                            status=status,
                            payload=payload,
                            content_hash=hash_value,
                        )
                    else:
                        chain_hash = self._latest_chain_hash(conn, assertion_id) or ""
                    return AssertionDecision(
                        assertion_id=assertion_id,
                        status=status,
                        version=existing_version,
                        content_hash=hash_value,
                        chain_hash=chain_hash,
                    )
                version = existing_version + 1
            else:
                version = 1

            conn.execute(
                """
                INSERT INTO assertions(
                    assertion_id, region, source_file, status, payload_json, content_hash,
                    version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(assertion_id) DO UPDATE SET
                    region = excluded.region,
                    source_file = excluded.source_file,
                    status = excluded.status,
                    payload_json = excluded.payload_json,
                    content_hash = excluded.content_hash,
                    version = excluded.version,
                    updated_at = excluded.updated_at
                """,
                (
                    assertion_id,
                    region,
                    source_file,
                    status,
                    _stable_json(payload),
                    hash_value,
                    version,
                    now,
                    now,
                ),
            )
            chain_hash = self._append_event(
                conn,
                assertion_id=assertion_id,
                version=version,
                action=action,
                actor=actor,
                reason=reason,
                status=status,
                payload=payload,
                content_hash=hash_value,
            )
            return AssertionDecision(
                assertion_id=assertion_id,
                status=status,
                version=version,
                content_hash=hash_value,
                chain_hash=chain_hash,
            )

    @staticmethod
    def _read_structured_file(path: Path) -> Dict[str, Any]:
        if path.suffix.lower() == ".json":
            with open(path, encoding="utf-8") as fh:
                raw = json.load(fh)
        else:
            with open(path, encoding="utf-8") as fh:
                raw = yaml.safe_load(fh) or {}
        if isinstance(raw, list):
            return {"assertions": raw}
        if isinstance(raw, dict):
            return raw
        raise ValueError(f"Unsupported assertion payload format in {path}")

    def _extract_assertions(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        assertions = payload.get("assertions", [])
        if not isinstance(assertions, list):
            raise ValueError("Assertion file 'assertions' must be a list")
        out: List[Dict[str, Any]] = []
        for row in assertions:
            if isinstance(row, dict):
                out.append(row)
        return out

    def bootstrap_from_yaml(self) -> Dict[str, int]:
        counts = {"imported": 0, "errors": 0}
        for region, path in (
            ("APAC", APAC_REGULATORY_ASSERTIONS),
            ("WESTERN", WESTERN_REGULATORY_ASSERTIONS),
            ("TFA", TFA_REGULATORY_ASSERTIONS),
        ):
            try:
                payload = self._read_structured_file(path)
                assertions = self._extract_assertions(payload)
                for row in assertions:
                    if region == "TFA" and not row.get("compound_class"):
                        row = dict(row)
                        row["compound_class"] = "TFA"
                    row = self._coerce_assertion_payload(row)
                    self.upsert_assertion(
                        payload=row,
                        status="approved",
                        region=region,
                        source_file=str(path.name),
                        actor="system.bootstrap",
                        reason="canonical import",
                        action="import",
                        record_if_unchanged=False,
                    )
                    counts["imported"] += 1
            except Exception as exc:
                logger.error("Assertion bootstrap failed for %s: %s", path, exc)
                counts["errors"] += 1
        return counts

    def list_assertions(self, *, status: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
        query = "SELECT * FROM assertions"
        params: List[Any] = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(int(limit))

        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        result: List[Dict[str, Any]] = []
        for row in rows:
            payload = json.loads(str(row["payload_json"]))
            payload["_meta"] = {
                "status": row["status"],
                "version": row["version"],
                "region": row["region"],
                "source_file": row["source_file"],
                "content_hash": row["content_hash"],
                "updated_at": row["updated_at"],
            }
            result.append(payload)
        return result

    def assertion_version(self) -> str:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*), COALESCE(MAX(updated_at), '') FROM assertions
                """
            ).fetchone()
        count = int(row[0] if row else 0)
        max_updated = str(row[1] if row else "")
        return sha256(f"{count}:{max_updated}".encode("utf-8")).hexdigest()

    def ensure_bootstrapped(self) -> Dict[str, int]:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM assertions").fetchone()
            count = int(row[0] if row else 0)
        if count > 0:
            return {"imported": 0, "errors": 0}
        return self.bootstrap_from_yaml()

    @staticmethod
    def _searchable_blob(payload: Dict[str, Any]) -> str:
        fragments: List[str] = []
        for key in (
            "assertion",
            "compound_class",
            "scope",
            "threshold_value",
            "regulatory_body",
        ):
            val = payload.get(key)
            if val is not None:
                fragments.append(str(val))
        for key in ("context", "exemptions"):
            val = payload.get(key)
            if isinstance(val, list):
                fragments.extend(str(x) for x in val)
        citations = payload.get("citations")
        if isinstance(citations, list):
            for c in citations:
                if isinstance(c, dict):
                    fragments.append(str(c.get("source") or ""))
                    fragments.append(str(c.get("url") or ""))
        return " ".join(fragments).lower()

    def _run_match(self, predicate) -> List[Dict[str, Any]]:
        rows = self.list_assertions(limit=5000)
        out: List[Dict[str, Any]] = []
        for row in rows:
            try:
                if predicate(row):
                    out.append(row)
            except Exception:
                continue
        return out

    def query_by_cas(self, cas: str) -> List[Dict[str, Any]]:
        token = (cas or "").strip()
        if not token:
            return []
        pattern = re.compile(rf"\b{re.escape(token)}\b")
        return self._run_match(lambda row: bool(pattern.search(self._searchable_blob(row))))

    def query_by_inchikey(self, inchikey: str) -> List[Dict[str, Any]]:
        token = (inchikey or "").strip().lower()
        if not token:
            return []
        return self._run_match(lambda row: token in self._searchable_blob(row))

    def query_by_name(self, name: str) -> List[Dict[str, Any]]:
        token = (name or "").strip().lower()
        if not token:
            return []
        pattern = re.compile(rf"\b{re.escape(token)}\b")
        return self._run_match(lambda row: bool(pattern.search(self._searchable_blob(row))))

    def query_by_compound_class(self, compound_class: str) -> List[Dict[str, Any]]:
        token = (compound_class or "").strip().lower()
        if not token:
            return []

        def _predicate(row: Dict[str, Any]) -> bool:
            klass = str(row.get("compound_class") or "").strip().lower()
            return klass == token or token in klass or klass in token

        return self._run_match(_predicate)

    def query_universal_pfas(self) -> List[Dict[str, Any]]:
        return self._run_match(
            lambda row: (
                "pfas_class" in str(row.get("compound_class") or "").lower()
                or "universal pfas" in self._searchable_blob(row)
                or "all pfas" in self._searchable_blob(row)
            )
        )

    def get_assertion(self, assertion_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM assertions WHERE assertion_id = ?",
                (assertion_id,),
            ).fetchone()
        if not row:
            return None
        payload = json.loads(str(row["payload_json"]))
        payload["_meta"] = {
            "status": row["status"],
            "version": row["version"],
            "region": row["region"],
            "source_file": row["source_file"],
            "content_hash": row["content_hash"],
            "updated_at": row["updated_at"],
        }
        return payload

    def list_assertion_history(self, assertion_id: str, *, limit: int = 50) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT event_id, assertion_id, version, action, actor, reason, status,
                       content_hash, prev_chain_hash, chain_hash, occurred_at
                FROM assertion_events
                WHERE assertion_id = ?
                ORDER BY event_id DESC
                LIMIT ?
                """,
                (assertion_id, int(limit)),
            ).fetchall()
        return [dict(row) for row in rows]

    def approve_pending_file(self, pending_path: Path, *, actor: str, reason: str) -> List[AssertionDecision]:
        payload = self._read_structured_file(pending_path)
        region = str(payload.get("region") or "PENDING").upper()
        assertions = self._extract_assertions(payload)
        if not assertions:
            raise ValueError(f"No assertions found in {pending_path.name}")

        decisions: List[AssertionDecision] = []
        for row in assertions:
            decisions.append(
                self.upsert_assertion(
                    payload=row,
                    status="approved",
                    region=region,
                    source_file=str(pending_path.name),
                    actor=actor,
                    reason=reason or "approved",
                    action="approve",
                    record_if_unchanged=True,
                )
            )

        approved_dir = PENDING_ASSERTIONS_DIR / "approved"
        approved_dir.mkdir(parents=True, exist_ok=True)
        target = approved_dir / pending_path.name
        shutil.move(str(pending_path), str(target))
        return decisions

    def reject_pending_file(
        self,
        pending_path: Path,
        *,
        assertion_id: str,
        actor: str,
        reason: str,
    ) -> Dict[str, Any]:
        rejected_dir = PENDING_ASSERTIONS_DIR / "rejected"
        rejected_dir.mkdir(parents=True, exist_ok=True)
        target = rejected_dir / pending_path.name
        shutil.move(str(pending_path), str(target))

        # Rejection event logged with tamper-evident chain against placeholder assertion ID.
        rejection_payload = {
            "id": assertion_id,
            "file": target.name,
            "reason": reason or "",
            "action": "reject",
        }
        decision = self.upsert_assertion(
            payload={
                "id": assertion_id,
                "assertion": f"Rejected pending assertion file {target.name}",
                "type": "rejected",
                "compound_class": "unknown",
                "confidence": 0.0,
                "status": "rejected",
                "dates": {},
                "citations": [],
                "context": [reason or "rejected"],
                "threshold_value": None,
                "exemptions": [],
            },
            status="rejected",
            region="PENDING",
            source_file=target.name,
            actor=actor,
            reason=reason or "rejected",
            action="reject",
            record_if_unchanged=True,
        )
        return {
            "file": target.name,
            "decision": decision,
            "meta": rejection_payload,
        }
