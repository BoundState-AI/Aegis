"""Query intelligence utilities.

Compliance: SWE-033 (Requirements Traceability)
"""
from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class QueryIntent(Enum):
    """Query intent types."""
    UNKNOWN = "unknown"
    PERMISSION = "permission"  # "can I", "allowed to"
    PROCEDURE = "procedure"  # "how to", "process for"
    POLICY = "policy"  # "what is the rule", "policy on"
    DEFINITION = "definition"  # "what is", "define"
    COMPLIANCE = "compliance"  # "requirements for", "standard for"

@dataclass
class QueryAnalysis:
    """Query analysis result."""
    intent: QueryIntent
    confidence: float
    entities: Dict[str, List[str]]  # e.g., {'MATERIAL': ['PFAS'], 'SYSTEM': ['propulsion']}
    suggested_filters: Dict[str, Any]  # e.g., {'doc_type': 'policy'}

class QueryIntelligence:
    """Intelligent query analyzer."""
    
    def __init__(self, model_name: str = "en_core_web_lg"):
        try:
            import spacy
            self.nlp = spacy.load(model_name)
            self.spacy_available = True
        except (ImportError, OSError):
            logger.warning(f"SpaCy model {model_name} not available, using fallback analysis")
            self.nlp = None
            self.spacy_available = False
    
    def analyze_query(self, query: str) -> QueryAnalysis:
        """Analyze query for intent and entities."""
        # Detect intent
        intent, conf = self._detect_intent(query)
        
        # Extract entities
        if self.spacy_available and self.nlp:
            doc = self.nlp(query.lower())
            entities = {label: [ent.text for ent in doc.ents if ent.label_ == label] 
                        for label in ['MATERIAL', 'SYSTEM', 'PPE', 'HAZARD']}
        else:
            # Fallback entity extraction
            entities = self._extract_entities_fallback(query)
        
        # Suggest filters
        filters = {}
        if intent == QueryIntent.POLICY:
            filters['doc_type'] = 'policy'
        elif intent == QueryIntent.PROCEDURE:
            filters['doc_type'] = 'procedure'
        
        return QueryAnalysis(
            intent=intent,
            confidence=conf,
            entities=entities,
            suggested_filters=filters
        )
    
    def _detect_intent(self, query: str) -> tuple[QueryIntent, float]:
        """Detect query intent."""
        patterns = {
            QueryIntent.PERMISSION: r"\b(can i|am i allowed|may i|is it ok|allowed to|permitted to)\b",
            QueryIntent.PROCEDURE: r"\b(how to|process for|steps to|procedure for)\b",
            QueryIntent.POLICY: r"\b(policy on|rules for|guidelines for|what is the policy)\b",
            QueryIntent.DEFINITION: r"\b(what is|define|meaning of|definition of)\b",
            QueryIntent.COMPLIANCE: r"\b(requirements for|standard for|compliance with|comply with)\b"
        }
        
        for intent, pattern in patterns.items():
            if re.search(pattern, query, re.I):
                return intent, 0.9
        
        return QueryIntent.UNKNOWN, 0.5
    
    def _extract_entities_fallback(self, query: str) -> Dict[str, List[str]]:
        """Fallback entity extraction without SpaCy."""
        entities = {
            'MATERIAL': [],
            'SYSTEM': [],
            'PPE': [],
            'HAZARD': []
        }
        
        # Simple keyword-based extraction
        material_keywords = ['pfas', 'chemical', 'material', 'substance']
        system_keywords = ['propulsion', 'avionics', 'hydraulic', 'electrical']
        ppe_keywords = ['ppe', 'gloves', 'goggles', 'mask', 'protective equipment']
        hazard_keywords = ['hazard', 'risk', 'danger', 'exposure']
        
        query_lower = query.lower()
        
        for keyword in material_keywords:
            if keyword in query_lower:
                entities['MATERIAL'].append(keyword)
        
        for keyword in system_keywords:
            if keyword in query_lower:
                entities['SYSTEM'].append(keyword)
                
        for keyword in ppe_keywords:
            if keyword in query_lower:
                entities['PPE'].append(keyword)
                
        for keyword in hazard_keywords:
            if keyword in query_lower:
                entities['HAZARD'].append(keyword)
        
        return entities
