#!/usr/bin/env python3
"""Document counting module with full corpus access

Fixes the TQP count issue by ensuring we count across all documents,
not just the indexed sections subset.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import logging

logger = logging.getLogger(__name__)


def _clean_doc_id(raw_id: Optional[str], base_id: Optional[str]) -> str:
    """Normalize raw metadata doc identifiers.

    Compliance: SWE-033
    """
    if raw_id:
        cleaned = re.sub(r"\.pdf.*$", "", raw_id, flags=re.IGNORECASE)
        cleaned = cleaned.replace("_v1.0", "").strip()
        if cleaned:
            return cleaned
    if base_id:
        return base_id
    return raw_id or "unknown"

def count_docs_with_terms(
    terms: Union[str, List[str]], 
    match_mode: str = "substring", 
    documents: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Count documents containing specified terms.
    
    Args:
        terms: Search term(s) as string or list
        match_mode: "substring", "regex", or "exact"
        documents: Document list with {'doc_id', 'text'} structure
                  If None, loads from canonical metadata catalog
    
    Returns:
        Dict with count, matching_docs list, and total_docs
    """
    if documents is None:
        documents = load_all_documents()
    
    # Normalize terms to list
    if isinstance(terms, str):
        terms = [terms]
    
    matching_docs = []
    
    for doc in documents:
        # Safe doc_id extraction with fallback
        doc_id = (doc.get("doc_id") 
                 or doc.get("metadata", {}).get("doc_id")
                 or doc.get("source_id")
                 or doc.get("filename")
                 or "UNKNOWN")
        
        text = doc.get("text", "").lower()
        
        # Check if any term matches
        matches = False
        full_text = doc.get("full_text", text)  # Use full_text if available
        for term in terms:
            term_lower = term.lower()
            
            if match_mode == "substring":
                if term_lower in full_text:
                    matches = True
                    break
            elif match_mode == "regex":
                if re.search(term, full_text, re.IGNORECASE):
                    matches = True
                    break  
            elif match_mode == "exact":
                # Word boundary matching
                if re.search(rf'\b{re.escape(term_lower)}\b', text):
                    matches = True
                    break
        
        if matches:
            matching_docs.append({
                "doc_id": doc_id,
                "title": doc.get("title", doc.get("metadata", {}).get("title", "")),
                "matched_terms": [t for t in terms if t.lower() in text]
            })
    
    result = {
        "count": len(matching_docs),
        "total_docs": len(documents),
        "matching_docs": matching_docs,
        "terms": terms,
        "match_mode": match_mode
    }
    
    logger.info(f"Document count for {terms}: {result['count']}/{result['total_docs']}")
    return result

def load_all_documents() -> List[Dict[str, Any]]:
    """Load all documents from metadata and supplement with extracted text files.
    
    Returns full document corpus by combining indexed metadata with extracted text files.
    """
    documents = []
    
    # First, try to load from metadata.json (indexed documents)
    documents.extend(_load_from_metadata())
    
    # Then supplement with documents from extracted text files that might not be in metadata
    extracted_docs = _load_from_extracted_text()
    
    # Merge, avoiding duplicates by normalizing document IDs
    def normalize_doc_id(doc_id: str) -> str:
        """Normalize document ID for comparison"""
        # Remove version info, spaces, underscores for comparison
        normalized = doc_id.replace("_v1.0", "").replace(" ", "_").replace("_r", " r").upper()
        return normalized
    
    existing_normalized = {normalize_doc_id(doc["doc_id"]) for doc in documents}
    added_count = 0
    
    for doc in extracted_docs:
        normalized_id = normalize_doc_id(doc["doc_id"])
        if normalized_id not in existing_normalized:
            documents.append(doc)
            existing_normalized.add(normalized_id)
            added_count += 1
    
    logger.info(f"Loaded {len(documents)} total documents ({len(documents) - added_count} from metadata, {added_count} additional from extracted text)")
    return documents

