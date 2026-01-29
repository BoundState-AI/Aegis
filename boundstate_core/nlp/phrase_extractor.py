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
BoundState Phrase Extractor Module
Compliance: SWE-013, SWE-033

Provides semantic hooks from raw text through statistical and linguistic analysis.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import Counter
from pathlib import Path
import json

from pydantic import BaseModel, Field, field_validator

# Lazy imports for heavy dependencies
spacy = None
Doc = None
Rake = None
np = None

logger = logging.getLogger(__name__)
__safety_critical__ = False

__all__ = [
    "ExtractedPhrases",
    "PhraseExtractor", 
    "extract_phrases",
    "calculate_semantic_overlap",
    "get_amentum_stopwords"
]


class ExtractedPhrases(BaseModel):
    """Container for extracted phrase results with metadata."""
    
    rake_keywords: List[Tuple[str, float]] = Field(
        description="RAKE-extracted keywords with scores"
    )
    noun_phrases: List[str] = Field(
        description="spaCy-extracted noun chunks"
    )
    named_entities: List[Tuple[str, str]] = Field(
        default_factory=list,
        description="Named entities (text, label)"
    )
    technical_terms: List[str] = Field(
        default_factory=list,
        description="Domain-specific technical terms"
    )
    compliance_refs: List[str] = Field(
        default_factory=list,
        description="Extracted compliance references (MIL-STD, etc.)"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Overall extraction confidence"
    )
    source: str = Field(
        description="Source identifier or text snippet"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional extraction metadata"
    )
    
    model_config = {"extra": "forbid", "populate_by_name": True}
    
    @field_validator("confidence")
    def validate_confidence(cls, v: float) -> float:
        """Ensure confidence is normalized."""
        return max(0.0, min(1.0, v))


