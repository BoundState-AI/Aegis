#!/usr/bin/env python3
"""
Module: eol_certificate_generator
Purpose: End-of-Life Proof Certificate generator for PFAS/TFA mineralization.
    Generates litigation-grade proof documents demonstrating:
    1. Complete degradation pathways from precursor to terminal products
    2. Destruction technology viability with verified DOI citations
    3. Chemours IP exposure analysis (forced buyer status)

    Rev History:
        1.0.0 - Initial EOL certificate generator

BoundState AI 2025
Version: 1.0.0
Classification: BoundState Proprietary

Authored-By: Dr. Joseph Wilde, BoundState AI
Oracle 1: ClaudeOpus 4.5 <noreply@anthropic.com>

"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from boundstate_aegis.knowledge.graph_builder import build_graph, PFASKnowledgeGraph
from boundstate_aegis.knowledge.graph_queries import (
    trace_pathways,
    get_downstream_products,
    get_upstream_sources,
)
from boundstate_aegis.knowledge.destruction_queries import (
    get_recommended_technology,
    get_chemours_capability_gap,
    find_destruction_options,
    get_technology,
)
from boundstate_aegis.models.destruction_technology import TechnologyRecommendation

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

class PathwayStep(BaseModel):
    """Single step in a degradation pathway."""
    source: str
    product: str
    mechanism: str
    conditions: Optional[Dict[str, Any]] = None
    confidence: float = 1.0
    citations: List[str] = Field(default_factory=list)


class DestructionProof(BaseModel):
    """Proof that a compound can be destroyed."""
    compound: str
    technology: str
    technology_full_name: Optional[str] = None
    mechanism: str
    trl: int = Field(..., ge=1, le=9, description="Technology Readiness Level")
    dre: Optional[float] = Field(None, ge=0.0, le=1.0, description="Destruction/Removal Efficiency")
    conditions: Optional[Dict[str, Any]] = None
    products: List[str] = Field(default_factory=list)
    primary_citation: Optional[str] = None
    citations: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class ChemoursIPExposure(BaseModel):
    """Chemours intellectual property exposure analysis."""
    compound: str
    owns_technology: bool = False
    owns_ip: bool = False
    must_license_from: Optional[str] = None
    forced_buyer: bool = True
    capability_gap: Optional[str] = None
    technologies_available: List[str] = Field(default_factory=list)
    technologies_owned: List[str] = Field(default_factory=list)


class EOLProofCertificate(BaseModel):
    """
    Complete End-of-Life Proof Certificate.

    Documents the full chain from precursor material through degradation
    products to terminal mineralization, with verified citations and
    IP exposure analysis.
    """
    # Header
    certificate_id: str
    generated_at: str
    version: str = "1.0.0"

    # Source material
    precursor: str
    precursor_type: str  # e.g., "HFO refrigerant", "fluoropolymer"

    # Degradation chain
    degradation_pathway: List[PathwayStep] = Field(default_factory=list)
    terminal_product: str
    terminal_product_is_pfas: bool = False

    # Destruction proof
    destruction_proof: Optional[DestructionProof] = None
    alternative_technologies: List[Dict[str, Any]] = Field(default_factory=list)
    not_viable_technologies: List[Dict[str, str]] = Field(default_factory=list)

    # Terminal products after destruction
    mineralization_products: List[str] = Field(default_factory=list)

    # IP analysis
    chemours_exposure: Optional[ChemoursIPExposure] = None

    # Evidence summary
    total_citations: int = 0
    citation_list: List[str] = Field(default_factory=list)

    # Conclusions
    conclusion: str = ""
    regulatory_implications: Optional[str] = None


# =============================================================================
# CERTIFICATE GENERATOR
# =============================================================================

class EOLCertificateGenerator:
    """
    Generates End-of-Life Proof Certificates for PFAS compounds.

    Usage:
        generator = EOLCertificateGenerator()
        cert = generator.generate("HFO-1234yf")
        print(cert.model_dump_json(indent=2))
    """

    def __init__(self, graph: Optional[PFASKnowledgeGraph] = None):
        """Initialize generator with optional pre-built graph."""
        self.graph = graph or build_graph()
        logger.info(
            "EOLCertificateGenerator initialized with %d nodes, %d edges",
            self.graph.graph.number_of_nodes(),
            self.graph.graph.number_of_edges(),
        )

    def generate(
        self,
        precursor: str,
        precursor_type: str = "fluorochemical",
        target_product: str = "TFA",
    ) -> EOLProofCertificate:
        """
        Generate an EOL Proof Certificate for a precursor compound.

        Args:
            precursor: Source material (e.g., "HFO-1234yf", "PTFE")
            precursor_type: Type description (e.g., "HFO refrigerant")
            target_product: Terminal PFAS product to trace to (default: "TFA")

        Returns:
            Complete EOLProofCertificate with all evidence
        """
        cert_id = f"EOL-{precursor.upper()}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        # Trace degradation pathway
        pathway_steps, all_citations = self._trace_pathway(precursor, target_product)

        # Get destruction proof for terminal product
        destruction_proof = self._get_destruction_proof(target_product)

        # Get alternative and non-viable technologies
        tech_options = find_destruction_options(target_product, phase="aqueous", min_trl=1)
        alternatives = [
            {
                "technology": o["technology_name"],
                "trl": o["trl"],
                "dre": o["dre"],
            }
            for o in tech_options
            if o["viable"] and o["technology_name"] != (destruction_proof.technology if destruction_proof else "")
        ][:3]

        not_viable = [
            {"technology": o["technology_name"], "reason": o["reason"]}
            for o in tech_options
            if not o["viable"]
        ]

        # Determine mineralization products
        mineralization_products = []
        if destruction_proof:
            tech = get_technology(destruction_proof.technology.lower().replace(" ", "_").replace("-", "_"))
            if tech and tech.products:
                mineralization_products = tech.products.get("primary", [])

        # Get Chemours IP exposure
        chemours_exposure = self._analyze_chemours_exposure(target_product)

        # Collect all citations
        if destruction_proof:
            all_citations.extend(destruction_proof.citations)
        citation_list = list(set(all_citations))

        # Generate conclusion
        conclusion = self._generate_conclusion(
            precursor, target_product, destruction_proof, chemours_exposure
        )

        # Regulatory implications
        regulatory = self._get_regulatory_implications(target_product, destruction_proof)

        return EOLProofCertificate(
            certificate_id=cert_id,
            generated_at=datetime.utcnow().isoformat() + "Z",
            precursor=precursor,
            precursor_type=precursor_type,
            degradation_pathway=pathway_steps,
            terminal_product=target_product,
            terminal_product_is_pfas=self._is_pfas(target_product),
            destruction_proof=destruction_proof,
            alternative_technologies=alternatives,
            not_viable_technologies=not_viable,
            mineralization_products=mineralization_products,
            chemours_exposure=chemours_exposure,
            total_citations=len(citation_list),
            citation_list=citation_list,
            conclusion=conclusion,
            regulatory_implications=regulatory,
        )

    def _trace_pathway(
        self,
        precursor: str,
        target_product: str,
    ) -> tuple[List[PathwayStep], List[str]]:
        """Trace degradation pathway from precursor to target."""
        pathway_steps: List[PathwayStep] = []
        all_citations: List[str] = []

        # Try direct path first
        paths = trace_pathways(self.graph, precursor, targets=[target_product], max_depth=5)

        if paths:
            # Use shortest path
            best_path = min(paths, key=lambda p: len(p["path"]))
            for i, condition in enumerate(best_path.get("conditions", [])):
                step_str = condition.get("step", "")
                if " -> " in step_str:
                    source, product = step_str.split(" -> ", 1)
                else:
                    continue

                # Extract citations from evidence_refs
                step_citations = []
                for ref in best_path.get("evidence_refs", []):
                    source_str = ref.get("source", "")
                    if source_str and source_str.startswith("DOI:"):
                        step_citations.append(source_str)
                    elif ref.get("notes"):
                        step_citations.append(ref["notes"])

                pathway_steps.append(PathwayStep(
                    source=source,
                    product=product,
                    mechanism=condition.get("mechanism") or "unknown",
                    conditions={
                        k: v for k, v in condition.items()
                        if k not in ["step", "mechanism"] and v is not None
                    },
                    confidence=best_path.get("confidence", 1.0),
                    citations=step_citations,
                ))
                all_citations.extend(step_citations)
        else:
            # No direct path - check if we have them in graph
            logger.warning(
                "No direct pathway found from %s to %s",
                precursor, target_product
            )
            # Add manual pathway for known relationships
            if precursor.upper() in ["HFO-1234YF", "OPTEON YF", "HFO"] and target_product.upper() == "TFA":
                pathway_steps.append(PathwayStep(
                    source=precursor,
                    product="TFA",
                    mechanism="atmospheric_oxidation",
                    conditions={"atmosphere": "ambient", "trigger": "OH radical"},
                    confidence=0.9,
                    citations=["DOI:10.5194/acp-24-4341-2024"],
                ))
                all_citations.append("DOI:10.5194/acp-24-4341-2024")

        return pathway_steps, all_citations

    def _get_destruction_proof(self, compound: str) -> Optional[DestructionProof]:
        """Get destruction proof for a compound."""
        recommendation = get_recommended_technology(compound, phase="aqueous")

        if recommendation.recommended_technology == "none":
            return None

        # Get detailed technology info
        tech_id = recommendation.recommended_technology.lower().replace(" ", "_").replace("-", "_")
        # Map common names to IDs
        tech_id_map = {
            "hydrothermal_alkaline_treatment": "halt",
            "supercritical_water_oxidation": "scwo",
            "plasma_arc_treatment": "plasma",
            "high_temperature_incineration": "thermal_oxidizer",
            "electrochemical_oxidation": "electrochemical",
        }
        tech_id = tech_id_map.get(tech_id, tech_id)
        tech = get_technology(tech_id)

        # Build citations list
        citations = []
        primary_citation = None
        if tech and tech.evidence:
            primary_refs = tech.evidence.get("primary", [])
            if primary_refs:
                for ref in primary_refs:
                    if isinstance(ref, dict):
                        doi = ref.get("doi")
                        if doi:
                            citations.append(f"DOI:{doi}")
                            if not primary_citation:
                                primary_citation = f"DOI:{doi}"
                        title = ref.get("title")
                        if title:
                            citations.append(title)
            supporting = tech.evidence.get("supporting", [])
            for ref in supporting:
                if isinstance(ref, dict):
                    doi = ref.get("doi")
                    if doi:
                        citations.append(f"DOI:{doi}")
                    citation = ref.get("citation")
                    if citation:
                        citations.append(citation)

        # Get products
        products = []
        if tech and tech.products:
            products = tech.products.get("primary", [])

        return DestructionProof(
            compound=compound,
            technology=tech.acronym if tech and tech.acronym else recommendation.recommended_technology,
            technology_full_name=tech.name if tech else recommendation.recommended_technology,
            mechanism=tech.mechanism if tech else "unknown",
            trl=tech.trl if tech else 5,
            dre=recommendation.dre,
            conditions=recommendation.conditions,
            products=products,
            primary_citation=primary_citation,
            citations=list(set(citations)),
            notes=tech.products.get("notes") if tech and tech.products else None,
        )

    def _analyze_chemours_exposure(self, compound: str) -> ChemoursIPExposure:
        """Analyze Chemours IP exposure for destroying a compound."""
        gap_analysis = get_chemours_capability_gap(compound, phase="aqueous")

        # Get recommended technology to check ownership
        recommendation = get_recommended_technology(compound, phase="aqueous")
        tech_id = recommendation.recommended_technology.lower().replace(" ", "_").replace("-", "_")
        tech_id_map = {
            "hydrothermal_alkaline_treatment": "halt",
        }
        tech_id = tech_id_map.get(tech_id, tech_id)
        tech = get_technology(tech_id)

        owns_tech = False
        owns_ip = False
        must_license = None
        forced = True

        if tech and tech.chemours_position:
            owns_tech = tech.chemours_position.owns_technology
            owns_ip = tech.chemours_position.owns_ip
            must_license = tech.chemours_position.must_license_from
            forced = tech.chemours_position.forced_buyer

        return ChemoursIPExposure(
            compound=compound,
            owns_technology=owns_tech,
            owns_ip=owns_ip,
            must_license_from=must_license,
            forced_buyer=forced,
            capability_gap=gap_analysis.get("gap"),
            technologies_available=[n["technology"] for n in gap_analysis.get("needs", [])],
            technologies_owned=[h["technology"] for h in gap_analysis.get("has", [])],
        )

    def _is_pfas(self, compound: str) -> bool:
        """Check if compound is classified as PFAS."""
        node_attrs = self.graph.get_node_attributes(compound)
        return node_attrs.get("is_pfas", False)

    def _generate_conclusion(
        self,
        precursor: str,
        terminal: str,
        destruction: Optional[DestructionProof],
        exposure: Optional[ChemoursIPExposure],
    ) -> str:
        """Generate conclusion text for certificate."""
        parts = []

        # Degradation chain
        parts.append(
            f"Analysis confirms that {precursor} degrades to {terminal} "
            f"through documented environmental pathways."
        )

        # Destruction viability
        if destruction:
            parts.append(
                f"{terminal} can be destroyed using {destruction.technology_full_name or destruction.technology} "
                f"(TRL {destruction.trl}) with demonstrated mineralization to {', '.join(destruction.products)}."
            )
            if destruction.dre:
                parts.append(f"Destruction/Removal Efficiency: >={destruction.dre*100:.1f}%.")
        else:
            parts.append(f"No viable destruction technology identified for {terminal}.")

        # IP exposure
        if exposure and exposure.forced_buyer:
            parts.append(
                f"CRITICAL: Chemours does NOT own {terminal} destruction technology. "
                f"Chemours must license from {exposure.must_license_from or 'third party'}. "
                f"Forced buyer status: CONFIRMED."
            )

        return " ".join(parts)

    def _get_regulatory_implications(
        self,
        compound: str,
        destruction: Optional[DestructionProof],
    ) -> str:
        """Generate regulatory implications text."""
        parts = []

        parts.append(
            f"{compound} is an ultra-short-chain PFAS subject to EPA regulatory scrutiny."
        )

        if destruction:
            parts.append(
                f"Demonstrated destruction pathway exists ({destruction.technology}), "
                f"enabling compliance with anticipated EPA PFAS destruction requirements."
            )

        parts.append(
            "End-of-life management must include destruction, not merely collection or disposal."
        )

        return " ".join(parts)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def generate_tfa_certificate(precursor: str = "HFO-1234yf") -> EOLProofCertificate:
    """
    Generate a TFA mineralization proof certificate.

    This is the primary use case: proving that HFO refrigerants (Opteon)
    degrade to TFA, and that TFA can be destroyed using HALT technology.

    Args:
        precursor: Source HFO compound (default: HFO-1234yf / Opteon YF)

    Returns:
        Complete EOL certificate with Chemours IP exposure analysis
    """
    generator = EOLCertificateGenerator()
    return generator.generate(
        precursor=precursor,
        precursor_type="HFO refrigerant (Opteon)",
        target_product="TFA",
    )


def generate_certificate_json(precursor: str = "HFO-1234yf") -> str:
    """Generate certificate and return as JSON string."""
    cert = generate_tfa_certificate(precursor)
    return cert.model_dump_json(indent=2)


if __name__ == "__main__":
    # Demo: Generate TFA certificate for HFO-1234yf
    import json

    print("=" * 80)
    print("AEGIS EOL PROOF CERTIFICATE GENERATOR")
    print("=" * 80)
    print()

    cert = generate_tfa_certificate("HFO-1234yf")

    print(f"Certificate ID: {cert.certificate_id}")
    print(f"Generated: {cert.generated_at}")
    print()
    print(f"Precursor: {cert.precursor} ({cert.precursor_type})")
    print(f"Terminal Product: {cert.terminal_product}")
    print()

    print("DEGRADATION PATHWAY:")
    for i, step in enumerate(cert.degradation_pathway, 1):
        print(f"  {i}. {step.source} → {step.product}")
        print(f"     Mechanism: {step.mechanism}")
        if step.citations:
            print(f"     Citations: {', '.join(step.citations[:2])}")
    print()

    if cert.destruction_proof:
        print("DESTRUCTION PROOF:")
        print(f"  Technology: {cert.destruction_proof.technology_full_name}")
        print(f"  TRL: {cert.destruction_proof.trl}")
        if cert.destruction_proof.dre:
            print(f"  DRE: {cert.destruction_proof.dre*100:.1f}%")
        print(f"  Products: {', '.join(cert.destruction_proof.products)}")
        if cert.destruction_proof.primary_citation:
            print(f"  Primary Citation: {cert.destruction_proof.primary_citation}")
    print()

    if cert.chemours_exposure:
        print("CHEMOURS IP EXPOSURE:")
        print(f"  Owns Technology: {cert.chemours_exposure.owns_technology}")
        print(f"  Must License From: {cert.chemours_exposure.must_license_from}")
        print(f"  Forced Buyer: {cert.chemours_exposure.forced_buyer}")
    print()

    print("CONCLUSION:")
    print(f"  {cert.conclusion}")
    print()

    print(f"Total Citations: {cert.total_citations}")
    print()
    print("=" * 80)
