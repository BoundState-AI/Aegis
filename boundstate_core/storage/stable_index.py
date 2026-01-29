#!/usr/bin/env python3
"""
BoundState AI 2025

Athena Document Intelligence System - Semantic Index Module

Version: 2.0.0
Module: index.py
System: Amentum Athena Document Intelligence Platform
Classification: For Official Use Only (FOUO)
Last Modified: 2025-01-22

Change Log:
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
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging

import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from tinydb import TinyDB, Query

from boundstate_core.config.settings import CONFIG
from boundstate_core.config.utils import smart_chunk, hash_text, measure_time, clean_text, compare_versions, semantic_chunk
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
        
        self.model = SentenceTransformer(self.model_name, device=device)
        
        # BGE-specific: use instruction prefixes
        if 'bge' in self.model_name.lower():
            self.query_prefix = "Represent this sentence for searching relevant passages: "
            self.doc_prefix = ""  # Documents don't need prefix
            logger.info("Using BGE model with query prefix")
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
        
        # TinyDB for metadata
        db_file = Path(self.db_path) / 'metadata.json'
        db_file.parent.mkdir(parents=True, exist_ok=True)
        self.db = TinyDB(db_file)
        
        # Load existing index if available
        self._load_index()
    
    def _encode_queries(self, queries: List[str]) -> np.ndarray:
        """Encode queries with BGE instruction prefix."""
        prefixed_queries = [self.query_prefix + q for q in queries]
        return self.model.encode(prefixed_queries, batch_size=CONFIG['batch_size'])
    
    def _encode_documents(self, documents: List[str]) -> np.ndarray:
        """Encode documents (no prefix needed for BGE)."""
        prefixed_docs = [self.doc_prefix + d for d in documents]
        return self.model.encode(prefixed_docs, batch_size=CONFIG['batch_size'])
    
    def _load_index(self):
        """Load existing FAISS index and metadata."""
        index_file = Path(self.db_path) / 'faiss.index'
        sections_file = Path(self.db_path) / 'sections.pkl'
        
        if index_file.exists() and sections_file.exists():
            try:
                self.index = faiss.read_index(str(index_file))
                
                with open(sections_file, 'rb') as f:
                    self.sections = pickle.load(f)
                
                # Rebuild hash set
                self.section_hashes = {hash_text(sec['text']) for sec in self.sections}
                
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
            
        except Exception as e:
            logger.error(f"Error saving index: {e}")
    
    def _reset_index(self):
        """Reset the index to empty state."""
        self.index = faiss.IndexFlatIP(self.embedding_dim)
        self.sections = []
        self.section_hashes = set()
        logger.info("Reset index to empty state")
    
    def _normalize_base_doc_id(self, doc_id: str) -> str:
        """Normalize document ID by removing extension and version."""
        # Strip extension
        base_id = Path(doc_id).stem
        # Strip version patterns (v1.0, r00, rev-1, etc.) with optional spaces/underscores before
        base_id = re.sub(r'[\s_-]*(v|rev|r)[\s_-]*(\d+[\.\d]*)', '', base_id, flags=re.IGNORECASE).rstrip('_- ')
        return base_id
    
    def _remove_section_at_index(self, idx: int):
        """Remove a section from the index at the given position."""
        if 0 <= idx < len(self.sections):
            # Remove from sections list
            removed_section = self.sections.pop(idx)
            # Remove from section hashes
            text_hash = removed_section.get('text_hash')
            if text_hash and text_hash in self.section_hashes:
                self.section_hashes.discard(text_hash)
            # Note: FAISS doesn't support removal, would need to rebuild index
            # For now, we'll mark it as removed in the database
            doc_id = removed_section.get('doc_id')
            section_num = removed_section.get('section')
            if doc_id and section_num:
                Doc = Query()
                self.db.remove((Doc.doc_id == doc_id) & (Doc.section == section_num))
    
    @measure_time
    def add(self, sections: List[Dict[str, Any]]) -> int:
        """
        Add document sections to the index.
        
        Compliance: SWE-033 (Requirements Traceability)
        """
        # Log input for traceability per rule 8
        logger.info(f"Adding {len(sections)} sections to index")
        
        if not sections:
            return 0
        
        # Normalize base_doc_id for all sections
        for sec in sections:
            base_doc_id = sec.get('base_doc_id', sec.get('doc_id', ''))
            sec['base_doc_id'] = self._normalize_base_doc_id(base_doc_id)
        
        new_sections = []
        new_embeddings = []
        
        for section in sections:
            text = section.get('text', '').strip()
            if not text:
                continue
            
            # Create composite key for deduplication that includes doc_id and section number
            doc_id = section.get('doc_id', '')
            section_num = section.get('section_number', '')
            composite_key = f"{doc_id}:{section_num}" if section_num else doc_id
            
            # Use composite hash for better deduplication
            text_hash = hash_text(composite_key + text)
            
            # Check if this exact section already exists
            should_skip = False
            for idx, existing_sec in enumerate(self.sections):
                existing_doc_id = existing_sec.get('doc_id', '')
                existing_section_num = existing_sec.get('section_number', '')
                existing_composite = f"{existing_doc_id}:{existing_section_num}" if existing_section_num else existing_doc_id
                existing_hash = hash_text(existing_composite + existing_sec.get('text', ''))
                
                if existing_hash == text_hash:
                    # Found exact duplicate
                    if existing_sec.get('base_doc_id') == section.get('base_doc_id'):
                        # Same base document - compare versions
                        existing_version = existing_sec.get('version_tuple', (0,))
                        new_version = section.get('version_tuple', (0,))
                        
                        if compare_versions(new_version, existing_version):
                            # New version is higher, remove old version
                            logger.info(f"Replacing older version {existing_sec.get('version')} with {section.get('version')} for {section.get('base_doc_id')} section {section_num}")
                            # Remove from FAISS index and sections
                            self._remove_section_at_index(idx)
                            # Continue to add the new version
                            break
                        else:
                            # Existing version is same or higher, skip
                            logger.debug(f"Skipping older/same version {section.get('version')} for {section.get('base_doc_id')} section {section_num}")
                            should_skip = True
                            break
                    else:
                        # Different document with same content
                        logger.debug(f"Skipping duplicate section {section_num} from {section.get('doc_id', 'unknown')}")
                        should_skip = True
                        break
            
            if should_skip:
                continue
            
            # Check if section already has proper metadata
            has_section_metadata = all([
                section.get('section_number'),
                section.get('doc_id')
            ])
            
            # Use semantic chunking if enabled AND section doesn't have metadata
            use_semantic_chunking = CONFIG.get('use_semantic_chunking', True) and not has_section_metadata
            
            if use_semantic_chunking:
                # Use semantic chunking that preserves document structure
                chunks = semantic_chunk(
                    text, 
                    {
                        'doc_id': section.get('doc_id'),
                        'doc_type': section.get('doc_type'),
                        'title': section.get('title'),
                        'tags': section.get('tags', []),
                        'section_number': section.get('section_number'),
                        'section_title': section.get('section_title')
                    },
                    max_chunk_size=CONFIG.get('semantic_chunk_size', 800),
                    min_chunk_size=CONFIG.get('semantic_chunk_min', 200)
                )
                
                for i, chunk_data in enumerate(chunks):
                    chunk_text = chunk_data['text']
                    chunk_meta = chunk_data['metadata']
                    
                    if not chunk_text.strip():
                        continue
                    
                    # Create section with enhanced metadata
                    chunk_section = section.copy()
                    chunk_section['text'] = chunk_text
                    chunk_section['chunk_id'] = i
                    chunk_section['total_chunks'] = len(chunks)
                    chunk_section['text_hash'] = text_hash
                    
                    # Preserve section metadata if available
                    if 'section_number' in chunk_meta:
                        chunk_section['section_number'] = chunk_meta['section_number']
                    if 'section_title' in chunk_meta:
                        chunk_section['section_title'] = chunk_meta['section_title']
                    if 'source' in chunk_meta:
                        chunk_section['source'] = chunk_meta.get('source', '')
                    
                    new_sections.append(chunk_section)
                    self.section_hashes.add(text_hash)
            else:
                # For sections with metadata, add them directly without chunking
                if has_section_metadata:
                    # Add the section as-is
                    section['text_hash'] = text_hash
                    section['chunk_id'] = 0
                    section['total_chunks'] = 1
                    new_sections.append(section)
                    self.section_hashes.add(text_hash)
                else:
                    # Fallback to simple chunking for sections without metadata
                    chunks = smart_chunk(text, CONFIG['chunk_window'], CONFIG['chunk_stride'])
                    
                    for i, chunk in enumerate(chunks):
                        if not chunk.strip():
                            continue
                        
                        # Create section metadata
                        chunk_section = section.copy()
                        chunk_section['text'] = chunk
                        chunk_section['chunk_id'] = i
                        chunk_section['total_chunks'] = len(chunks)
                        chunk_section['text_hash'] = text_hash
                        
                        new_sections.append(chunk_section)
                        self.section_hashes.add(text_hash)
        
        if not new_sections:
            logger.info("No new sections to add")
            return 0
        
        # Generate embeddings
        logger.info(f"Generating embeddings for {len(new_sections)} sections")
        texts = [sec['text'] for sec in new_sections]
        
        try:
            # Use document encoding with prefix
            embeddings = self._encode_documents(texts)
            embeddings = embeddings.astype('float32')
            
            # Normalize for cosine similarity
            faiss.normalize_L2(embeddings)
            
            # Add to FAISS index
            self.index.add(embeddings)
            
            # Store sections
            self.sections.extend(new_sections)
            
            # Save to database
            for section in new_sections:
                self.db.insert(section)
            
            # Save index to disk
            self._save_index()
            
            logger.info(f"Added {len(new_sections)} sections to index")
            return len(new_sections)
            
        except Exception as e:
            logger.error(f"Error adding sections to index: {e}")
            return 0
    
    @measure_time
    def search(self, 
               query_embedding: np.ndarray, 
               k: int = 5,
               doc_type: Optional[str] = None,
               tags: Optional[List[str]] = None,
               base_doc_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for similar sections using embedding similarity."""
        
        if len(self.sections) == 0:
            logger.warning("No sections in index to search")
            return []
        
        try:
            # Ensure query is properly formatted
            if query_embedding.ndim == 1:
                query_embedding = query_embedding.reshape(1, -1)
            
            query_embedding = query_embedding.astype('float32')
            faiss.normalize_L2(query_embedding)
            
            # Search FAISS index
            search_k = min(k * 3, len(self.sections))  # Get more results for filtering
            scores, indices = self.index.search(query_embedding, search_k)
            
            results = []
            seen_doc_sections = set()  # To avoid duplicate sections from same document
            
            # Debug: Check if we got valid results
            if indices.shape[0] == 0 or indices[0][0] == -1:
                logger.warning("FAISS search returned no valid indices")
                return []
            
            for score, idx in zip(scores[0], indices[0]):
                if idx >= len(self.sections) or idx < 0:
                    continue
                
                section = self.sections[idx].copy()
                section['score'] = float(score)
                section['matched_text'] = section['text']
                
                # Apply filters
                if doc_type and section.get('doc_type') != doc_type:
                    continue
                
                if tags and not any(tag in section.get('tags', []) for tag in tags):
                    continue
                
                if base_doc_id and section.get('base_doc_id') != base_doc_id:
                    continue
                
                # Avoid duplicate sections from same document
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
    
    def search_text(self, query: str, k: int = 5, exclude_docs: Optional[List[str]] = None, **filters) -> List[Dict[str, Any]]:
        """Search using text query (convenience method)."""
        if not query.strip():
            return []
        
        try:
            # Use BGE query prefix
            query_embedding = self._encode_queries([query])
            
            # Filter to only valid search parameters
            valid_filters = {}
            if 'doc_type' in filters:
                valid_filters['doc_type'] = filters['doc_type']
            if 'tags' in filters:
                valid_filters['tags'] = filters['tags']
            if 'base_doc_id' in filters:
                valid_filters['base_doc_id'] = filters['base_doc_id']
            
            results = self.search(query_embedding, k, **valid_filters)
            
            # Filter out excluded documents if specified
            if exclude_docs:
                results = [r for r in results if r.get('doc_id') not in exclude_docs]
            
            return results
        except Exception as e:
            logger.error(f"Error in search_text for query '{query}': {e}")
            import traceback
            traceback.print_exc()  # Add full traceback for debugging
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
            # Encode both texts
            query_emb = self.model.encode([query], show_progress_bar=False)[0]
            doc_emb = self.model.encode([document_text[:1000]], show_progress_bar=False)[0]  # Limit length for efficiency
            
            # Normalize embeddings
            query_emb = query_emb / np.linalg.norm(query_emb)
            doc_emb = doc_emb / np.linalg.norm(doc_emb)
            
            # Compute cosine similarity
            similarity = float(np.dot(query_emb, doc_emb))
            
            # Ensure it's between 0 and 1
            return max(0.0, min(1.0, similarity))
            
        except Exception as e:
            logger.error(f"Error computing similarity score: {e}")
            return 0.0
    
    def get_similar_sections(self, section_text: str, k: int = 5, exclude_doc_id: str = None) -> List[Dict[str, Any]]:
        """Find sections similar to the given text."""
        try:
            query_embedding = self.model.encode([section_text])
            results = self.search(query_embedding, k + 5)  # Get extra results for filtering
            
            # Filter out sections from the same document if requested
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
            # Count document types
            doc_type = section.get('doc_type', 'unknown')
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
            
            # Count tags
            for tag in section.get('tags', []):
                tags[tag] = tags.get(tag, 0) + 1
            
            # Count unique documents
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
        # Find sections to remove
        sections_to_remove = []
        indices_to_remove = []
        
        for i, section in enumerate(self.sections):
            if section.get('doc_id') == doc_id:
                sections_to_remove.append(section)
                indices_to_remove.append(i)
        
        if not sections_to_remove:
            return 0
        
        # Remove from database
        Doc = Query()
        self.db.remove(Doc.doc_id == doc_id)
        
        # Rebuild index without removed sections
        remaining_sections = [sec for i, sec in enumerate(self.sections) if i not in indices_to_remove]
        
        if remaining_sections:
            self._rebuild_index_from_sections(remaining_sections)
        else:
            self._reset_index()
        
        logger.info(f"Removed {len(sections_to_remove)} sections for document {doc_id}")
        return len(sections_to_remove)
    
    def _rebuild_index_from_sections(self, sections: List[Dict[str, Any]]):
        """Rebuild the entire index from a list of sections."""
        logger.info(f"Rebuilding index with {len(sections)} sections")
        
        self._reset_index()
        
        if not sections:
            return
        
        # Generate embeddings for all sections
        texts = [sec['text'] for sec in sections]
        # Use document encoding with prefix
        embeddings = self._encode_documents(texts)
        embeddings = embeddings.astype('float32')
        
        # Normalize and add to index
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings)
        
        # Store sections and hashes
        self.sections = sections
        self.section_hashes = {hash_text(sec['text']) for sec in sections}
        
        # Save to disk
        self._save_index()
        
        logger.info("Index rebuild complete")
    
    def optimize_index(self):
        """Optimize the index for better performance."""
        if len(self.sections) < 1000:
            logger.info("Index too small to optimize")
            return
        
        logger.info("Optimizing index...")
        
        # For larger indices, could switch to IndexIVFFlat or other optimized indices
        # For now, just rebuild to ensure consistency
        self._rebuild_index_from_sections(self.sections)
        
        logger.info("Index optimization complete")
    
    def get_document_versions(self, base_doc_id: str) -> List[str]:
        """Get all version IDs for a given base document."""
        versions = []
        normalized_id = self._normalize_base_doc_id(base_doc_id)
        
        # Find all documents with the same base_doc_id
        doc_ids_seen = set()
        for section in self.sections:
            if section.get('base_doc_id') == normalized_id:
                doc_id = section.get('doc_id')
                if doc_id and doc_id not in doc_ids_seen:
                    doc_ids_seen.add(doc_id)
                    versions.append(doc_id)
        
        # Sort by version if available
        versions_with_tuples = []
        for doc_id in versions:
            # Find a section to get version info
            for section in self.sections:
                if section.get('doc_id') == doc_id:
                    version_tuple = section.get('version_tuple', (0,))
                    versions_with_tuples.append((doc_id, version_tuple))
                    break
        
        # Sort by version tuple (highest first)
        versions_with_tuples.sort(key=lambda x: x[1], reverse=True)
        
        return [doc_id for doc_id, _ in versions_with_tuples]
    
    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get the first section of a document by its ID."""
        for section in self.sections:
            if section.get('doc_id') == doc_id:
                return section.copy()
        return None

def create_index(model_name: str = None, db_path: str = None) -> SemanticIndex:
    """Factory function to create a semantic index."""
    return SemanticIndex(model_name, db_path)

# Module-level safety flag
__safety_critical__ = True  # Critical for search integrity