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

# boundstate/cartographer/intent_classifier.py
from __future__ import annotations

import re
import logging
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, field_validator, model_validator, TypeAdapter

# Configure logging
logger = logging.getLogger(__name__)

# Define intents and rule-based patterns (keywords/phrases, case-insensitive)
INTENT_PATTERNS = {  # Weights rationale: Higher for domain-strong (e.g., 'shall'/NASA-STD in specs), lower for common; negatives subtract, logged if applied
    
    # Amentum Document Classification System - document codes get highest weight
    "form": [
        (re.compile(r"^F\d{4}\.\d+[A-Z]?"), 5.0),  # F1301.1F - Forms
        (re.compile(r"\bform\b", re.IGNORECASE), 2.0),
        # Negatives
        (re.compile(r"\bguideline\b", re.IGNORECASE), -2.0),
    ],
    "guideline": [
        (re.compile(r"^G\d{4}\.\d+[A-Z]?"), 5.0),  # G8100.1A - Guidelines  
        (re.compile(r"\bguideline\b", re.IGNORECASE), 3.0),
    ],
    "work_instruction": [
        (re.compile(r"^W\d{4}\.\d+[A-Z]?"), 5.0),  # W-series - Work Instructions
        (re.compile(r"\bwork instruction\b", re.IGNORECASE), 3.0),
        (re.compile(r"\binstruction\b", re.IGNORECASE), 2.0),
    ],
    "template": [
        (re.compile(r"^T\d{4}\.\d+[A-Z]?"), 5.0),  # T7600.1A - Templates
        (re.compile(r"\btemplate\b", re.IGNORECASE), 3.0),
    ],
    "policy": [
        (re.compile(r"^P\d{4}\.\d+[A-Z]?"), 5.0),  # P-series - Policies
        (re.compile(r"^POL\d+"), 5.0),             # POL4010 - Also policies
        (re.compile(r"\b(policy|guideline|rule|compliance|osha|safety|procedure)\b", re.IGNORECASE), 2.5),
        (re.compile(r"\b(must|shall|prohibited|required|authorized)\b", re.IGNORECASE), 2.0),
    ],
    
    # Original patterns continue below...
    "specification": [
        (re.compile(r"\b(shall|must|requirement|tolerance|conform|spec|specification)\b", re.IGNORECASE), 3.0),
        (re.compile(r"\b(?:±|dimension|material|criteria|standard)\b", re.IGNORECASE), 1.0),
        # Domain-specific strong signals
        (re.compile(r"\bNASA-STD-\d+\b", re.IGNORECASE), 4.0),  # Strong domain spec signal
        (re.compile(r"\bMIL-STD-\d+\b", re.IGNORECASE), 4.0),  # Strong domain spec signal
        # Negatives (subtract if matched)
        (re.compile(r"\binvoice\s+number\b", re.IGNORECASE), -3.0),
        (re.compile(r"\bpayment\s+terms\b", re.IGNORECASE), -2.0),
    ],
    "contract": [
        (re.compile(r"\b(contract|agreement|clause|party|vendor|nda|sow|terms)\b", re.IGNORECASE), 2.5),
        (re.compile(r"\b(signature|effective date|termination|payment)\b", re.IGNORECASE), 2.0),
        # TODO: Add domain-specific patterns
        # Add similar for other intents; e.g., for "invoice":
        # (re.compile(r"\binvoice\s+number\b", re.IGNORECASE), 3.0), positives
        # (re.compile(r"\bshall\b", re.IGNORECASE), -2.0), negative to avoid spec confusion
    ],
    # ... (expand for all intents with positives/negatives; keep configurable)
    "test_report": [
        (re.compile(r"\b(test|report|result|data|analysis)\b", re.IGNORECASE), 2.0),
        (re.compile(r"\b(pass|fail|specimen|method)\b", re.IGNORECASE), 2.5),
        (re.compile(r"\b(ASTM|NASA-STD.*test)\b", re.IGNORECASE), 3.0),
        (re.compile(r"\binvoice\b", re.IGNORECASE), -3.0),
    ],
    "invoice": [
        (re.compile(r"\binvoice\s+number\b", re.IGNORECASE), 4.0),
        (re.compile(r"\b(amount\s+due|payment|total)\b", re.IGNORECASE), 3.0),
        (re.compile(r"\b(item|quantity|price|billing)\b", re.IGNORECASE), 2.0),
        (re.compile(r"\bshall\b", re.IGNORECASE), -2.0),  # Not a spec
    ],
    "memo": [
        (re.compile(r"\b(memo|memorandum|note|update|decision|meeting)\b", re.IGNORECASE), 2.5),
        (re.compile(r"\b(from:|to:|subject:|date:)\b", re.IGNORECASE), 3.0),
    ],
    "procedure": [
        (re.compile(r"\b(procedure|step|instruction|process|method|how to)\b", re.IGNORECASE), 2.5),
        (re.compile(r"\b(1\.|2\.|section \d|perform|execute)\b", re.IGNORECASE), 2.0),
    ],
    "presentation": [
        (re.compile(r"\b(slide|presentation|deck|agenda|summary|chart|graph)\b", re.IGNORECASE), 2.5),
        (re.compile(r"\b(bullet|key point|overview|conclusion)\b", re.IGNORECASE), 2.0),
    ],
    "training": [
        (re.compile(r"\b(training|course|module|lesson|certification|exercise)\b", re.IGNORECASE), 2.5),
        (re.compile(r"\b(learn|objective|quiz|participant)\b", re.IGNORECASE), 2.0),
    ],
    "change_notice": [
        (re.compile(r"\b(change|notice|revision|update|modification|amendment)\b", re.IGNORECASE), 2.5),
        (re.compile(r"\b(rev|version|effective|previous|new)\b", re.IGNORECASE), 2.0),
    ],

    # Query intent: count documents mentioning a term
    # These patterns aim to detect user questions that request a count of documents
    "count_documents": [
        (re.compile(r"\b(how\s+many|number\s+of)\s+documents?\b", re.IGNORECASE), 5.0),
        (re.compile(r"\bcount\b", re.IGNORECASE), 1.5),
        (re.compile(r"\bdocuments?\s+mention(?:ing)?\b", re.IGNORECASE), 1.0),
    ],
}

