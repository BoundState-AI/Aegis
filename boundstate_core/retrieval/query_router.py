#!/usr/bin/env python3
"""
Query Router - Routes queries to appropriate document subsets
Implements first-stage filtering as described in this.txt
"""
__safety_critical__ = True

import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class QueryRouter:
    """Routes queries to appropriate document subsets before embedding search"""
    
    def __init__(self):
        # Broad intent-based routing patterns - ORDER MATTERS: specific patterns first!
        self.routing_rules = {
            "procurement": {
                "patterns": [
                    r"purchase", r"procurement", r"vendor", r"supplier",
                    r"contract", r"buy", r"order", r"sole.*source", r"justification",
                    r"quotation", r"request.*for.*quotation", r"rfq"
                ],
                "doc_filters": [
                    lambda md: self._is_procurement_doc(md)
                ],
                "min_candidates": 50
            },
            "travel": {
                "patterns": [
                    r"travel", r"tdy", r"per diem", r"per-diem", r"lodging", 
                    r"airfare", r"trip", r"destination", r"hotel", r"expense",
                    r"stay.*extra.*days",
                    r"extend.*stay", r"personal.*travel"
                ],
                "doc_filters": [
                    lambda md: self._is_travel_doc(md)
                ],
                "min_candidates": 30  # Fallback threshold
            },
            "tqp": {
                "patterns": [
                    r"tqp", r"technical.*qualification.*program", r"qualification.*program",
                    r"how.*many.*tqp", r"count.*tqp", r"documents.*mention.*tqp",
                    r"mention.*tqp", r"document.*tqp", r"does.*mention.*tqp", r"contain.*tqp"
                ],
                "doc_filters": [
                    lambda md: self._is_tqp_doc(md)
                ],
                "min_candidates": 10  # Lower threshold for TQP as there are fewer docs
            },
            "safety": {
                "patterns": [
                    r"safety", r"hazard", r"risk", r"accident", r"incident",
                    r"ppe", r"protection", r"emergency", r"evacuation",
                    r"certification", r"certify", r"certified", r"operate.*equipment",
                    r"equipment.*operate", r"machine.*operation", r"training.*required",
                    r"required.*training", r"workplace.*accident", r"report.*accident"
                ],
                "doc_filters": [
                    lambda md: self._is_safety_doc(md)
                ],
                "min_candidates": 50
            },
            "policy_info": {
                "patterns": [r"what is", r"who does", r"how is", r"what are", r"purpose"],
                "doc_filters": [lambda md: any(t in md.get('tags', []) for t in ['policy', 'guideline', 'procedure'])],
                "min_candidates": 30
            },
            "process": {
                "patterns": [r"action", r"maintain", r"activities"],
                "doc_filters": [lambda md: 'process' in md.get('text', '').lower()],
                "min_candidates": 30
            },
            "hr_policy": {
                "patterns": [
                    r"employee", r"personnel", r"timecard", r"vacation",
                    r"leave", r"hours", r"overtime", r"benefits", r"pto",
                    r"time.*off", r"referral", r"hiring", r"probationary.*period",
                    r"probation", r"new.*hire", r"onboarding", r"employment.*start"
                ],
                "doc_filters": [
                    lambda md: self._is_hr_doc(md)
                ],
                "min_candidates": 50
            }
        }
    
    def route_query(self, query: str, all_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Route query to appropriate document subset before embedding search.
        """
        query_lower = query.lower()
        for name, rule in self.routing_rules.items():
            for pattern in rule['patterns']:
                if re.search(pattern, query_lower):
                    candidates = [c for c in all_chunks if any(f(c) for f in rule['doc_filters'])]
                    if len(candidates) >= rule.get('min_candidates', 0):
                        logger.info(f"Detected {name} query, using {len(candidates)} filtered chunks")
                        return candidates
        
        logger.info("No specific query type detected, using all chunks")
        return all_chunks
    
    def _is_travel_doc(self, metadata: Dict[str, Any]) -> bool:
        """Check if document is travel-related"""
        # Check multiple possible field names
        doc_id = metadata.get("doc_id", "").lower()
        filename = metadata.get("filename", metadata.get("file_name", "")).lower()
        title = metadata.get("title", "").lower()
        section = metadata.get("section_heading", metadata.get("section", "")).lower()
        
        combined = f"{doc_id} {filename} {title} {section}"
        
        # Strong travel indicators - prioritize actual travel policy documents
        strong_travel_indicators = [
            "pol1901", "g1901", "travel policy", "business travel"
        ]
        
        # Weak travel indicators - general travel terms
        weak_travel_indicators = [
            "travel", "tdy", "per diem", "per-diem", "expense", 
            "lodging", "airfare", "trip", "destination"
        ]
        
        # Prefer strong indicators
        if any(indicator in combined for indicator in strong_travel_indicators):
            return True
        
        # Special check for TQP/TIPI/Innovation grants and other document types  
        if 'tqp' in combined or 'tipi' in combined or 'innovation grants' in combined or 'new employee' in combined or 'quotation' in combined or 'transition plan' in combined:
            return True
            
        # Only accept weak indicators if filename/doc_id suggests policy document
        if any(indicator in combined for indicator in weak_travel_indicators):
            return "pol" in doc_id or "pol" in filename or "policy" in combined
            
        return False
    
    def _is_safety_doc(self, metadata: Dict[str, Any]) -> bool:
        """Check if document is safety-related"""
        filename = metadata.get("filename", metadata.get("doc_id", "")).lower()
        title = metadata.get("title", "").lower()
        section = metadata.get("section_heading", metadata.get("section", "")).lower()
        
        combined = f"{filename} {title} {section}"
        
        safety_indicators = [
            "safety", "hazard", "risk", "accident", "incident", "emergency",
            "ppe", "protection", "evacuation", "osha", "safety plan"
        ]
        
        return any(indicator in combined for indicator in safety_indicators)
    
    def _is_procurement_doc(self, metadata: Dict[str, Any]) -> bool:
        """Check if document is procurement-related"""
        # Check doc_type first
        doc_type = metadata.get("doc_type", "").lower()
        if doc_type == "procurement":
            return True
            
        filename = metadata.get("filename", metadata.get("doc_id", "")).lower()
        title = metadata.get("title", "").lower()
        section = metadata.get("section_heading", metadata.get("section", "")).lower()
        text = metadata.get("text", "")[:200].lower()  # Check first 200 chars of text
        
        combined = f"{filename} {title} {section} {text}"
        
        procurement_indicators = [
            "procurement", "purchase", "vendor", "supplier", "contract",
            "buying", "sourcing", "rfp", "proposal", "sole source", "justification",
            "f1301", "quotation", "order"
        ]
        
        return any(indicator in combined for indicator in procurement_indicators)
    
    def _is_hr_doc(self, metadata: Dict[str, Any]) -> bool:
        """Check if document is HR/personnel-related"""
        filename = metadata.get("filename", metadata.get("doc_id", "")).lower()
        title = metadata.get("title", "").lower()
        section = metadata.get("section_heading", metadata.get("section", "")).lower()
        
        combined = f"{filename} {title} {section}"
        
        hr_indicators = [
            "personnel", "employee", "timecard", "pol2320", "vacation",
            "leave", "benefits", "payroll", "hr", "human resources"
        ]
        
        return any(indicator in combined for indicator in hr_indicators)
    
    def _is_tqp_doc(self, metadata: Dict[str, Any]) -> bool:
        """Check if document is TQP-related"""
        doc_id = metadata.get("doc_id", "").lower()
        filename = metadata.get("filename", metadata.get("file_name", "")).lower()
        title = metadata.get("title", "").lower()
        section = metadata.get("section_heading", metadata.get("section", "")).lower()
        text = metadata.get("text", "").lower()  # Check full text for TQP, not just first 500 chars

        combined = f"{doc_id} {filename} {title} {section} {text}"

        # More comprehensive TQP indicators
        tqp_indicators = [
            "tqp", "technical qualification program", "qualification program",
            "quality plan", "controlling document", "p7301"
        ]

        # First check for obvious TQP indicators
        if any(indicator in combined for indicator in tqp_indicators):
            return True

        # Additional check: if text contains "tqp" multiple times, it's likely a TQP document
        tqp_count = text.count("tqp")
        if tqp_count >= 3:  # Document mentions TQP 3+ times
            return True

        return False
    
    # Relaxed filter methods for stage 2
    def _is_travel_doc_relaxed(self, metadata: Dict[str, Any]) -> bool:
        """Relaxed check for travel-related documents"""
        # Check multiple possible field names
        doc_id = metadata.get("doc_id", "").lower()
        filename = metadata.get("filename", metadata.get("file_name", "")).lower()
        title = metadata.get("title", "").lower()
        section = metadata.get("section_heading", metadata.get("section", "")).lower()
        text = metadata.get("text", "").lower()[:200]  # Check first 200 chars of text
        
        combined = f"{doc_id} {filename} {title} {section} {text}"
        
        # More lenient - accept any travel-related term
        travel_indicators = [
            "travel", "trip", "expense", "per diem", "lodging", "hotel",
            "airfare", "destination", "tdy", "business trip", "reimburs",
            "pol1901"  # Explicitly include POL1901
        ]
        
        return any(indicator in combined for indicator in travel_indicators)
    
    def _is_safety_doc_relaxed(self, metadata: Dict[str, Any]) -> bool:
        """Relaxed check for safety-related documents"""
        filename = metadata.get("filename", metadata.get("doc_id", "")).lower()
        title = metadata.get("title", "").lower()
        section = metadata.get("section_heading", metadata.get("section", "")).lower()
        text = metadata.get("text", "").lower()[:200]
        
        combined = f"{filename} {title} {section} {text}"
        
        # More lenient safety indicators
        safety_indicators = [
            "safe", "hazard", "risk", "danger", "caution", "warning",
            "accident", "incident", "injury", "protect", "prevent"
        ]
        
        return any(indicator in combined for indicator in safety_indicators)
    
    def _is_procurement_doc_relaxed(self, metadata: Dict[str, Any]) -> bool:
        """Relaxed check for procurement-related documents"""
        filename = metadata.get("filename", metadata.get("doc_id", "")).lower()
        title = metadata.get("title", "").lower()
        section = metadata.get("section_heading", metadata.get("section", "")).lower()
        text = metadata.get("text", "").lower()[:200]
        
        combined = f"{filename} {title} {section} {text}"
        
        # More lenient procurement indicators
        procurement_indicators = [
            "buy", "purchase", "order", "vendor", "supplier", "contract",
            "procure", "acquire", "payment", "invoice", "quote"
        ]
        
        return any(indicator in combined for indicator in procurement_indicators)
    
    def _is_hr_doc_relaxed(self, metadata: Dict[str, Any]) -> bool:
        """Relaxed check for HR-related documents"""
        filename = metadata.get("filename", metadata.get("doc_id", "")).lower()
        title = metadata.get("title", "").lower()
        section = metadata.get("section_heading", metadata.get("section", "")).lower()
        text = metadata.get("text", "").lower()[:200]
        
        combined = f"{filename} {title} {section} {text}"
        
        # More lenient HR indicators
        hr_indicators = [
            "employee", "staff", "personnel", "time", "hour", "leave",
            "vacation", "benefit", "policy", "work", "pay"
        ]
        
        return any(indicator in combined for indicator in hr_indicators)
    
    def _is_tqp_doc_relaxed(self, metadata: Dict[str, Any]) -> bool:
        """Relaxed check for TQP-related documents"""
        doc_id = metadata.get("doc_id", "").lower()
        filename = metadata.get("filename", metadata.get("file_name", "")).lower()
        title = metadata.get("title", "").lower()
        section = metadata.get("section_heading", metadata.get("section", "")).lower()
        text = metadata.get("text", "").lower()[:500]
        
        combined = f"{doc_id} {filename} {title} {section} {text}"
        
        # Very relaxed TQP indicators - catch any mention
        tqp_indicators = [
            "tqp", "qualification", "quality", "plan", "program", "technical",
            "training", "competence", "skills", "assessment"
        ]
        
        return any(indicator in combined for indicator in tqp_indicators)

# Global instance
_query_router = None

def get_query_router() -> QueryRouter:
    """Get global query router instance"""
    global _query_router
    if _query_router is None:
        _query_router = QueryRouter()
    return _query_router

def route_query(query: str, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Route query to appropriate document subset"""
    router = get_query_router()
    return router.route_query(query, chunks)