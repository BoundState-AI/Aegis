# Copyright 2025 BoundStateAI
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Content Miner for BoundState Cartographer
========================================

Extracts structured content from document text:
- Entities (materials, systems, PPE, hazards)
- References (NASA-STD, MIL-STD, Amentum codes) with enhanced patterns and normalization
- Semantic tags
- Issues and conflicts

This is the "what's in it" module of document understanding.

Compliance: SWE-013, SWE-033
"""

import re
import json
import math
import os
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path

import logging
import spacy
from spacy.language import Language
from spacy.matcher import PhraseMatcher
from spacy.tokens import Span
from loguru import logger

# TQP detection
try:
    from ..tagger import tqp_decision, tqp_evidence
except ImportError:
    try:
        from boundstate_core.ingestion.tagger import tqp_decision, tqp_evidence
    except ImportError:
        import sys
        sys.path.append(str(Path(__file__).parent.parent.parent))
        from archive_unused_modules.tqp_rules import tqp_decision, tqp_evidence

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Configure logger
logger.add(
    "logs/content_miner.log",
    rotation="10 MB", retention="30 days", format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)

# Regular expression for simple acronym detection
# Matches sequences of 3 or more uppercase letters or alphanumerics
ACRONYM_RE = re.compile(r'\b[A-Z][A-Z0-9]{2,}\b')


def load_entity_config(config_path: str = "entity_phrases_amentum.json") -> Dict[str, List[str]]:
    """Load entity phrases from JSON config if available.

    Args:
        config_path: Path to config file.

    Returns:
        Dict of entity types to phrase lists.
    """
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.info(f"No config file at {config_path}, using defaults")
        return {
            "MATERIAL": ["Kapton", "Silicone Rubber", "PTFE", "Viton", "EPDM", "Nitronic 60", "Aluminum Alloy",
                         "Titanium Alloy", "Inconel", "PFAS", "Carbon Composite", "Stainless Steel", "Kevlar",
                         "Nomex", "Teflon", "Polyimide", "Fluoroelastomer", "Graphite Epoxy", "Polyethylene",
                         "Ceramic Coating"],
            "SYSTEM": ["Propulsion System", "Life Support System", "Hydraulic System", "Cryogenic Storage System",
                       "Avionics System", "Thermal Control System", "Electrical Power System",
                       "Guidance Navigation and Control", "Environmental Control System", "Telemetry System",
                       "Fuel Delivery System", "Launch Abort System", "Fire Suppression System",
                       "Landing Gear System", "Communication System", "Cooling Loop", "Pressure Vessel",
                       "Fuel Cell System", "Oxygen Generation System"],
            "PPE": [
                "Self-Contained Breathing Apparatus", "SCBA", "Respirator", "Protective Suit", "Safety Glasses",
                "Face Shield", "Hearing Protection", "Hard Hat", "Fire-Resistant Clothing",
                "Chemical Protective Gloves", "Arc Flash Suit", "Safety Harness", "Hi-Vis Vest"
            ],
            "HAZARD": [
                "Oxygen incompatibility", "High-pressure risk", "Radiation exposure", "Cryogenic Hazard",
                "Flammability", "Explosion risk", "Electrical hazard", "Corrosion risk", "Contamination",
                "High-temperature risk", "Toxic exposure", "Laser hazard", "Noise hazard", "Arc flash risk",
                "Asphyxiation risk"
            ]
        }
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {config_path}: {e}")
        return {
            "MATERIAL": ["Kapton", "Silicone Rubber", "PTFE", "Viton", "EPDM", "Nitronic 60", "Aluminum Alloy",
                         "Titanium Alloy", "Inconel", "PFAS", "Carbon Composite", "Stainless Steel", "Kevlar",
                         "Nomex", "Teflon", "Polyimide", "Fluoroelastomer", "Graphite Epoxy", "Polyethylene",
                         "Ceramic Coating"],
            "SYSTEM": ["Propulsion System", "Life Support System", "Hydraulic System", "Cryogenic Storage System",
                       "Avionics System", "Thermal Control System", "Electrical Power System",
                       "Guidance Navigation and Control", "Environmental Control System", "Telemetry System",
                       "Fuel Delivery System", "Launch Abort System", "Fire Suppression System",
                       "Landing Gear System", "Communication System", "Cooling Loop", "Pressure Vessel",
                       "Fuel Cell System", "Oxygen Generation System"],
            "PPE": [
                "Self-Contained Breathing Apparatus", "SCBA", "Respirator", "Protective Suit", "Safety Glasses",
                "Face Shield", "Hearing Protection", "Hard Hat", "Fire-Resistant Clothing",
                "Chemical Protective Gloves", "Arc Flash Suit", "Safety Harness", "Hi-Vis Vest"
            ],
            "HAZARD": [
                "Oxygen incompatibility", "High-pressure risk", "Radiation exposure", "Cryogenic Hazard",
                "Flammability", "Explosion risk", "Electrical hazard", "Corrosion risk", "Contamination",
                "High-temperature risk", "Toxic exposure", "Laser hazard", "Noise hazard", "Arc flash risk",
                "Asphyxiation risk"
            ]
        }


# Load entity phrases (from JSON if available, otherwise defaults)
ENTITY_PHRASES = load_entity_config()

# Map entity labels to output keys
ENTITY_LABELS = {
    "MATERIAL": "materials",
    "SYSTEM": "systems",
    "PPE": "ppe",
    "HAZARD": "hazards"
    # Additional labels (e.g., detected acronyms) will be added dynamically in extraction
}


@dataclass
class ContentResult:
    """Results from content mining operation."""
    entities: Dict[str, Dict[str, List[Tuple[str, float]]]] = field(default_factory=lambda: {
        "verified": defaultdict(list),
        "inferred": defaultdict(list)
    })
    references: List[Dict[str, Any]] = field(default_factory=list)  # Structured refs as list of dicts
    tags: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    confidence: Dict[str, Any] = field(default_factory=dict)
    evidence: Dict[str, List[Tuple[str, str]]] = field(default_factory=lambda: defaultdict(list))


class ContentMiner:
    """Extracts structured content from document text.

    Compliance: SWE-013, SWE-033
    """

    def __init__(self, model_name: str = "en_core_web_lg"):
        """Initialize with spaCy model and custom components.

        Args:
            model_name: spaCy model name.
        """
        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            logger.error(f"Model {model_name} not found. Installing...")
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", model_name])
            self.nlp = spacy.load(model_name)

        # Add custom entity recognition
        self._add_domain_entities()

        logger.info(f"ContentMiner initialized with model: {model_name}")

    @Language.factory("domain_ner")
    def create_domain_ner(nlp, name):
        matcher = PhraseMatcher(nlp.vocab, attr="LOWER")

        for label, phrases in ENTITY_PHRASES.items():
            patterns = [nlp.make_doc(phrase.lower()) for phrase in phrases]
            matcher.add(label, patterns)

        def domain_ner_component(doc):
            matches = matcher(doc)
            spans = []
            for match_id, start, end in matches:
                label = nlp.vocab.strings[match_id]
                span = Span(doc, start, end, label=label)
                spans.append(span)

            existing_spans = list(doc.ents)
            all_spans = existing_spans + spans
            doc.ents = spacy.util.filter_spans(all_spans)

            return doc

        return domain_ner_component

    def _add_domain_entities(self):
        """Add domain-specific entity recognition."""
        if "domain_ner" not in self.nlp.pipe_names:
            self.nlp.add_pipe("domain_ner", after="ner")

    def mine_content(self, text: str, doc_metadata: Optional[Dict] = None) -> ContentResult:
        """Extract all content from document text.

        Args:
            text: Document text to analyze.
            doc_metadata: Optional metadata about the document.

        Returns:
            ContentResult with extracted content.
        """
        result = ContentResult()

        doc = self.nlp(text)

        result.entities, entity_evidence = self.extract_entities(doc)
        result.evidence.update(entity_evidence)

        refs, ref_evidence = self.extract_references(text)
        result.references = refs
        result.evidence["references"] = ref_evidence

        result.tags = self.generate_tags(text, result)

        # TQP detection using evidence-based rules
        tqp_result = tqp_decision(text)
        is_tqp = tqp_result.get('decision', False) if isinstance(tqp_result, dict) else bool(tqp_result)
        if is_tqp:
            result.tags = list(set(result.tags + ["tqp"]))
            if not hasattr(result, 'evidence'):
                result.evidence = {}
            result.evidence["tqp"] = tqp_evidence(text)
            logger.info(f"TQP detected in document with {len(result.evidence['tqp'])} evidence snippets")

        result.issues = self.detect_issues(text, result)

        result.confidence = self.calculate_confidence(result)

        logger.info(f"Content mining complete: {len(result.entities['verified'])} verified entities, "
                   f"{len(result.references)} references, {len(result.tags)} tags")

        return result

    def extract_entities(self, doc) -> Tuple[Dict, Dict]:
        """Extract named entities with confidence scores.

        Returns:
            Tuple of entities dict and evidence dict.
        """
        entities = {
            "verified": defaultdict(list),
            "inferred": defaultdict(list)
        }
        evidence = defaultdict(list)

        # Collect spans of already recognized entities to avoid duplicate acronym extraction
        recognized_spans = []
        for ent in doc.ents:
            if ent.label_ in ENTITY_LABELS:
                confidence = self._calculate_entity_confidence(ent.text, doc.text, ent.label_)

                output_key = ENTITY_LABELS[ent.label_]

                bucket = "verified" if confidence >= 0.75 else "inferred"

                entity_tuple = (ent.text, confidence)
                if entity_tuple not in entities[bucket][output_key]:
                    entities[bucket][output_key].append(entity_tuple)

                start = max(0, ent.start_char - 50)
                end = min(len(doc.text), ent.end_char + 50)
                context = doc.text[start:end].strip()
                evidence[output_key].append((ent.text, context))

                # Track the character span for later duplicate filtering
                recognized_spans.append((ent.start_char, ent.end_char))

        # Detect acronyms that may not be covered by the domain-specific entities
        # We dynamically assign them under the 'acronyms' output key. These tokens are often
        # meaningful identifiers (e.g., test names, program abbreviations) that should
        # remain searchable. This improves recall for queries like "How many documents mention X".
        acronyms_found = []
        for match in ACRONYM_RE.finditer(doc.text):
            acronym_text = match.group(0)
            # Skip if this acronym overlaps with an existing recognized entity span
            m_start, m_end = match.start(), match.end()
            overlap = any(not (m_end <= s or m_start >= e) for s, e in recognized_spans)
            if overlap:
                continue
            # Skip common stopwords or very common short words
            if acronym_text in {"THE", "AND", "FOR", "WITH", "ARE"}:
                continue
            # Add the acronym to the entities structure
            # Use a moderate confidence; acronyms are explicit in text
            confidence = 0.8
            output_key = "acronyms"
            if (acronym_text, confidence) not in entities["verified"][output_key]:
                entities["verified"][output_key].append((acronym_text, confidence))
                # Provide context around the acronym occurrence for evidence
                start = max(0, m_start - 50)
                end = min(len(doc.text), m_end + 50)
                context = doc.text[start:end].strip()
                evidence[output_key].append((acronym_text, context))

        for key in evidence:
            evidence[key] = list(dict.fromkeys(evidence[key]))[:10]

        return entities, dict(evidence)

    def _calculate_entity_confidence(self, entity_text: str, context: str, label: str) -> float:
        """Calculate confidence based on context clues."""
        confidence = 0.8

        boost_patterns = {
            "MATERIAL": [r"made of", r"composed of", r"material:", r"substrate", r"coating"],
            "SYSTEM": [r"system", r"equipment", r"component", r"assembly", r"subsystem"],
            "PPE": [r"wear", r"required", r"protection", r"PPE", r"don"],
            "HAZARD": [r"hazard", r"danger", r"risk", r"warning", r"caution"]
        }

        for pattern in boost_patterns.get(label, []):
            if re.search(pattern, context, re.IGNORECASE):
                confidence = min(0.95, confidence + 0.1)
                break

        return confidence

    def extract_references(self, text: str) -> Tuple[List[Dict[str, Any]], List[Tuple[str, str]]]:
        """Extract and normalize references with context.

        Returns:
            List of reference dicts and evidence list.
        """
        refs = []
        evidence = []
        seen = set()

        # Contextual prefixes for better capture
        context_prefix = r'(?:per|IAW|see|refer to|reference|as defined in|specified in|complies with|meets requirements of|in accordance with|as per|per procedure|see form|implements|from|per|ref)?\s*'

        patterns = {
            "amentum_internal": context_prefix + r'([FGPWTM]\d{4}\.\d[A-Z]?)(?:\s*r(\d{2}))?',
            "amentum_policy": context_prefix + r'(POL\d{4})(?:\s*r(\d{2}))?',
            "as_standard": context_prefix + r'(AS9100|AS9110|AS9120|AS9100 Rev [A-D])(?::\d{4})?',
            "iso_standard": context_prefix + r'(ISO\s+9001|ISO\s+14001|ISO\s+45001)(?::\d{4})?',
            "aqap_standard": context_prefix + r'(AQAP\s+2110|AQAP\s+2120)(?::\d{4})?',
            "mil_std": context_prefix + r'(MIL-STD-882E|MIL-STD-1472H|MIL-STD-810G)(?::\d{4})?',
            "nasa_std": context_prefix + r'(NASA-STD-8739\.8B|NASA-STD-5005)(?::\d{4})?',
            "mil_hdbk": context_prefix + r'(MIL-HDBK-217F|MIL-HDBK-470A)(?::\d{4})?',
            "astm": context_prefix + r'(ASTM\s+F2413-18|ASTM\s+E1444)(?::\d{4})?',
            "sae": context_prefix + r'(SAE\s+AMS2750|SAE\s+AS5553)(?::\d{4})?',
            "ams": context_prefix + r'(AMS\s+2759|AMS-STD-2154)(?::\d{4})?'
        }

        for ref_type, pattern in patterns.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                full_ref = match.group(0).strip()
                base_ref = match.group(1).upper() if match.groups() else full_ref.upper()

                # Normalize: upper, strip context prefixes, handle revs
                normalized = re.sub(r'^(per|iaw|see|refer to|reference|as defined in|specified in|complies with|meets requirements of|in accordance with|as per|per procedure|see form|implements|from|per|ref)\s+', '', base_ref, flags=re.I).upper()
                normalized = re.sub(r'\s*(REV|R|V)?\s*([A-Z]\d?)$', r' REV \2', normalized)  # Standardize rev

                # Skip if looks like section/year/partial
                if re.fullmatch(r'^\d+(?:\.\d+)*$', normalized) or re.fullmatch(r'^\d{4}$', normalized) or len(normalized) < 4:
                    continue

                # Version extraction
                version_match = re.search(r'(REV|R|V)\s*([A-Z]\d?)$|:\d{4}$', normalized, re.I)
                version = version_match.group(2) if version_match else None

                # Base ID: strip version/year
                base_id = re.sub(r'(?:\s*REV\s*[A-Z]\d?|:\d{4})$', '', normalized).strip()

                ref_dict = {
                    "id": normalized,
                    "base_id": base_id,
                    "full": full_ref,
                    "type": ref_type,
                    "version": version
                }

                ref_key = f"{normalized}_{ref_type}"
                if ref_key not in seen:
                    seen.add(ref_key)
                    refs.append(ref_dict)

                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].strip()
                evidence.append((full_ref, context))

        return refs, evidence[:20]  # Cap for efficiency

    def generate_tags(self, text: str, result: ContentResult) -> List[str]:
        """Generate semantic tags based on content."""
        tags = []

        safety_terms = ["safety", "hazard", "PPE", "protection", "emergency", "incident"]
        if any(term in text.lower() for term in safety_terms):
            tags.append("safety")

        if result.references:
            tags.append("compliance")
            if any(ref["type"] in ["mil_std", "mil_hdbk"] for ref in result.references):
                tags.append("military-spec")
            if any(ref["type"] == "nasa_std" for ref in result.references):
                tags.append("nasa-spec")
            if any(ref["type"] in ["as_standard", "iso_standard", "aqap_standard"] for ref in result.references):
                tags.append("quality-standard")

        if result.entities["verified"].get("materials"):
            materials = [m[0].lower() for m in result.entities["verified"]["materials"]]
            if any("pfas" in m or "pfoa" in m or "pfos" in m for m in materials):
                tags.append("pfas-related")
            if any("composite" in m or "carbon" in m for m in materials):
                tags.append("composite-materials")

        status_patterns = {
            "draft": r'\b(draft|preliminary|proposed)\b',
            "deprecated": r'\b(deprecated|obsolete|superseded|cancelled)\b',
            "revised": r'\b(revised|updated|amendment|change\s+\d+)\b'
        }

        for tag, pattern in status_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                tags.append(tag)

        return list(set(tags))

    def detect_issues(self, text: str, result: ContentResult) -> List[str]:
        """Detect potential issues or conflicts."""
        issues = []

        mil_refs = [r for r in result.references if r["type"] in ["mil_std", "mil_hdbk"]]
        if len(mil_refs) > 3:
            issues.append("Multiple MIL references may indicate complexity")

        deprecated_pattern = r'\b(superseded by|replaced by|cancelled|withdrawn)\b'
        if re.search(deprecated_pattern, text, re.IGNORECASE):
            issues.append("Document may reference superseded standards")

        if result.entities["verified"].get("hazards") and not result.entities["verified"].get("ppe"):
            issues.append("Hazards identified but no PPE specified")

        todo_pattern = r'\b(TODO|TBD|TBR|to be determined)\b'
        if re.search(todo_pattern, text, re.IGNORECASE):
            issues.append("Contains incomplete sections (TODO/TBD)")

        # New: Check for unmatched references (e.g., cited doc not in corpus - but needs external check)
        # For now, flag if reference to old rev
        for ref in result.references:
            # Check for old revisions (only for numeric versions)
            if ref["version"] and ref["version"].isdigit() and int(ref["version"]) < 1:
                issues.append(f"Potential old revision: {ref['id']}")

        return issues

    def calculate_confidence(self, result: ContentResult) -> Dict[str, Any]:
        """Calculate overall confidence scores with intervals."""
        confidence = {}

        total_entities = 0

        for entity_type in ["materials", "systems", "ppe", "hazards"]:
            verified = result.entities["verified"].get(entity_type, [])
            inferred = result.entities["inferred"].get(entity_type, [])

            if verified or inferred:
                total_items = len(verified) + len(inferred)
                total_entities += total_items
                verified_weight = len(verified) * 0.9
                inferred_weight = len(inferred) * 0.6
                point_estimate = (verified_weight + inferred_weight) / total_items if total_items > 0 else 0.0

                ci_lower, ci_upper = calculate_confidence_interval(point_estimate, total_items)

                confidence[entity_type] = {
                    "point": point_estimate,
                    "ci_lower": ci_lower,
                    "ci_upper": ci_upper,
                    "n": total_items
                }
            else:
                confidence[entity_type] = {
                    "point": 0.0,
                    "ci_lower": 0.0,
                    "ci_upper": 0.0,
                    "n": 0
                }

        ref_count = len(result.references)
        ref_confidence = min(0.95, ref_count * 0.2) if ref_count > 0 else 0.0
        ci_lower, ci_upper = calculate_confidence_interval(ref_confidence, ref_count)

        confidence["references"] = {
            "point": ref_confidence,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
            "n": ref_count
        }

        point_estimates = [c["point"] for c in confidence.values() if c["n"] > 0]
        overall_point = sum(point_estimates) / len(point_estimates) if point_estimates else 0.0

        total_n = total_entities + ref_count
        ci_lower, ci_upper = calculate_confidence_interval(overall_point, max(1, total_n))

        confidence["overall"] = {
            "point": overall_point,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
            "n": total_n,
            "interval_width": ci_upper - ci_lower
        }

        return confidence


def calculate_confidence_interval(confidence: float, sample_size: int = 100, z_score: float = 1.96) -> Tuple[float, float]:
    """Calculate confidence interval."""
    if sample_size > 0:
        se = math.sqrt((confidence * (1 - confidence)) / sample_size)
        margin = z_score * se
        lower = max(0, confidence - margin)
        upper = min(1, confidence + margin)
    else:
        lower = upper = confidence
    return (lower, upper)


if __name__ == "__main__":
    test_text = """
    Per F1301.1F r01, implement MIL-STD-882E for safety. See G8100.1A for reporting. Complies with AS9100 Rev D and NASA-STD-8739.8B.
    """
    miner = ContentMiner()
    result = miner.mine_content(test_text)
    print("References:", json.dumps(result.references, indent=2))