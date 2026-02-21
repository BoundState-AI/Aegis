#!/usr/bin/env python3
"""
Persistence utilities for monitor snapshots, signals, and run locks.
"""

from __future__ import annotations

import base64
import gzip
import json
import logging
import os
import sqlite3
from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha1
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from boundstate_aegis.config import (
    MONITOR_DATA_DIR,
    MONITOR_SIGNALS_FILE,
    MONITOR_SNAPSHOT_RETENTION_MONTHS,
    MONITOR_SNAPSHOTS_DIR,
)

from .models import ContentSnapshot

logger = logging.getLogger(__name__)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def source_id_for_url(url: str) -> str:
    return sha1(url.encode("utf-8")).hexdigest()[:16]


def _json_default(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "value"):
        return getattr(value, "value")
    raise TypeError(f"Unsupported json type: {type(value)!r}")


def dataclass_to_plain(value: Any) -> Any:
    if is_dataclass(value):
        out: Dict[str, Any] = {}
        for key, val in asdict(value).items():
            out[key] = dataclass_to_plain(val)
        return out
    if isinstance(value, list):
        return [dataclass_to_plain(item) for item in value]
    if isinstance(value, dict):
        return {k: dataclass_to_plain(v) for k, v in value.items()}
    if hasattr(value, "value"):
        return getattr(value, "value")
    return value


class SnapshotStore:
    def __init__(
        self,
        base_dir: Path = MONITOR_SNAPSHOTS_DIR,
        retention_months: int = MONITOR_SNAPSHOT_RETENTION_MONTHS,
    ) -> None:
        self.base_dir = Path(base_dir)
        self.retention_months = retention_months
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _source_dir(self, source_id: str) -> Path:
        path = self.base_dir / source_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def list_snapshot_files(self, source_id: str) -> List[Path]:
        source_dir = self._source_dir(source_id)
        return sorted(source_dir.glob("*.json"))

    def load_latest(self, source_id: str) -> Optional[ContentSnapshot]:
        files = self.list_snapshot_files(source_id)
        if not files:
            return None
        latest = files[-1]
        with open(latest, encoding="utf-8") as fh:
            raw = json.load(fh)
        return ContentSnapshot(**raw)

    def save(self, snapshot: ContentSnapshot, raw_content: bytes | None = None) -> Path:
        source_dir = self._source_dir(snapshot.source_id)
        timestamp = snapshot.captured_at.replace(":", "-").replace("+00-00", "Z")
        out_path = source_dir / f"{timestamp}.json"
        payload = dataclass_to_plain(snapshot)

        if raw_content:
            payload["raw_content_gzip_b64"] = base64.b64encode(gzip.compress(raw_content)).decode("ascii")

        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, default=_json_default)

        self.prune(snapshot.source_id)
        return out_path

    def prune(self, source_id: str) -> None:
        if self.retention_months <= 0:
            return
        cutoff = datetime.now(timezone.utc) - timedelta(days=30 * self.retention_months)
        for path in self.list_snapshot_files(source_id):
            try:
                with open(path, encoding="utf-8") as fh:
                    raw = json.load(fh)
                captured_at = raw.get("captured_at")
                if not captured_at:
                    continue
                dt = datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
                if dt < cutoff:
                    path.unlink(missing_ok=True)
            except Exception:
                continue


