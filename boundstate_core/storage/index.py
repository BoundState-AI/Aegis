#!/usr/bin/env python3
"""
BoundState AI 2025

Athena Document Intelligence System - Semantic Index Module

Version: 2.0.1
Module: index.py
System: Amentum Athena Document Intelligence Platform
Classification: For Official Use Only (FOUO)
Last Modified: 2025-08-02

Change Log:
- 2.0.3 (2025-10-03): Performance - Disabled TinyDB (duplicates sections.pkl inefficiently)
- 2.0.2 (2025-10-03): Grok Fix - Removed unsafe embed_text pre-chunking bypass
- 2.0.1 (2025-08-02): Fixed AttributeError in add method, improved Q&A deduplication
- 2.0.0 (2025-01-22): Added get_document_versions method for CAG support
- 1.5.0 (2025-01-21): Version-aware deduplication and enhanced metadata
- 1.0.0 (2025-01-20): Initial FAISS implementation with safety compliance

Co-Authored-By: Claude Opus 4.0 <noreply@anthropic.com>
Co-Authored-By: Fran OpenAI o3/4.0/4.5 <noreply@openai.com>
Co-Authored-By: Grok 4.0 <noreply@x.ai>
Co-Authored-By: Dr. Joseph Wilde, BoundState AI

This module provides FAISS-powered semantic search with aerospace compliance.
Supports version-aware document management and rapid similarity search.

NASA/Defense Compliance:
    - SWE-013: Software configuration management
    - SWE-033: Requirements traceability
    - NASA-STD-8739.8B: Software assurance

Author: BoundState Team
Created: 2025
"""

__safety_critical__ = False  # NASA SWE-013: Search indexing is not safety-critical

import os
import json
import pickle
import uuid
import re
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging

import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
# TinyDB - DISABLED (duplicates sections.pkl inefficiently)
# from tinydb import TinyDB, Query
# from tinydb.middlewares import CachingMiddleware
# from tinydb.storages import JSONStorage

from boundstate_core.config.settings import CONFIG
from boundstate_core.config.utils import smart_chunk, hash_text, measure_time, clean_text, compare_versions
from boundstate_core.nlp.semantic_chunker import semantic_chunk
from boundstate_core.ingestion.tagger import tag_sections

logger = logging.getLogger(__name__)

