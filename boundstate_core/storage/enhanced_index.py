# boundstate/enhanced_index.py
from typing import List, Dict, Any, Optional
import numpy as np
import logging

from boundstate_core.storage.index import SemanticIndex
from boundstate_core.nlp.query_intelligence import QueryIntelligence

logger = logging.getLogger(__name__)

class EnhancedSemanticIndex(SemanticIndex):
    """Enhanced semantic search with multi-stage retrieval."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.query_intelligence = QueryIntelligence()
        logger.info("EnhancedSemanticIndex initialized with query intelligence")
    
    def search_with_reranking(self, query: str, k: int = 5, 
                             rerank_k: int = 20, **filters) -> List[Dict[str, Any]]:
        """Search with semantic reranking."""
        # Get initial candidates
        candidates = self.search_text(query, k=rerank_k, **filters)
        
        if not candidates:
            return []
        
        # Rerank using advanced scoring
        reranked = self._rerank_results(query, candidates)
        
        return reranked[:k]
    
    def _rerank_results(self, query: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rerank results using advanced scoring."""
        # Analyze query for better understanding
        analysis = self.query_intelligence.analyze_query(query)
        
        for candidate in candidates:
            # Original score
            base_score = candidate.get('score', 0)
            
            # Document quality score
            quality_score = self._calculate_quality_score(candidate)
            
            # Relevance boost for exact matches
            exact_match_score = self._calculate_exact_match_score(query, candidate.get('text', ''))
            
            # Intent-based relevance
            intent_score = self._calculate_intent_relevance(analysis, candidate)
            
            # Combined score with weights
            candidate['final_score'] = (
                base_score * 0.4 +
                quality_score * 0.2 +
                exact_match_score * 0.3 +
                intent_score * 0.1
            )
            
            # Store component scores for debugging
            candidate['score_components'] = {
                'base': base_score,
                'quality': quality_score,
                'exact_match': exact_match_score,
                'intent': intent_score
            }
        
        return sorted(candidates, key=lambda x: x['final_score'], reverse=True)
    
    def _calculate_quality_score(self, doc: Dict[str, Any]) -> float:
        """Calculate document quality score."""
        score = 0.5  # Base score
        
        # Boost for official documents
        doc_type = doc.get('metadata', {}).get('doc_type', doc.get('doc_type', ''))
        if doc_type in ['policy', 'standard', 'specification']:
            score += 0.2
        elif doc_type in ['procedure', 'work_instruction']:
            score += 0.15
        
        # Boost for tagged documents
        tags = doc.get('metadata', {}).get('tags', doc.get('tags', []))
        if tags:
            score += min(0.2, len(tags) * 0.05)
        
        # Boost for recent versions
        version = doc.get('metadata', {}).get('version', doc.get('version', ''))
        if version:
            score += 0.1
        
        # Boost for complete sections
        section = doc.get('metadata', {}).get('section', doc.get('section', ''))
        if section and any(keyword in section.lower() for keyword in ['overview', 'policy', 'requirements']):
            score += 0.05
        
        return min(1.0, score)
    
    def _calculate_exact_match_score(self, query: str, text: str) -> float:
        """Calculate exact match score."""
        if not text:
            return 0.0
            
        query_lower = query.lower()
        text_lower = text.lower()
        
        # Check for exact phrase matches
        if query_lower in text_lower:
            return 1.0
        
        # Check for all query terms
        query_terms = set(query_lower.split())
        text_terms = set(text_lower.split())
        
        # Remove common words
        stop_words = {'a', 'an', 'the', 'is', 'are', 'was', 'were', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        query_terms = query_terms - stop_words
        
        if not query_terms:
            return 0.5
        
        # Calculate overlap
        overlap = len(query_terms & text_terms)
        coverage = overlap / len(query_terms)
        
        # Bonus for terms appearing close together
        if coverage > 0.5:
            # Check if query terms appear within a window
            text_words = text_lower.split()
            window_size = 10
            
            for i in range(len(text_words) - window_size + 1):
                window = set(text_words[i:i + window_size])
                if len(query_terms & window) >= len(query_terms) * 0.8:
                    coverage += 0.2
                    break
        
        return min(1.0, coverage)
    
    def _calculate_intent_relevance(self, analysis, doc: Dict[str, Any]) -> float:
        """Calculate relevance based on query intent."""
        score = 0.5
        
        doc_type = doc.get('metadata', {}).get('doc_type', doc.get('doc_type', ''))
        tags = doc.get('metadata', {}).get('tags', doc.get('tags', []))
        text = doc.get('text', '').lower()
        
        # Match document type to intent
        if analysis.intent.value == "policy":
            if doc_type == 'policy':
                score += 0.3
            elif any('policy' in tag.lower() for tag in tags):
                score += 0.2
            elif 'policy' in text:
                score += 0.1
                
        elif analysis.intent.value == "procedure":
            if doc_type in ['procedure', 'work_instruction']:
                score += 0.3
            elif any('procedure' in tag.lower() or 'process' in tag.lower() for tag in tags):
                score += 0.2
            elif any(word in text for word in ['procedure', 'process', 'steps', 'instructions']):
                score += 0.1
                
        elif analysis.intent.value == "compliance":
            if any(tag in ['compliance', 'standard', 'regulation'] for tag in tags):
                score += 0.3
            elif doc_type in ['standard', 'specification', 'regulation']:
                score += 0.2
            elif any(word in text for word in ['compliance', 'requirement', 'standard', 'shall', 'must']):
                score += 0.1
                
        elif analysis.intent.value == "permission":
            # Permission queries often need policy documents
            if doc_type == 'policy':
                score += 0.25
            elif any(word in text for word in ['allowed', 'permitted', 'may', 'can', 'authorized']):
                score += 0.15
        
        # Boost for entity matches
        for entity_type, entities in analysis.entities.items():
            for entity in entities:
                if entity.lower() in text:
                    score += 0.05
        
        return min(1.0, score)
    
    def multi_stage_search(self, query: str, k: int = 5, 
                          stages: Optional[List[Dict]] = None) -> List[Dict[str, Any]]:
        """Perform multi-stage search with different strategies."""
        if stages is None:
            stages = [
                {'method': 'semantic', 'k': 20},
                {'method': 'keyword', 'k': 10},
                {'method': 'rerank', 'k': k}
            ]
        
        all_results = []
        seen_ids = set()
        
        for stage in stages:
            method = stage.get('method', 'semantic')
            stage_k = stage.get('k', k)
            
            if method == 'semantic':
                # Regular semantic search
                results = self.search_text(query, k=stage_k)
                
            elif method == 'keyword':
                # Keyword-based search (if available)
                results = self._keyword_search(query, k=stage_k)
                
            elif method == 'rerank':
                # Rerank all collected results
                if all_results:
                    results = self._rerank_results(query, all_results)[:stage_k]
                else:
                    results = []
            
            # Add unique results
            for result in results:
                doc_id = result.get('metadata', {}).get('doc_id', result.get('doc_id', ''))
                if doc_id and doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    all_results.append(result)
        
        return all_results[:k]
    
    def _keyword_search(self, query: str, k: int = 10) -> List[Dict[str, Any]]:
        """Fallback keyword search (simplified BM25-like)."""
        results = []
        query_terms = set(query.lower().split())
        
        # Search through all sections
        for section in self.sections:
            text = section.get('text', '').lower()
            
            # Simple term frequency score
            score = 0
            for term in query_terms:
                score += text.count(term) / (len(text.split()) + 1)
            
            if score > 0:
                section_copy = section.copy()
                section_copy['score'] = score
                results.append(section_copy)
        
        # Sort by score and return top k
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:k]