class _SQLiteMonitorDB:
    def __init__(self, db_path: Path) -> None:
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
                CREATE TABLE IF NOT EXISTS monitor_signals (
                    signal_id TEXT PRIMARY KEY,
                    detected_at TEXT NOT NULL,
                    severity TEXT,
                    classification TEXT,
                    source_label TEXT,
                    source_url TEXT,
                    country TEXT,
                    payload_json TEXT NOT NULL,
                    inserted_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_monitor_signals_detected_at "
                "ON monitor_signals(detected_at DESC)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS monitor_run_locks (
                    lock_name TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    acquired_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_monitor_run_locks_expires_at "
                "ON monitor_run_locks(expires_at)"
            )

    def insert_signal_if_new(self, row: Dict[str, Any]) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO monitor_signals (
                    signal_id, detected_at, severity, classification,
                    source_label, source_url, country, payload_json, inserted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(signal_id) DO NOTHING
                """,
                (
                    row["signal_id"],
                    row.get("detected_at", ""),
                    row.get("severity"),
                    row.get("classification"),
                    row.get("source_label"),
                    row.get("source_url"),
                    row.get("country"),
                    json.dumps(row, default=_json_default),
                    utc_now_iso(),
                ),
            )
            return cur.rowcount == 1

    def list_recent_signals(self, limit: int) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            cur = conn.execute(
                """
                SELECT payload_json FROM monitor_signals
                ORDER BY detected_at DESC
                LIMIT ?
                """,
                (int(limit),),
            )
            rows = []
            for db_row in cur.fetchall():
                try:
                    rows.append(json.loads(db_row["payload_json"]))
                except Exception:
                    continue
            return rows

    def get_signal(self, signal_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT payload_json FROM monitor_signals WHERE signal_id = ?",
                (signal_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            try:
                return json.loads(row["payload_json"])
            except Exception:
                return None

    def delete_signals_by_id_prefix(self, prefix: str) -> int:
        if not prefix:
            return 0
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM monitor_signals WHERE signal_id LIKE ?",
                (f"{prefix}%",),
            )
            return int(cur.rowcount or 0)

    def count_signals(self) -> int:
        with self._connect() as conn:
            cur = conn.execute("SELECT COUNT(*) AS c FROM monitor_signals")
            row = cur.fetchone()
            return int(row["c"] if row else 0)

    def acquire_lock(self, lock_name: str, owner_id: str, ttl_seconds: int) -> bool:
        now = datetime.now(timezone.utc)
        expires = now + timedelta(seconds=max(30, int(ttl_seconds)))
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "DELETE FROM monitor_run_locks WHERE expires_at < ?",
                (now.isoformat(),),
            )
            cur = conn.execute(
                """
                INSERT INTO monitor_run_locks(lock_name, owner_id, acquired_at, expires_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(lock_name) DO NOTHING
                """,
                (lock_name, owner_id, now.isoformat(), expires.isoformat()),
            )
            conn.commit()
            return cur.rowcount == 1

    def release_lock(self, lock_name: str, owner_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM monitor_run_locks WHERE lock_name = ? AND owner_id = ?",
                (lock_name, owner_id),
            )


class _PostgresMonitorDB:
    def __init__(self, dsn: str) -> None:
        try:
            import psycopg  # type: ignore
        except Exception as exc:  # pragma: no cover - dependency-gated
            raise RuntimeError(
                "Postgres backend requested via AEGIS_MONITOR_DB_URL but psycopg is not installed."
            ) from exc
        self.psycopg = psycopg
        self.dsn = dsn
        self._init_schema()

    def _connect(self):
        conn = self.psycopg.connect(self.dsn)
        conn.autocommit = True
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS monitor_signals (
                    signal_id TEXT PRIMARY KEY,
                    detected_at TEXT NOT NULL,
                    severity TEXT,
                    classification TEXT,
                    source_label TEXT,
                    source_url TEXT,
                    country TEXT,
                    payload_json TEXT NOT NULL,
                    inserted_at TEXT NOT NULL
                )
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_monitor_signals_detected_at "
                "ON monitor_signals(detected_at DESC)"
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS monitor_run_locks (
                    lock_name TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    acquired_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_monitor_run_locks_expires_at "
                "ON monitor_run_locks(expires_at)"
            )

    def insert_signal_if_new(self, row: Dict[str, Any]) -> bool:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO monitor_signals (
                    signal_id, detected_at, severity, classification,
                    source_label, source_url, country, payload_json, inserted_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(signal_id) DO NOTHING
                """,
                (
                    row["signal_id"],
                    row.get("detected_at", ""),
                    row.get("severity"),
                    row.get("classification"),
                    row.get("source_label"),
                    row.get("source_url"),
                    row.get("country"),
                    json.dumps(row, default=_json_default),
                    utc_now_iso(),
                ),
            )
            return cur.rowcount == 1

    def list_recent_signals(self, limit: int) -> List[Dict[str, Any]]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT payload_json FROM monitor_signals
                ORDER BY detected_at DESC
                LIMIT %s
                """,
                (int(limit),),
            )
            rows = []
            for (payload_json,) in cur.fetchall():
                try:
                    rows.append(json.loads(payload_json))
                except Exception:
                    continue
            return rows

    def get_signal(self, signal_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT payload_json FROM monitor_signals WHERE signal_id = %s",
                (signal_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            try:
                return json.loads(row[0])
            except Exception:
                return None

    def delete_signals_by_id_prefix(self, prefix: str) -> int:
        if not prefix:
            return 0
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "DELETE FROM monitor_signals WHERE signal_id LIKE %s",
                (f"{prefix}%",),
            )
            return int(cur.rowcount or 0)

    def count_signals(self) -> int:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM monitor_signals")
            row = cur.fetchone()
            return int(row[0] if row else 0)

    def acquire_lock(self, lock_name: str, owner_id: str, ttl_seconds: int) -> bool:
        now = datetime.now(timezone.utc)
        expires = now + timedelta(seconds=max(30, int(ttl_seconds)))
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "DELETE FROM monitor_run_locks WHERE expires_at < %s",
                (now.isoformat(),),
            )
            cur.execute(
                """
                INSERT INTO monitor_run_locks(lock_name, owner_id, acquired_at, expires_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT(lock_name) DO NOTHING
                """,
                (lock_name, owner_id, now.isoformat(), expires.isoformat()),
            )
            return cur.rowcount == 1

    def release_lock(self, lock_name: str, owner_id: str) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                "DELETE FROM monitor_run_locks WHERE lock_name = %s AND owner_id = %s",
                (lock_name, owner_id),
            )


def _build_monitor_db() -> Any:
    db_url = os.getenv("AEGIS_MONITOR_DB_URL", "").strip()
    if not db_url:
        db_path = Path(os.getenv("AEGIS_MONITOR_SQLITE_PATH", str(MONITOR_DATA_DIR / "monitor.db")))
        return _SQLiteMonitorDB(db_path=db_path)

    parsed = urlparse(db_url)
    if parsed.scheme.startswith("postgres"):
        return _PostgresMonitorDB(dsn=db_url)
    if parsed.scheme.startswith("sqlite"):
        if parsed.path:
            raw_path = parsed.path
            # Preserve absolute POSIX paths; normalize Windows drive paths like /D:/...
            if len(raw_path) > 3 and raw_path[0] == "/" and raw_path[2] == ":":
                raw_path = raw_path[1:]
            db_path = Path(raw_path)
        else:
            db_path = Path(MONITOR_DATA_DIR / "monitor.db")
        return _SQLiteMonitorDB(db_path=db_path)
    raise RuntimeError(f"Unsupported AEGIS_MONITOR_DB_URL scheme: {parsed.scheme!r}")


class SignalStore:
    """
    DB-backed signal persistence with idempotent inserts.
    """

    def __init__(self, file_path: Path = MONITOR_SIGNALS_FILE) -> None:
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = _build_monitor_db()
        self._migrate_legacy_json()

    def _migrate_legacy_json(self) -> None:
        if not self.file_path.exists():
            return
        if self.db.count_signals() > 0:
            return
        try:
            with open(self.file_path, encoding="utf-8") as fh:
                rows = json.load(fh)
            if not isinstance(rows, list):
                return
            migrated = 0
            for row in rows:
                if not isinstance(row, dict):
                    continue
                signal_id = str(row.get("signal_id") or "").strip()
                if not signal_id:
                    continue
                if self.db.insert_signal_if_new(row):
                    migrated += 1
            if migrated:
                logger.info("Migrated %d legacy signal rows into monitor.db", migrated)
        except Exception as exc:
            logger.warning("Failed legacy signal migration from %s: %s", self.file_path, exc)

    def append(self, signal: Any) -> bool:
        row = dataclass_to_plain(signal)
        signal_id = str(row.get("signal_id") or "").strip()
        if not signal_id:
            raise ValueError("signal_id is required for idempotent persistence")
        return self.db.insert_signal_if_new(row)

    def list_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.db.list_recent_signals(limit=limit)

    def get(self, signal_id: str) -> Optional[Dict[str, Any]]:
        return self.db.get_signal(signal_id=signal_id)

    def delete_by_signal_id_prefix(self, prefix: str) -> int:
        return int(self.db.delete_signals_by_id_prefix(prefix=prefix))


class RunLockStore:
    """
    Coarse-grained monitor run lock to prevent concurrent overlapping runs.
    """

    def __init__(self) -> None:
        self.db = _build_monitor_db()

    def acquire(self, *, lock_name: str, owner_id: str, ttl_seconds: int) -> bool:
        return self.db.acquire_lock(lock_name=lock_name, owner_id=owner_id, ttl_seconds=ttl_seconds)

    def release(self, *, lock_name: str, owner_id: str) -> None:
        self.db.release_lock(lock_name=lock_name, owner_id=owner_id)