class PhraseExtractor:
    """
    Advanced phrase extraction with domain awareness.
    
    Compliance: SWE-013 - Traceability of extracted terms
    """
    
    def __init__(
        self,
        spacy_model: str = "en_core_web_sm",
        custom_stopwords: Optional[List[str]] = None,
        domain_terms_file: Optional[str] = None,
        lazy_load: bool = True
    ):
        """Initialize phrase extractor with configuration."""
        self.spacy_model = spacy_model
        self.lazy_load = lazy_load
        self.nlp = None  # Lazy load spaCy model
        
        if not lazy_load:
            self._ensure_spacy_loaded()
        
        # Initialize RAKE stopwords
        self.stopwords = get_amentum_stopwords()
        if custom_stopwords:
            self.stopwords.extend(custom_stopwords)
        
        # Load domain-specific terms
        self.domain_terms = self._load_domain_terms(domain_terms_file)
        
        # Compliance patterns
        self.compliance_patterns = [
            (r'\bMIL-STD-\d+[A-Z]?\b', 'MIL-STD'),
            (r'\bNASA-STD-\d+\b', 'NASA-STD'),
            (r'\bASTM\s+[A-Z]\d+\b', 'ASTM'),
            (r'\bISO\s+\d+\b', 'ISO'),
            (r'\bAS9100\b', 'AS9100'),
            (r'\bITAR\b', 'ITAR'),
            (r'\bDFARS?\b', 'DFAR'),
            (r'\bFAR\s+\d+\.\d+\b', 'FAR')
        ]
    
    def _load_domain_terms(self, terms_file: Optional[str]) -> Set[str]:
        """Load domain-specific technical terms."""
        if not terms_file or not Path(terms_file).exists():
            # Default Amentum/aerospace terms
            return {
                'pfas', 'fod', 'nonconformance', 'corrective action',
                'preventive action', 'root cause', 'risk assessment',
                'quality assurance', 'configuration management',
                'work breakdown structure', 'statement of work',
                'foreign object debris', 'aerospace', 'defense',
                'hazardous material', 'material safety data sheet'
            }
        
        try:
            with open(terms_file, 'r') as f:
                terms = json.load(f)
                return set(term.lower() for term in terms)
        except Exception as e:
            logger.warning(f"Could not load domain terms: {e}")
            return set()
    
    def _ensure_spacy_loaded(self):
        """Lazy load spaCy and its dependencies."""
        global spacy, Doc, Rake, np
        
        if self.nlp is None:
            try:
                if spacy is None:
                    import spacy as _spacy
                    from spacy.tokens import Doc as _Doc
                    spacy = _spacy
                    Doc = _Doc
                    logger.info("Loaded spaCy library")
                
                self.nlp = spacy.load(self.spacy_model)
                logger.info(f"Loaded spaCy model: {self.spacy_model}")
                
                # Also ensure RAKE and numpy are loaded
                if Rake is None:
                    from rake_nltk import Rake as _Rake
                    Rake = _Rake
                    logger.info("Loaded RAKE library")
                
                if np is None:
                    import numpy as _np
                    np = _np
                    logger.info("Loaded numpy library")
                    
            except ImportError as e:
                logger.error(f"Failed to load NLP dependencies: {e}")
                raise ImportError(
                    "NLP dependencies not installed. Install with: "
                    "pip install spacy rake-nltk numpy && "
                    "python -m spacy download en_core_web_sm"
                )
    
    def extract(
        self,
        text: str,
        rake_min_length: int = 1,
        rake_max_length: int = 4,
        rake_threshold: float = 0.0,
        include_entities: bool = True,
        source: Optional[str] = None
    ) -> ExtractedPhrases:
        """
        Extract phrases with multiple techniques.
        
        Args:
            text: Input text to analyze
            rake_min_length: Min words in RAKE phrases
            rake_max_length: Max words in RAKE phrases  
            rake_threshold: Min score for RAKE keywords
            include_entities: Whether to extract named entities
            source: Source identifier
            
        Returns:
            ExtractedPhrases with all extracted content
            
        Compliance: SWE-033 - Full extraction traceability
        """
        # Ensure spaCy is loaded before processing
        self._ensure_spacy_loaded()
        
        # RAKE extraction
        rake_keywords = self._extract_rake_keywords(
            text, rake_min_length, rake_max_length, rake_threshold
        )
        
        # spaCy processing
        doc = self.nlp(text)
        
        # Noun phrases
        noun_phrases = [chunk.text for chunk in doc.noun_chunks]
        
        # Named entities
        named_entities = []
        if include_entities:
            named_entities = [
                (ent.text, ent.label_) 
                for ent in doc.ents
                if ent.label_ not in ['DATE', 'TIME', 'CARDINAL']
            ]
        
        # Technical terms
        technical_terms = self._extract_technical_terms(doc)
        
        # Compliance references
        compliance_refs = self._extract_compliance_refs(text)
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            rake_keywords, noun_phrases, technical_terms
        )
        
        # Prepare metadata
        metadata = {
            'text_length': len(text),
            'sentence_count': len(list(doc.sents)),
            'extraction_method': 'rake+spacy',
            'spacy_model': self.nlp.meta['name']
        }
        
        return ExtractedPhrases(
            rake_keywords=rake_keywords,
            noun_phrases=noun_phrases,
            named_entities=named_entities,
            technical_terms=technical_terms,
            compliance_refs=compliance_refs,
            confidence=confidence,
            source=source or text[:100] + "...",
            metadata=metadata
        )
    
    def _extract_rake_keywords(
        self,
        text: str,
        min_length: int,
        max_length: int,
        threshold: float
    ) -> List[Tuple[str, float]]:
        """Extract keywords using RAKE algorithm."""
        try:
            r = Rake(
                stopwords=self.stopwords,
                min_length=min_length,
                max_length=max_length
            )
            r.extract_keywords_from_text(text)
            
            # Get keywords with scores above threshold
            keywords = [
                (phrase, float(score))
                for score, phrase in r.get_ranked_phrases_with_scores()
                if score >= threshold
            ]
            
            # Sort by score descending
            keywords.sort(key=lambda x: x[1], reverse=True)
            
            return keywords
            
        except Exception as e:
            logger.error(f"RAKE extraction failed: {e}")
            return []
    
    def _extract_technical_terms(self, doc: Doc) -> List[str]:
        """Extract domain-specific technical terms."""
        technical_terms = []
        
        # Check noun phrases against domain terms
        for chunk in doc.noun_chunks:
            chunk_lower = chunk.text.lower()
            if chunk_lower in self.domain_terms:
                technical_terms.append(chunk.text)
            else:
                # Check if any domain term is contained
                for term in self.domain_terms:
                    if term in chunk_lower and len(term) > 3:
                        technical_terms.append(chunk.text)
                        break
        
        # Check individual tokens
        for token in doc:
            if token.text.lower() in self.domain_terms and token.pos_ in ['NOUN', 'PROPN']:
                if token.text not in technical_terms:
                    technical_terms.append(token.text)
        
        return list(set(technical_terms))
    
    def _extract_compliance_refs(self, text: str) -> List[str]:
        """Extract compliance and standard references."""
        import re
        
        refs = []
        for pattern, ref_type in self.compliance_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            refs.extend(matches)
        
        return list(set(refs))
    
    def _calculate_confidence(
        self,
        rake_keywords: List[Tuple[str, float]],
        noun_phrases: List[str],
        technical_terms: List[str]
    ) -> float:
        """Calculate overall extraction confidence."""
        confidence_factors = []
        
        # RAKE confidence (normalized scores)
        if rake_keywords:
            scores = [score for _, score in rake_keywords]
            max_score = max(scores) if scores else 1.0
            normalized_scores = [s / max_score for s in scores]
            confidence_factors.append(np.mean(normalized_scores))
        
        # Noun phrase density
        if noun_phrases:
            # More noun phrases = higher confidence
            density = min(len(noun_phrases) / 10.0, 1.0)
            confidence_factors.append(density)
        
        # Technical term presence
        if technical_terms:
            # Technical terms indicate domain relevance
            confidence_factors.append(min(len(technical_terms) / 5.0, 1.0))
        
        # Average confidence
        if confidence_factors:
            return float(np.mean(confidence_factors))
        return 0.5  # Default medium confidence