class IntentClassificationResult(BaseModel):
    """Result of document intent classification.

    Args:
        scores: Dict of intent names to confidence scores (0.0-1.0).
        evidence: List of text snippets supporting the intents.
        secondaries: Intents with scores >0.4 besides primary.

    Compliance: SWE-013 (traceability via evidence), SWE-033 (logging of results).
    """
    scores: Dict[str, float]
    evidence: List[str]
    secondaries: Optional[List[str]] = None

    model_config = {"extra": "forbid", "populate_by_name": True}

    @field_validator("scores")
    @classmethod
    def validate_intent_scores(cls, v: Dict[str, float]) -> Dict[str, float]:
        """Validate intent scores are between 0.0 and 1.0."""
        for score in v.values():
            if not 0.0 <= score <= 1.0:
                raise ValueError("Intent scores must be between 0.0 and 1.0")
        return v

    @model_validator(mode="after")
    def check_unknown_fallback(self) -> IntentClassificationResult:
        """Fallback to 'unknown' if all scores below threshold."""
        threshold = 0.5
        if not self.scores or all(score < threshold for score in self.scores.values()):
            self.scores = {"unknown": 1.0}
            self.secondaries = []
        else:
            # Extract secondaries (>0.4, exclude primary)
            if self.scores:
                primary = max(self.scores, key=self.scores.get)
                self.secondaries = [i for i, s in self.scores.items() if s > 0.4 and i != primary]
        return self

    def best(self) -> tuple[str, float]:
        """Return the highest-scoring intent and its score."""
        if not self.scores:
            return "unknown", 0.0
        intent, score = max(self.scores.items(), key=lambda item: item[1])
        return intent, score

    # Backwards compatibility alias
    @property
    def intent(self) -> Dict[str, float]:
        """Deprecated: Use .scores instead."""
        return self.scores