class SemanticIndex:
    """
    FAISS-powered semantic index for document search and retrieval.
    
    Compliance: SWE-013 (Software Configuration Management)
    Compliance: SWE-033 (Requirements Traceability)
    """
    
    def __init__(self, model_name: str = None, db_path: str = None):
        self.model_name = model_name or CONFIG['model_name']
        self.db_path = db_path or CONFIG['db_path']

        # Initialize embedding model with GPU support
        device = CONFIG.get('device', 'cpu')
        logger.info(f"Loading embedding model: {self.model_name} on device: {device}")

        self.model = SentenceTransformer(self.model_name, device=device, trust_remote_code=False)

        # Model-specific: use instruction prefixes
        if 'bge' in self.model_name.lower():
            self.query_prefix = "Represent this sentence for searching relevant passages: "
            self.doc_prefix = ""  # Documents don't need prefix
            logger.info("Using BGE model with query prefix")
        elif 'nomic' in self.model_name.lower():
            self.query_prefix = "search_query: "
            self.doc_prefix = "search_document: "
            logger.info("Using Nomic model with instruction prefixes")
        else:
            self.query_prefix = ""
            self.doc_prefix = ""

        # Log GPU info if available
        if device == 'cuda':
            logger.info(f"Using GPU: {CONFIG.get('gpu_name', 'Unknown')}")

        self.embedding_dim = self.model.get_sentence_embedding_dimension()

        # Initialize FAISS index
        self.index = faiss.IndexFlatIP(self.embedding_dim)  # Inner product for cosine similarity

        # Document storage
        self.sections = []  # List of document sections with metadata
        self.section_hashes = set()  # For deduplication

        # Grok/Fran Optimization: O(1) lookup structures for deduplication
        self._hash_to_idx: Dict[str, int] = {}  # hash → section index
        self._version_map: Dict[Tuple[str, str], Tuple[str, Tuple]] = {}  # (base_doc_id, section) → (doc_id, version_tuple)
        self._since_last_save: int = 0  # Track sections added for save frequency

        # TinyDB for metadata - DISABLED (duplicates sections.pkl inefficiently)
        # db_file = Path(self.db_path) / 'metadata.json'
        # db_file.parent.mkdir(parents=True, exist_ok=True)
        # cache_size = CONFIG.get('tinydb_cache_size', 512)
        # storage_cls = CachingMiddleware(JSONStorage, cache_size=cache_size)
        # self.db = TinyDB(db_file, storage=storage_cls)

        # Persistence controls
        self._autosave_interval = CONFIG.get('index_autosave_interval', 2000)
        self._autosave_seconds = CONFIG.get('index_autosave_seconds', 600)
        self._unsaved_sections = 0
        self._last_save_time = time.time()

        # Load existing index if available
        self._load_index()
        self._unsaved_sections = 0
        self._last_save_time = time.time()

        # Load BM25 index if available (for hybrid search)
        self.bm25_index = None
        self.bm25_tokenizer = None
        self.reranker = None
        self._load_hybrid_components()
    
    def _load_hybrid_components(self):
        """Load BM25 index and reranker for hybrid search."""
        try:
            # Load BM25 index
            bm25_path = Path(self.db_path) / 'bm25.pkl'
            if bm25_path.exists():
                import pickle
                with open(bm25_path, 'rb') as f:
                    self.bm25_index = pickle.load(f)
                # Define consistent tokenizer (matches rebuild script)
                import re
                self.bm25_tokenizer = lambda s: re.findall(r"\w+(?:-\w+)?", (s or "").lower())
                logger.info("Loaded BM25 index for hybrid search")
            else:
                logger.info("No BM25 index found, using dense search only")
            
            # Load reranker (CPU for RTX 2070 VRAM management)
            try:
                from sentence_transformers import CrossEncoder
                self.reranker = CrossEncoder('mixedbread-ai/mxbai-rerank-base-v1', device='cuda')
                logger.info("Loaded CrossEncoder reranker for hybrid search")
            except Exception as e:
                logger.warning(f"Could not load reranker: {e}")
                self.reranker = None
                
        except Exception as e:
            logger.warning(f"Could not load hybrid components: {e}")
            self.bm25_index = None
            self.reranker = None
    
    def _encode_queries(self, queries: List[str]) -> np.ndarray:
        """Encode queries with BGE instruction prefix."""
        prefixed_queries = [self.query_prefix + q for q in queries]
        return self.model.encode(prefixed_queries, batch_size=CONFIG['batch_size'], show_progress_bar=False)
    
    def _encode_documents(self, documents: List[str]) -> np.ndarray:
        """Encode documents with prefix and optimized batch size.

        Grok/Fran Optimization: Uses torch.inference_mode() and env variable override
        """
        import os
        import torch

        # Allow override from environment (useful for load testing)
        bs_conf = int(os.getenv("BS_EMBED_BATCH", "0"))
        if bs_conf > 0:
            batch_size = bs_conf
        else:
            # Use larger batches on GPU for better throughput
            batch_size = 128 if getattr(self.model, "device", None) and self.model.device.type == "cuda" else 32

        prefixed_docs = [self.doc_prefix + d for d in documents]

        # Use inference_mode for GPU optimization (no gradient tracking)
        with torch.inference_mode():
            return self.model.encode(prefixed_docs, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=False)
    
    
    def _load_index(self):
        """Load existing FAISS index and metadata.

        Grok/Fran Optimization: Rebuild hash maps for O(1) lookups
        """
        index_file = Path(self.db_path) / 'faiss.index'
        sections_file = Path(self.db_path) / 'sections.pkl'

        if index_file.exists() and sections_file.exists():
            try:
                self.index = faiss.read_index(str(index_file))

                with open(sections_file, 'rb') as f:
                    self.sections = pickle.load(f)

                # Rebuild hash set AND hash maps for O(1) lookups
                self.section_hashes.clear()
                self._hash_to_idx.clear()
                self._version_map = {}

                for i, sec in enumerate(self.sections):
                    h = hash_text(f"{sec.get('doc_id', '')}:{sec.get('section', '')}:{sec.get('text', '')}")
                    self.section_hashes.add(h)
                    self._hash_to_idx[h] = i

                    # Rebuild version map for fast lookups
                    base_id = sec.get('base_doc_id', '')
                    section_num = sec.get('section', '')
                    if base_id and section_num:
                        key = (base_id, section_num)
                        doc_id = sec.get('doc_id', '')
                        version_tuple = sec.get('version_tuple', (0,))
                        self._version_map[key] = (doc_id, version_tuple)

                logger.info(f"Loaded index with {len(self.sections)} sections")

            except Exception as e:
                logger.warning(f"Could not load existing index: {e}")
                self._reset_index()
        else:
            logger.info("No existing index found, starting fresh")
    
    def _save_index(self):
        """Save FAISS index and metadata to disk."""
        try:
            os.makedirs(self.db_path, exist_ok=True)
            
            index_file = Path(self.db_path) / 'faiss.index'
            sections_file = Path(self.db_path) / 'sections.pkl'
            
            faiss.write_index(self.index, str(index_file))
            
            with open(sections_file, 'wb') as f:
                pickle.dump(self.sections, f)

            logger.info(f"Saved index with {len(self.sections)} sections")
            self._unsaved_sections = 0
            self._last_save_time = time.time()

        except Exception as e:
            logger.error(f"Error saving index: {e}")

    def _should_autosave(self) -> bool:
        if not self._unsaved_sections:
            return False

        if self._autosave_interval and self._unsaved_sections >= self._autosave_interval:
            return True

        if self._autosave_seconds and (time.time() - self._last_save_time) >= self._autosave_seconds:
            return True

        return False

    def flush(self, force: bool = False) -> None:
        """Persist pending FAISS and metadata changes.

        Compliance: SWE-013, SWE-033
        """
        if force or self._unsaved_sections:
            self._save_index()

        # TinyDB flush - DISABLED (duplicates sections.pkl inefficiently)
        # if hasattr(self.db, "storage"):
        #     try:
        #         self.db.storage.flush()
        #     except AttributeError:
        #         pass

    def _reset_index(self):
        """Reset the index to empty state."""
        self.index = faiss.IndexFlatIP(self.embedding_dim)
        self.sections = []
        self.section_hashes = set()
        logger.info("Reset index to empty state")
    
    def _normalize_base_doc_id(self, doc_id: str) -> str:
        """Normalize document ID by removing extension and version."""
        base_id = Path(doc_id).stem
        base_id = re.sub(r'[\s_-]*(v|rev|r)[\s_-]*(\d+[\.\d]*)', '', base_id, flags=re.IGNORECASE).rstrip('_- ')
        return base_id
    
    def _remove_section_at_index(self, idx: int):
        """Remove a section from the index at the given position."""
        if 0 <= idx < len(self.sections):
            removed_section = self.sections.pop(idx)
            text_hash = hash_text(f"{removed_section.get('doc_id', '')}:{removed_section.get('section', '')}:{removed_section.get('text', '')}")
            if text_hash in self.section_hashes:
                self.section_hashes.discard(text_hash)
            doc_id = removed_section.get('doc_id')
            section_num = removed_section.get('section')
            # TinyDB remove - DISABLED (duplicates sections.pkl inefficiently)
            # if doc_id and section_num:
            #     Doc = Query()
            #     self.db.remove((Doc.doc_id == doc_id) & (Doc.section == section_num))
            self._unsaved_sections += 1
    
    @measure_time
    def add(self, sections: List[Dict[str, Any]]) -> int:
        """
        Add document sections to the index.
        
        Compliance: SWE-033 (Requirements Traceability)
        """
        logger.info(f"Adding {len(sections)} sections to index", extra={'req_id': str(uuid.uuid4())})
        
        if not sections:
            return 0
        
        for sec in sections:
            # Add full_text field for counting module
            sec['full_text'] = sec.get('text', '') + ' '.join(t.get('extracted_text', '') for t in sec.get('tables', []))
            base_doc_id = sec.get('base_doc_id', sec.get('doc_id', ''))
            sec['base_doc_id'] = self._normalize_base_doc_id(base_doc_id)
        
        new_sections = []
        new_embeddings = []
        
        for section in sections:
            text = section.get('text', '').strip()
            if not text:
                continue
            
            doc_id = section.get('doc_id', '')
            section_num = section.get('section', '')
            composite_key = f"{doc_id}:{section_num}"
            text_hash = hash_text(composite_key + text)
            
            # Grok/Fran Optimization: O(1) hash lookup instead of O(n) scan
            if text_hash in self.section_hashes:
                # Fast lookup: check if we have this exact hash
                existing_idx = self._hash_to_idx.get(text_hash)
                if existing_idx is not None and existing_idx < len(self.sections):
                    existing_sec = self.sections[existing_idx]
                    if existing_sec and existing_sec.get('base_doc_id') == section.get('base_doc_id'):
                        existing_version = existing_sec.get('version_tuple', (0,))
                        new_version = section.get('version_tuple', (0,))

                        if compare_versions(new_version, existing_version):
                            logger.info(f"Replacing older version {existing_sec.get('version')} with {section.get('version')} for {section.get('base_doc_id')} section {section_num}")
                            # Mark for replacement by setting to None, will compact later
                            self.sections[existing_idx] = None
                            self.section_hashes.discard(text_hash)
                            if text_hash in self._hash_to_idx:
                                del self._hash_to_idx[text_hash]
                        else:
                            logger.debug(f"Skipping older/same version {section.get('version')} for {section.get('base_doc_id')} section {section_num}")
                            continue
                    else:
                        logger.debug(f"Skipping duplicate section {section_num} from {section.get('doc_id', 'unknown')}")
                        continue
            
            has_section_metadata = all([
                section.get('section'),
                section.get('doc_id')
            ])
            
            use_semantic_chunking = CONFIG.get('use_semantic_chunking', True) and not has_section_metadata
            
            if use_semantic_chunking:
                chunks = semantic_chunk(
                    text, 
                    {
                        'doc_id': section.get('doc_id'),
                        'doc_type': section.get('doc_type'),
                        'title': section.get('title'),
                        'tags': section.get('tags', []),
                        'section_number': section.get('section'),
                        'section_title': section.get('title')
                    },
                    max_chunk_size=CONFIG.get('semantic_chunk_size', 800),
                    min_chunk_size=CONFIG.get('semantic_chunk_min', 200)
                )
                
                for i, chunk_data in enumerate(chunks):
                    chunk_text = chunk_data['text']
                    chunk_meta = chunk_data['metadata']
                    
                    if not chunk_text.strip():
                        continue
                    
                    chunk_section = section.copy()
                    chunk_section['text'] = chunk_text
                    chunk_section['chunk_id'] = i
                    chunk_section['total_chunks'] = len(chunks)
                    chunk_section['text_hash'] = text_hash
                    
                    if 'section_number' in chunk_meta:
                        chunk_section['section'] = chunk_meta['section_number']
                    if 'section_title' in chunk_meta:
                        chunk_section['title'] = chunk_meta['section_title']
                    if 'source' in chunk_meta:
                        chunk_section['source'] = chunk_meta.get('source', '')
                    
                    new_sections.append(chunk_section)
                    self.section_hashes.add(text_hash)
            else:
                if has_section_metadata:
                    section['text_hash'] = text_hash
                    section['chunk_id'] = 0
                    section['total_chunks'] = 1
                    new_sections.append(section)
                    self.section_hashes.add(text_hash)
                else:
                    # No reliable section metadata → ALWAYS smart-chunk here
                    chunks = smart_chunk(text, CONFIG['chunk_window'], CONFIG['chunk_stride'])
                    
                    for i, chunk in enumerate(chunks):
                        chunk_text = chunk['text'] if isinstance(chunk, dict) else chunk
                        if not chunk_text.strip():
                            continue
                        
                        chunk_section = section.copy()
                        chunk_section['text'] = chunk_text
                        chunk_section['chunk_id'] = i
                        chunk_section['total_chunks'] = len(chunks)
                        chunk_section['text_hash'] = text_hash
                        
                        new_sections.append(chunk_section)
                        self.section_hashes.add(text_hash)
        
        if not new_sections:
            logger.info("No new sections to add")
            return 0
        
        # Log section processing details
        original_count = len(sections)
        filtered_count = len(new_sections)
        if original_count != filtered_count:
            logger.info(f"Section filtering: {original_count} -> {filtered_count} (deduped/filtered {original_count - filtered_count})")
        
        # Check for empty sections
        empty_sections = [i for i, s in enumerate(new_sections) if not (s.get('embed_text', '').strip() or s.get('text', '').strip())]
        if empty_sections:
            logger.warning(f"Found {len(empty_sections)} empty sections at indices: {empty_sections}")
        
        logger.info(f"Generating embeddings for {len(new_sections)} sections")
        # Grok/Fran Fix: Use chunked text, not embed_text for embedding
        texts = [sec.get('text', '') for sec in new_sections]

        try:
            # Use optimized encoding with torch.inference_mode()
            embeddings = self._encode_documents(texts)
            embeddings = embeddings.astype('float32')

            faiss.normalize_L2(embeddings)
            self.index.add(embeddings)

            # Grok/Fran Optimization: Compact sections list (remove None placeholders from replacements)
            self.sections = [s for s in self.sections if s is not None]

            # Add new sections
            self.sections.extend(new_sections)

            # Grok/Fran Optimization: Complete hash map rebuild to prevent drift
            self.section_hashes.clear()
            self._hash_to_idx.clear()
            self._version_map = {}

            for i, sec in enumerate(self.sections):
                h = hash_text(f"{sec.get('doc_id', '')}:{sec.get('section', '')}:{sec.get('text', '')}")
                self.section_hashes.add(h)
                self._hash_to_idx[h] = i

                # Update version map
                base_id = sec.get('base_doc_id', '')
                section_num = sec.get('section', '')
                if base_id and section_num:
                    key = (base_id, section_num)
                    doc_id = sec.get('doc_id', '')
                    version_tuple = sec.get('version_tuple', (0,))
                    # Keep the newest version in the map
                    existing = self._version_map.get(key)
                    if not existing or compare_versions(version_tuple, existing[1]):
                        self._version_map[key] = (doc_id, version_tuple)

            # TinyDB insert - DISABLED (duplicates sections.pkl inefficiently)
            # if new_sections:
            #     self.db.insert_multiple(new_sections)

            # Grok/Fran Optimization: Save every 20k sections instead of every batch
            self._since_last_save += len(new_sections)
            if self._since_last_save >= CONFIG.get("save_every_sections", 20000):
                self._save_index()
                self._since_last_save = 0

            logger.info(f"Added {len(new_sections)} sections to index")
            return len(new_sections)

        except Exception as e:
            logger.exception(f"Error adding sections to index: {e}")
            return 0
    
    @measure_time
    def search(self, 
               query_embedding: np.ndarray, 
               k: int = 5,
               doc_type: Optional[str] = None,
               tags: Optional[List[str]] = None,
               base_doc_id: Optional[str] = None,
               query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for similar sections using embedding similarity."""
        
        if len(self.sections) == 0:
            logger.warning("No sections in index to search")
            return []
        
        try:
            if query_embedding.ndim == 1:
                query_embedding = query_embedding.reshape(1, -1)
            
            query_embedding = query_embedding.astype('float32')
            faiss.normalize_L2(query_embedding)
            
            search_k = min(k * 3, len(self.sections))
            scores, indices = self.index.search(query_embedding, search_k)
            
            results = []
            seen_doc_sections = set()
            
            if indices.shape[0] == 0 or indices[0][0] == -1:
                logger.warning("FAISS search returned no valid indices")
                return []
            
            for score, idx in zip(scores[0], indices[0]):
                if idx >= len(self.sections) or idx < 0:
                    continue
                
                section = self.sections[idx].copy()
                
                # Weight sections (lower numbers like 1.0 more relevant than higher numbers)
                section_num = section.get('section', '0')
                try:
                    section_first_part = float(str(section_num).split('.')[0]) if section_num else 0
                    # Stronger weighting for section 1.0 (purpose sections)
                    if section_first_part == 1:
                        section_weight = 3.0  # Strong boost for section 1.x
                    elif section_first_part == 2:
                        section_weight = 2.0  # Medium boost for section 2.x  
                    else:
                        section_weight = 1.0 / (section_first_part + 1)
                except (ValueError, ZeroDivisionError):
                    section_weight = 1.0
                
                # Also boost P-series (policy) documents over G-series (guidelines)
                doc_id = section.get('doc_id', '')
                doc_type_boost = 1.0
                if query:
                    if doc_id.startswith('P') and any(term in query.lower() for term in ['tqp', 'policy', 'purpose']):
                        doc_type_boost = 2.0  # Boost policies over training materials
                    elif doc_id.startswith('G') and 'training' in section.get('text', '').lower():
                        doc_type_boost = 0.5  # Reduce training material ranking
                
                weighted_score = float(score) * section_weight * doc_type_boost
                section['score'] = weighted_score
                section['section_weight'] = section_weight
                section['original_score'] = float(score)
                section['matched_text'] = section['text']
                
                if doc_type and section.get('doc_type') != doc_type:
                    continue
                
                if tags and not any(tag in section.get('tags', []) for tag in tags):
                    continue
                
                if base_doc_id and section.get('base_doc_id') != base_doc_id:
                    continue
                
                doc_section_key = f"{section.get('doc_id', '')}-{section.get('section', '')}"
                if doc_section_key in seen_doc_sections:
                    continue
                
                seen_doc_sections.add(doc_section_key)
                results.append(section)
                
                if len(results) >= k:
                    break
            
            return results
            
        except Exception as e:
            logger.error(f"Error during search: {e}")
            return []
    
    def _hybrid_search_with_rerank(self, query: str, candidate_sections: List[Dict], k: int = 5) -> List[Dict[str, Any]]:
        """Perform hybrid dense + BM25 search with reranking."""
        if not self.bm25_index or not candidate_sections:
            # Fallback to dense only
            query_embedding = self._encode_queries([query])
            original_sections = self.sections
            self.sections = candidate_sections
            results = self.search(query_embedding, k, query=query)
            self.sections = original_sections
            return results
        
        # Create section ID mapping for alignment
        id_map = {(sec.get('doc_id'), sec.get('section')): i for i, sec in enumerate(candidate_sections)}
        
        # Dense search
        query_embedding = self._encode_queries([query])
        original_sections = self.sections
        self.sections = candidate_sections
        dense_hits = self.search(query_embedding, min(60, len(candidate_sections)), query=query)
        self.sections = original_sections
        
        # Convert to (index, score) format
        dense_results = []
        for hit in dense_hits:
            key = (hit.get('doc_id'), hit.get('section'))
            idx = id_map.get(key)
            if idx is not None:
                dense_results.append((idx, hit.get('score', 0.0)))
        
        # BM25 sparse search
        query_tokens = self.bm25_tokenizer(query)
        bm25_scores = self.bm25_index.get_scores(query_tokens)
        sparse_results = sorted(enumerate(bm25_scores), key=lambda x: x[1], reverse=True)[:60]
        
        # RRF fusion (from rebuild script)
        def rrf_fusion(dense_results, sparse_results, k_rrf=60):
            ranks = {}
            for rank, (idx, _) in enumerate(dense_results[:60], start=1):
                ranks[idx] = ranks.get(idx, 0) + 1.0/(k_rrf + rank)
            for rank, (idx, _) in enumerate(sparse_results[:60], start=1):
                ranks[idx] = ranks.get(idx, 0) + 1.0/(k_rrf + rank)
            return sorted(ranks.items(), key=lambda x: x[1], reverse=True)
        
        fused_results = rrf_fusion(dense_results, sparse_results)
        
        # Get top candidates for reranking (balanced: 30 for accuracy vs speed)
        rerank_candidates = []
        for idx, _ in fused_results[:min(30, len(fused_results))]:
            if idx < len(candidate_sections):
                rerank_candidates.append(candidate_sections[idx])
        
        if not rerank_candidates or not self.reranker:
            # Return top results without reranking
            return rerank_candidates[:k]
        
        # Rerank with CrossEncoder
        try:
            pairs = [[query, candidate.get('text', '')] for candidate in rerank_candidates]
            rerank_scores = self.reranker.predict(pairs)
            
            # Sort by rerank score and add scores to results
            ranked_results = []
            for candidate, score in zip(rerank_candidates, rerank_scores):
                candidate = candidate.copy()
                candidate['rerank_score'] = float(score)
                candidate['score'] = float(score)  # Use rerank score as final score
                ranked_results.append(candidate)
            
            ranked_results.sort(key=lambda x: x['rerank_score'], reverse=True)
            return ranked_results[:k]
            
        except Exception as e:
            logger.warning(f"Reranking failed: {e}, using fusion results")
            return rerank_candidates[:k]
    
    def search_text(self, query: str, k: int = 5, exclude_docs: Optional[List[str]] = None, **filters) -> List[Dict[str, Any]]:
        """Search using text query with intelligent routing and keyword gating."""
        if not query.strip():
            return []
        
        try:
            # Step 1: Apply first-stage document routing
            try:
                from boundstate_core.retrieval.query_router import route_query
                candidate_sections = route_query(query, self.sections)
                logger.info(f"Document routing: {len(self.sections)} -> {len(candidate_sections)} candidates")
            except ImportError:
                candidate_sections = self.sections
                logger.warning("Query router not available, using all sections")
            
            # Step 2: Enhanced query for embedding search
            try:
                from boundstate_core.nlp.query_enhancer import enhance_search_query
                enhanced_query = enhance_search_query(query)
            except ImportError:
                enhanced_query = query
            
            query_embedding = self._encode_queries([enhanced_query])
            
            # Step 3: Embedding search on filtered candidates
            valid_filters = {}
            if 'doc_type' in filters:
                valid_filters['doc_type'] = filters['doc_type']
            if 'tags' in filters:
                valid_filters['tags'] = filters['tags']
            if 'base_doc_id' in filters:
                valid_filters['base_doc_id'] = filters['base_doc_id']
            
            # Step 3: Hybrid search (dense + BM25 + rerank) or fallback to dense
            search_k = min(k * 4, len(candidate_sections))  # Get more for keyword filtering
            if self.bm25_index and self.reranker:
                logger.info("Using hybrid search (dense + BM25 + rerank)")
                results = self._hybrid_search_with_rerank(enhanced_query, candidate_sections, search_k)
                logger.info(f"Hybrid search returned {len(results)} results")
            else:
                logger.info("Using dense search only (no BM25/reranker)")
                # Fallback to dense search
                original_sections = self.sections
                self.sections = candidate_sections
                results = self.search(query_embedding, search_k, query=query, **valid_filters)
                logger.info(f"Dense search returned {len(results)} results")
                self.sections = original_sections
            
            # Step 4: Apply keyword gate for lexical precision
            logger.info(f"Before keyword gating: {len(results)} results")
            try:
                from boundstate_core.retrieval.keyword_gate import apply_keyword_gate, boost_keyword_matches
                results = apply_keyword_gate(query, results)
                results = boost_keyword_matches(query, results)
                logger.info(f"After keyword gating: {len(results)} results")
            except ImportError:
                logger.warning("Keyword gate not available")
            
            # Step 5: Apply hybrid boosting (multiple signals)
            try:
                from boundstate_core.nlp.query_enhancer import QueryEnhancer
                enhancer = QueryEnhancer()
                results = enhancer.apply_hybrid_boost(query, results)
                logger.info(f"Applied hybrid boosting to {len(results)} results")
            except ImportError:
                logger.warning("Query enhancer hybrid boost not available")
            
            # Take top k after all filtering and boosting
            results = results[:k]
            
            if exclude_docs:
                results = [r for r in results if r.get('doc_id') not in exclude_docs]
            
            return results
        except Exception as e:
            logger.exception(f"Error in search_text for query '{query}': {e}")
            return []
    
    def score_text(self, query: str, document_text: str) -> float:
        """
        Calculate semantic similarity score between query and document text.
        
        Args:
            query: Query text
            document_text: Document text to score against
            
        Returns:
            Similarity score between 0 and 1
            
        Compliance: SWE-033 (Traceability)
        """
        try:
            query_emb = self.model.encode([query], show_progress_bar=False)[0]
            doc_emb = self.model.encode([document_text[:1000]], show_progress_bar=False)[0]
            
            query_emb = query_emb / np.linalg.norm(query_emb)
            doc_emb = doc_emb / np.linalg.norm(doc_emb)
            
            similarity = float(np.dot(query_emb, doc_emb))
            return max(0.0, min(1.0, similarity))
            
        except Exception as e:
            logger.error(f"Error computing similarity score: {e}")
            return 0.0
    
    def get_similar_sections(self, section_text: str, k: int = 5, exclude_doc_id: str = None) -> List[Dict[str, Any]]:
        """Find sections similar to the given text."""
        try:
            query_embedding = self.model.encode([section_text], show_progress_bar=False)
            results = self.search(query_embedding, k + 5)
            
            if exclude_doc_id:
                results = [r for r in results if r.get('doc_id') != exclude_doc_id]
            
            return results[:k]
            
        except Exception as e:
            logger.error(f"Error finding similar sections: {e}")
            return []
    
    def get_document_sections(self, doc_id: str) -> List[Dict[str, Any]]:
        """Get all sections for a specific document."""
        return [sec for sec in self.sections if sec.get('doc_id') == doc_id]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        doc_types = {}
        tags = {}
        doc_ids = set()
        
        for section in self.sections:
            doc_type = section.get('doc_type', 'unknown')
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
            
            for tag in section.get('tags', []):
                tags[tag] = tags.get(tag, 0) + 1
            
            doc_ids.add(section.get('doc_id', 'unknown'))
        
        return {
            'total_sections': len(self.sections),
            'total_documents': len(doc_ids),
            'index_size': self.index.ntotal,
            'embedding_dimension': self.embedding_dim,
            'model_name': self.model_name,
            'doc_types': doc_types,
            'tags': tags
        }
    
    def delete_document(self, doc_id: str) -> int:
        """Remove all sections for a document from the index."""
        sections_to_remove = []
        indices_to_remove = []
        
        for i, section in enumerate(self.sections):
            if section.get('doc_id') == doc_id:
                sections_to_remove.append(section)
                indices_to_remove.append(i)
        
        if not sections_to_remove:
            return 0

        # TinyDB remove - DISABLED (duplicates sections.pkl inefficiently)
        # Doc = Query()
        # self.db.remove(Doc.doc_id == doc_id)

        remaining_sections = [sec for i, sec in enumerate(self.sections) if i not in indices_to_remove]
        
        if remaining_sections:
            self._rebuild_index_from_sections(remaining_sections)
        else:
            self._reset_index()
        
        logger.info(f"Removed {len(sections_to_remove)} sections for document {doc_id}")
        return len(sections_to_remove)
    
    def _rebuild_index_from_sections(self, sections: List[Dict[str, Any]]):
        """Rebuild the entire index from a list of sections.

        Grok/Fran Optimization: Use _encode_documents and rebuild hash maps
        """
        logger.info(f"Rebuilding index with {len(sections)} sections")

        self._reset_index()

        if not sections:
            return

        # Use chunked text for encoding
        texts = [sec.get('text', '') for sec in sections]
        embeddings = self._encode_documents(texts)
        embeddings = embeddings.astype('float32')

        faiss.normalize_L2(embeddings)
        self.index.add(embeddings)

        self.sections = sections

        # Rebuild all hash structures
        self.section_hashes.clear()
        self._hash_to_idx.clear()
        self._version_map = {}

        for i, sec in enumerate(sections):
            h = hash_text(f"{sec.get('doc_id', '')}:{sec.get('section', '')}:{sec['text']}")
            self.section_hashes.add(h)
            self._hash_to_idx[h] = i

            # Rebuild version map
            base_id = sec.get('base_doc_id', '')
            section_num = sec.get('section', '')
            if base_id and section_num:
                key = (base_id, section_num)
                doc_id = sec.get('doc_id', '')
                version_tuple = sec.get('version_tuple', (0,))
                self._version_map[key] = (doc_id, version_tuple)

        self._save_index()

        logger.info("Index rebuild complete")
    
    def optimize_index(self):
        """Optimize the index for better performance."""
        if len(self.sections) < 1000:
            logger.info("Index too small to optimize")
            return
        
        logger.info("Optimizing index...")
        self._rebuild_index_from_sections(self.sections)
        logger.info("Index optimization complete")
    
    def get_document_versions(self, base_doc_id: str) -> List[str]:
        """Get all version IDs for a given base document."""
        versions = []
        normalized_id = self._normalize_base_doc_id(base_doc_id)
        
        doc_ids_seen = set()
        for section in self.sections:
            if section.get('base_doc_id') == normalized_id:
                doc_id = section.get('doc_id')
                if doc_id and doc_id not in doc_ids_seen:
                    doc_ids_seen.add(doc_id)
                    versions.append(doc_id)
        
        versions_with_tuples = []
        for doc_id in versions:
            for section in self.sections:
                if section.get('doc_id') == doc_id:
                    version_tuple = section.get('version_tuple', (0,))
                    versions_with_tuples.append((doc_id, version_tuple))
                    break
        
        versions_with_tuples.sort(key=lambda x: x[1], reverse=True)
        return [doc_id for doc_id, _ in versions_with_tuples]
    
    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get the first section of a document by its ID."""
        for section in self.sections:
            if section.get('doc_id') == doc_id:
                return section.copy()
        return None
    
    def search_with_docid_filter(self, query: str, k: int = 5, doc_id_filter: Optional[str] = None, **kwargs):
        """
        Enhanced search that can filter by document ID.
        
        Args:
            query: Search query
            k: Number of results
            doc_id_filter: Optional document ID to filter results
            **kwargs: Additional filters
        
        Returns:
            List of matching documents
        """
        # If doc_id_filter provided, first try exact match
        if doc_id_filter:
            # Normalize the doc_id for matching
            doc_id_normalized = doc_id_filter.upper().replace('.', '').replace('_', '')
            
            # First pass: get more results than needed
            initial_k = min(k * 10, len(self.sections))  # Get 10x results to filter from, but not more than total
            results = self.search_text(query, k=initial_k, **kwargs)
            
            # Filter for documents matching the doc_id
            filtered_results = []
            for result in results:
                result_doc_id = result.get('doc_id', '').upper()
                # Normalize for comparison - handle variations like W7201.1A_r00_v1.0
                result_normalized = result_doc_id.replace('.', '').replace('_', '').replace('R00', '').replace('R01', '').replace('V10', '').replace('V11', '')
                
                if doc_id_normalized in result_normalized or result_normalized.startswith(doc_id_normalized):
                    filtered_results.append(result)
            
            # If we found matches, return them
            if filtered_results:
                logger.info(f"Found {len(filtered_results)} results for doc_id {doc_id_filter}")
                return filtered_results[:k]
            
            # If no exact matches, fall back to including doc_id in query
            logger.info(f"No exact matches for doc_id {doc_id_filter}, trying enhanced query")
            enhanced_query = f"{doc_id_filter} {query}"
            return self.search_text(enhanced_query, k=k, **kwargs)
        
        # No doc_id filter, use regular search
        return self.search_text(query, k=k, **kwargs)

def create_index(model_name: str = None, db_path: str = None) -> SemanticIndex:
    """Factory function to create a semantic index."""
    return SemanticIndex(model_name, db_path)

# Module-level safety flag
__safety_critical__ = True  # Critical for search integrity
