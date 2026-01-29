#!/usr/bin/env python3
"""
Query Enhancement for better search relevance
Improves search quality by expanding queries and boosting relevant document types
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class QueryEnhancer:
    """Enhances queries to improve search relevance"""
    
    def __init__(self):
        # Query expansion patterns - add context words to improve semantic matching
        self.expansion_patterns = {
            # Travel extension questions should emphasize policy aspects
            "travel_extension": {
                "patterns": [
                    r"\b(stay|extend|add).*extra.*days?\b",
                    r"\bcan.*stay.*longer\b",
                    r"\bextend.*trip\b",
                    r"\bpersonal.*travel\b",
                    r"\bbusiness.*personal.*travel\b"
                ],
                "expansions": [
                    "travel policy",
                    "personal arrangements", 
                    "business travel policy",
                    "employee travel guidelines",
                    "POL1901",
                    "G1901"
                ]
            },
            
            # General travel questions
            "travel_policy": {
                "patterns": [
                    r"\btravel.*policy\b",
                    r"\btravel.*procedures?\b", 
                    r"\btravel.*guidelines?\b",
                    r"\btravel.*rules?\b"
                ],
                "expansions": [
                    "POL1901",
                    "employee travel",
                    "business travel policy"
                ]
            },
            
            # Time/timecard questions should stay with timecard docs
            "timecard": {
                "patterns": [
                    r"\btimecard\b",
                    r"\btime.*sheet\b",
                    r"\bhours.*worked\b", 
                    r"\bbillable.*hours\b",
                    r"\btime.*tracking\b"
                ],
                "expansions": [
                    "POL2320",
                    "timecard policy",
                    "hours worked"
                ]
            }
        }
        
        # Document type priorities for different query types
        self.doc_type_boost = {
            "travel_extension": {
                "POL1901": 1.4,  # Travel policy gets boost
                "G1901": 1.3,
                "TRAVEL POLICY": 1.2,
                "POL2320": 0.7   # Timecard policy gets penalty
            },
            "travel_policy": {
                "POL1901": 1.4,
                "W1901": 1.2,    # Travel work instructions
                "POL2320": 0.6
            },
            "timecard": {
                "POL2320": 1.3,
                "POL1901": 0.8
            }
        }
    
    def enhance_query(self, query: str) -> str:
        """Enhance query with relevant context terms"""
        enhanced_query = query
        
        # Detect query type and add relevant context
        query_type = self._detect_query_type(query)
        
        if query_type and query_type in self.expansion_patterns:
            expansions = self.expansion_patterns[query_type]["expansions"]
            # Add key terms to help find the right documents
            enhanced_query = f"{query} {' '.join(expansions[:2])}"
            logger.info(f"Enhanced query type '{query_type}': '{query}' -> '{enhanced_query}'")
        
        return enhanced_query
    
    def boost_results(self, query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply document type boosting to search results"""
        query_type = self._detect_query_type(query)
        
        if not query_type or query_type not in self.doc_type_boost:
            return results
        
        boost_config = self.doc_type_boost[query_type]
        
        # Apply boosts and re-sort
        boosted_results = []
        for result in results:
            doc_id = result.get('doc_id', '').upper()
            title = result.get('title', '').upper()
            original_score = result.get('score', 0.0)
            
            # Find matching boost factor
            boost_factor = 1.0
            for doc_pattern, factor in boost_config.items():
                if doc_pattern in doc_id or doc_pattern in title:
                    boost_factor = factor
                    break
            
            # Apply boost
            boosted_score = original_score * boost_factor
            
            # Create new result with boosted score
            boosted_result = result.copy()
            boosted_result['score'] = boosted_score
            boosted_result['original_score'] = original_score
            boosted_result['boost_factor'] = boost_factor
            
            boosted_results.append(boosted_result)
        
        # Sort by boosted score
        boosted_results.sort(key=lambda x: x['score'], reverse=True)
        
        logger.info(f"Applied {query_type} boosting - top result: {boosted_results[0]['doc_id']} "
                   f"(score: {boosted_results[0]['original_score']:.4f} -> {boosted_results[0]['score']:.4f})")
        
        return boosted_results
    
    def apply_hybrid_boost(self, query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply hybrid boosting using multiple signals"""
        if not results:
            return results
        
        # Apply document type boosting first  
        results = self.boost_results(query, results)
        
        # Apply negation detection boost (from this.txt guidance)
        results = self._boost_negation_signals(results)
        
        # Apply policy document preference
        results = self._boost_policy_documents(query, results)
        
        return results
    
    def _boost_negation_signals(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Boost results containing negation signals (not authorized, not reimbursable, etc.)"""
        negation_patterns = [
            r"not\s+(?:authorized|reimbursable|covered|paid)",
            r"no\s+(?:per\s+diem|lodging|reimbursement)",
            r"at\s+employee\s+expense",
            r"personal\s+travel",
            r"personal.*expense",
            r"not\s+reimbursed"
        ]
        
        boosted_results = []
        for result in results:
            text = result.get('text', '').lower()
            boost_factor = 1.0
            
            # Check for negation patterns
            for pattern in negation_patterns:
                if re.search(pattern, text):
                    boost_factor *= 1.25  # Boost negation signals
                    break
            
            if boost_factor > 1.0:
                boosted_result = result.copy()
                boosted_result['score'] = result.get('score', 0) * boost_factor
                boosted_result['negation_boost'] = True
                boosted_results.append(boosted_result)
            else:
                boosted_results.append(result)
        
        return boosted_results
    
    def _boost_policy_documents(self, query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply policy-specific document preference"""
        query_lower = query.lower()
        
        # Detect if this is a policy question
        is_policy_question = any(term in query_lower for term in [
            "policy", "allowed", "permitted", "authorized", "can i", "may i"
        ])
        
        if not is_policy_question:
            return results
        
        boosted_results = []
        for result in results:
            doc_id = result.get('doc_id', '').upper()
            boost_factor = 1.0
            
            # Prefer POL documents for policy questions
            if 'POL' in doc_id:
                boost_factor *= 1.3
            
            # Prefer latest revision
            if any(rev in doc_id for rev in ['R01', 'R02', 'R03']):
                boost_factor *= 1.1
            
            if boost_factor > 1.0:
                boosted_result = result.copy()
                boosted_result['score'] = result.get('score', 0) * boost_factor
                boosted_result['policy_boost'] = True
                boosted_results.append(boosted_result)
            else:
                boosted_results.append(result)
        
        return boosted_results
    
    def _detect_query_type(self, query: str) -> Optional[str]:
        """Detect the type of query to apply appropriate enhancements"""
        query_lower = query.lower()
        
        # Check each pattern type
        for query_type, config in self.expansion_patterns.items():
            patterns = config["patterns"]
            
            for pattern in patterns:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    return query_type
        
        return None

# Global instance
_query_enhancer = None

def get_query_enhancer() -> QueryEnhancer:
    """Get global query enhancer instance"""
    global _query_enhancer
    if _query_enhancer is None:
        _query_enhancer = QueryEnhancer()
    return _query_enhancer

def enhance_search_query(query: str) -> str:
    """Enhance a search query for better relevance"""
    enhancer = get_query_enhancer()
    return enhancer.enhance_query(query)

def boost_search_results(query: str, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Boost search results based on query type"""
    enhancer = get_query_enhancer()
    return enhancer.boost_results(query, results)