"""Infrastructure adapters (DB, graph, config, logging, cache)."""

from __future__ import annotations

from .document_store import DocumentStore, DocumentHit, NullDocumentStore

# Lazy import for FaissDocumentStore (requires optional deps)
def get_faiss_store():
    """Get FaissDocumentStore class (lazy import)."""
    from .faiss_store import FaissDocumentStore
    return FaissDocumentStore

__all__ = [
    "DocumentStore",
    "DocumentHit",
    "NullDocumentStore",
    "get_faiss_store",
]
