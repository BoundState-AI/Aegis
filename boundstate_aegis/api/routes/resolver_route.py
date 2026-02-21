#!/usr/bin/env python3
"""
Recursive regulatory resolver API endpoints.
"""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from boundstate_aegis.api.routes.monitor_route import require_approver, require_operator, require_viewer
from boundstate_aegis.engines.hitl_gates import GateId, HITLGateStore
from boundstate_aegis.engines.product_manifest import ProductManifest
from boundstate_aegis.engines.recursive_resolver import UnresolvableCompound, resolve

router = APIRouter()
_HITL_STORE = HITLGateStore()


class ResolveRequest(BaseModel):
    compound: str = Field(..., description="Product name, CAS, SMILES, or common name")
    max_depth: int = Field(4, ge=1, le=8)
    max_nodes: int = Field(50, ge=10, le=200)
    max_branching: int = Field(10, ge=3, le=25)
    min_confidence: float = Field(0.3, ge=0.0, le=1.0)
    include_evidence: bool = Field(True)


class BatchResolveRequest(BaseModel):
    compounds: List[str] = Field(default_factory=list, max_length=20)
    max_depth: int = Field(4, ge=1, le=8)
    max_nodes: int = Field(50, ge=10, le=200)
    max_branching: int = Field(10, ge=3, le=25)
    min_confidence: float = Field(0.3, ge=0.0, le=1.0)
    include_evidence: bool = Field(False)


class ReviewRequest(BaseModel):
    resolution_id: str = Field(..., min_length=4)
    action: str = Field(..., description="confirm|override|add_context|dismiss|escalate")
    justification: str = Field(default="")
    previous_value: Dict[str, Any] = Field(default_factory=dict)
    new_value: Dict[str, Any] = Field(default_factory=dict)


class ApproveRequest(BaseModel):
    resolution_id: str = Field(..., min_length=4)
    action: str = Field(..., description="approve|edit|reclassify|hold")
    justification: str = Field(default="")
    previous_value: Dict[str, Any] = Field(default_factory=dict)
    new_value: Dict[str, Any] = Field(default_factory=dict)


@router.post("/resolve")
async def resolve_compound_exposure(
    request: ResolveRequest,
    _auth: Dict[str, str] = Depends(require_viewer),
) -> Dict[str, Any]:
    try:
        raw_result = resolve(
            input_str=request.compound,
            max_depth=request.max_depth,
            max_nodes=request.max_nodes,
            max_branching=request.max_branching,
            min_confidence=request.min_confidence,
            include_evidence=request.include_evidence,
        )
        return _HITL_STORE.create_resolution(
            raw_result,
            created_by=str(_auth.get("principal", "unknown")),
        )
    except UnresolvableCompound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - runtime guard
        raise HTTPException(status_code=500, detail=f"Resolution failed: {exc}") from exc


@router.get("/resolve/{compound}")
async def resolve_quick(
    compound: str,
    include_evidence: bool = Query(False),
    _auth: Dict[str, str] = Depends(require_viewer),
) -> Dict[str, Any]:
    try:
        result = resolve(input_str=compound, include_evidence=include_evidence)
    except UnresolvableCompound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - runtime guard
        raise HTTPException(status_code=500, detail=f"Resolution failed: {exc}") from exc
    return {
        "compound": result["query_compound"]["preferred_name"],
        "total_assertions": result["total_exposure"]["assertions_triggered"],
        "trajectory": result["total_exposure"]["trajectory"],
        "threat_flags": len(result["threat_flags"]),
        "most_severe": result["total_exposure"]["most_severe_id"],
        "degradation_products": result["degradation_tree"]["total_nodes"],
    }


@router.get("/products")
async def list_products(
    _auth: Dict[str, str] = Depends(require_viewer),
) -> Dict[str, Any]:
    manifest = ProductManifest.load()
    return {"version": manifest.version, "products": manifest.list_products()}


@router.post("/resolve/batch")
async def resolve_batch(
    request: BatchResolveRequest,
    _auth: Dict[str, str] = Depends(require_viewer),
) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    for raw in request.compounds[:20]:
        try:
            raw_result = resolve(
                input_str=raw,
                max_depth=request.max_depth,
                max_nodes=request.max_nodes,
                max_branching=request.max_branching,
                min_confidence=request.min_confidence,
                include_evidence=request.include_evidence,
            )
            queued = _HITL_STORE.create_resolution(
                raw_result,
                created_by=str(_auth.get("principal", "unknown")),
            )
            results.append(queued)
        except Exception as exc:
            results.append({"compound": raw, "error": str(exc)})
    return {"count": len(results), "results": results}


@router.post("/review")
async def submit_hitl_review(
    request: ReviewRequest,
    auth: Dict[str, str] = Depends(require_operator),
) -> Dict[str, Any]:
    try:
        return _HITL_STORE.apply_gate_action(
            gate_id=GateId.HITL_1.value,
            resolution_id=request.resolution_id,
            action=request.action,
            analyst_id=str(auth.get("principal", "unknown")),
            justification=request.justification,
            previous_value=request.previous_value,
            new_value=request.new_value,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - runtime guard
        raise HTTPException(status_code=500, detail=f"Review action failed: {exc}") from exc


@router.post("/approve")
async def submit_hitl_approval(
    request: ApproveRequest,
    auth: Dict[str, str] = Depends(require_approver),
) -> Dict[str, Any]:
    try:
        return _HITL_STORE.apply_gate_action(
            gate_id=GateId.HITL_2.value,
            resolution_id=request.resolution_id,
            action=request.action,
            analyst_id=str(auth.get("principal", "unknown")),
            justification=request.justification,
            previous_value=request.previous_value,
            new_value=request.new_value,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - runtime guard
        raise HTTPException(status_code=500, detail=f"Approval action failed: {exc}") from exc


@router.get("/pending")
async def list_pending_reviews(
    limit: int = Query(100, ge=1, le=500),
    _auth: Dict[str, str] = Depends(require_viewer),
) -> Dict[str, Any]:
    rows = _HITL_STORE.list_pending(limit=limit)
    return {"count": len(rows), "items": rows}
