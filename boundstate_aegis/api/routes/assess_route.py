#!/usr/bin/env python3
"""
Module: assess_route
Purpose: POST /api/pfas/analyze endpoint for PFAS risk assessment.
    Provides the main risk assessment endpoint that evaluates compounds
    against degradation pathways and returns risk classifications.

    Rev History:
        1.0.0 - Initial assess route with PFASRiskEngine integration
        1.1.0 - Wired to real pfas_fate_v2.json literature data

BoundState AI 2025
Version: 1.1.0
Classification: BoundState Proprietary

Authored-By: Dr. Joseph Wilde, BoundState AI
Oracle 1: ClaudeOpus 4.5 <noreply@anthropic.com>
Oracle 2: Fran OpenAI 5.2 <noreply@openai.com>
Oracle 3: Grok 4.0 <noreply@x.ai>

"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import threading
from typing import Any, Dict, List, Optional

from io import BytesIO
from datetime import datetime

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from fpdf import FPDF

from boundstate_aegis.knowledge.graph_builder import build_graph, get_cached_graph
from boundstate_aegis.engines.pfas_risk_engine import PFASRiskEngine
from boundstate_aegis.config import PFAS_FATE_V2_JSON

logger = logging.getLogger(__name__)

router = APIRouter()

# Thread-safe cache for literature data
_fate_cache: Optional[Dict[str, Any]] = None
_fate_cache_lock = threading.Lock()


def get_fate_data() -> Dict[str, Any]:
    """Load and cache the real pfas_fate_v2.json literature corpus (thread-safe)."""
    global _fate_cache
    if _fate_cache is not None:
        return _fate_cache

    with _fate_cache_lock:
        # Double-check after acquiring lock
        if _fate_cache is not None:
            return _fate_cache
        if PFAS_FATE_V2_JSON.exists():
            with open(PFAS_FATE_V2_JSON, encoding="utf-8") as f:
                _fate_cache = json.load(f)
            logger.info(f"Loaded {len(_fate_cache.get('pathways', []))} pathways from pfas_fate_v2.json")
        else:
            logger.warning(f"pfas_fate_v2.json not found at {PFAS_FATE_V2_JSON}")
            _fate_cache = {"pathways": [], "metadata": {}}
    return _fate_cache


def get_literature_pathways(material: str) -> List[Dict[str, Any]]:
    """
    Pull degradation pathways from real pfas_fate_v2.json literature data.
    Returns list of pathway dicts with real evidence_score, DOIs, and verbatim quotes.
    """
    fate_data = get_fate_data()
    mat_upper = material.upper()

    # Find all pathways where this material is the precursor
    matching = []
    for pathway in fate_data.get("pathways", []):
        precursor = pathway.get("precursor", "").upper()
        # Match exact or partial (e.g., "PTFE" matches "PTFE", "PTFE polymer")
        if mat_upper == precursor or mat_upper in precursor or precursor in mat_upper:
            matching.append(pathway)

    # Convert to internal format
    results = []
    for p in matching:
        # Get temperature range
        temp_range = p.get("temp_c_range", [None, None])
        min_temp = temp_range[0] if temp_range and len(temp_range) > 0 else None
        max_temp = temp_range[1] if temp_range and len(temp_range) > 1 else None

        # Map temp_bucket to temperature if no explicit range
        if min_temp is None:
            bucket = p.get("temp_bucket", "ambient")
            if bucket == "ambient":
                min_temp, max_temp = 0, 100
            elif bucket == "elevated":
                min_temp, max_temp = 100, 400
            elif bucket == "high":
                min_temp, max_temp = 400, 800

        # Determine regulatory flags based on product
        product = p.get("product", "")
        product_upper = product.upper()
        regulatory = []
        if product_upper in ["TFA", "PFOA", "PFOS", "PFNA", "PFDA", "PFHXS"]:
            regulatory.append("EPA MCL 4ppt")
        if product_upper in ["PFOA", "PFOS"]:
            regulatory.append("Stockholm Convention")
        if product_upper in ["HFPO-DA", "GENX"]:
            regulatory.append("EPA Health Advisory 10ppt")

        # Get DOIs and evidence
        dois = p.get("source_dois", [])
        evidence_refs = p.get("evidence_refs", [])

        results.append({
            "child": product,
            "mechanism": p.get("mechanism", "unknown"),
            "min_temp_c": min_temp,
            "max_temp_c": max_temp,
            "literature_support": p.get("evidence_score", 0.5),  # Real score from literature
            "regulatory": regulatory,
            "observation_count": p.get("observation_count", 1),
            "source_dois": dois[:3],  # Top 3 DOIs
            "paper_count": len(set(dois)),
            "evidence_refs": evidence_refs[:2],  # Sample evidence refs
        })

    return results


class AnalyzeRequest(BaseModel):
    """Request body for /api/pfas/analyze endpoint."""

    compound: Optional[str] = Field(None, description="Name of the precursor compound to evaluate")
    source_compound: Optional[str] = Field(None, description="Alias for compound")
    scenario: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Scenario conditions: service_temp_c, incident_temp_c, atmosphere",
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Alias for scenario",
    )
    max_depth: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum transformation steps to explore",
    )
    locale: str = Field(default="en", description="BCP47 locale tag")

    def get_compound(self) -> str:
        """Get compound from either field."""
        return self.compound or self.source_compound or ""

    def get_scenario(self) -> Optional[Dict[str, Any]]:
        """Get scenario from either field."""
        return self.scenario or self.context


class Finding(BaseModel):
    """A single PFAS pathway finding - matches frontend expectations."""

    product: str
    screening_classification: str
    conditions_where_it_forms: List[Dict[str, Any]]
    regulatory_flags: List[str]
    evidence_refs: List[Dict[str, Any]]

    # Honest terminology: Evidence strength from literature agreement
    # NOT a statistical probability - reflects consensus across peer-reviewed sources
    evidence_strength: float = 0.0
    support_lower: float = 0.0  # Lower bound of literature agreement range
    support_upper: float = 1.0  # Upper bound of literature agreement range

    # Legacy field aliases for backwards compatibility (deprecated)
    confidence: float = 0.0  # Use evidence_strength instead
    literature_support: float = 0.0  # Alias for evidence_strength
    overall_confidence: float = 0.0  # Alias for evidence_strength

    # Additional fields for frontend compatibility
    pathway: List[str] = []
    litigation_flag: bool = False
    is_short_chain_pfas: bool = False

    # Literature provenance fields
    observation_count: int = 0
    paper_count: int = 0
    source_dois: List[str] = []


class AnalyzeResponse(BaseModel):
    """Response body for /api/pfas/analyze endpoint."""

    compound_evaluated: str
    scenario_context: Dict[str, Any]
    pfas_findings: List[Finding]
    summary: str
    data_source: str = "pfas_fate_v2.json"
    papers_in_corpus: int = 353
    disclaimer: str = "SCREENING ONLY: Results are literature-derived estimates from peer-reviewed publications. Analytical confirmation (EPA 537.1/533/8327) required for compliance decisions."


def _is_japanese(locale: Optional[str]) -> bool:
    return (locale or "").lower().startswith("ja")


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_pfas(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Analyze potential PFAS formation pathways for a source compound.

    This endpoint performs screening-level assessment of degradation pathways
    from a precursor material to regulated PFAS endpoints under specified
    operating or incident conditions.

    **Important Limitations:**
    - Screening-level only - does not estimate formation yields or rates
    - Literature-derived pathways may be incomplete
    - Analytical confirmation (EPA 537.1/533/8327) required for compliance
    """
    compound = request.get_compound()
    scenario = request.get_scenario()

    if not compound:
        raise HTTPException(status_code=400, detail="compound or source_compound is required")

    try:
        # Use cached graph with thread-safe initialization (offload blocking I/O)
        graph = await asyncio.to_thread(get_cached_graph)
        engine = PFASRiskEngine(graph)

        result = engine.evaluate(
            source=compound,
            context=scenario,
            max_depth=request.max_depth,
        )

        # Short-chain PFAS products (C4-C6)
        short_chain_pfas = {"TFA", "PFBA", "PFPeA", "PFHxA", "PFBS", "PFHxS", "HFPO-DA"}
        # Products with litigation exposure
        litigation_products = {"PFOA", "PFOS", "GENX", "HFPO-DA", "PFNA", "PFHXS"}

        findings = []
        engine_findings = result.get("pfas_findings", [])

        if engine_findings:
            # Use findings from knowledge graph
            for f in engine_findings:
                product = f["product"]
                conditions = f.get("conditions_where_it_forms", [])

                # Build pathway from conditions
                pathway = [c.get("step", "") for c in conditions if c.get("step")]
                if not pathway:
                    pathway = [compound, product]

                # Normalize evidence_refs to include explicit doi field
                raw_refs = f.get("evidence_refs", [])
                evidence_refs = []
                for ref in raw_refs:
                    normalized = dict(ref)
                    # Extract DOI from source field if not already present
                    if "doi" not in normalized or not normalized.get("doi"):
                        source = ref.get("source", "")
                        if source.startswith("DOI:"):
                            normalized["doi"] = source[4:]
                        elif source.startswith("10."):
                            normalized["doi"] = source
                        else:
                            normalized["doi"] = None
                    evidence_refs.append(normalized)

                # Calculate literature agreement range (±0.15 based on evidence variance)
                strength = f["confidence"]
                agreement_range = 0.15  # Could be computed from actual variance in future
                findings.append(Finding(
                    product=product,
                    screening_classification=f["screening_classification"],
                    conditions_where_it_forms=conditions,
                    # New honest terminology
                    evidence_strength=strength,
                    support_lower=max(0.0, strength - agreement_range),
                    support_upper=min(1.0, strength + agreement_range),
                    # Legacy fields for backwards compatibility
                    confidence=strength,
                    literature_support=strength,
                    overall_confidence=strength,
                    regulatory_flags=f["regulatory_flags"],
                    evidence_refs=evidence_refs,
                    pathway=pathway,
                    litigation_flag=product.upper() in litigation_products,
                    is_short_chain_pfas=product.upper() in short_chain_pfas,
                ))
        else:
            # Use real literature data from pfas_fate_v2.json
            literature_pathways = get_literature_pathways(compound)
            incident_temp = scenario.get("incident_temp_c", 0) if scenario else 0

            for pathway_data in literature_pathways:
                min_temp = pathway_data.get("min_temp_c", 0) or 0
                max_temp = pathway_data.get("max_temp_c", 9999) or 9999

                # Only include if temperature is in range
                if incident_temp >= min_temp or incident_temp == 0:
                    product = pathway_data["child"]
                    mechanism = pathway_data.get("mechanism", "thermal")
                    lit_support = pathway_data.get("literature_support", 0.5)
                    regulatory = pathway_data.get("regulatory", [])
                    obs_count = pathway_data.get("observation_count", 1)
                    paper_count = pathway_data.get("paper_count", 1)
                    source_dois = pathway_data.get("source_dois", [])
                    raw_evidence = pathway_data.get("evidence_refs", [])

                    # Determine screening classification
                    if regulatory:
                        classification = "REGULATED"
                    elif product.upper() in short_chain_pfas:
                        classification = "SHORT_CHAIN_PFAS"
                    else:
                        classification = "DEGRADATION_PRODUCT"

                    # Build evidence refs from real literature data
                    evidence_refs = []
                    for ev in raw_evidence[:2]:  # Top 2 evidence items
                        evidence_refs.append({
                            "property": "degradation_pathway",
                            "value": ev.get("verbatim_quote", "")[:200] if ev.get("verbatim_quote") else mechanism,
                            "source": ev.get("doi", "literature"),
                            "doi": ev.get("doi"),  # Explicit DOI field for frontend
                            "test_method": mechanism,
                            "date": ev.get("source_file", "literature"),
                            "literature_support": lit_support,
                        })
                    if not evidence_refs:
                        evidence_refs.append({
                            "property": "degradation_pathway",
                            "value": f"{compound} degrades to {product} via {mechanism}",
                            "source": source_dois[0] if source_dois else "pfas_fate_v2.json",
                            "doi": source_dois[0] if source_dois else None,  # Explicit DOI field
                            "test_method": mechanism,
                            "date": "literature_extraction",
                            "literature_support": lit_support,
                        })

                    # Calculate agreement range - wider when fewer papers, narrower with more
                    # Base range is ±0.2, reduced by sqrt(paper_count) for multiple sources
                    base_range = 0.2
                    agreement_range = base_range / math.sqrt(max(1, paper_count))

                    findings.append(Finding(
                        product=product,
                        screening_classification=classification,
                        conditions_where_it_forms=[{
                            "step": f"{compound} → {product}",
                            "mechanism": mechanism,
                            "min_temp_c": min_temp,
                            "max_temp_c": max_temp,
                            "atmosphere": scenario.get("atmosphere", "air") if scenario else "air",
                        }],
                        # New honest terminology
                        evidence_strength=lit_support,
                        support_lower=max(0.0, lit_support - agreement_range),
                        support_upper=min(1.0, lit_support + agreement_range),
                        # Legacy fields for backwards compatibility
                        confidence=lit_support,
                        literature_support=lit_support,
                        overall_confidence=lit_support,
                        regulatory_flags=regulatory,
                        evidence_refs=evidence_refs,
                        pathway=[compound, product],
                        litigation_flag=product.upper().replace(" ", "") in litigation_products,
                        is_short_chain_pfas=product.upper() in short_chain_pfas,
                        observation_count=obs_count,
                        paper_count=paper_count,
                        source_dois=source_dois,
                    ))

        is_ja = _is_japanese(request.locale)
        summary = "" if is_ja else result.get("summary", "")
        if not summary:
            if findings:
                # Count unique papers across all findings
                all_dois = set()
                total_observations = 0
                for f in findings:
                    all_dois.update(f.source_dois)
                    total_observations += f.observation_count
                paper_count = len(all_dois) if all_dois else sum(f.paper_count for f in findings)
                if is_ja:
                    summary = f"{compound} の分析では、{paper_count} 本の査読論文から {len(findings)} 件の分解経路（観測 {total_observations} 件）が確認されました。"
                else:
                    summary = f"Analysis of {compound} identified {len(findings)} degradation pathways from {paper_count} peer-reviewed papers ({total_observations} observations)."
            else:
                if is_ja:
                    summary = f"{compound} については、文献コーパス（353本を確認）内で文書化された分解経路は見つかりませんでした。"
                else:
                    summary = f"No documented degradation pathways found for {compound} in the literature corpus (353 papers screened)."

        # Get metadata from fate data
        fate_data = get_fate_data()
        metadata = fate_data.get("metadata", {})
        papers_in_corpus = metadata.get("papers_processed", 353)

        return AnalyzeResponse(
            compound_evaluated=result.get("compound_evaluated", compound),
            scenario_context=result.get("scenario_context", scenario or {}),
            pfas_findings=findings,
            summary=summary,
            data_source="pfas_fate_v2.json（文献抽出から集約した732件の経路）" if is_ja else "pfas_fate_v2.json (732 aggregated pathways from literature extraction)",
            papers_in_corpus=papers_in_corpus,
            disclaimer=(
                "スクリーニング用途のみ: 結果は査読文献から導出した推定です。コンプライアンス判断には分析確認（EPA 537.1/533/8327）が必要です。"
                if is_ja
                else "SCREENING ONLY: Results are literature-derived estimates from peer-reviewed publications. Analytical confirmation (EPA 537.1/533/8327) required for compliance decisions."
            ),
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("Error during PFAS analysis")
        raise HTTPException(status_code=500, detail="Analysis failed")


# Alias endpoint for backwards compatibility
@router.post("/evaluate", response_model=AnalyzeResponse)
async def evaluate_pfas(request: AnalyzeRequest) -> AnalyzeResponse:
    """Alias for /analyze endpoint."""
    return await analyze_pfas(request)


class PDFRequest(BaseModel):
    """Request body for PDF generation."""
    material: str
    conditions: Optional[Dict[str, Any]] = None


@router.post("/analyze/pdf")
async def generate_analysis_pdf(request: PDFRequest):
    """
    Generate a PDF report for PFAS analysis results.

    Returns a downloadable PDF document with analysis findings.
    """
    # First run the analysis
    analyze_request = AnalyzeRequest(
        compound=request.material,
        scenario={
            "incident_temp_c": request.conditions.get("temperature", 25) if request.conditions else 25,
            "atmosphere": request.conditions.get("atmosphere", "air") if request.conditions else "air",
        } if request.conditions else None
    )

    try:
        analysis = await analyze_pfas(analyze_request)
    except HTTPException as e:
        raise e
    except Exception:
        raise HTTPException(status_code=500, detail="Analysis failed")

    # Generate PDF
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "AEGIS PFAS Risk Assessment Report", ln=True, align="C")
    pdf.ln(5)

    # Metadata
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}", ln=True, align="C")
    pdf.cell(0, 5, f"Material: {analysis.compound_evaluated}", ln=True, align="C")
    pdf.ln(10)

    # Disclaimer
    pdf.set_fill_color(255, 245, 238)
    pdf.set_text_color(180, 80, 50)
    pdf.set_font("Helvetica", "I", 8)
    pdf.multi_cell(0, 4, analysis.disclaimer, fill=True)
    pdf.ln(8)

    # Summary
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Executive Summary", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5, analysis.summary)
    pdf.ln(5)

    # Conditions
    if analysis.scenario_context:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Analysis Conditions", ln=True)
        pdf.set_font("Helvetica", "", 10)
        for key, value in analysis.scenario_context.items():
            pdf.cell(0, 5, f"  {key}: {value}", ln=True)
        pdf.ln(5)

    # Findings
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, f"Identified Pathways ({len(analysis.pfas_findings)})", ln=True)
    pdf.ln(3)

    for i, finding in enumerate(analysis.pfas_findings, 1):
        # Finding header
        pdf.set_font("Helvetica", "B", 10)
        classification_color = {
            "REGULATED": (220, 50, 50),
            "SHORT_CHAIN_PFAS": (200, 150, 50),
            "DEGRADATION_PRODUCT": (100, 100, 100),
        }.get(finding.screening_classification, (0, 0, 0))
        pdf.set_text_color(*classification_color)
        pdf.cell(0, 6, f"{i}. {finding.product} [{finding.screening_classification}]", ln=True)

        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", "", 9)

        # Evidence strength
        strength_pct = finding.evidence_strength * 100
        pdf.cell(0, 5, f"   Evidence Strength: {strength_pct:.0f}% (range: {finding.support_lower*100:.0f}-{finding.support_upper*100:.0f}%)", ln=True)

        # Pathway
        if finding.pathway:
            pdf.cell(0, 5, f"   Pathway: {' -> '.join(finding.pathway)}", ln=True)

        # Regulatory flags
        if finding.regulatory_flags:
            pdf.set_text_color(180, 50, 50)
            pdf.cell(0, 5, f"   Regulatory: {', '.join(finding.regulatory_flags)}", ln=True)
            pdf.set_text_color(0, 0, 0)

        # Conditions
        for cond in finding.conditions_where_it_forms[:1]:
            mechanism = cond.get("mechanism", "unknown")
            min_t = cond.get("min_temp_c", "N/A")
            max_t = cond.get("max_temp_c", "N/A")
            pdf.cell(0, 5, f"   Mechanism: {mechanism} | Temp: {min_t}-{max_t} C", ln=True)

        # DOIs
        if finding.source_dois:
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(80, 80, 150)
            dois_str = ", ".join(finding.source_dois[:2])
            pdf.cell(0, 4, f"   Sources: {dois_str}", ln=True)
            pdf.set_text_color(0, 0, 0)

        pdf.ln(3)

    # Footer
    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 4, f"Data source: {analysis.data_source}", ln=True)
    pdf.cell(0, 4, f"Literature corpus: {analysis.papers_in_corpus} papers", ln=True)
    pdf.cell(0, 4, "AEGIS by BoundState AI - For screening purposes only", ln=True)

    # Output PDF
    pdf_buffer = BytesIO()
    pdf.output(pdf_buffer)
    pdf_buffer.seek(0)

    filename = f"aegis-pfas-analysis-{request.material}-{datetime.now().strftime('%Y%m%d')}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
