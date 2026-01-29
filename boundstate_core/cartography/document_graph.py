"""
BoundState AI - Document Graph
Cross-document relationship mapping and ID normalization.
Enables graph-based query expansion and impact analysis.
"""

import networkx as nx
from dataclasses import dataclass
from typing import List, Dict, Set, Tuple, Optional, Any
import re
import logging
from collections import defaultdict
from boundstate_core.ingestion.structured_parser import DocumentStructure, CrossRef
from boundstate_core.nlp.hierarchical_chunker import Chunk

logger = logging.getLogger(__name__)

@dataclass
class Edge:
    """A relationship between documents or chunks."""
    source: str  # doc_id or chunk_id
    target: str
    edge_type: str  # "refers_to", "defines", "updates", "contradicts", "similar"
    confidence: float  # 0.0 to 1.0
    evidence: str  # Supporting text
    metadata: Dict[str, Any] = None

@dataclass
class GraphNode:
    """A node in the document graph."""
    node_id: str
    node_type: str  # "document", "section", "chunk"
    doc_id: str
    title: str
    metadata: Dict[str, Any] = None

class DocumentGraph:
    """Cross-document relationship graph."""
    
    def __init__(self):
        self.graph = nx.DiGraph()  # Directed graph for relationships
        self.doc_id_mapping = {}  # Normalized ID -> canonical ID
        self.reverse_mapping = {}  # Canonical ID -> all variations
    
    def build_graph(self, documents: List[DocumentStructure]) -> nx.DiGraph:
        """Build complete document graph."""
        logger.info(f"Building graph from {len(documents)} documents")
        
        # Step 1: Add all documents as nodes
        self._add_document_nodes(documents)
        
        # Step 2: Normalize and map document IDs
        self._build_id_mappings(documents)
        
        # Step 3: Add cross-references as edges
        self._add_cross_reference_edges(documents)
        
        # Step 4: Add semantic similarity edges (optional)
        # self._add_similarity_edges(documents)
        
        logger.info(f"Built graph with {len(self.graph.nodes)} nodes and {len(self.graph.edges)} edges")
        return self.graph
    
    def expand_query_results(self, initial_chunks: List[Chunk], 
                           max_hops: int = 1,
                           max_expansion: int = 10) -> List[Chunk]:
        """Expand query results using graph connections."""
        if not initial_chunks:
            return []
        
        # Get connected chunks via graph traversal
        expanded_chunk_ids = set(chunk.chunk_id for chunk in initial_chunks)
        
        for chunk in initial_chunks:
            # Find connected documents/chunks
            connected = self._find_connected_nodes(chunk.doc_id, max_hops)
            
            # Limit expansion to avoid noise
            for connected_id in list(connected)[:max_expansion]:
                expanded_chunk_ids.add(connected_id)
        
        # This is now a placeholder - use enhanced_system._expand_with_graph instead
        logger.warning("expand_query_results is deprecated, use enhanced_system._expand_with_graph")
        return initial_chunks
    
    def find_impact_path(self, doc_id: str) -> List[str]:
        """Find which documents would be impacted if doc_id changes."""
        if doc_id not in self.graph:
            return []
        
        # Find all documents that reference this one
        impacted = []
        
        # Direct references (incoming edges)
        for predecessor in self.graph.predecessors(doc_id):
            if predecessor != doc_id:
                impacted.append(predecessor)
        
        # Transitive references (2-hop paths)
        for intermediate in self.graph.predecessors(doc_id):
            for second_level in self.graph.predecessors(intermediate):
                if second_level not in impacted and second_level != doc_id:
                    impacted.append(second_level)
        
        return list(set(impacted))
    
    def get_document_cluster(self, doc_id: str, max_distance: int = 2) -> Set[str]:
        """Get cluster of related documents."""
        if doc_id not in self.graph:
            return {doc_id}
        
        cluster = {doc_id}
        
        # BFS to find connected documents within max_distance
        visited = set()
        queue = [(doc_id, 0)]
        
        while queue:
            current_doc, distance = queue.pop(0)
            
            if current_doc in visited or distance >= max_distance:
                continue
            
            visited.add(current_doc)
            
            # Add neighbors (both directions)
            for neighbor in self.graph.neighbors(current_doc):
                if neighbor not in visited:
                    cluster.add(neighbor)
                    queue.append((neighbor, distance + 1))
            
            for predecessor in self.graph.predecessors(current_doc):
                if predecessor not in visited:
                    cluster.add(predecessor)
                    queue.append((predecessor, distance + 1))
        
        return cluster
    
    def _add_document_nodes(self, documents: List[DocumentStructure]) -> None:
        """Add documents as graph nodes."""
        for doc in documents:
            node = GraphNode(
                node_id=doc.doc_id,
                node_type="document",
                doc_id=doc.doc_id,
                title=doc.title,
                metadata={
                    'total_pages': doc.total_pages,
                    'sections': len(doc.sections),
                    'tables': len(doc.tables),
                    'figures': len(doc.figures)
                }
            )
            
            self.graph.add_node(doc.doc_id, **{
                'node_type': node.node_type,
                'title': node.title,
                'metadata': node.metadata
            })
    
    def _build_id_mappings(self, documents: List[DocumentStructure]) -> None:
        """Build normalized ID mappings."""
        all_doc_ids = [doc.doc_id for doc in documents]
        
        # Extract all referenced IDs from cross-references
        referenced_ids = set()
        for doc in documents:
            for cross_ref in doc.cross_refs:
                referenced_ids.add(cross_ref.target_id)
        
        # Normalize both document IDs and referenced IDs
        all_ids = set(all_doc_ids) | referenced_ids
        
        for doc_id in all_ids:
            normalized = self._normalize_id(doc_id)
            
            if normalized not in self.doc_id_mapping:
                self.doc_id_mapping[normalized] = doc_id  # First occurrence is canonical
                self.reverse_mapping[doc_id] = [normalized]
            else:
                # Track variations
                canonical = self.doc_id_mapping[normalized]
                if canonical not in self.reverse_mapping:
                    self.reverse_mapping[canonical] = []
                if normalized not in self.reverse_mapping[canonical]:
                    self.reverse_mapping[canonical].append(normalized)
    
    def _add_cross_reference_edges(self, documents: List[DocumentStructure]) -> None:
        """Add cross-reference relationships as edges."""
        for doc in documents:
            source_id = doc.doc_id
            
            for cross_ref in doc.cross_refs:
                target_id = self._resolve_target_id(cross_ref.target_id)
                
                if target_id and target_id != source_id:
                    # Determine edge type based on reference context
                    edge_type = self._classify_reference_type(cross_ref.text)
                    
                    edge = Edge(
                        source=source_id,
                        target=target_id,
                        edge_type=edge_type,
                        confidence=0.8,  # High confidence for explicit references
                        evidence=cross_ref.text,
                        metadata={
                            'source_section': cross_ref.source_section,
                            'ref_type': cross_ref.ref_type
                        }
                    )
                    
                    self.graph.add_edge(source_id, target_id, **{
                        'edge_type': edge.edge_type,
                        'confidence': edge.confidence,
                        'evidence': edge.evidence,
                        'metadata': edge.metadata
                    })
    
    def _normalize_id(self, doc_id: str) -> str:
        """Normalize document ID for consistent matching."""
        # Remove extra whitespace
        normalized = re.sub(r'\s+', '', doc_id.upper())
        
        # Standardize revision notation: "REV F" -> "F"
        normalized = re.sub(r'REV([A-Z])', r'\1', normalized)
        
        # Remove common prefixes/suffixes that don't affect identity
        normalized = re.sub(r'^(DOC|DOCUMENT|PROC|PROCEDURE|POL|POLICY)', '', normalized)
        
        # Standardize separators
        normalized = re.sub(r'[-_]', '.', normalized)
        
        return normalized
    
    def _resolve_target_id(self, target_id: str) -> Optional[str]:
        """Resolve a target ID to canonical document ID."""
        normalized = self._normalize_id(target_id)
        
        # Direct mapping
        if normalized in self.doc_id_mapping:
            return self.doc_id_mapping[normalized]
        
        # Fuzzy matching for close variants
        for canonical_id, variants in self.reverse_mapping.items():
            if normalized in variants:
                return canonical_id
        
        # Partial matching (for incomplete references)
        for canonical_id in self.reverse_mapping.keys():
            canonical_normalized = self._normalize_id(canonical_id)
            if (len(normalized) > 3 and normalized in canonical_normalized) or \
               (len(canonical_normalized) > 3 and canonical_normalized in normalized):
                return canonical_id
        
        return None  # No match found
    
    def _classify_reference_type(self, reference_text: str) -> str:
        """Classify the type of reference based on context."""
        text_lower = reference_text.lower()
        
        # Keywords that indicate different relationship types
        if any(word in text_lower for word in ['see also', 'refer to', 'reference']):
            return 'refers_to'
        elif any(word in text_lower for word in ['per', 'according to', 'as defined in']):
            return 'defines'
        elif any(word in text_lower for word in ['update', 'supersede', 'replace']):
            return 'updates'
        elif any(word in text_lower for word in ['conflict', 'contradict', 'differ']):
            return 'contradicts'
        else:
            return 'refers_to'  # Default
    
    def _find_connected_nodes(self, node_id: str, max_hops: int) -> Set[str]:
        """Find nodes connected to given node within max_hops."""
        if node_id not in self.graph:
            return set()
        
        connected = set()
        visited = set()
        queue = [(node_id, 0)]
        
        while queue:
            current_node, hops = queue.pop(0)
            
            if current_node in visited or hops >= max_hops:
                continue
            
            visited.add(current_node)
            
            # Add all neighbors (outgoing edges)
            for neighbor in self.graph.neighbors(current_node):
                if neighbor not in visited:
                    connected.add(neighbor)
                    if hops + 1 < max_hops:
                        queue.append((neighbor, hops + 1))
            
            # Add predecessors (incoming edges) 
            for predecessor in self.graph.predecessors(current_node):
                if predecessor not in visited:
                    connected.add(predecessor)
                    if hops + 1 < max_hops:
                        queue.append((predecessor, hops + 1))
        
        return connected
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        if not self.graph:
            return {}
        
        edge_types = defaultdict(int)
        for _, _, data in self.graph.edges(data=True):
            edge_types[data.get('edge_type', 'unknown')] += 1
        
        return {
            'total_nodes': len(self.graph.nodes),
            'total_edges': len(self.graph.edges),
            'edge_types': dict(edge_types),
            'avg_degree': sum(dict(self.graph.degree()).values()) / len(self.graph.nodes) if self.graph.nodes else 0,
            'connected_components': nx.number_connected_components(self.graph.to_undirected()),
            'id_mappings': len(self.doc_id_mapping)
        }
    
    def export_for_visualization(self) -> Dict[str, Any]:
        """Export graph in format suitable for visualization."""
        nodes = []
        edges = []
        
        for node_id, data in self.graph.nodes(data=True):
            nodes.append({
                'id': node_id,
                'title': data.get('title', node_id),
                'type': data.get('node_type', 'document'),
                'metadata': data.get('metadata', {})
            })
        
        for source, target, data in self.graph.edges(data=True):
            edges.append({
                'source': source,
                'target': target,
                'type': data.get('edge_type', 'refers_to'),
                'confidence': data.get('confidence', 0.5),
                'evidence': data.get('evidence', '')
            })
        
        return {
            'nodes': nodes,
            'edges': edges,
            'stats': self.get_graph_stats()
        }


