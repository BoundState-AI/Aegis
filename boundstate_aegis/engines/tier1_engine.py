#!/usr/bin/env python3
"""
Module: tier1_engine
Purpose: AEGIS Tier 1 Structural Similarity + Pathway Engine.
    Combines the EPA PFAS database (10,974 compounds with SMILES),
    the literature pathway corpus (732 pathways from 353 papers),
    and evidence chains with DOI citations to provide structure-aware
    compound screening.

    NOT A PREDICTION ENGINE. Returns what the published literature shows
    for structurally similar compounds.

    Rev History:
        1.0.0 - Initial Tier 1 engine with structural similarity and
                pathway endpoint aggregation

BoundState AI 2025
Version: 1.0.0
Classification: BoundState Proprietary

Authored-By: Dr. Joseph Wilde, BoundState AI
Oracle 1: ClaudeOpus 4.5 <noreply@anthropic.com>
Oracle 2: Fran OpenAI 5.2 <noreply@openai.com>
Oracle 3: Grok 4.0 <noreply@x.ai>

"""

from __future__ import annotations

import csv
import json
import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from boundstate_aegis.config import EPA_COMPTOX_CSV, PFAS_FATE_V2_JSON
from boundstate_aegis.taxonomy import ENDPOINT_TAXONOMY, classify_endpoint

logger = logging.getLogger(__name__)

# RDKit is optional — degrade gracefully
try:
    from rdkit import Chem
    from rdkit.Chem import AllChem, DataStructs, Descriptors
    from rdkit import RDLogger
    RDLogger.DisableLog("rdApp.*")
    HAS_RDKIT = True
except ImportError:
    HAS_RDKIT = False
    logger.warning("RDKit not available. Tier 1 structural similarity disabled.")


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Evidence:
    """A single piece of evidence from the literature."""
    doi: str
    verbatim_quote: str
    evidence_location: str
    temperature_c: Optional[float] = None
    yield_percent: Optional[float] = None
    confidence: str = "medium"
    source_file: str = ""


@dataclass
class Pathway:
    """A degradation pathway from parent to product."""
    id: str
    precursor: str
    product: str
    mechanism: str
    temp_bucket: str
    observation_count: int
    evidence_score: float
    temp_c_range: Tuple[Optional[float], Optional[float]]
    yield_percent_median: Optional[float]
    evidence_refs: List[Evidence]
    source_dois: List[str]


@dataclass
class Compound:
    """A compound with optional structural data."""
    name: str
    smiles: Optional[str] = None
    cas: Optional[str] = None
    dtxsid: Optional[str] = None
    is_pfas: bool = False
    degrades_to: List[str] = field(default_factory=list)
    degrades_from: List[str] = field(default_factory=list)
    fingerprint: Optional[object] = None
    f_count: int = 0
    c_count: int = 0
    mw: float = 0.0


@dataclass
class SimilarityResult:
    """Result of a similarity search with pathway context."""
    compound: Compound
    similarity: float
    pathways: List[Pathway]
    endpoints: List[str]
    evidence_count: int


@dataclass
class NeighborhoodProfile:
    """Aggregated profile of structural neighbors."""
    n_neighbors: int
    avg_similarity: float
    endpoint_histogram: Dict[str, int]
    top_endpoints: List[Tuple[str, int, float]]  # (endpoint, count, fraction)
    mechanism_histogram: Dict[str, int]
    evidence_citations: List[Dict[str, str]]  # Top DOIs with context
    risk_signal: str  # "HIGH", "MEDIUM", "LOW", "UNKNOWN"


# =============================================================================
# MANUAL SMILES FOR KEY COMPOUNDS
# =============================================================================