def extract_phrases(
    text: str,
    rake_min_length: int = 1,
    rake_max_length: int = 4,
    stopwords: Optional[List[str]] = None,
    rake_threshold: float = 0.0,
    source: Optional[str] = None,
    include_entities: bool = True,
    domain_terms_file: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extract keyword phrases and noun phrases from text.
    
    This is a convenience function that creates a PhraseExtractor
    and performs extraction in one call.
    
    Args:
        text: Input text to process
        rake_min_length: Minimum number of words in RAKE phrases
        rake_max_length: Maximum number of words in RAKE phrases
        stopwords: Custom stopwords list for RAKE
        rake_threshold: Minimum score threshold for RAKE keywords
        source: Identifier for the text source
        include_entities: Whether to extract named entities
        domain_terms_file: Path to domain terms JSON file
        
    Returns:
        Dictionary with extracted phrases and metadata
        
    Compliance: SWE-013, SWE-033
    """
    try:
        extractor = PhraseExtractor(
            custom_stopwords=stopwords,
            domain_terms_file=domain_terms_file
        )
        
        result = extractor.extract(
            text=text,
            rake_min_length=rake_min_length,
            rake_max_length=rake_max_length,
            rake_threshold=rake_threshold,
            include_entities=include_entities,
            source=source
        )
        
        return result.model_dump()
        
    except Exception as e:
        logger.error(f"Error in phrase extraction: {e}", extra={"source": source})
        raise


def calculate_semantic_overlap(
    phrases1: ExtractedPhrases,
    phrases2: ExtractedPhrases,
    min_overlap: float = 0.3
) -> Dict[str, Any]:
    """
    Calculate semantic overlap between two sets of extracted phrases.
    
    Args:
        phrases1: First set of extracted phrases
        phrases2: Second set of extracted phrases
        min_overlap: Minimum overlap ratio to consider significant
        
    Returns:
        Dictionary with overlap metrics and shared terms
    """
    # Get all terms from both sets
    terms1 = set()
    terms2 = set()
    
    # Add RAKE keywords (just the phrases, not scores)
    terms1.update(phrase for phrase, _ in phrases1.rake_keywords)
    terms2.update(phrase for phrase, _ in phrases2.rake_keywords)
    
    # Add noun phrases
    terms1.update(phrases1.noun_phrases)
    terms2.update(phrases2.noun_phrases)
    
    # Add technical terms
    terms1.update(phrases1.technical_terms)
    terms2.update(phrases2.technical_terms)
    
    # Calculate overlap
    shared_terms = terms1.intersection(terms2)
    total_terms = terms1.union(terms2)
    
    overlap_ratio = len(shared_terms) / len(total_terms) if total_terms else 0.0
    
    # Check compliance reference overlap
    shared_compliance = set(phrases1.compliance_refs).intersection(
        set(phrases2.compliance_refs)
    )
    
    return {
        'overlap_ratio': overlap_ratio,
        'is_significant': overlap_ratio >= min_overlap,
        'shared_terms': list(shared_terms),
        'shared_compliance_refs': list(shared_compliance),
        'unique_to_first': list(terms1 - terms2),
        'unique_to_second': list(terms2 - terms1),
        'metadata': {
            'terms_count_1': len(terms1),
            'terms_count_2': len(terms2),
            'shared_count': len(shared_terms)
        }
    }


def get_amentum_stopwords() -> List[str]:
    """
    Get Amentum-specific stopwords for aerospace/defense domain.
    
    Returns:
        List of stopwords including standard English + domain terms
    """
    # Standard English stopwords
    base_stopwords = [
        'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for',
        'from', 'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on',
        'that', 'the', 'to', 'was', 'will', 'with', 'the', 'this',
        'these', 'those', 'such', 'been', 'being', 'have', 'has',
        'had', 'having', 'do', 'does', 'did', 'doing', 'would',
        'could', 'should', 'may', 'might', 'must', 'shall', 'can',
        'cannot', 'if', 'then', 'else', 'when', 'where', 'which',
        'who', 'whom', 'whose', 'what', 'why', 'how'
    ]
    
    # Amentum/business-specific common words to exclude
    domain_stopwords = [
        'shall', 'must', 'should', 'may', 'document', 'documents',
        'section', 'page', 'refer', 'reference', 'see', 'appendix',
        'figure', 'table', 'item', 'items', 'number', 'date',
        'revision', 'rev', 'version', 'approved', 'reviewed'
    ]
    
    return base_stopwords + domain_stopwords