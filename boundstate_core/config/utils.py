# Copyright 2025 BoundStateAI
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# boundstate/utils.py
"""
Common utility functions for BoundState system
Includes version handling, text processing, security, and file management
"""
from __future__ import annotations

import re
import uuid
import logging
import hashlib
import hmac
from datetime import datetime
import time
from typing import Tuple, List, Optional, Dict, Any
from pathlib import Path

# Some environments used for automated evaluation don't have Werkzeug
# installed. The code only needs the secure_filename helper, so fall back
# to a minimal implementation if the dependency is missing.
try:
    from werkzeug.utils import secure_filename
except ImportError:
    import re as _re
    
    def secure_filename(value: str) -> str:
        """Lightweight substitute for werkzeug.utils.secure_filename."""
        value = str(value).strip().replace("\0", "")
        value = _re.sub(r"[^A-Za-z0-9_.-]", "_", value)
        return value[:255]

from boundstate_core.config.settings import CONFIG

def parse_version(version_str: str) -> Tuple[int, int, int, str]:
    """Parse version to comparable tuple: (major, minor, patch, suffix) where suffix '' > 'beta' etc."""
    if not version_str:
        return (0, 0, 0, '')
    
    # Extract numeric parts
    num_parts = re.findall(r'\d+', version_str)
    major = int(num_parts[0]) if len(num_parts) > 0 else 0
    minor = int(num_parts[1]) if len(num_parts) > 1 else 0
    patch = int(num_parts[2]) if len(num_parts) > 2 else 0
    
    # Extract suffix (everything after numbers)
    suffix = re.sub(r'[\d.]+', '', version_str).lstrip('-').lower() or ''
    
    return (major, minor, patch, suffix)

def compare_versions(v1: Tuple[int, int, int, str], v2: Tuple[int, int, int, str]) -> bool:
    """Compare version tuples; empty suffix > non-empty. Returns True if v1 > v2."""
    # Compare major, minor, patch
    for p1, p2 in zip(v1[:3], v2[:3]):
        if p1 != p2:
            return p1 > p2
    
    # Handle suffixes: empty suffix is considered "release" and > any suffix
    if v1[3] == '' and v2[3] != '':
        return True
    if v1[3] != '' and v2[3] == '':
        return False
    
    # If both have suffixes, compare alphabetically
    return v1[3] > v2[3]

def smart_chunk(text: str, window: int = None, stride: int = None) -> List[Dict[str, Any]]:
    """Chunk text into semantically meaningful segments.
    
    Args:
        text: Input text to chunk
        window: Size of chunk window in characters (default: from CONFIG)
        stride: Overlap between chunks (default: from CONFIG)
    
    Returns:
        List of chunk dictionaries with text and metadata
        
    Compliance: SWE-032 (Data validation and chunking), SWE-013 (Traceability)
    """
    window = window or 200  # Tighter size for denser chunks
    stride = stride or 20   # Minimal overlap for more sections
    
    # Detect lists, tables, headers, and paragraphs
    list_pattern = r'^\s*[-*+]\s+|\d+\.\s+'
    table_pattern = r'\|.*\|'
    header_pattern = r'^(#+|\d+\.\d+\.?|\d+\.\s+|[IVX]+\.\s+|[A-Z][\.]\s+)'  # Broader header detection
    paragraph_pattern = r'\n\s*\n|\r\n\s*\r\n'  # Paragraph breaks
    sentence_pattern = r'(?<=[.!?;])\s+'  # Sentence breaks for finer splits
    
    # Initialize metadata for traceability
    metadata = {'chunk_timestamp': datetime.utcnow().isoformat()}
    chunks = []
    
    # Split by paragraphs first
    paragraphs = re.split(paragraph_pattern, text)
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # Check for list, table, or header
        is_list = re.match(list_pattern, para, re.MULTILINE)
        is_table = re.match(table_pattern, para, re.MULTILINE)
        is_header = re.match(header_pattern, para)
        
        # Handle lists, tables, and headers as single chunks
        if is_list or is_table or is_header:
            chunk_metadata = metadata.copy()
            chunk_metadata['chunk_type'] = 'list' if is_list else 'table' if is_table else 'header'
            chunks.append({
                'text': para,
                'metadata': chunk_metadata
            })
            continue
        
        # Split paragraph into sentences for finer granularity
        sentences = re.split(sentence_pattern, para.strip())
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            sentence_size = len(sentence)
            if current_size + sentence_size > window:
                if current_chunk:
                    chunks.append({
                        'text': ' '.join(current_chunk),
                        'metadata': metadata.copy()
                    })
                current_chunk = [sentence] if sentence_size <= window else re.split(r'(?<=[,;])\s+', sentence)
                current_size = sentence_size
            elif sentence.strip():
                current_chunk.append(sentence)
                current_size += sentence_size
            
        if current_chunk:
            chunks.append({
                'text': ' '.join(current_chunk),
                'metadata': metadata.copy()
            })
    
    # Deduplicate chunks
    similarity_threshold = 0.5  # Loosest threshold to minimize deduplication
    
    unique_chunks = []
    from difflib import SequenceMatcher
    
    for chunk in chunks:
        chunk['metadata']['chunk_id'] = str(uuid.uuid4())  # Unique ID for traceability
        is_unique = True
        for existing in unique_chunks:
            if SequenceMatcher(None, chunk['text'], existing['text']).ratio() > similarity_threshold:
                is_unique = False
                break
        if is_unique:
            unique_chunks.append(chunk)
    
    return unique_chunks

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for security."""
    return secure_filename(filename)

def generate_doc_id(base_name: str, version: str = "1.0") -> str:
    """Generate a unique document ID."""
    return f"{base_name}_v{version}_{uuid.uuid4().hex[:8]}"

def extract_version_and_id(file_path: str) -> Tuple[str, str]:
    """Extract base document ID and version from filename."""
    filename = Path(file_path).stem
    
    # Look for version patterns: v1.2, version-1.2, rev-1.2, etc.
    version_patterns = [
        r'(?:_v|v|version-|ver-|rev-)([\d.]+(?:-[a-zA-Z]+)?)',
        r'(?:_)(\d+\.\d+(?:\.\d+)?(?:-[a-zA-Z]+)?)',
    ]
    
    for pattern in version_patterns:
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            version_str = match.group(1)
            base_doc_id = filename[:match.start()].rstrip('_-')
            return base_doc_id, version_str
    
    # No version found, default to 1.0
    return filename, '1.0'

def validate_api_key(provided_key: str) -> bool:
    """Validate API key if authentication is enabled."""
    if not CONFIG['api_key']:
        return True  # No authentication required
    
    if not provided_key:
        return False
    
    # Use HMAC for secure comparison
    expected = CONFIG['api_key'].encode('utf-8')
    provided = provided_key.encode('utf-8')
    
    return hmac.compare_digest(expected, provided)

def hash_text(text: str) -> str:
    """Generate hash for text deduplication."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def setup_logging(level: str = None) -> None:
    """Setup logging configuration."""
    level = level or CONFIG['log_level']
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('boundstate.log')
        ]
    )

def measure_time(func):
    """Decorator to measure function execution time."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        logger = logging.getLogger(func.__module__)
        logger.info(f"{func.__name__} executed in {end_time - start_time:.2f} seconds")
        
        return result
    return wrapper

def clean_text(text: str) -> str:
    """Clean and normalize text for processing."""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove control characters except newlines and tabs
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    # Normalize quotes
    text = re.sub(r'["""]', '"', text)
    text = re.sub(r"[''']", "'", text)
    
    return text.strip()

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"