MANUAL_SMILES: Dict[str, str] = {
    # Polymers (using monomer/representative structures)
    "PTFE": "C(F)(F)=C(F)F",
    "PVDF": "C(F)(F)=C",
    "FEP": "C(F)(F)=C(F)C(F)(F)F",
    # Short-chain acids and gases
    "TFA": "OC(=O)C(F)(F)F",
    "trifluoroacetic acid": "OC(=O)C(F)(F)F",
    "COF2": "FC(F)=O",
    "carbonyl fluoride": "FC(F)=O",
    "HF": "F",
    "CF4": "FC(F)(F)F",
    "fluoride": "[F-]",
    "F-": "[F-]",
    "CO2": "O=C=O",
    "H2O": "O",
    # Common acids
    "PFPeA": "OC(=O)C(F)(F)C(F)(F)C(F)(F)C(F)(F)F",
    "PFHpA": "OC(=O)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)F",
    "PFBS": "OS(=O)(=O)C(F)(F)C(F)(F)C(F)(F)C(F)(F)F",
    "PFHxS": "OS(=O)(=O)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)F",
    "HFPO-DA": "OC(=O)C(F)(OC(F)(F)C(F)(F)C(F)(F)F)C(F)(F)F",
    "4:2 FTOH": "OCCC(F)(F)C(F)(F)C(F)(F)C(F)(F)F",
    "10:2 FTOH": "OCCC(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)F",
    "acetic acid": "CC(=O)O",
    "formic acid": "OC=O",
}

CAS_MAP: Dict[str, str] = {
    "PFOA": "335-67-1",
    "PFOS": "1763-23-1",
    "GenX": "13252-13-6",
    "6:2 FTOH": "647-42-7",
    "8:2 FTOH": "678-39-7",
    "PFBA": "375-22-4",
    "PFHxA": "307-24-4",
    "PFNA": "375-95-1",
    "PFDA": "335-76-2",
    "PFUnDA": "2058-94-8",
    "PFDoDA": "307-55-1",
}


# =============================================================================
# MAIN ENGINE
# =============================================================================

