#!/usr/bin/env python3
"""
Hybrid retrieval combining dense (FAISS) and sparse (BM25) retrieval
with Reciprocal Rank Fusion (RRF) for optimal accuracy
"""
__safety_critical__ = True

import logging
from typing import List, Dict, Any, Optional, Set
import numpy as np
from collections import Counter
import math
import re

logger = logging.getLogger(__name__)

try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    logger.warning("rank_bm25 not available, using simple TF-IDF fallback")

class HybridRetriever:
    """
    Hybrid retrieval combining:
    1. Dense retrieval (4096d embeddings) for semantic similarity
    2. Sparse retrieval (BM25) for exact term matching
    3. RRF fusion for optimal ranking
    
    No hardcoded filename patterns - learns from document structure only.
    """
    
    def __init__(self, semantic_index, k1: float = 1.2, b: float = 0.75):
        """
        Initialize hybrid retriever.
        
        Args:
            semantic_index: The 4096d semantic index
            k1: BM25 term frequency saturation parameter
            b: BM25 document length normalization parameter
        """
        self.semantic_index = semantic_index
        self.k1 = k1
        self.b = b
        
        # BM25 components
        self.bm25 = None
        self.documents = []
        self.document_tokens = []
        
        # Build BM25 index from existing sections
        self._build_sparse_index()
    
    def _build_sparse_index(self):
        """Build BM25 index from document sections"""
        if not self.semantic_index.sections:
            logger.info("No sections available for BM25 indexing")
            return
        
        logger.info(f"Building BM25 index for {len(self.semantic_index.sections)} sections...")
        
        # Extract structured text from each section
        self.documents = []
        self.document_tokens = []
        
        for section in self.semantic_index.sections:
            # Combine different text fields with appropriate weighting
            structured_text = self._extract_structured_text(section)
            
            # Tokenize for BM25
            tokens = self._tokenize_for_bm25(structured_text)
            
            self.documents.append(structured_text)
            self.document_tokens.append(tokens)
        
        # Initialize BM25
        if BM25_AVAILABLE and self.document_tokens:
            self.bm25 = BM25Okapi(self.document_tokens, k1=self.k1, b=self.b)
            logger.info("BM25 index built successfully")
        else:
            logger.warning("BM25 not available, using TF-IDF fallback")
            self._build_tfidf_fallback()
    
    def _extract_structured_text(self, section: Dict[str, Any]) -> str:
        """
        Extract text with structural awareness (not filename patterns).
        
        Boosts important document elements:
        - Titles and headers (learned from parsing)
        - Table content (structured data)
        - Key metadata fields
        """
        text_parts = []
        
        # Main text content
        main_text = section.get('text', '')
        if main_text:
            text_parts.append(main_text)
        
        # Title/header boosting (structure-based, not name-based)
        title = section.get('title', '')
        if title:
            # Repeat title for BM25 boosting
            text_parts.extend([title] * 2)
        
        # Section headers (if available)
        headers = section.get('headers', [])
        for header in headers:
            text_parts.extend([header] * 2)  # Boost headers
        
        # Table content (enhanced table parsing output)
        table_text = section.get('table_content', '')
        if table_text:
            # Tables are important for structured queries
            text_parts.extend([table_text] * 3)
        
        # Form fields (if this is a form)
        form_fields = section.get('form_fields', [])
        for field in form_fields:
            text_parts.append(field)
        
        # Metadata that might be searchable
        doc_type = section.get('doc_type', '')
        if doc_type:
            text_parts.append(doc_type)
        
        tags = section.get('tags', [])
        for tag in tags:
            text_parts.append(tag)
        
        return ' '.join(text_parts)
    
    def _tokenize_for_bm25(self, text: str) -> List[str]:
        """Tokenize text for BM25 with domain-appropriate preprocessing"""
        # Convert to lowercase
        text = text.lower()
        
        # Preserve important aerospace/document patterns
        # Keep document IDs, procedure numbers, etc.
        text = re.sub(r'([a-z])(\d)', r'\1 \2', text)  # word-number boundaries
        text = re.sub(r'(\d)([a-z])', r'\1 \2', text)  # number-word boundaries
        
        # Split on whitespace and punctuation, but preserve some patterns
        tokens = re.findall(r'\b\w+\b', text)
        
        # Filter very short tokens and stopwords
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 
            'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be',
            'this', 'that', 'these', 'those', 'it', 'its'
        }
        
        tokens = [
            token for token in tokens 
            if len(token) >= 2 and token not in stopwords
        ]
        
        return tokens
    
    def _build_tfidf_fallback(self):
        """Build simple TF-IDF fallback when BM25 is not available"""
        logger.info("Building TF-IDF fallback index...")
        
        # Build vocabulary
        self.vocab = set()
        for tokens in self.document_tokens:
            self.vocab.update(tokens)
        
        self.vocab = list(self.vocab)
        self.vocab_to_id = {term: i for i, term in enumerate(self.vocab)}
        
        # Calculate IDF scores
        self.idf_scores = {}
        total_docs = len(self.document_tokens)
        
        for term in self.vocab:
            doc_freq = sum(1 for tokens in self.document_tokens if term in tokens)
            self.idf_scores[term] = math.log(total_docs / (doc_freq + 1))
        
        logger.info(f"TF-IDF fallback built with {len(self.vocab)} terms")
    
    def search_sparse(self, query: str, k: int = 50) -> List[Dict[str, Any]]:
        """Perform sparse (BM25/TF-IDF) retrieval"""
        if not self.documents:
            return []
        
        # Tokenize query
        query_tokens = self._tokenize_for_bm25(query)
        if not query_tokens:
            return []
        
        if BM25_AVAILABLE and self.bm25:
            # Use BM25
            scores = self.bm25.get_scores(query_tokens)
        else:
            # Use TF-IDF fallback
            scores = self._compute_tfidf_scores(query_tokens)
        
        # Get top k results
        top_indices = np.argsort(scores)[::-1][:k]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only include positive scores
                doc = self.semantic_index.sections[idx].copy()
                doc['sparse_score'] = float(scores[idx])
                doc['sparse_rank'] = len(results) + 1
                results.append(doc)
        
        return results
    
    def _compute_tfidf_scores(self, query_tokens: List[str]) -> np.ndarray:
        """Compute TF-IDF scores for fallback"""
        scores = np.zeros(len(self.document_tokens))
        
        for doc_idx, doc_tokens in enumerate(self.document_tokens):
            doc_token_counts = Counter(doc_tokens)
            doc_length = len(doc_tokens)
            
            score = 0.0
            for term in query_tokens:
                if term in doc_token_counts:
                    tf = doc_token_counts[term] / doc_length
                    idf = self.idf_scores.get(term, 0)
                    score += tf * idf
            
            scores[doc_idx] = score
        
        return scores
    
    def search_hybrid(self,
                     query: str,
                     k: int = 10,
                     dense_k: int = 50,
                     sparse_k: int = 50,
                     rrf_k: int = 60,
                     alpha: float = 0.5) -> List[Dict[str, Any]]:
        """
        Perform hybrid search with RRF fusion.
        
        Args:
            query: Search query
            k: Final number of results
            dense_k: Number of dense retrieval candidates
            sparse_k: Number of sparse retrieval candidates  
            rrf_k: RRF parameter (higher = more fusion)
            alpha: Dense vs sparse weighting (0.5 = equal)
            
        Returns:
            Fused and ranked results
        """
        # Get dense results (semantic similarity)
        dense_results = self.semantic_index.search_text(
            query, 
            k=dense_k, 
            use_reranking=False  # We'll rerank the fused results
        )
        
        # Get sparse results (keyword matching)
        sparse_results = self.search_sparse(query, k=sparse_k)
        
        # Apply Reciprocal Rank Fusion
        fused_results = self._reciprocal_rank_fusion(
            dense_results, 
            sparse_results, 
            rrf_k=rrf_k
        )
        
        logger.debug(f"Fused {len(dense_results)} dense + {len(sparse_results)} sparse -> {len(fused_results)} results")
        
        return fused_results[:k]
    
    def _reciprocal_rank_fusion(self,
                               dense_results: List[Dict],
                               sparse_results: List[Dict],
                               rrf_k: int = 60) -> List[Dict]:
        """
        Apply Reciprocal Rank Fusion to combine dense and sparse results.
        
        RRF score = sum(1/(k + rank_i)) for all result lists where doc appears
        """
        # Build document lookup by ID
        doc_scores = {}
        
        # Process dense results
        for rank, doc in enumerate(dense_results, 1):
            doc_id = self._get_doc_identifier(doc)
            if doc_id not in doc_scores:
                doc_scores[doc_id] = {
                    'doc': doc,
                    'dense_rank': rank,
                    'sparse_rank': None,
                    'dense_score': doc.get('embedding_score', 0),
                    'sparse_score': 0,
                    'rrf_score': 0
                }
            
            # Add RRF score from dense ranking
            doc_scores[doc_id]['rrf_score'] += 1 / (rrf_k + rank)
        
        # Process sparse results
        for rank, doc in enumerate(sparse_results, 1):
            doc_id = self._get_doc_identifier(doc)
            
            if doc_id not in doc_scores:
                doc_scores[doc_id] = {
                    'doc': doc,
                    'dense_rank': None,
                    'sparse_rank': rank,
                    'dense_score': 0,
                    'sparse_score': doc.get('sparse_score', 0),
                    'rrf_score': 0
                }
            else:
                # Update sparse info
                doc_scores[doc_id]['sparse_rank'] = rank
                doc_scores[doc_id]['sparse_score'] = doc.get('sparse_score', 0)
            
            # Add RRF score from sparse ranking
            doc_scores[doc_id]['rrf_score'] += 1 / (rrf_k + rank)
        
        # Build final results
        fused_results = []
        for doc_info in doc_scores.values():
            doc = doc_info['doc'].copy()
            doc.update({
                'dense_rank': doc_info['dense_rank'],
                'sparse_rank': doc_info['sparse_rank'], 
                'dense_score': doc_info['dense_score'],
                'sparse_score': doc_info['sparse_score'],
                'rrf_score': doc_info['rrf_score']
            })
            fused_results.append(doc)
        
        # Sort by RRF score
        fused_results.sort(key=lambda x: x['rrf_score'], reverse=True)
        
        return fused_results
    
    def _get_doc_identifier(self, doc: Dict[str, Any]) -> str:
        """Get unique identifier for a document section"""
        # Use combination of doc_id and section for uniqueness
        doc_id = doc.get('doc_id', '')
        section = doc.get('section', '')
        text_hash = str(abs(hash(doc.get('text', '')[:100])))[:8]
        return f"{doc_id}:{section}:{text_hash}"
    
    def rebuild_sparse_index(self):
        """Rebuild the sparse index (call after adding new documents)"""
        self._build_sparse_index()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get hybrid retrieval statistics"""
        return {
            'total_documents': len(self.documents),
            'bm25_available': BM25_AVAILABLE and self.bm25 is not None,
            'vocab_size': len(self.vocab) if hasattr(self, 'vocab') else 0,
            'sparse_index_type': 'BM25' if (BM25_AVAILABLE and self.bm25) else 'TF-IDF'
        }