def _load_from_metadata() -> List[Dict[str, Any]]:
    """Load documents from metadata.json"""
    # Try multiple possible locations for metadata.json
    possible_paths = [
        Path("index/metadata.json"),  # Legacy flat layout
        Path("index/metadata/metadata.json"),  # Current directory structure
        Path(__file__).parent.parent / "index" / "metadata.json",  # Project root (flat)
        Path(__file__).parent.parent / "index" / "metadata" / "metadata.json",  # Project root (nested)
        Path("/mnt/c/users/jnwil/amentum-doc-system/index/metadata.json"),  # Absolute path
    ]
    
    metadata_path = None
    for path in possible_paths:
        if path.exists():
            metadata_path = path
            break
    
    if metadata_path is None:
        logger.warning(f"Metadata file not found in any of: {possible_paths}")
        return []
    
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        documents = []
        
        # Handle different metadata formats
        sections_data = metadata.get("_default", metadata.get("documents", {}))
        
        # Group sections by document ID
        doc_texts = {}
        for section_id, section_info in sections_data.items():
            base_doc_id = section_info.get("base_doc_id")
            raw_doc_id = section_info.get("doc_id", "unknown")
            doc_id = _clean_doc_id(raw_doc_id, base_doc_id)
            text = section_info.get("text", "")

            doc_entry = doc_texts.setdefault(
                doc_id,
                {
                    "sections": [],
                    "title": section_info.get("title", ""),
                    "metadata": {
                        "doc_id": raw_doc_id,
                        "base_doc_id": base_doc_id or doc_id,
                        **section_info.get("metadata", {}),
                    },
                },
            )
            doc_entry["sections"].append(text)

        # Create documents from grouped sections
        for doc_id, doc_data in doc_texts.items():
            # Concatenate all section texts for this document
            text = "\n".join(doc_data["sections"])

            documents.append({
                "doc_id": doc_id,
                "text": text,
                "title": doc_data["title"],
                "metadata": doc_data["metadata"],
                "source": "metadata"
            })
        
        return documents
        
    except Exception as e:
        logger.error(f"Error loading documents from metadata: {e}")
        return []

def _load_from_extracted_text() -> List[Dict[str, Any]]:
    """Load documents from extracted_text directory as fallback"""
    documents = []
    
    # Try multiple possible locations for extracted_text
    possible_paths = [
        Path("extracted_text"),
        Path(__file__).parent.parent / "extracted_text",
        Path("/mnt/c/users/jnwil/amentum-doc-system/extracted_text"),
    ]
    
    extracted_path = None
    for path in possible_paths:
        if path.exists() and path.is_dir():
            extracted_path = path
            break
    
    if extracted_path is None:
        logger.debug("No extracted_text directory found")
        return []
    
    try:
        for text_file in extracted_path.glob("*.txt"):
            try:
                with open(text_file, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                # Extract doc_id from filename
                doc_id = text_file.stem
                
                documents.append({
                    "doc_id": doc_id,
                    "text": text,
                    "title": doc_id,
                    "metadata": {"file_path": str(text_file)},
                    "source": "extracted_text"
                })
                
            except Exception as e:
                logger.warning(f"Error reading {text_file}: {e}")
                continue
        
        return documents
        
    except Exception as e:
        logger.error(f"Error scanning extracted_text directory: {e}")
        return []

def count_tqp_documents() -> int:
    """Quick TQP document counter for the specific user complaint."""
    result = count_docs_with_terms("tqp", match_mode="substring")
    return result["count"]

def is_count_query(query: str) -> bool:
    """Detect if query is asking for document counts."""
    query_lower = query.lower()
    count_patterns = [
        r"how many.*documents?",
        r"how many.*docs?", 
        r"count.*documents?",
        r"number.*documents?",
        r"which documents?",
        r"what documents?",
        r"list.*documents?"
    ]
    
    return any(re.search(pattern, query_lower) for pattern in count_patterns)

def handle_count_query(query: str) -> Optional[str]:
    """Handle count queries by extracting terms and returning formatted response.
    
    Args:
        query: User's count query
        
    Returns:
        Formatted count response or None if not a count query
    """
    if not is_count_query(query):
        return None
    
    # Extract key terms from query
    terms = extract_query_terms(query)
    if not terms:
        return "I couldn't identify specific terms to count in your query."
    
    # Perform the count
    result = count_docs_with_terms(terms, match_mode="substring")
    
    # Format response
    if result["count"] == 0:
        return f"No documents found containing '{' '.join(terms)}'."
    elif result["count"] == 1:
        doc = result["matching_docs"][0]
        return f"1 document contains '{' '.join(terms)}': {doc['doc_id']}"
    else:
        doc_ids = [doc["doc_id"] for doc in result["matching_docs"]]
        
        # Always show all documents for any query that found them
        # Users asking about documents usually want to see the complete list
        return f"{result['count']} documents contain '{' '.join(terms)}': {', '.join(doc_ids)}"

def extract_query_terms(query: str) -> List[str]:
    """Extract searchable terms from count queries."""
    query_lower = query.lower()
    
    # Remove count-specific or generic words
    stop_words = {
        'how', 'many', 'documents', 'document', 'docs', 'doc', 'mention', 'mentions',
        'contain', 'contains', 'have', 'with', 'about', 'the', 'a', 'an', 'in', 'of',
        'for', 'on', 'at', 'list', 'tell', 'me', 'which', 'what', 'that', 'are', 'is',
        'there', 'all', 'some', 'any', 'show', 'find', 'get', 'give', 'can', 'you',
        'total', 'number', 'count'
    }

    # Simple word extraction
    words = re.findall(r'\b\w+\b', query_lower)
    terms = [w for w in words if w not in stop_words and len(w) > 2]

    # Prefer longer, more specific terms
    seen = set()
    ordered_terms = []
    for term in sorted(terms, key=len, reverse=True):
        if term not in seen:
            seen.add(term)
            ordered_terms.append(term)

    return ordered_terms