class AEGISTier1Engine:
    """
    Combined structural similarity + pathway endpoint engine.

    Provides:
    1. Structural similarity search against 10,974 EPA compounds
    2. Pathway endpoint aggregation from 732 literature pathways
    3. Evidence citations with DOIs
    """

    def __init__(
        self,
        epa_csv_path: Optional[Path] = None,
        fate_json_path: Optional[Path] = None,
    ):
        if not HAS_RDKIT:
            raise RuntimeError(
                "RDKit is required for Tier 1 engine. "
                "Install with: pip install rdkit-pypi"
            )

        self.compounds: Dict[str, Compound] = {}
        self.epa_compounds: List[Compound] = []
        self.pathways: List[Pathway] = []
        self.pathway_by_precursor: Dict[str, List[Pathway]] = defaultdict(list)

        epa_path = epa_csv_path or EPA_COMPTOX_CSV
        fate_path = fate_json_path or PFAS_FATE_V2_JSON

        if epa_path.exists():
            self._load_epa_data(epa_path)
        else:
            logger.warning("EPA CompTox CSV not found at %s", epa_path)

        if fate_path.exists():
            self._load_fate_data(fate_path)
        else:
            logger.warning("Fate V2 JSON not found at %s", fate_path)

        self._compute_fingerprints()

    def _load_epa_data(self, csv_path: Path) -> None:
        """Load EPA PFAS database."""
        skipped = 0
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                smiles = row.get("SMILES", "").strip()
                if not smiles:
                    continue

                mol = Chem.MolFromSmiles(smiles)
                if mol is None:
                    continue

                try:
                    fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
                    f_count = sum(1 for atom in mol.GetAtoms() if atom.GetSymbol() == "F")
                    c_count = sum(1 for atom in mol.GetAtoms() if atom.GetSymbol() == "C")

                    compound = Compound(
                        name=row.get("PREFERRED NAME", ""),
                        smiles=smiles,
                        cas=row.get("CASRN", ""),
                        dtxsid=row.get("DTXSID", "").split("/")[-1],
                        is_pfas=True,
                        fingerprint=fp,
                        f_count=f_count,
                        c_count=c_count,
                        mw=Descriptors.MolWt(mol),
                    )
                    self.epa_compounds.append(compound)
                except Exception as e:
                    skipped += 1
                    logger.debug("Skipping EPA compound %s: %s", smiles, e)

        logger.info(
            "Loaded %d EPA compounds with SMILES (%d skipped)",
            len(self.epa_compounds), skipped,
        )

    def _load_fate_data(self, json_path: Path) -> None:
        """Load pathway/fate data."""
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Load compounds
        for name, comp_data in data.get("compounds", {}).items():
            smiles = MANUAL_SMILES.get(name)
            cas = CAS_MAP.get(name, comp_data.get("cas"))

            # Try to resolve SMILES from EPA database by CAS
            if not smiles and cas:
                for epa_comp in self.epa_compounds:
                    if epa_comp.cas == cas:
                        smiles = epa_comp.smiles
                        break

            self.compounds[name] = Compound(
                name=name,
                smiles=smiles,
                cas=cas,
                is_pfas=comp_data.get("is_pfas", False),
                degrades_to=comp_data.get("degrades_to", []),
                degrades_from=comp_data.get("degrades_from", []),
            )

        # Load pathways
        for p in data.get("pathways", []):
            evidence_refs = [
                Evidence(
                    doi=e.get("doi", ""),
                    verbatim_quote=e.get("verbatim_quote", ""),
                    evidence_location=e.get("evidence_location", ""),
                    temperature_c=e.get("temperature_c"),
                    yield_percent=e.get("yield_percent"),
                    confidence=e.get("confidence", "medium"),
                    source_file=e.get("source_file", ""),
                )
                for e in p.get("evidence_refs", [])
            ]

            temp_range = p.get("temp_c_range", [None, None])

            pathway = Pathway(
                id=p.get("id", ""),
                precursor=p.get("precursor", ""),
                product=p.get("product", ""),
                mechanism=p.get("mechanism") or "unknown",
                temp_bucket=p.get("temp_bucket", ""),
                observation_count=p.get("observation_count", 1),
                evidence_score=p.get("evidence_score", 0.5),
                temp_c_range=(temp_range[0], temp_range[1]) if temp_range else (None, None),
                yield_percent_median=p.get("yield_percent_median"),
                evidence_refs=evidence_refs,
                source_dois=p.get("source_dois", []),
            )

            self.pathways.append(pathway)
            self.pathway_by_precursor[pathway.precursor].append(pathway)

        logger.info(
            "Loaded %d pathways from %d compounds",
            len(self.pathways),
            len(self.compounds),
        )

    def _compute_fingerprints(self) -> None:
        """Compute fingerprints for fate compounds with SMILES."""
        computed = 0
        skipped = 0
        for comp in self.compounds.values():
            if comp.smiles:
                mol = Chem.MolFromSmiles(comp.smiles)
                if mol:
                    try:
                        comp.fingerprint = AllChem.GetMorganFingerprintAsBitVect(
                            mol, 2, nBits=2048
                        )
                        comp.f_count = sum(
                            1 for atom in mol.GetAtoms() if atom.GetSymbol() == "F"
                        )
                        comp.c_count = sum(
                            1 for atom in mol.GetAtoms() if atom.GetSymbol() == "C"
                        )
                        comp.mw = Descriptors.MolWt(mol)
                        computed += 1
                    except Exception as e:
                        skipped += 1
                        logger.debug(
                            "Fingerprint failed for %s (%s): %s",
                            comp.name, comp.smiles, e,
                        )

        logger.info(
            "Computed fingerprints for %d fate compounds (%d skipped)",
            computed, skipped,
        )

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------

    def find_similar_epa(
        self,
        query_smiles: str,
        top_k: int = 10,
        min_similarity: float = 0.5,
    ) -> List[Tuple[Compound, float]]:
        """Find structurally similar compounds in the EPA database."""
        query_mol = Chem.MolFromSmiles(query_smiles)
        if query_mol is None:
            raise ValueError(f"Invalid SMILES: {query_smiles}")

        query_fp = AllChem.GetMorganFingerprintAsBitVect(query_mol, 2, nBits=2048)

        results = []
        for comp in self.epa_compounds:
            sim = DataStructs.TanimotoSimilarity(query_fp, comp.fingerprint)
            if sim >= min_similarity:
                results.append((comp, sim))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def find_similar_with_pathways(
        self,
        query_smiles: str,
        top_k: int = 10,
        min_similarity: float = 0.5,
    ) -> List[SimilarityResult]:
        """Find similar compounds and their known degradation pathways."""
        query_mol = Chem.MolFromSmiles(query_smiles)
        if query_mol is None:
            raise ValueError(f"Invalid SMILES: {query_smiles}")

        query_fp = AllChem.GetMorganFingerprintAsBitVect(query_mol, 2, nBits=2048)

        results = []
        for name, comp in self.compounds.items():
            if not comp.fingerprint:
                continue

            sim = DataStructs.TanimotoSimilarity(query_fp, comp.fingerprint)
            if sim < min_similarity:
                continue

            pathways = self.pathway_by_precursor.get(name, [])
            endpoints = [p.product for p in pathways]
            evidence_count = sum(len(p.evidence_refs) for p in pathways)

            results.append(
                SimilarityResult(
                    compound=comp,
                    similarity=sim,
                    pathways=pathways,
                    endpoints=endpoints,
                    evidence_count=evidence_count,
                )
            )

        results.sort(key=lambda x: x.similarity, reverse=True)
        return results[:top_k]

    def get_neighborhood_profile(
        self,
        query_smiles: str,
        n_neighbors: int = 20,
        min_similarity: float = 0.4,
    ) -> NeighborhoodProfile:
        """
        Generate a comprehensive neighborhood profile for screening.

        This is the core Tier 1 output: aggregate what the literature
        shows for structurally similar compounds.
        """
        results = self.find_similar_with_pathways(
            query_smiles,
            top_k=n_neighbors,
            min_similarity=min_similarity,
        )

        if not results:
            return NeighborhoodProfile(
                n_neighbors=0,
                avg_similarity=0.0,
                endpoint_histogram={},
                top_endpoints=[],
                mechanism_histogram={},
                evidence_citations=[],
                risk_signal="UNKNOWN",
            )

        # Aggregate endpoints
        endpoint_counts: Counter[str] = Counter()
        endpoint_classes: Counter[str] = Counter()
        mechanism_counts: Counter[str] = Counter()
        all_dois: List[Dict[str, str]] = []

        for r in results:
            for pathway in r.pathways:
                endpoint_counts[pathway.product] += 1
                endpoint_classes[classify_endpoint(pathway.product)] += 1
                mechanism_counts[pathway.mechanism] += 1

                for evidence in pathway.evidence_refs:
                    if evidence.doi:
                        quote = evidence.verbatim_quote
                        all_dois.append(
                            {
                                "doi": evidence.doi,
                                "precursor": pathway.precursor,
                                "product": pathway.product,
                                "quote": (quote[:200] + "...") if len(quote) > 200 else quote,
                                "location": evidence.evidence_location,
                            }
                        )

        total_endpoints = sum(endpoint_counts.values()) or 1
        top_endpoints = [
            (ep, count, count / total_endpoints)
            for ep, count in endpoint_counts.most_common(10)
        ]

        # Risk signal based on endpoint classes
        high_risk_classes = {"long_chain_acids", "sulfonates"}
        medium_risk_classes = {"short_chain_acids", "fluorotelomers"}

        if any(endpoint_classes.get(c, 0) > 0 for c in high_risk_classes):
            risk_signal = "HIGH"
        elif any(endpoint_classes.get(c, 0) > 0 for c in medium_risk_classes):
            risk_signal = "MEDIUM"
        elif endpoint_classes.get("benign", 0) > 0:
            risk_signal = "LOW"
        else:
            risk_signal = "UNKNOWN"

        # Deduplicate DOIs
        seen_dois: set[str] = set()
        unique_citations: List[Dict[str, str]] = []
        for cite in all_dois:
            if cite["doi"] not in seen_dois:
                seen_dois.add(cite["doi"])
                unique_citations.append(cite)

        return NeighborhoodProfile(
            n_neighbors=len(results),
            avg_similarity=float(np.mean([r.similarity for r in results])),
            endpoint_histogram=dict(endpoint_counts),
            top_endpoints=top_endpoints,
            mechanism_histogram={k or "unknown": v for k, v in mechanism_counts.items()},
            evidence_citations=unique_citations[:10],
            risk_signal=risk_signal,
        )

    def resolve_smiles(self, name_or_cas: str) -> Optional[str]:
        """
        Resolve a compound name or CAS number to a SMILES string.

        Checks: MANUAL_SMILES → CAS_MAP → fate compounds → EPA database.
        """
        # Check manual SMILES
        if name_or_cas in MANUAL_SMILES:
            return MANUAL_SMILES[name_or_cas]

        # Check fate compounds
        comp = self.compounds.get(name_or_cas)
        if comp and comp.smiles:
            return comp.smiles

        # Check CAS map → EPA lookup
        cas = CAS_MAP.get(name_or_cas, name_or_cas)
        for epa_comp in self.epa_compounds:
            if epa_comp.cas == cas or epa_comp.name.upper() == name_or_cas.upper():
                return epa_comp.smiles

        return None

    def get_tier2_context(self, smiles: str) -> Optional[Dict[str, Any]]:
        """Call Tier 2 engine and return pattern correlations."""
        try:
            from boundstate_aegis.engines.tier2_substructure_engine import Tier2Engine
            tier2 = Tier2Engine(tier1_engine=self)
            return tier2.predict_endpoints(smiles).model_dump()
        except Exception as e:
            logger.warning("Tier 2 unavailable: %s", e)
            return None

    def query(self, query_smiles: str, compound_name: str = "Query") -> Dict[str, Any]:
        """
        Full query interface returning structured results for the API.
        """
        profile = self.get_neighborhood_profile(query_smiles)
        similar_epa = self.find_similar_epa(query_smiles, top_k=5)
        similar_fate = self.find_similar_with_pathways(query_smiles, top_k=5)

        result = {
            "query": {"name": compound_name, "smiles": query_smiles},
            "risk_signal": profile.risk_signal,
            "n_neighbors_with_pathways": profile.n_neighbors,
            "avg_similarity": round(profile.avg_similarity, 3),
            "top_endpoints": [
                {"endpoint": ep, "count": cnt, "fraction": round(frac, 3)}
                for ep, cnt, frac in profile.top_endpoints
            ],
            "mechanisms": profile.mechanism_histogram,
            "similar_in_epa": [
                {
                    "name": comp.name,
                    "cas": comp.cas,
                    "similarity": round(sim, 3),
                    "f_count": comp.f_count,
                    "c_count": comp.c_count,
                    "mw": round(comp.mw, 1),
                }
                for comp, sim in similar_epa
            ],
            "similar_with_pathways": [
                {
                    "name": r.compound.name,
                    "similarity": round(r.similarity, 3),
                    "pathways_count": len(r.pathways),
                    "endpoints": r.endpoints[:5],
                    "evidence_count": r.evidence_count,
                }
                for r in similar_fate
            ],
            "evidence_citations": profile.evidence_citations[:5],
            "disclaimer": (
                "This is a screening tool based on structural similarity to compounds "
                "with documented degradation pathways in peer-reviewed literature. "
                "Results reflect literature patterns, not predictions. "
                "Independent verification required for regulatory decisions."
            ),
        }

        # Attach Tier 2 substructure correlations if available
        result["tier2"] = self.get_tier2_context(query_smiles)

        return result
