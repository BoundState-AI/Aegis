#!/usr/bin/env python3
"""
RTX 2070 Optimized Chunker - Token-based chunking for better document context
Based on Fran's analysis - 420 tokens vs 80 characters for massive improvement
"""

import re
import uuid
from typing import List, Dict, Any
import logging
from transformers import AutoTokenizer

logger = logging.getLogger(__name__)

class RTX2070OptimizedChunker:
    """
    Token-based chunker optimized for RTX 2070 + Nomic embeddings
    - Uses 420 tokens per chunk (vs 80 chars)
    - Adds embed_text field with titles
    - Preserves document structure
    """
    
    def __init__(self, model_name: str = 'nomic-ai/nomic-embed-text-v1.5'):
        # Load tokenizer for accurate token counting
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        except Exception as e:
            logger.warning(f"Could not load tokenizer for {model_name}: {e}")
            # Fallback to rough estimation
            self.tokenizer = None
        
        # Optimized settings based on that.txt analysis
        self.chunk_size_tokens = 420  # Sweet spot for context vs performance
        self.overlap_tokens = 60      # Good overlap for coherence
        self.max_seq_length = 8192    # Nomic can handle this
        
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text using actual tokenizer"""
        if self.tokenizer:
            try:
                return len(self.tokenizer.encode(text, add_special_tokens=False))
            except:
                pass
        
        # Fallback: rough estimation (1 token ≈ 4 chars)
        return len(text) // 4
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences for better chunk boundaries"""
        # Enhanced sentence splitting pattern
        sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])'
        sentences = re.split(sentence_pattern, text.strip())
        return [s.strip() for s in sentences if s.strip()]
    
    def _create_embed_text(self, title: str, content: str, tables: List[Dict] = None) -> str:
        """
        Create optimized embed_text field as per Fran's recommendation
        Format: title + "\n" + body + flattened tables
        """
        parts = []
        
        # Add title if available
        if title and title.strip():
            parts.append(title.strip())
        
        # Add main content
        if content and content.strip():
            parts.append(content.strip())
        
        # Add flattened table content for better search
        if tables:
            for table in tables:
                if isinstance(table, dict):
                    # Extract table text or key-value pairs
                    table_text = table.get('extracted_text', '')
                    if table_text:
                        # Clean table text and add as searchable content
                        cleaned_table = re.sub(r'\s+', ' ', table_text).strip()
                        if cleaned_table:
                            parts.append(f"Table: {cleaned_table}")
        
        return "\n".join(parts)
    
    def _create_bm25_text(self, title: str, content: str, tables: List[Dict] = None) -> str:
        """
        Create BM25-optimized text for hybrid search
        Includes flattened key:value pairs from tables
        """
        parts = []
        
        if title and title.strip():
            parts.append(title.strip())
        
        if content and content.strip():
            parts.append(content.strip())
        
        # Add structured table content for BM25
        if tables:
            for table in tables:
                if isinstance(table, dict):
                    table_text = table.get('extracted_text', '')
                    if table_text:
                        # Create key:value pairs for better BM25 matching
                        lines = table_text.split('\n')
                        for line in lines:
                            line = line.strip()
                            if ':' in line:
                                # Already key:value format
                                parts.append(line)
                            elif line:
                                # Add as regular content
                                parts.append(line)
        
        return " ".join(parts)
    
    def chunk_with_tokens(self, text: str, metadata: Dict[str, Any], doc_type: str) -> List[Dict[str, Any]]:
        """
        Optimized token-based chunking for RTX 2070
        Main improvement: 420 tokens vs 80 characters
        """
        chunks = []

        if not text or not text.strip():
            return chunks

        # Check if text is too large for processing
        total_tokens = self._count_tokens(text)
        if total_tokens > self.max_seq_length:
            logger.warning(f"Text too large ({total_tokens} tokens > {self.max_seq_length}), truncating to first {self.max_seq_length} tokens")
            # Truncate to max length to prevent model errors
            if self.tokenizer:
                try:
                    tokens = self.tokenizer.encode(text, add_special_tokens=False)[:self.max_seq_length]
                    text = self.tokenizer.decode(tokens)
                except:
                    # Fallback: rough character truncation
                    text = text[:self.max_seq_length * 4]
            else:
                text = text[:self.max_seq_length * 4]
        
        # Get title from metadata
        title = metadata.get('title', '')
        if not title:
            title = metadata.get('filename', '').replace('.pdf', '').replace('.docx', '')
        
        # Handle structured documents (forms, policies) differently
        if doc_type in ['form', 'hr_policy']:
            return self._chunk_structured_document(text, metadata, doc_type, title)
        
        # For general documents, use token-based chunking
        sentences = self._split_into_sentences(text)
        current_chunk = []
        current_tokens = 0
        section_num = 1
        
        for sentence in sentences:
            sentence_tokens = self._count_tokens(sentence)
            
            # Check if adding this sentence would exceed chunk size
            if current_tokens + sentence_tokens > self.chunk_size_tokens and current_chunk:
                # Create chunk from current content
                chunk_text = ' '.join(current_chunk)
                
                # Create the chunk with optimized fields
                doc_id = metadata.get('doc_id', f"{metadata['filename']}_{uuid.uuid4().hex[:8]}")
                
                chunk = {
                    'text': chunk_text,  # Original text field
                    'embed_text': self._create_embed_text(title, chunk_text, metadata.get('tables')),  # For embeddings
                    'bm25_text': self._create_bm25_text(title, chunk_text, metadata.get('tables')),    # For BM25
                    'metadata': metadata.copy(),
                    'doc_id': doc_id,
                    'base_doc_id': self._normalize_base_doc_id(doc_id),
                    'doc_type': doc_type,
                    'section': str(section_num),
                    'title': title or f"Section {section_num}",
                    'tags': [doc_type],
                    'version': metadata.get('version', '1.0'),
                    'version_tuple': metadata.get('version_tuple', (1, 0, 0, '')),
                    'file_path': metadata.get('source_path', ''),
                    'file_name': metadata.get('filename', ''),
                    'source': metadata.get('source_path', ''),
                    'token_count': current_tokens,  # Track actual token count
                    'chunk_method': 'token_based_420'  # Track chunking method
                }
                
                chunks.append(chunk)
                section_num += 1
                
                # Start new chunk with overlap
                if self.overlap_tokens > 0 and len(current_chunk) > 1:
                    # Keep last few sentences for overlap
                    overlap_sentences = []
                    overlap_tokens = 0
                    for i in range(len(current_chunk) - 1, -1, -1):
                        sent_tokens = self._count_tokens(current_chunk[i])
                        if overlap_tokens + sent_tokens <= self.overlap_tokens:
                            overlap_sentences.insert(0, current_chunk[i])
                            overlap_tokens += sent_tokens
                        else:
                            break
                    current_chunk = overlap_sentences
                    current_tokens = overlap_tokens
                else:
                    current_chunk = []
                    current_tokens = 0
            
            # Add current sentence to chunk
            current_chunk.append(sentence)
            current_tokens += sentence_tokens
        
        # Handle final chunk if there's remaining content
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            doc_id = metadata.get('doc_id', f"{metadata['filename']}_{uuid.uuid4().hex[:8]}")
            
            chunk = {
                'text': chunk_text,
                'embed_text': self._create_embed_text(title, chunk_text, metadata.get('tables')),
                'bm25_text': self._create_bm25_text(title, chunk_text, metadata.get('tables')),
                'metadata': metadata.copy(),
                'doc_id': doc_id,
                'base_doc_id': self._normalize_base_doc_id(doc_id),
                'doc_type': doc_type,
                'section': str(section_num),
                'title': title or f"Section {section_num}",
                'tags': [doc_type],
                'version': metadata.get('version', '1.0'),
                'version_tuple': metadata.get('version_tuple', (1, 0, 0, '')),
                'file_path': metadata.get('source_path', ''),
                'file_name': metadata.get('filename', ''),
                'source': metadata.get('source_path', ''),
                'token_count': current_tokens,
                'chunk_method': 'token_based_420'
            }
            
            chunks.append(chunk)
        
        logger.info(f"Token-based chunking: {len(text)} chars -> {len(chunks)} chunks (avg {sum(c['token_count'] for c in chunks) // len(chunks) if chunks else 0} tokens)")
        return chunks
    
    def _chunk_structured_document(self, text: str, metadata: Dict[str, Any], doc_type: str, title: str) -> List[Dict[str, Any]]:
        """Handle forms and structured documents with section-aware chunking"""
        chunks = []
        
        # Section patterns for structured documents
        qa_pattern = re.compile(r'(\d+\.\d+\s+[^?\n]+?\?)', re.MULTILINE)
        score_pattern = re.compile(r'^(Overall Section Score:.*?(?:Acceptable|Not Acceptable))', re.MULTILINE)
        section_pattern = re.compile(r'^(\d+\.\d+\s+[^?\n]+(?:\?)?)', re.MULTILINE)
        
        last_end = 0
        section_num = 1
        
        for match in section_pattern.finditer(text):
            # Content before this section
            content = text[last_end:match.start()].strip()
            if content:
                doc_id = metadata.get('doc_id', f"{metadata['filename']}_{uuid.uuid4().hex[:8]}")
                
                chunk = {
                    'text': content,
                    'embed_text': self._create_embed_text(title, content, metadata.get('tables')),
                    'bm25_text': self._create_bm25_text(title, content, metadata.get('tables')),
                    'metadata': metadata.copy(),
                    'doc_id': doc_id,
                    'base_doc_id': self._normalize_base_doc_id(doc_id),
                    'doc_type': doc_type,
                    'section': str(section_num),
                    'title': title or f"Section {section_num}",
                    'tags': ['form' if doc_type == 'form' else 'hr_policy'],
                    'version': metadata.get('version', '1.0'),
                    'version_tuple': metadata.get('version_tuple', (1, 0, 0, '')),
                    'file_path': metadata.get('source_path', ''),
                    'file_name': metadata.get('filename', ''),
                    'source': metadata.get('source_path', ''),
                    'token_count': self._count_tokens(content),
                    'chunk_method': 'structured_section'
                }
                
                chunks.append(chunk)
                section_num += 1
            
            # Process the section itself
            section_text = match.group(1).strip()
            qa_match = qa_pattern.match(section_text)
            doc_id = metadata.get('doc_id', f"{metadata['filename']}_{uuid.uuid4().hex[:8]}")
            
            if qa_match:
                qa_num = section_text.split()[0]
                chunk_title = section_text.split('?')[0].strip()
                tags = ['question', 'form' if doc_type == 'form' else 'hr_policy']
                section_id = f"{section_num}.{qa_num}"
            elif score_pattern.match(section_text):
                chunk_title = section_text
                tags = ['score', 'form' if doc_type == 'form' else 'hr_policy']
                section_id = str(section_num)
            else:
                chunk_title = section_text
                tags = ['form' if doc_type == 'form' else 'hr_policy']
                section_id = str(section_num)
            
            chunk = {
                'text': section_text,
                'embed_text': self._create_embed_text(chunk_title, section_text, metadata.get('tables')),
                'bm25_text': self._create_bm25_text(chunk_title, section_text, metadata.get('tables')),
                'metadata': metadata.copy(),
                'doc_id': doc_id,
                'base_doc_id': self._normalize_base_doc_id(doc_id),
                'doc_type': doc_type,
                'section': section_id,
                'title': chunk_title,
                'tags': tags,
                'version': metadata.get('version', '1.0'),
                'version_tuple': metadata.get('version_tuple', (1, 0, 0, '')),
                'file_path': metadata.get('source_path', ''),
                'file_name': metadata.get('filename', ''),
                'source': metadata.get('source_path', ''),
                'token_count': self._count_tokens(section_text),
                'chunk_method': 'structured_qa'
            }
            
            chunks.append(chunk)
            last_end = match.end()
        
        # Handle final content
        if last_end < len(text):
            content = text[last_end:].strip()
            if content:
                doc_id = metadata.get('doc_id', f"{metadata['filename']}_{uuid.uuid4().hex[:8]}")
                
                chunk = {
                    'text': content,
                    'embed_text': self._create_embed_text(title, content, metadata.get('tables')),
                    'bm25_text': self._create_bm25_text(title, content, metadata.get('tables')),
                    'metadata': metadata.copy(),
                    'doc_id': doc_id,
                    'base_doc_id': self._normalize_base_doc_id(doc_id),
                    'doc_type': doc_type,
                    'section': str(section_num),
                    'title': title or f"Section {section_num}",
                    'tags': ['form' if doc_type == 'form' else 'hr_policy'],
                    'version': metadata.get('version', '1.0'),
                    'version_tuple': metadata.get('version_tuple', (1, 0, 0, '')),
                    'file_path': metadata.get('source_path', ''),
                    'file_name': metadata.get('filename', ''),
                    'source': metadata.get('source_path', ''),
                    'token_count': self._count_tokens(content),
                    'chunk_method': 'structured_final'
                }
                
                chunks.append(chunk)
        
        return chunks
    
    def _normalize_base_doc_id(self, doc_id: str) -> str:
        """Normalize document ID by removing extension and version."""
        from pathlib import Path
        base_id = Path(doc_id).stem
        base_id = re.sub(r'[\s_-]*(v|rev|r)[\s_-]*(\d+[\.\d]*)', '', base_id, flags=re.IGNORECASE).rstrip('_- ')
        return base_id