# boundstate/ranking_trace.py
"""
Ranking Trace Logger for Observability
Logs detailed ranking information for debugging and optimization
"""

import logging
from typing import List, Dict, Any, Optional
from boundstate_core.config.settings import CONFIG

logger = logging.getLogger(__name__)
__safety_critical__ = False

def log_ranking_trace(
    query: str,
    dense_results: List[tuple],
    sparse_results: List[tuple], 
    fused_results: List[tuple],
    reranked_results: List[Dict],
    final_results: List[Dict]
):
    """
    Log comprehensive ranking trace for a query.
    
    Args:
        query: The user query
        dense_results: List of (idx, score) from dense search
        sparse_results: List of (idx, score) from BM25 search  
        fused_results: List of (idx, rrf_score) from RRF fusion
        reranked_results: List of dicts with rerank scores
        final_results: List of final ranked results
    """
    if not CONFIG.get('enable_ranking_trace', False):
        return
    
    logger.info(f"RANKING_TRACE | Query: {query[:50]}...")
    
    # Log top dense results
    top_dense = dense_results[:5]
    dense_trace = " | ".join([f"idx={idx},score={score:.3f}" for idx, score in top_dense])
    logger.info(f"RANKING_TRACE | Dense_top5: {dense_trace}")
    
    # Log top sparse results  
    top_sparse = sparse_results[:5]
    sparse_trace = " | ".join([f"idx={idx},score={score:.3f}" for idx, score in top_sparse])
    logger.info(f"RANKING_TRACE | BM25_top5: {sparse_trace}")
    
    # Log top fused results
    top_fused = fused_results[:5]  
    fused_trace = " | ".join([f"idx={idx},rrf={score:.3f}" for idx, score in top_fused])
    logger.info(f"RANKING_TRACE | RRF_top5: {fused_trace}")
    
    # Log reranked results
    if reranked_results:
        rerank_trace = " | ".join([
            f"doc={r.get('doc_id', 'unk')[:8]},rerank={r.get('rerank_score', 0):.3f}" 
            for r in reranked_results[:3]
        ])
        logger.info(f"RANKING_TRACE | Rerank_top3: {rerank_trace}")
    
    # Log final confidence
    if final_results:
        avg_confidence = sum(r.get('score', 0) for r in final_results[:3]) / min(3, len(final_results))
        logger.info(f"RANKING_TRACE | Final_confidence: {avg_confidence:.3f}")

def log_chunk_reason_trace(chunk: Dict[str, Any], **scores):
    """
    Log detailed reason trace for individual chunk.
    
    Args:
        chunk: The chunk data
        **scores: Various score components (dense_score, bm25_rank, rrf, rerank, etc.)
    """
    if not CONFIG.get('enable_ranking_trace', False):
        return
    
    doc_id = chunk.get('doc_id', 'unknown')[:12]
    section = chunk.get('section', 'unknown')
    
    # Build trace components
    trace_parts = []
    for key, value in scores.items():
        if isinstance(value, float):
            trace_parts.append(f"{key}={value:.3f}")
        else:
            trace_parts.append(f"{key}={value}")
    
    trace_string = " | ".join(trace_parts)
    logger.info(f"CHUNK_TRACE | [{doc_id} §{section}] | {trace_string}")

def should_log_confidence(confidence: float) -> bool:
    """Check if confidence meets logging threshold."""
    threshold = CONFIG.get('log_confidence_threshold', 0.7)
    return confidence >= threshold