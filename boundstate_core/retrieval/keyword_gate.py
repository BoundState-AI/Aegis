#!/usr/bin/env python3
"""
Keyword Gate - Adds lexical precision to embedding search
Implements keyword filtering as described in this.txt
"""

import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class KeywordGate:
    """Applies keyword filtering to embedding search results for lexical precision"""
    
    def __init__(self):
        # Build inverted index for fast keyword lookup
        self.inverted_index = {}  # word -> set of doc_ids
        self.index_built = False
        
        # Intent-based keyword requirements - relaxed approach
        self.keyword_rules = {
            "policy": {
                "query_patterns": [r"what is", r"who does", r"how is", r"purpose", r"apply to"],
                "required_terms": [],
                "optional_terms": ["process", "plan", "checklist", "form", "procedure"]
            },
            "travel": {
                "query_patterns": [r"stay.*extra", r"extend.*stay", r"extra.*days", r"personal.*travel"],
                "required_terms": [],
                "optional_terms": ["approval", "expense", "lodging"]
            }
        }
    
    def build_inverted_index(self, all_sections: List[Dict[str, Any]]):
        """Build inverted index for fast keyword lookup"""
        self.inverted_index = {}
        
        for section in all_sections:
            doc_id = section.get('doc_id', '')
            text = section.get('text', '').lower()
            
            # Extract words and add to inverted index
            words = re.findall(r'\b\w+\b', text)
            for word in words:
                if word not in self.inverted_index:
                    self.inverted_index[word] = set()
                self.inverted_index[word].add(doc_id)
        
        self.index_built = True
        logger.info(f"Built inverted index with {len(self.inverted_index)} terms")
    
    def apply_gate(self, query: str, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply keyword gate filtering to search results."""
        query_type = self._detect_query_type(query)
        if not query_type:
            logger.info("No keyword gate rules apply, returning all results")
            return search_results
        
        logger.info(f"Applying relaxed {query_type} keyword gate")
        
        # Since required_terms is empty in the new approach, just return all results
        # This makes the gate much more permissive
        logger.info(f"Relaxed keyword gate passed {len(search_results)} results")
        return search_results
    
    def _detect_query_type(self, query: str) -> str:
        """Detect query type based on patterns."""
        query_lower = query.lower()
        for query_type, rules in self.keyword_rules.items():
            for pattern in rules["query_patterns"]:
                if re.search(pattern, query_lower):
                    return query_type
        return None
    
    def boost_keyword_matches(self, query: str, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Boost results that contain important keywords
        
        Args:
            query: User query
            search_results: Search results to boost
            
        Returns:
            Results with boosted scores for keyword matches
        """
        query_lower = query.lower()
        query_terms = set(re.findall(r'\b\w+\b', query_lower))
        
        boosted_results = []
        for result in search_results:
            result_copy = result.copy()
            text_lower = result.get('text', '').lower()
            
            # Calculate keyword boost
            boost_factor = 1.0
            
            # Boost for exact query term matches
            text_terms = set(re.findall(r'\b\w+\b', text_lower))
            common_terms = query_terms.intersection(text_terms)
            if common_terms:
                boost_factor *= 1.0 + (len(common_terms) / len(query_terms)) * 0.2
            
            # Boost for important policy terms
            important_terms = {
                "per diem": 0.15,
                "personal travel": 0.2,
                "not authorized": 0.25,
                "not reimbursable": 0.25,
                "employee expense": 0.2,
                "fare difference": 0.15,
                "tqp": 0.3, 
                "tipi": 0.2, 
                "innovation grants": 0.2,
                "new employee": 0.25,
                "quotation": 0.25,
                "transition plan": 0.2
            }
            
            for term, boost in important_terms.items():
                if term in text_lower:
                    boost_factor *= 1.0 + boost
            
            # Apply boost to score
            if 'score' in result_copy:
                result_copy['score'] = result_copy['score'] * boost_factor
            
            boosted_results.append(result_copy)
        
        # Re-sort by boosted scores
        boosted_results.sort(key=lambda x: x.get('score', 0), reverse=True)
        return boosted_results

# Global instance
_keyword_gate = None

def get_keyword_gate() -> KeywordGate:
    """Get global keyword gate instance"""
    global _keyword_gate
    if _keyword_gate is None:
        _keyword_gate = KeywordGate()
    return _keyword_gate

def apply_keyword_gate(query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Apply keyword gate to search results"""
    gate = get_keyword_gate()
    return gate.apply_gate(query, results)

def boost_keyword_matches(query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Boost results based on keyword matches"""
    gate = get_keyword_gate()
    return gate.boost_keyword_matches(query, results)