class GraphExpander:
    """Utility class for graph-based query expansion."""
    
    def __init__(self, document_graph: DocumentGraph):
        self.graph = document_graph
    
    def expand_with_graph(self, initial_doc_ids: List[str],
                         boost_factor: float = 0.1,
                         max_expansion: int = 5) -> List[Tuple[str, float]]:
        """Expand document list with graph-connected documents."""
        expanded = []
        
        for doc_id in initial_doc_ids:
            # Add original document with no boost
            expanded.append((doc_id, 0.0))
            
            # Find connected documents
            connected = self.graph._find_connected_nodes(doc_id, max_hops=1)
            
            # Add connected documents with boost
            for connected_id in list(connected)[:max_expansion]:
                if connected_id not in initial_doc_ids:
                    # Calculate boost based on edge strength
                    edge_data = self.graph.graph.get_edge_data(doc_id, connected_id)
                    if edge_data:
                        confidence = edge_data.get('confidence', 0.5)
                        boost = boost_factor * confidence
                        expanded.append((connected_id, boost))
        
        return expanded


def main():
    """Test the document graph."""
    import sys
    from boundstate_core.ingestion.structured_parser import StructuredDocumentParser
    
    if len(sys.argv) < 2:
        print("Usage: python document_graph.py <pdf_file1> [pdf_file2] ...")
        sys.exit(1)
    
    # Parse documents
    parser = StructuredDocumentParser()
    documents = []
    
    for file_path in sys.argv[1:]:
        try:
            doc_structure = parser.parse(file_path)
            documents.append(doc_structure)
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
    
    if not documents:
        print("No documents parsed successfully")
        sys.exit(1)
    
    # Build graph
    graph_builder = DocumentGraph()
    graph = graph_builder.build_graph(documents)
    
    # Show statistics
    stats = graph_builder.get_graph_stats()
    print(f"Graph Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Show some example relationships
    print(f"\nExample relationships:")
    for i, (source, target, data) in enumerate(graph.edges(data=True)):
        if i >= 5:  # Show first 5
            break
        print(f"  {source} -> {target} ({data.get('edge_type', 'unknown')})")
        if data.get('evidence'):
            print(f"    Evidence: {data['evidence'][:50]}...")


if __name__ == "__main__":
    main()