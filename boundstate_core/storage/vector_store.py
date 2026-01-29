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

# boundstate/vector_store.py
"""
LlamaIndex VectorStore integration for BoundState
Provides a bridge between BoundState's SemanticIndex and LlamaIndex RAG capabilities
"""
from typing import List, Any, Optional
import logging

import numpy as np

try:
    from llama_index.core.vector_stores.types import VectorStore
    from llama_index.core.schema import TextNode, NodeWithScore
    from llama_index.core.vector_stores.types import (
        MetadataFilters, 
        FilterOperator, 
        MetadataFilter,
        VectorStoreQuery,
        VectorStoreQueryResult
    )
    LLAMA_INDEX_AVAILABLE = True
except ImportError:
    LLAMA_INDEX_AVAILABLE = False
    VectorStore = object
    TextNode = object
    NodeWithScore = object
    # Add missing type definitions for when LlamaIndex is not available
    VectorStoreQuery = object
    VectorStoreQueryResult = object
    MetadataFilter = object
    FilterOperator = object
    MetadataFilters = object

from boundstate_core.storage.index import SemanticIndex
from boundstate_core.config.utils import parse_version
from boundstate_core.config.settings import CONFIG

logger = logging.getLogger(__name__)

class BoundStateVectorStore(VectorStore):
    """LlamaIndex VectorStore implementation using BoundState SemanticIndex."""
    
    stores_text: bool = True
    is_embedding_query: bool = True
    
    def __init__(self, semantic_index: SemanticIndex, **kwargs: Any) -> None:
        """Initialize with a SemanticIndex instance."""
        if not LLAMA_INDEX_AVAILABLE:
            raise ImportError("llama-index is required for BoundStateVectorStore")
        
        self.semantic_index = semantic_index
        super().__init__(**kwargs)
    
    @classmethod
    def class_name(cls) -> str:
        return "BoundStateVectorStore"
    
    def add(self, nodes: List[TextNode], **add_kwargs: Any) -> List[str]:
        """Add nodes to the vector store."""
        if not nodes:
            return []
        
        sections = []
        node_ids = []
        
        for node in nodes:
            # Convert TextNode to section format
            section = {
                "doc_id": node.metadata.get("doc_id", f"node_{node.id_}"),
                "base_doc_id": node.metadata.get("base_doc_id", "unknown"),
                "version": node.metadata.get("version", "1.0"),
                "version_tuple": parse_version(node.metadata.get("version", "1.0")),
                "section": node.metadata.get("section", "0"),
                "title": node.metadata.get("title", "Untitled"),
                "text": node.text,
                "tags": node.metadata.get("tags", []),
                "doc_type": node.metadata.get("doc_type", "unknown"),
                "file_path": node.metadata.get("file_path", ""),
                "file_name": node.metadata.get("file_name", ""),
                "node_id": node.id_
            }
            
            sections.append(section)
            node_ids.append(node.id_)
        
        # Add to semantic index
        added_count = self.semantic_index.add(sections)
        logger.info(f"Added {added_count} sections to BoundState vector store")
        
        return node_ids
    
    def delete(self, ref_doc_id: str, **delete_kwargs: Any) -> None:
        """Delete nodes by reference document ID."""
        deleted_count = self.semantic_index.delete_document(ref_doc_id)
        logger.info(f"Deleted {deleted_count} sections for document {ref_doc_id}")
    
    def query(self, query: VectorStoreQuery, **kwargs: Any) -> VectorStoreQueryResult:
        """Query the vector store."""
        if not query.query_embedding:
            logger.warning("No query embedding provided")
            return VectorStoreQueryResult(nodes=[], similarities=[], ids=[])
        
        # Extract filters
        doc_type = None
        tags = None
        base_doc_id = None
        
        if query.filters:
            for filter_item in query.filters.filters:
                if filter_item.key == "doc_type" and filter_item.operator == FilterOperator.EQ:
                    doc_type = filter_item.value
                elif filter_item.key == "tags" and filter_item.operator == FilterOperator.CONTAINS:
                    tags = filter_item.value if isinstance(filter_item.value, list) else [filter_item.value]
                elif filter_item.key == "base_doc_id" and filter_item.operator == FilterOperator.EQ:
                    base_doc_id = filter_item.value
        
        # Search semantic index
        query_embedding = np.array(query.query_embedding).reshape(1, -1)
        results = self.semantic_index.search(
            query_embedding=query_embedding,
            k=query.similarity_top_k,
            doc_type=doc_type,
            tags=tags,
            base_doc_id=base_doc_id
        )
        
        # Convert results to LlamaIndex format
        nodes = []
        similarities = []
        ids = []
        
        for result in results:
            # Create TextNode from result
            node = TextNode(
                text=result["text"],
                id_=result.get("node_id", f"{result['doc_id']}_{result['section']}"),
                metadata={
                    "doc_id": result["doc_id"],
                    "section": result["section"],
                    "title": result["title"],
                    "tags": result["tags"],
                    "doc_type": result["doc_type"],
                    "file_name": result.get("file_name", ""),
                    "score": result["score"]
                }
            )
            
            node_with_score = NodeWithScore(node=node, score=result["score"])
            nodes.append(node_with_score)
            similarities.append(result["score"])
            ids.append(node.id_)
        
        return VectorStoreQueryResult(
            nodes=nodes,
            similarities=similarities,
            ids=ids
        )
    
    @property
    def client(self) -> Any:
        """Return the underlying semantic index."""
        return self.semantic_index
    
    def get_stats(self) -> dict:
        """Get statistics about the vector store."""
        return self.semantic_index.get_stats()
    
    def optimize(self) -> None:
        """Optimize the underlying index."""
        self.semantic_index.optimize_index()

def create_vector_store(semantic_index: SemanticIndex = None, **kwargs) -> BoundStateVectorStore:
    """Factory function to create a BoundStateVectorStore."""
    if not LLAMA_INDEX_AVAILABLE:
        raise ImportError("llama-index is required for BoundStateVectorStore")
    
    if semantic_index is None:
        from boundstate_core.storage.index import create_index
        semantic_index = create_index()
    
    return BoundStateVectorStore(semantic_index, **kwargs)

# Compatibility functions for systems that don't have LlamaIndex
def create_mock_vector_store(semantic_index: SemanticIndex = None, **kwargs):
    """Create a mock vector store when LlamaIndex is not available."""
    if semantic_index is None:
        from boundstate_core.storage.index import create_index
        semantic_index = create_index()
    
    class MockVectorStore:
        def __init__(self, semantic_index):
            self.semantic_index = semantic_index
        
        def add_texts(self, texts, metadatas=None):
            sections = []
            for i, text in enumerate(texts):
                metadata = metadatas[i] if metadatas else {}
                section = {
                    "doc_id": metadata.get("doc_id", f"text_{i}"),
                    "base_doc_id": metadata.get("base_doc_id", "unknown"),
                    "version": metadata.get("version", "1.0"),
                    "version_tuple": parse_version(metadata.get("version", "1.0")),
                    "section": metadata.get("section", str(i)),
                    "title": metadata.get("title", "Untitled"),
                    "text": text,
                    "tags": metadata.get("tags", []),
                    "doc_type": metadata.get("doc_type", "unknown"),
                }
                sections.append(section)
            return self.semantic_index.add(sections)
        
        def search(self, query, k=5, **filters):
            return self.semantic_index.search_text(query, k, **filters)
        
        def get_stats(self):
            return self.semantic_index.get_stats()
    
    return MockVectorStore(semantic_index)