def classify_intent(
    text: str,
    structure_hints: Optional[Dict[str, str]] = None,
    mod_date: Optional[datetime] = None,
    cited: bool = True,
    decay_factor: float = 0.1,
) -> IntentClassificationResult:
    """Classify the intent of a document based on text and hints.
    
    Args:
        text: Cleaned document text.
        structure_hints: Optional dict with 'title', 'filename', etc.
        mod_date: Optional modification date for decay.
        cited: Whether the doc is cited elsewhere (avoids decay if True).
        decay_factor: Rate of confidence decay per year if aged/uncited.
    
    Returns:
        IntentClassificationResult with scores and evidence.
    
    Raises:
        ValueError: If text is empty.
    """
    
    if not text.strip():
        raise ValueError("Text cannot be empty")

    try:
        scores: Dict[str, float] = {}
        evidence: List[str] = []
        
        # Rule-based scoring
        for intent, weighted_patterns in INTENT_PATTERNS.items():
            intent_evidence = []
            total_weight = sum(abs(weight) for _, weight in weighted_patterns)
            matched_weight = 0.0
            
            for pattern, weight in weighted_patterns:
                match = pattern.search(text)
                if match:
                    matched_weight += weight
                    if weight > 0:  # Evidence only for positives
                        snippet = text[max(0, match.start() - 20) : match.end() + 20].strip()
                        intent_evidence.append(snippet)
                    if weight < 0:
                        snippet = text[max(0, match.start() - 20) : match.end() + 20].strip()
                        logging.info(f"Negative weight applied for {intent}: {weight} on '{snippet}'")  # Trace negatives
            
            # Only record positive scores
            if matched_weight > 0:
                score = matched_weight / total_weight
                score = max(0.0, min(1.0, score))  # Cap 0-1, prevent negative dominance
                scores[intent] = score
                evidence.extend(intent_evidence[:5])  # Limit to top 5 per intent

        # Check filename patterns if provided in structure_hints
        if structure_hints and "filename" in structure_hints:
            filename = structure_hints["filename"]
            for intent, weighted_patterns in INTENT_PATTERNS.items():
                for pattern, weight in weighted_patterns:
                    if pattern.match(filename):
                        # Filename match is authoritative - set high score
                        scores[intent] = 0.95  # Very high confidence
                        evidence.append(f"Filename pattern match: {filename}")
                        break

        # Enhanced intent classifier rules for edge cases
        text_lower = text.lower()
        filename_lower = structure_hints.get("filename", "").lower() if structure_hints else ""
        
        # Insurance/Certificate documents
        if any(term in text_lower for term in ['insurance', 'certificate', 'coverage', 'liability']):
            if 'contract' not in scores:
                scores['contract'] = 0.0
            scores['contract'] = min(1.0, scores['contract'] + 0.3)
            evidence.append('insurance_terms')

        # Transition plans
        if 'transition' in filename_lower and 'plan' in filename_lower:
            if 'procedure' not in scores:
                scores['procedure'] = 0.0
            if 'guideline' not in scores:
                scores['guideline'] = 0.0
            scores['procedure'] = min(1.0, scores['procedure'] + 0.3)
            scores['guideline'] = min(1.0, scores['guideline'] + 0.2)
            evidence.append('transition_plan_filename')

        # Reference documents  
        if any(term in text_lower[:200] for term in ['see attachment', 'refer to', 'reference only']):
            # Add reference indicator to structure hints
            if not structure_hints:
                structure_hints = {}
            structure_hints['is_reference'] = True
            evidence.append('reference_document_indicator')

        # Incorporate structure hints (boost scores)
        if structure_hints:
            hint_text = " ".join(structure_hints.values()).lower()
            for intent in scores:
                if intent in hint_text:
                    scores[intent] = min(1.0, scores[intent] * 1.2)

        # Normalize only if max >1.0 (from boosts/hints)
        if scores:
            max_score = max(scores.values())
            if max_score > 1.0:
                for intent in scores:
                    scores[intent] /= max_score

        # Apply confidence decay if aged and uncited
        if mod_date and not cited:
            age_years = (datetime.now() - mod_date).days / 365.0
            decay = max(0.5, 1.0 - (decay_factor * age_years))
            for intent in scores:
                scores[intent] *= decay
            evidence.append(f"Decay applied: {decay:.2f} (age {age_years:.1f} years)")

        # Dedup and cap evidence globally
        evidence = list(dict.fromkeys(evidence))[:10]  # Preserve order, unique top 10

        result = IntentClassificationResult(
            scores=scores or {"unknown": 1.0},
            evidence=evidence
        )

        logging.info(f"Classified intent: {result.scores}, evidence count: {len(result.evidence)}")
        return result

    except Exception as e:
        logging.error(f"Error in classify_intent: {e}", exc_info=True)
        raise


def _ml_classify_intent(text: str) -> Dict[str, float]:
    """Placeholder for future ML enhancement (SetFit/MiniLM fine-tune).
    
    Args:
        text: Document text.
    
    Returns:
        Intent scores from ML model.
    """
    # TODO: Implement with SetFitTrainer on org-specific labels
    # Example:
    # model = SetFitModel.from_pretrained("sentence-transformers/all-MiniLM-L6-v2")
    # # Fine-tune on labeled data
    # return {"specification": 0.95}  # Stub
    return {}


if __name__ == "__main__":
    import streamlit as st

    st.title("BoundState Intent Classifier Demo")

    text = st.text_area("Enter cleaned document text:")
    hints = st.text_input("Structure hints (JSON, e.g. {'title': 'Spec Doc'}):")
    mod_date_str = st.text_input("Mod date (YYYY-MM-DD, optional):")
    cited = st.checkbox("Document is cited elsewhere", value=True)
    decay_factor = st.slider("Decay factor", 0.0, 0.5, 0.1)

    if st.button("Classify"):
        try:
            structure_hints_dict = TypeAdapter(Dict[str, str]).validate_json(hints) if hints else None
            mod_date = datetime.fromisoformat(mod_date_str) if mod_date_str else None
            result = classify_intent(text, structure_hints_dict, mod_date, cited, decay_factor)
            st.json(result.model_dump())
        except Exception as e:
            st.error(f"Error: {e}")