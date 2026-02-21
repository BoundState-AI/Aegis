#!/usr/bin/env python3
"""
Capability registry for destruction/remediation coverage.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from boundstate_aegis.config import DATA_DIR


@dataclass(frozen=True)
class TechCapability:
    technology: str
    provider: str
    trl: int
    effective_compounds: Tuple[str, ...]
    evidence: Tuple[Dict[str, Any], ...]
    client_status: Dict[str, str]
    notes: str = ""

    def supports(self, compound: str) -> bool:
        needle = (compound or "").strip().lower()
        for token in self.effective_compounds:
            t = token.strip().lower()
            if needle == t or needle in t or t in needle:
                return True
        return False

    def status_for_client(self, client: str) -> str:
        return str(self.client_status.get((client or "").lower(), "unknown")).lower()


class CapabilityRegistry:
    def __init__(self, *, version: str, capabilities: List[TechCapability]) -> None:
        self.version = version
        self.capabilities = capabilities

    def has_client_capability(self, compound: str, client: str = "chemours") -> bool:
        for cap in self.capabilities:
            if cap.supports(compound) and cap.status_for_client(client) in {"owned", "licensed"}:
                return True
        return False

    def get_available_technologies(self, compound: str) -> List[TechCapability]:
        return [cap for cap in self.capabilities if cap.supports(compound)]

    def get_gap_detail(self, compound: str, client: str = "chemours") -> str:
        available = self.get_available_technologies(compound)
        if not available:
            return f"No known destruction/remediation technology registered for {compound}."
        owned = [c.technology for c in available if c.status_for_client(client) in {"owned", "licensed"}]
        if owned:
            return f"{client} has capability coverage for {compound}: {', '.join(sorted(owned))}."
        providers = ", ".join(sorted({f"{c.technology} ({c.provider})" for c in available}))
        return (
            f"{client} has no owned/licensed capability for {compound}. "
            f"Known external technologies: {providers}."
        )

    @classmethod
    @lru_cache(maxsize=1)
    def load(cls, path: Optional[Path] = None) -> "CapabilityRegistry":
        registry_path = path or (DATA_DIR / "capability_registry.yaml")
        with open(registry_path, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}

        version = str(raw.get("registry_version") or "1.0.0")
        caps: List[TechCapability] = []
        for row in raw.get("capabilities") or []:
            if not isinstance(row, dict):
                continue
            caps.append(
                TechCapability(
                    technology=str(row.get("technology") or "").strip(),
                    provider=str(row.get("provider") or "").strip(),
                    trl=int(row.get("trl") or 0),
                    effective_compounds=tuple(
                        str(x).strip() for x in (row.get("effective_compounds") or []) if str(x).strip()
                    ),
                    evidence=tuple(x for x in (row.get("evidence") or []) if isinstance(x, dict)),
                    client_status={str(k).lower(): str(v) for k, v in (row.get("client_status") or {}).items()},
                    notes=str(row.get("notes") or ""),
                )
            )
        return cls(version=version, capabilities=caps)
