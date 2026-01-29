#!/usr/bin/env python3
"""
Production Semantic Index with 4096-dimensional NV-Embed-v2
Current #1 on MTEB leaderboard (72.31 overall, 62.65 retrieval)
Compliance: SWE-013, SWE-033, NASA-STD-8739.8B
"""
__safety_critical__ = True

import logging
import time
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import torch
import faiss
from sentence_transformers import SentenceTransformer, CrossEncoder
from transformers import AutoModel, AutoTokenizer
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

class SemanticIndex4096:
    """
    Ultra-high precision semantic index with 4096 dimensions.
    
    Key improvements:
    - 4096 dimensions capture 8x more semantic information than 512d models
    - 32k token context window (vs 512 for most models)
    - Instruction-aware embeddings for task-specific optimization
    - Proven 62.65 NDCG@10 on retrieval (best available)
    
    Compliance: SWE-013 (configuration), SWE-033 (traceability)
    """
    
    def __init__(self, 
                 model_name: str = 'nvidia/NV-Embed-v2',
                 index_path: str = 'index',
                 use_gpu: bool = True,
                 reduce_dims: bool = False):
        """
        Initialize with NV-Embed-v2 4096-dimensional embeddings.
        
        Args:
            model_name: Embedding model (NV-Embed-v2 recommended)
            index_path: Path to index directory
            use_gpu: Use CUDA if available (HIGHLY recommended for 4096d)
            reduce_dims: Optionally reduce to 1536d for speed/memory
            
        Compliance: SWE-047 (safety-critical configuration)
        """
        self.model_name = model_name or CONFIG.get('model_name', 'nvidia/NV-Embed-v2')
        self.index_path = Path(index_path)
        self.dimension = 4096  # Full NV-Embed-v2 dimensions
        self.use_gpu = use_gpu and torch.cuda.is_available()
        self.reduce_dims = reduce_dims
        
        # Device setup
        self.device = torch.device('cuda' if self.use_gpu else 'cpu')
        logger.info(f"Using device: {self.device}")
        
        # Auto-configure based on GPU memory
        self.batch_size = self._get_optimal_batch_size()
        
        # Load NV-Embed-v2 with proper configuration
        logger.info(f"Loading {self.model_name} (4096 dimensions)...")
        
        try:
            # Try SentenceTransformer first (simpler)
            self.model = SentenceTransformer(
                self.model_name,
                trust_remote_code=True,
                device=self.device
            )
            self.use_sentence_transformer = True
            logger.info("Loaded via SentenceTransformer")
        except Exception as e:
            logger.warning(f"SentenceTransformer failed: {e}, trying AutoModel")
            # Fallback to AutoModel approach
            self.model = AutoModel.from_pretrained(
                self.model_name,
                trust_remote_code=True
            ).to(self.device)
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.use_sentence_transformer = False
            logger.info("Loaded via AutoModel")
        
        # Instruction prefixes for NV-Embed-v2 (critical for performance)
        self.query_instruction = "Instruct: Given a question about aerospace documentation, retrieve the relevant passages.\nQuery: "
        self.doc_instruction = ""  # Documents don't need instruction
        
        # Dimension reduction (optional for memory/speed)
        if self.reduce_dims:
            from sklearn.decomposition import PCA
            self.target_dim = 1536  # Still high-dimensional
            self.reducer = PCA(n_components=self.target_dim)
            self.dimension = self.target_dim
            logger.info(f"Will reduce embeddings to {self.target_dim} dimensions")
        
        # Initialize components
        self.index = None
        self.sections = []
        self.reranker = None
        
        # Load existing index if available
        self._load_existing_index()
    
    def _get_optimal_batch_size(self) -> int:
        """Determine optimal batch size based on available GPU memory"""
        if not self.use_gpu:
            return 1
            
        try:
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
            if gpu_memory >= 24:  # A100, A6000
                return 8
            elif gpu_memory >= 16:  # V100, RTX 4080
                return 4  
            elif gpu_memory >= 8:   # RTX 3060, T4
                return 2
            else:
                return 1
        except:
            return 2  # Safe default
    
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
        """Initialize FAISS with optimization for 4096-dimensional vectors"""
        logger.info(f"Initializing FAISS for {self.dimension} dimensions...")
        
        if len(self.sections) < 50000:
            # For smaller corpora, use exact search (best quality)
            self.index = faiss.IndexIDMap(faiss.IndexFlatIP(self.dimension))
            logger.info("Using exact search (IndexFlatIP)")
        else:
            # For larger corpora, use IVF with PQ for efficiency
            nlist = min(1024, int(np.sqrt(len(self.sections))))
            m = min(256, self.dimension // 16)  # Subquantizers
            
            quantizer = faiss.IndexFlatIP(self.dimension)
            self.index = faiss.IndexIVFPQ(
                quantizer, 
                self.dimension,
                nlist,  # Number of clusters
                m,      # Number of subquantizers
                8       # Bits per subquantizer
            )
            logger.info(f"Using IVF-PQ index (nlist={nlist}, m={m})")
    
    def encode_texts(self, 
                    texts: List[str], 
                    is_query: bool = False) -> np.ndarray:
        """
        Encode texts with NV-Embed-v2's 4096 dimensions.
        
        Args:
            texts: List of texts to encode
            is_query: Whether these are queries (apply instruction prefix)
            
        Returns:
            4096-dimensional embeddings (or reduced if configured)
        """
        if not texts:
            return np.array([])
        
        # Add instruction prefix for queries
        if is_query:
            texts = [self.query_instruction + text for text in texts]
        
        if self.use_sentence_transformer:
            # Use SentenceTransformer encode method
            embeddings = self.model.encode(
                texts,
                batch_size=self.batch_size,
                normalize_embeddings=True,
                convert_to_tensor=True,
                device=self.device,
                show_progress_bar=len(texts) > 10
            ).cpu().numpy()
        else:
            # Use manual encoding with AutoModel
            all_embeddings = []
            
            for i in range(0, len(texts), self.batch_size):
                batch_texts = texts[i:i+self.batch_size]
                
                # Tokenize
                inputs = self.tokenizer(
                    batch_texts,
                    padding=True,
                    truncation=True,
                    max_length=32768,  # NV-Embed-v2 supports 32k!
                    return_tensors='pt'
                ).to(self.device)
                
                # Encode
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    
                    # Mean pooling (NV-Embed-v2 uses mean pooling)
                    embeddings = outputs.last_hidden_state.mean(dim=1)
                    
                    # L2 normalize for cosine similarity
                    embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
                    
                    all_embeddings.append(embeddings.cpu().numpy())
                
                # Clear GPU cache periodically
                if self.use_gpu and i % (self.batch_size * 10) == 0:
                    torch.cuda.empty_cache()
                    gc.collect()
            
            # Concatenate all batches
            embeddings = np.vstack(all_embeddings)
        
        # Apply dimension reduction if configured
        if self.reduce_dims:
            if is_query and hasattr(self, 'reducer'):
                # For queries, use transform (don't refit)
                embeddings = self.reducer.transform(embeddings)
            elif not is_query:
                # For documents, fit and transform
                if not hasattr(self, 'reducer'):
                    from sklearn.decomposition import PCA
                    self.reducer = PCA(n_components=self.target_dim)
                embeddings = self.reducer.fit_transform(embeddings)
                logger.info(f"Reduced embeddings from 4096 to {self.target_dim}")
        
        return embeddings
    
    def add_documents(self, documents: List[Dict[str, Any]]):
        """Add documents to the 4096-dimensional index"""
        if not documents:
            return
        
        logger.info(f"Adding {len(documents)} documents to 4096d index...")
        
        # Initialize index if needed
        if self.index is None:
            self._initialize_index()
        
        texts = [doc.get('text', '') for doc in documents]
        
        # Encode documents (no instruction prefix)
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
        Search using 4096-dimensional embeddings with optional reranking.
        """
        if not query.strip() or not self.sections:
            return []
        
        # Encode query with instruction prefix (critical for NV-Embed-v2)
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
                # Try NVIDIA reranker first
                self.reranker = CrossEncoder('nvidia/NV-RerankQA-Mistral-4B-v3')
            except Exception as e:
                logger.warning(f"NVIDIA reranker failed: {e}, trying mixedbread")
                try:
                    self.reranker = CrossEncoder('mixedbread-ai/mxbai-rerank-large-v1')
                except Exception as e2:
                    logger.error(f"All rerankers failed: {e2}")
                    return candidates
        
        # Create query-document pairs
        pairs = [[query, doc['text'][:2000]] for doc in candidates]
        
        # Get reranking scores
        logger.debug("Reranking with cross-encoder...")
        rerank_scores = self.reranker.predict(
            pairs,
            batch_size=4,
            show_progress_bar=False
        )
        
        # Combine scores
        for doc, rerank_score in zip(candidates, rerank_scores):
            doc['rerank_score'] = float(rerank_score)
            
            # Weighted combination (60% rerank, 40% embedding)
            doc['final_score'] = (
                0.6 * rerank_score + 
                0.4 * doc['embedding_score']
            )
        
        # Sort by final score
        candidates.sort(key=lambda x: x['final_score'], reverse=True)
        
        return candidates
    
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
        
        logger.info(f"Index saved to {self.index_path}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        return {
            'model_name': self.model_name,
            'total_sections': len(self.sections),
            'dimension': self.dimension,
            'device': str(self.device),
            'index_type': type(self.index).__name__ if self.index else 'None'
        }