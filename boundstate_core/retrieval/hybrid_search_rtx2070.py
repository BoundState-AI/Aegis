#!/usr/bin/env python3
"""
RTX 2070 Optimized Hybrid Search Engine
Combines dense (FAISS) + sparse (BM25) retrieval with RRF fusion
Based on that.txt analysis for maximum accuracy on RTX 2070
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional
from collections import defaultdict
import pickle
from pathlib import Path

try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    logging.warning("rank-bm25 not available - install with: pip install rank-bm25")

try:
    from sentence_transformers import CrossEncoder
    RERANKER_AVAILABLE = True
except ImportError:
    RERANKER_AVAILABLE = False

logger = logging.getLogger(__name__)

class HybridSearchRTX2070:
    """
    Hybrid search optimized for RTX 2070
    - Dense search: Nomic embeddings via FAISS
    - Sparse search: BM25 on bm25_text field  
    - Fusion: Reciprocal Rank Fusion (RRF)
    - Reranking: mixedbread base model
    """
    
    def __init__(self, dense_index, reranker_model: str = 'mixedbread-ai/mxbai-rerank-base-v1'):
        self.dense_index = dense_index  # SemanticIndex instance
        self.bm25_index = None
        self.bm25_texts = []
        self.doc_id_to_bm25_idx = {}
        self.bm25_idx_to_section = {}
        
        # Load reranker
        self.reranker = None
        if RERANKER_AVAILABLE:
            try:
                # Run reranker on CPU to save VRAM for embeddings
                self.reranker = CrossEncoder(reranker_model, device='cpu')
                logger.info(f"Loaded reranker: {reranker_model} on CPU")
            except Exception as e:
                logger.warning(f"Could not load reranker {reranker_model}: {e}")
        
        # RRF parameters from that.txt
        self.rrf_k = 60  # Standard RRF parameter
        self.topk_dense = 80   # Get 80 from dense search
        self.topk_bm25 = 80    # Get 80 from BM25 search
        self.topk_rerank = 12  # Return top 12 after reranking
        
        logger.info("Initialized RTX2070 Hybrid Search Engine")
    
    def build_bm25_index(self, sections: List[Dict[str, Any]]):
        """Build BM25 index from sections using bm25_text field"""
        if not BM25_AVAILABLE:
            logger.error("BM25 not available - cannot build sparse index")
            return
        
        logger.info(f"Building BM25 index from {len(sections)} sections...")
        
        # Extract BM25 texts and create mappings
        self.bm25_texts = []
        self.doc_id_to_bm25_idx = {}
        self.bm25_idx_to_section = {}
        
        for i, section in enumerate(sections):
            # Use bm25_text if available, otherwise fall back to text
            bm25_text = section.get('bm25_text', section.get('text', ''))
            
            if bm25_text and bm25_text.strip():
                # Tokenize for BM25 (simple whitespace splitting)
                tokens = bm25_text.lower().split()
                self.bm25_texts.append(tokens)
                
                # Create mappings
                doc_id = section.get('doc_id', '')
                section_num = section.get('section', '')
                key = f"{doc_id}:{section_num}"
                
                bm25_idx = len(self.bm25_texts) - 1
                self.doc_id_to_bm25_idx[key] = bm25_idx
                self.bm25_idx_to_section[bm25_idx] = section
        
        # Build BM25 index
        if self.bm25_texts:
            self.bm25_index = BM25Okapi(self.bm25_texts)
            logger.info(f"Built BM25 index with {len(self.bm25_texts)} documents")
        else:
            logger.warning("No valid BM25 texts found")
    
    def save_bm25_index(self, path: str):
        """Save BM25 index to disk"""
        if not self.bm25_index:
            logger.warning("No BM25 index to save")
            return
        
        bm25_data = {
            'bm25_texts': self.bm25_texts,
            'doc_id_to_bm25_idx': self.doc_id_to_bm25_idx,
            'bm25_idx_to_section': self.bm25_idx_to_section,
            'bm25_index_state': {
                'doc_freqs': self.bm25_index.doc_freqs,
                'idf': self.bm25_index.idf,
                'doc_len': self.bm25_index.doc_len,
                'avgdl': self.bm25_index.avgdl,
                'k1': self.bm25_index.k1,
                'b': self.bm25_index.b
            }
        }
        
        with open(path, 'wb') as f:
            pickle.dump(bm25_data, f)
        
        logger.info(f"Saved BM25 index to {path}")
    
    def load_bm25_index(self, path: str):
        """Load BM25 index from disk"""
        if not Path(path).exists():
            logger.warning(f"BM25 index file not found: {path}")
            return False
        
        try:
            with open(path, 'rb') as f:
                bm25_data = pickle.load(f)
            
            self.bm25_texts = bm25_data['bm25_texts']
            self.doc_id_to_bm25_idx = bm25_data['doc_id_to_bm25_idx']
            self.bm25_idx_to_section = bm25_data['bm25_idx_to_section']
            
            # Recreate BM25 index
            if self.bm25_texts and BM25_AVAILABLE:
                self.bm25_index = BM25Okapi(self.bm25_texts)
                
                # Restore state if available
                if 'bm25_index_state' in bm25_data:
                    state = bm25_data['bm25_index_state']
                    self.bm25_index.doc_freqs = state['doc_freqs']
                    self.bm25_index.idf = state['idf']
                    self.bm25_index.doc_len = state['doc_len']
                    self.bm25_index.avgdl = state['avgdl']
                    self.bm25_index.k1 = state.get('k1', 1.2)
                    self.bm25_index.b = state.get('b', 0.75)
                
                logger.info(f"Loaded BM25 index with {len(self.bm25_texts)} documents")
                return True
            
        except Exception as e:
            logger.error(f"Error loading BM25 index: {e}")
            return False
        
        return False
    
    def bm25_search(self, query: str, k: int = 80) -> List[Dict[str, Any]]:
        """Perform BM25 sparse search"""
        if not self.bm25_index or not BM25_AVAILABLE:
            logger.warning("BM25 index not available")
            return []
        
        # Tokenize query
        query_tokens = query.lower().split()
        
        # Get BM25 scores
        scores = self.bm25_index.get_scores(query_tokens)
        
        # Get top k indices
        top_indices = np.argsort(scores)[::-1][:k]
        
        results = []
        for idx in top_indices:
            if idx < len(self.bm25_idx_to_section):
                section = self.bm25_idx_to_section[idx].copy()
                section['bm25_score'] = float(scores[idx])
                section['search_type'] = 'bm25'
                results.append(section)
        
        logger.debug(f"BM25 search returned {len(results)} results for query: {query[:50]}...")
        return results
    
    def dense_search(self, query: str, k: int = 80, **filters) -> List[Dict[str, Any]]:
        """Perform dense search using the semantic index"""
        results = self.dense_index.search_text(query, k=k, **filters)
        
        # Add search type marker
        for result in results:
            result['search_type'] = 'dense'
            if 'score' not in result:
                result['dense_score'] = result.get('original_score', 0.0)
        
        logger.debug(f"Dense search returned {len(results)} results for query: {query[:50]}...")
        return results
    
    def reciprocal_rank_fusion(self, dense_results: List[Dict], sparse_results: List[Dict], k: int = 60) -> List[Dict]:
        """
        Apply Reciprocal Rank Fusion to combine dense and sparse results
        Implementation from that.txt analysis
        """
        acc = {}
        
        # Process dense results
        for rank, item in enumerate(dense_results[:k], 1):
            doc_id = item.get('doc_id', '')
            section = item.get('section', '')
            key = f"{doc_id}:{section}"
            
            if key not in acc:
                acc[key] = {'doc': item, 'rrf': 0.0}
            
            acc[key]['rrf'] += 1.0 / (self.rrf_k + rank)
        
        # Process sparse results  
        for rank, item in enumerate(sparse_results[:k], 1):
            doc_id = item.get('doc_id', '')
            section = item.get('section', '')
            key = f"{doc_id}:{section}"
            
            if key not in acc:
                acc[key] = {'doc': item, 'rrf': 0.0}
            
            acc[key]['rrf'] += 1.0 / (self.rrf_k + rank)
        
        # Create fused results
        fused = []
        for key, value in acc.items():
            result = value['doc'].copy()
            result['rrf_score'] = value['rrf']
            result['fusion_key'] = key
            
            # Preserve original scores
            if 'dense_score' not in result and 'score' in result:
                result['dense_score'] = result['score']
            
            fused.append(result)
        
        # Sort by RRF score
        fused.sort(key=lambda x: x['rrf_score'], reverse=True)
        
        logger.debug(f"RRF fusion combined {len(dense_results)} dense + {len(sparse_results)} sparse -> {len(fused)} results")
        return fused
    
    def rerank_results(self, query: str, results: List[Dict[str, Any]], k: int = 12) -> List[Dict[str, Any]]:
        """Apply cross-encoder reranking to top results"""
        if not self.reranker or not results:
            logger.debug("No reranker available or no results to rerank")
            return results[:k]
        
        # Prepare query-document pairs for reranking
        pairs = []
        valid_results = []
        
        for result in results:
            # Use embed_text if available, otherwise text
            doc_text = result.get('embed_text', result.get('text', ''))
            if doc_text and doc_text.strip():
                pairs.append([query, doc_text])
                valid_results.append(result)
        
        if not pairs:
            logger.warning("No valid pairs for reranking")
            return results[:k]
        
        try:
            # Get reranking scores (batch_size=8 for RTX 2070)
            rerank_scores = self.reranker.predict(pairs, batch_size=8)
            
            # Add rerank scores to results
            for result, score in zip(valid_results, rerank_scores):
                result['rerank_score'] = float(score)
            
            # Sort by rerank score
            reranked = sorted(valid_results, key=lambda x: x['rerank_score'], reverse=True)
            
            logger.debug(f"Reranked {len(reranked)} results")
            return reranked[:k]
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return results[:k]
    
    def hybrid_search(self, query: str, k: int = 12, **filters) -> List[Dict[str, Any]]:
        """
        Complete hybrid search pipeline for RTX 2070
        Dense + Sparse + RRF + Reranking
        """
        logger.debug(f"Starting hybrid search for: {query[:50]}...")
        
        # Stage 1: Dense search
        dense_results = self.dense_search(query, k=self.topk_dense, **filters)
        
        # Stage 2: Sparse search  
        sparse_results = self.bm25_search(query, k=self.topk_bm25)
        
        # Stage 3: RRF fusion
        fused_results = self.reciprocal_rank_fusion(dense_results, sparse_results)
        
        # Stage 4: Reranking
        final_results = self.rerank_results(query, fused_results, k=self.topk_rerank)
        
        # Add search metadata
        for i, result in enumerate(final_results):
            result['hybrid_rank'] = i + 1
            result['search_method'] = 'hybrid_rtx2070'
        
        logger.info(f"Hybrid search: {len(dense_results)} dense + {len(sparse_results)} sparse -> {len(fused_results)} fused -> {len(final_results)} final")
        
        return final_results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get hybrid search statistics"""
        stats = {
            'dense_index_available': self.dense_index is not None,
            'bm25_index_available': self.bm25_index is not None,
            'reranker_available': self.reranker is not None,
            'bm25_documents': len(self.bm25_texts) if self.bm25_texts else 0,
            'dense_documents': len(self.dense_index.sections) if self.dense_index else 0,
            'rrf_k': self.rrf_k,
            'topk_settings': {
                'dense': self.topk_dense,
                'bm25': self.topk_bm25,
                'rerank': self.topk_rerank
            }
        }
        
        if self.dense_index:
            dense_stats = self.dense_index.get_stats()
            stats.update({
                'embedding_model': dense_stats.get('model_name', ''),
                'embedding_dim': dense_stats.get('embedding_dimension', 0)
            })
        
        return stats