#!/usr/bin/env python3
"""
Optimized Semantic Index with Nomic-Embed-v1.5 (768d)
Instruction-aware embeddings with excellent compatibility
"""
__safety_critical__ = True

import logging
import time
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import torch
import faiss
from sentence_transformers import SentenceTransformer, CrossEncoder
import gc
import pickle
from pathlib import Path

try:
    from boundstate_core.config.settings import CONFIG
except ImportError:
    # When running directly, use absolute import
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent))
    from config import CONFIG

logger = logging.getLogger(__name__)

class SemanticIndexNomic768:
    """
    High-performance semantic index with Nomic-Embed-v1.5 (768 dimensions).
    
    Key features:
    - 768 dimensions for excellent semantic understanding
    - Instruction-aware embeddings (search_query: / search_document:)
    - 8k token context window
    - Excellent compatibility and reliability
    - Fast inference and low memory usage
    
    Compliance: SWE-013 (configuration), SWE-033 (traceability)
    """
    
    def __init__(self, 
                 model_name: str = 'nomic-ai/nomic-embed-text-v1.5',
                 index_path: str = 'index',
                 use_gpu: bool = True):
        """
        Initialize with Nomic-Embed-v1.5 768-dimensional embeddings.
        
        Args:
            model_name: Embedding model (nomic-embed-text-v1.5 recommended)
            index_path: Path to index directory
            use_gpu: Use CUDA if available
        """
        self.model_name = model_name or CONFIG.get('model_name', 'nomic-ai/nomic-embed-text-v1.5')
        self.index_path = Path(index_path)
        self.dimension = 768  # Nomic-Embed-v1.5 dimensions
        self.use_gpu = use_gpu and torch.cuda.is_available()
        
        # Device setup
        self.device = torch.device('cuda' if self.use_gpu else 'cpu')
        logger.info(f"Using device: {self.device}")
        
        # Optimal batch size for 768d
        self.batch_size = self._get_optimal_batch_size()
        
        # Load Nomic-Embed-v1.5
        logger.info(f"Loading {self.model_name} (768 dimensions)...")
        
        self.model = SentenceTransformer(
            self.model_name,
            trust_remote_code=True,
            device=self.device
        )
        logger.info("Model loaded successfully via SentenceTransformer")
        
        # Instruction prefixes for Nomic (critical for performance)
        self.query_instruction = "search_query: "
        self.doc_instruction = "search_document: "
        
        # Initialize components
        self.index = None
        self.sections = []
        self.reranker = None
        
        # Load existing index if available
        self._load_existing_index()
    
    def _get_optimal_batch_size(self) -> int:
        """Determine optimal batch size for 768d embeddings"""
        if not self.use_gpu:
            return 8
            
        try:
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
            if gpu_memory >= 16:  # High-end GPU
                return 32
            elif gpu_memory >= 8:   # Mid-tier GPU
                return 16  
            else:                   # Entry GPU
                return 8
        except:
            return 16  # Safe default
    
    def _load_existing_index(self):
        """Load existing index files if they exist"""
        sections_file = self.index_path / 'sections.pkl'
        faiss_file = self.index_path / 'faiss.index'
        
        if sections_file.exists() and faiss_file.exists():
            logger.info("Loading existing index...")
            
            # Load sections
            with open(sections_file, 'rb') as f:
                self.sections = pickle.load(f)
            
            # Load FAISS index
            self.index = faiss.read_index(str(faiss_file))
            
            logger.info(f"Loaded index with {len(self.sections)} sections")
        else:
            logger.info("No existing index found, will create new one")
            self._initialize_index()
    
    def _initialize_index(self):
        """Initialize FAISS index optimized for 768 dimensions"""
        logger.info(f"Initializing FAISS for {self.dimension} dimensions...")
        
        # For 768d, we can use exact search for most corpus sizes
        if len(self.sections) < 100000:
            # Exact search with inner product (for normalized vectors)
            self.index = faiss.IndexIDMap(faiss.IndexFlatIP(self.dimension))
            logger.info("Using exact search (IndexFlatIP)")
        else:
            # For very large corpora, use IVF for speed
            nlist = min(4096, int(np.sqrt(len(self.sections))))
            quantizer = faiss.IndexFlatIP(self.dimension)
            self.index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist)
            logger.info(f"Using IVF index (nlist={nlist})")
    
    def encode_texts(self, 
                    texts: List[str], 
                    is_query: bool = False) -> np.ndarray:
        """
        Encode texts with Nomic's instruction-aware embeddings.
        
        Args:
            texts: List of texts to encode
            is_query: Whether these are queries (apply search_query: prefix)
            
        Returns:
            768-dimensional embeddings
        """
        if not texts:
            return np.array([])
        
        # Add instruction prefixes (critical for Nomic performance)
        if is_query:
            texts = [self.query_instruction + text for text in texts]
        else:
            texts = [self.doc_instruction + text for text in texts]
        
        # Encode using SentenceTransformer
        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,  # Critical for cosine similarity
            convert_to_tensor=True,
            device=self.device,
            show_progress_bar=len(texts) > 50
        ).cpu().numpy()
        
        return embeddings
    
    def add_documents(self, documents: List[Dict[str, Any]]):
        """Add documents to the 768-dimensional index"""
        if not documents:
            return
        
        logger.info(f"Adding {len(documents)} documents to Nomic 768d index...")
        
        # Initialize index if needed
        if self.index is None:
            self._initialize_index()
        
        texts = [doc.get('text', '') for doc in documents]
        
        # Encode documents with search_document: prefix
        embeddings = self.encode_texts(texts, is_query=False)
        
        # If using IVF index, train it first
        if hasattr(self.index, 'is_trained') and not self.index.is_trained:
            logger.info("Training IVF index...")
            self.index.train(embeddings)
        
        # Add to index
        start_id = len(self.sections)
        ids = np.arange(start_id, start_id + len(documents))
        self.index.add_with_ids(embeddings, ids)
        
        # Store sections
        self.sections.extend(documents)
        
        logger.info(f"Added {len(documents)} documents (total: {len(self.sections)})")
    
    def search_text(self,
                   query: str,
                   k: int = 10,
                   use_reranking: bool = False,
                   expansion_factor: int = 3) -> List[Dict[str, Any]]:
        """
        Search using Nomic's 768-dimensional embeddings with optional reranking.
        """
        if not query.strip() or not self.sections:
            return []
        
        # Encode query with search_query: prefix (critical for Nomic)
        query_embedding = self.encode_texts([query], is_query=True)
        if query_embedding.size == 0:
            return []
        
        # Search more candidates for reranking
        num_candidates = min(k * expansion_factor, len(self.sections))
        
        # Configure search parameters for IVF index
        if hasattr(self.index, 'nprobe'):
            self.index.nprobe = min(64, self.index.nlist // 2)
        
        # Search
        distances, indices = self.index.search(
            query_embedding.reshape(1, -1), 
            num_candidates
        )
        
        # Build candidate list
        candidates = []
        for idx, score in zip(indices[0], distances[0]):
            if idx == -1 or idx >= len(self.sections):
                continue
                
            doc = self.sections[idx].copy()
            doc['embedding_score'] = float(score)
            doc['rank'] = len(candidates) + 1
            candidates.append(doc)
        
        logger.debug(f"Retrieved {len(candidates)} candidates for: {query[:50]}")
        
        # Apply reranking for precision
        if use_reranking and candidates:
            candidates = self._rerank_candidates(query, candidates)
        
        return candidates[:k]
    
    def _rerank_candidates(self, query: str, candidates: List[Dict]) -> List[Dict]:
        """Apply cross-encoder reranking for precision"""
        if self.reranker is None:
            try:
                logger.info("Loading reranker...")
                # Use mixedbread reranker (very good and compatible)
                self.reranker = CrossEncoder('mixedbread-ai/mxbai-rerank-base-v1')
            except Exception as e:
                logger.error(f"Reranker loading failed: {e}")
                return candidates
        
        # Create query-document pairs
        pairs = [[query, doc['text'][:1000]] for doc in candidates]
        
        # Get reranking scores
        logger.debug("Reranking with cross-encoder...")
        rerank_scores = self.reranker.predict(
            pairs,
            batch_size=8,
            show_progress_bar=False
        )
        
        # Combine scores
        for doc, rerank_score in zip(candidates, rerank_scores):
            doc['rerank_score'] = float(rerank_score)
            
            # Weighted combination (70% rerank, 30% embedding for Nomic)
            doc['final_score'] = (
                0.7 * rerank_score + 
                0.3 * doc['embedding_score']
            )
        
        # Sort by final score
        candidates.sort(key=lambda x: x['final_score'], reverse=True)
        
        return candidates
    
    def score_similarity(self, text1: str, text2: str) -> float:
        """Score similarity between two texts using Nomic embeddings"""
        embeddings = self.encode_texts([text1, text2], is_query=False)
        similarity = np.dot(embeddings[0], embeddings[1])
        return float(similarity)
    
    def diagnose_retrieval(self, query: str, expected_doc_id: str):
        """Diagnose why a specific document isn't being retrieved"""
        # Find the expected document
        expected_sections = [
            s for s in self.sections 
            if s.get('doc_id') == expected_doc_id
        ]
        
        if not expected_sections:
            return f"Document {expected_doc_id} not found in index"
        
        # Get query embedding
        query_emb = self.encode_texts([query], is_query=True)[0]
        
        # Score against expected document
        doc_text = expected_sections[0]['text']
        doc_emb = self.encode_texts([doc_text], is_query=False)[0]
        
        expected_score = np.dot(query_emb, doc_emb)
        
        # Get actual search results
        results = self.search_text(query, k=20, use_reranking=False)
        
        # Find rank of expected document
        expected_rank = None
        for i, result in enumerate(results):
            if result.get('doc_id') == expected_doc_id:
                expected_rank = i + 1
                break
        
        diagnosis = {
            'query': query,
            'expected_doc_id': expected_doc_id,
            'expected_score': float(expected_score),
            'expected_rank': expected_rank or 'Not in top 20',
            'model': 'nomic-ai/nomic-embed-text-v1.5',
            'dimensions': 768,
            'top_5_results': [
                {
                    'doc_id': r.get('doc_id'),
                    'score': r.get('embedding_score'),
                    'text_preview': r.get('text', '')[:100]
                }
                for r in results[:5]
            ]
        }
        
        return diagnosis
    
    def save_index(self):
        """Save index to disk"""
        self.index_path.mkdir(parents=True, exist_ok=True)
        
        # Save sections
        sections_file = self.index_path / 'sections.pkl'
        with open(sections_file, 'wb') as f:
            pickle.dump(self.sections, f)
        
        # Save FAISS index
        faiss_file = self.index_path / 'faiss.index'
        faiss.write_index(self.index, str(faiss_file))
        
        # Save metadata
        metadata_file = self.index_path / 'metadata.json'
        metadata = {
            'model_name': self.model_name,
            'dimension': self.dimension,
            'total_sections': len(self.sections),
            'index_type': type(self.index).__name__
        }
        
        import json
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Nomic 768d index saved to {self.index_path}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        return {
            'model_name': self.model_name,
            'total_sections': len(self.sections),
            'dimension': self.dimension,
            'device': str(self.device),
            'index_type': type(self.index).__name__ if self.index else 'None',
            'batch_size': self.batch_size,
            'instruction_aware': True
        }