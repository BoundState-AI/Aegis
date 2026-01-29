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

"""
Enhanced Graph Builder for BoundState Cartographer
=================================================

Builds document relationship graphs with ID normalization
to handle format mismatches between extracted references
and actual document IDs.

Key Features:
- Normalizes reference formats (F1301.1 REV F → F1301.1F r00)
- Creates bidirectional edges with relationship types
- Tracks edge confidence and metadata
- Supports AS9100 Rev D traceability
- Impact analysis in both directions

Compliance: SWE-013, SWE-033
"""

import re
import json
import os
from typing import Dict, List, Tuple, Optional, Set, Any
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path
import networkx as nx
from loguru import logger

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Configure logger
logger.add(
    "logs/graph_builder.log",
    rotation="10 MB",
    retention="30 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
)


@dataclass
class DocumentNode:
    """Represents a document in the graph."""
    doc_id: str
    normalized_id: str  # For matching
    doc_type: str
    title: str = ""
    version: str = ""
    status: str = "active"
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    
@dataclass 
class DocumentEdge:
    """Represents a relationship between documents."""
    source_id: str
    target_id: str
    relationship_type: str
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    evidence: List[str] = field(default_factory=list)


class IDNormalizer:
    """Handles ID format normalization for matching."""
    
    @staticmethod
    def normalize(doc_id: str) -> str:
        """Normalize document ID for matching.
        
        Handles conversions like:
        - "F1301.1 REV F" → "F1301.1F"
        - "F1301.1F r00" → "F1301.1F"
        - "POL4000 r02" → "POL4000"
        
        Args:
            doc_id: Raw document ID
            
        Returns:
            Normalized ID for matching
        """
        # Remove extra whitespace
        normalized = doc_id.strip().upper()
        
        # Handle "REV X" format → append letter directly
        # F1301.1 REV F → F1301.1F
        rev_pattern = r'^([A-Z]\d+\.\d+)\s+REV\s+([A-Z])$'
        match = re.match(rev_pattern, normalized)
        if match:
            normalized = f"{match.group(1)}{match.group(2)}"
        
        # Remove revision numbers (r00, r01, etc.)
        # F1301.1F r00 → F1301.1F
        normalized = re.sub(r'\s+[rR]\d{2}$', '', normalized)
        
        # Remove trailing version indicators
        normalized = re.sub(r'\s+[vV]\d+$', '', normalized)
        
        # Handle policy format
        # POL4000 r02 → POL4000
        if normalized.startswith('POL'):
            normalized = re.sub(r'\s+[rR]\d{2}$', '', normalized)
            
        return normalized
    
    @staticmethod
    def extract_base_and_version(doc_id: str) -> Tuple[str, Optional[str]]:
        """Extract base ID and version components.
        
        Returns:
            Tuple of (base_id, version)
        """
        # Pattern for Amentum internal docs
        pattern = r'^([A-Z]\d+\.\d+)([A-Z]?)\s*(?:[rR](\d{2}))?$'
        match = re.match(pattern, doc_id.strip())
        
        if match:
            base = match.group(1)
            letter = match.group(2) or ""
            revision = match.group(3)
            return base + letter, revision
            
        # Pattern for policies
        if doc_id.startswith('POL'):
            pattern = r'^(POL\d+)\s*(?:[rR](\d{2}))?$'
            match = re.match(pattern, doc_id.strip())
            if match:
                return match.group(1), match.group(2)
                
        return doc_id, None


class GraphBuilder:
    """Builds document relationship graphs with ID normalization.
    
    Compliance: SWE-013, SWE-033
    """
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.nodes: Dict[str, DocumentNode] = {}
        self.edges: List[DocumentEdge] = []
        self.id_normalizer = IDNormalizer()
        
        # Caches for performance
        self.normalized_id_map: Dict[str, str] = {}  # normalized → actual doc_id
        self.reference_stats: Dict[str, int] = defaultdict(int)
        
        # Track unmatched references for debugging
        self.unmatched_references: Dict[str, List[str]] = defaultdict(list)
        
        logger.info("GraphBuilder initialized with ID normalization")
        
    def add_document(self, doc_id: str, doc_type: str = "unknown", 
                    title: str = "", metadata: Optional[Dict] = None) -> DocumentNode:
        """Add a document node to the graph.
        
        Args:
            doc_id: Document identifier
            doc_type: Type of document
            title: Document title
            metadata: Additional metadata
            
        Returns:
            Created or existing DocumentNode
        """
        if doc_id in self.nodes:
            return self.nodes[doc_id]
            
        normalized_id = self.id_normalizer.normalize(doc_id)
        base_id, version = self.id_normalizer.extract_base_and_version(doc_id)
        
        node = DocumentNode(
            doc_id=doc_id,
            normalized_id=normalized_id,
            doc_type=doc_type,
            title=title,
            version=version or "",
            metadata=metadata or {}
        )
        
        self.nodes[doc_id] = node
        
        # Always populate normalized_id_map at insertion (Fran's suggestion #3)
        self.normalized_id_map[normalized_id] = doc_id
        
        # Add to NetworkX graph
        self.graph.add_node(doc_id, **{
            'type': doc_type,
            'title': title,
            'normalized_id': normalized_id,
            'version': version
        })
        
        logger.debug(f"Added node: {doc_id} (normalized: {normalized_id})")
        return node
        
    def add_reference(self, source_doc_id: str, referenced_id: str,
                     relationship_type: str = "references",
                     confidence: float = 1.0,
                     evidence: Optional[List[str]] = None) -> Optional[DocumentEdge]:
        """Add a reference edge with ID normalization.
        
        Args:
            source_doc_id: Document making the reference
            referenced_id: ID being referenced (will be normalized)
            relationship_type: Type of relationship
            confidence: Confidence score
            evidence: Supporting evidence
            
        Returns:
            Created edge or None if target not found
        """
        # Normalize the referenced ID
        normalized_ref = self.id_normalizer.normalize(referenced_id)
        
        # Find actual document ID from normalized form
        target_doc_id = self._find_document_by_normalized_id(normalized_ref)
        
        if not target_doc_id:
            # Enhanced logging with clearer guidance (Fran's suggestion #1)
            logger.warning(
                f"No match found: Original ID '{referenced_id}' normalized to '{normalized_ref}'. "
                f"Source document: '{source_doc_id}'. "
                "Consider verifying the referenced document is loaded or check ID format."
            )
            
            # Track unmatched references for analysis
            self.unmatched_references[normalized_ref].append({
                'original': referenced_id,
                'source': source_doc_id
            })
            return None
            
        # Create edge
        edge = DocumentEdge(
            source_id=source_doc_id,
            target_id=target_doc_id,
            relationship_type=relationship_type,
            confidence=confidence,
            evidence=evidence or [],
            metadata={
                'original_reference': referenced_id,
                'normalized_reference': normalized_ref
            }
        )
        
        self.edges.append(edge)
        
        # Add to NetworkX graph
        self.graph.add_edge(source_doc_id, target_doc_id,
                           relationship=relationship_type,
                           confidence=confidence,
                           original_ref=referenced_id)
        
        # Track statistics
        self.reference_stats[normalized_ref] += 1
        
        logger.debug(f"Added edge: {source_doc_id} → {target_doc_id} "
                    f"(via {referenced_id} → {normalized_ref})")
        
        return edge
        
    def _find_document_by_normalized_id(self, normalized_id: str) -> Optional[str]:
        """Find actual document ID from normalized form.
        
        Args:
            normalized_id: Normalized ID to search for
            
        Returns:
            Actual document ID or None
        """
        # Direct lookup (should always work with suggestion #3)
        if normalized_id in self.normalized_id_map:
            return self.normalized_id_map[normalized_id]
            
        # Fallback: search through all nodes
        for doc_id, node in self.nodes.items():
            if node.normalized_id == normalized_id:
                self.normalized_id_map[normalized_id] = doc_id
                return doc_id
                
        return None
        
    def build_from_content_results(self, content_results: Dict[str, Any]) -> None:
        """Build graph from ContentMiner results.
        
        Args:
            content_results: Results from content mining with documents and references
        """
        logger.info("Building graph from content results")
        
        # Check if this is the extraction results format
        if 'results' in content_results and isinstance(content_results['results'], list):
            logger.info("Detected extraction results format")
            
            # First pass: Add all documents
            for result in content_results['results']:
                if result.get('status') == 'success' and result.get('doc_id'):
                    self.add_document(
                        doc_id=result['doc_id'],
                        doc_type='unknown',  # We'll need to infer this
                        title=result.get('file', '').split('\\')[-1],  # Use filename as title
                        metadata={'file_path': result.get('file', '')}
                    )
            
            # Second pass: Add references
            reference_count = 0
            matched_count = 0
            
            for result in content_results['results']:
                if result.get('status') == 'success' and result.get('doc_id'):
                    doc_id = result['doc_id']
                    references = result.get('references', [])
                    
                    for ref in references:
                        reference_count += 1
                        
                        # Extract reference ID
                        if isinstance(ref, dict):
                            ref_id = ref.get('id', '')
                        else:
                            ref_id = str(ref)
                        
                        if ref_id:
                            edge = self.add_reference(
                                source_doc_id=doc_id,
                                referenced_id=ref_id,
                                confidence=1.0
                            )
                            if edge:
                                matched_count += 1
        
        # Handle other formats (original code)
        elif isinstance(next(iter(content_results.values()), None), list):
            logger.info("Detected simple reference list structure")
            # Simple reference list structure
            for doc_id, references in content_results.items():
                reference_count = 0
                matched_count = 0
                
                for ref in references:
                    if isinstance(ref, dict):
                        ref_id = ref.get('id', '')
                    else:
                        ref_id = str(ref)
                        
                    if ref_id:
                        reference_count += 1
                        edge = self.add_reference(
                            source_doc_id=doc_id,
                            referenced_id=ref_id,
                            confidence=ref.get('confidence', 1.0) if isinstance(ref, dict) else 1.0
                        )
                        if edge:
                            matched_count += 1
        else:
            logger.info("Detected full document structure")
            # Full document structure (original code)
            # First pass: Add all documents
            for doc_id, doc_data in content_results.items():
                self.add_document(
                    doc_id=doc_id,
                    doc_type=doc_data.get('doc_type', 'unknown'),
                    title=doc_data.get('title', ''),
                    metadata=doc_data.get('metadata', {})
                )
                
            # Second pass: Add references
            reference_count = 0
            matched_count = 0
            
            for doc_id, doc_data in content_results.items():
                references = doc_data.get('references', [])
                
                for ref in references:
                    if isinstance(ref, dict):
                        ref_id = ref.get('id', '')
                    else:
                        ref_id = str(ref)
                        
                    if ref_id:
                        reference_count += 1
                        edge = self.add_reference(
                            source_doc_id=doc_id,
                            referenced_id=ref_id,
                            confidence=ref.get('confidence', 1.0) if isinstance(ref, dict) else 1.0
                        )
                        if edge:
                            matched_count += 1
                            
        pct = matched_count / reference_count * 100 if reference_count else 0
        logger.info("Processed %d references, matched %d (%.1f%%)", 
                   reference_count, matched_count, pct)
        
        # Log unmatched references summary
        if self.unmatched_references:
            logger.warning(f"Found {len(self.unmatched_references)} unmatched reference patterns")
            for ref, sources in list(self.unmatched_references.items())[:5]:
                logger.warning(f"  '{ref}': {len(sources)} occurrences")
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics.
        
        Returns:
            Dictionary of statistics
        """
        stats = {
            'node_count': self.graph.number_of_nodes(),
            'edge_count': self.graph.number_of_edges(),
            'avg_degree': sum(dict(self.graph.degree()).values()) / self.graph.number_of_nodes() 
                         if self.graph.number_of_nodes() > 0 else 0,
            'connected_components': nx.number_weakly_connected_components(self.graph),
            'most_referenced': self._get_most_referenced(10),
            'most_referencing': self._get_most_referencing(10),
            'orphan_nodes': self._get_orphan_nodes(),
            'normalization_stats': {
                'total_normalizations': len(self.normalized_id_map),
                'unique_normalized_ids': len(set(self.normalized_id_map.keys())),
                'unmatched_references': len(self.unmatched_references)
            }
        }
        
        return stats
        
    def _get_most_referenced(self, n: int = 10) -> List[Tuple[str, int]]:
        """Get most referenced documents."""
        in_degrees = dict(self.graph.in_degree())
        return sorted(in_degrees.items(), key=lambda x: x[1], reverse=True)[:n]
        
    def _get_most_referencing(self, n: int = 10) -> List[Tuple[str, int]]:
        """Get documents that reference the most others."""
        out_degrees = dict(self.graph.out_degree())
        return sorted(out_degrees.items(), key=lambda x: x[1], reverse=True)[:n]
        
    def _get_orphan_nodes(self) -> List[str]:
        """Get nodes with no connections."""
        return [node for node in self.graph.nodes() 
                if self.graph.in_degree(node) == 0 and self.graph.out_degree(node) == 0]
        
    def find_impact_path(self, doc_id: str, max_depth: int = 5, 
                        direction: str = "upstream") -> Dict[str, Set[str]]:
        """Find all documents impacted by changes to a document.
        
        Enhanced with bidirectional support (Fran's suggestion #2).
        
        Args:
            doc_id: Document to analyze
            max_depth: Maximum depth to search
            direction: 'upstream' (who references me), 'downstream' (who I reference), 
                      or 'both'
            
        Returns:
            Dict mapping depth to set of impacted documents
        """
        if doc_id not in self.graph:
            logger.warning(f"Document '{doc_id}' not found in graph")
            return {}
            
        impacted = defaultdict(set)
        
        if direction in ["upstream", "both"]:
            # Find documents that reference this one (predecessors)
            upstream = self._trace_impact(doc_id, max_depth, use_predecessors=True)
            for depth, docs in upstream.items():
                impacted[f"upstream_{depth}"] = docs
                
        if direction in ["downstream", "both"]:
            # Find documents this one references (successors)
            downstream = self._trace_impact(doc_id, max_depth, use_predecessors=False)
            for depth, docs in downstream.items():
                impacted[f"downstream_{depth}"] = docs
                
        # Add NetworkX descendants for convenience
        if direction == "downstream":
            try:
                all_descendants = nx.descendants(self.graph, doc_id)
                impacted["all_downstream"] = all_descendants
            except nx.NetworkXError:
                pass
                
        return dict(impacted)
        
    def _trace_impact(self, doc_id: str, max_depth: int, 
                     use_predecessors: bool = True) -> Dict[int, Set[str]]:
        """Helper to trace impact in one direction."""
        impacted = {}
        current_level = {doc_id}
        
        for depth in range(1, max_depth + 1):
            next_level = set()
            
            for current_doc in current_level:
                if use_predecessors:
                    neighbors = set(self.graph.predecessors(current_doc))
                else:
                    neighbors = set(self.graph.successors(current_doc))
                next_level.update(neighbors)
                
            if not next_level:
                break
                
            impacted[depth] = next_level
            current_level = next_level
            
        return impacted
        
    def export_for_visualization(self, output_path: str) -> None:
        """Export graph data for D3.js visualization.
        
        Args:
            output_path: Path to save JSON file
        """
        # Convert to D3-friendly format
        nodes = []
        links = []
        
        # Create node list with indices
        node_index = {}
        for i, (node_id, node_data) in enumerate(self.nodes.items()):
            nodes.append({
                'id': node_id,
                'normalized_id': node_data.normalized_id,
                'type': node_data.doc_type,
                'title': node_data.title,
                'version': node_data.version,
                'in_degree': self.graph.in_degree(node_id),
                'out_degree': self.graph.out_degree(node_id)
            })
            node_index[node_id] = i
            
        # Create links
        for edge in self.edges:
            if edge.source_id in node_index and edge.target_id in node_index:
                links.append({
                    'source': node_index[edge.source_id],
                    'target': node_index[edge.target_id],
                    'type': edge.relationship_type,
                    'confidence': edge.confidence
                })
                
        # Save as JSON
        graph_data = {
            'nodes': nodes,
            'links': links,
            'statistics': self.get_statistics(),
            'unmatched_references': dict(self.unmatched_references) if self.unmatched_references else {}
        }
        
        with open(output_path, 'w') as f:
            json.dump(graph_data, f, indent=2)
            
        logger.info(f"Exported graph to {output_path}")
        
    def export_for_d3(self, output_path: str):
        """Export graph in D3.js format with proper node IDs"""
        
        # Get the existing data
        nodes = []
        node_id_map = {}  # Map from integer index to actual ID
        
        for i, (node_id, node_data) in enumerate(self.graph.nodes(data=True)):
            node_id_map[i] = node_id
            nodes.append({
                "id": node_id,
                "type": node_data.get('type', 'document'),
                "importance": node_data.get('in_degree', 0) / 10.0,  # Scale importance
                "metadata": {
                    "type": node_data.get('type', 'unknown'),
                    "title": node_data.get('title', node_id),
                    "version": node_data.get('version', ''),
                    "in_degree": node_data.get('in_degree', 0),
                    "out_degree": node_data.get('out_degree', 0)
                }
            })
        
        # Convert links from indices to IDs
        links = []
        for edge in self.graph.edges(data=True):
            links.append({
                "source": edge[0],  # These are already string IDs
                "target": edge[1],
                "type": edge[2].get('type', 'references'),
                "strength": edge[2].get('confidence', 1.0)
            })
        
        with open(output_path, 'w') as f:
            json.dump({"nodes": nodes, "links": links}, f, indent=2)
        
        print(f"Exported D3 visualization to {output_path}")
        

def diagnose_unmatched_references(graph_builder, content_results):
    """Diagnose why references aren't matching"""
    
    print("\n[UNMATCHED REFERENCE ANALYSIS]")
    print("="*60)
    
    # Get all document IDs in the graph
    graph_doc_ids = set(graph_builder.nodes.keys())
    normalized_ids = {node.normalized_id: doc_id for doc_id, node in graph_builder.nodes.items()}
    
    print(f"Documents in graph: {len(graph_doc_ids)}")
    print(f"Normalized ID mappings: {len(normalized_ids)}")
    
    # Track all references
    all_refs = []
    unmatched_refs = defaultdict(list)
    
    # Check each document's references
    for result in content_results['results']:
        if result.get('status') == 'success' and result.get('doc_id'):
            source_doc = result['doc_id']
            references = result.get('references', [])
            
            for ref in references:
                ref_id = ref.get('id', '') if isinstance(ref, dict) else str(ref)
                if ref_id:
                    all_refs.append((source_doc, ref_id))
                    
                    # Try to normalize and find
                    normalized = graph_builder.id_normalizer.normalize(ref_id)
                    
                    if normalized not in normalized_ids and ref_id not in graph_doc_ids:
                        unmatched_refs[ref_id].append(source_doc)
    
    print(f"\nTotal references found: {len(all_refs)}")
    print(f"Unmatched references: {len(unmatched_refs)}")
    
    # Group unmatched by pattern
    patterns = defaultdict(list)
    for ref_id in unmatched_refs:
        if ref_id.startswith('AS'):
            patterns['AS Standards'].append(ref_id)
        elif ref_id.startswith('ISO'):
            patterns['ISO Standards'].append(ref_id)
        elif ref_id.startswith('MIL'):
            patterns['MIL Standards'].append(ref_id)
        elif ref_id.startswith('NASA'):
            patterns['NASA Standards'].append(ref_id)
        elif ref_id.startswith('ASTM'):
            patterns['ASTM Standards'].append(ref_id)
        elif ref_id.startswith('ANSI'):
            patterns['ANSI Standards'].append(ref_id)
        elif any(ref_id.startswith(prefix) for prefix in ['P', 'F', 'G', 'W', 'T']):
            patterns['Amentum Internal (unmatched)'].append(ref_id)
        else:
            patterns['Other'].append(ref_id)
    
    # Show pattern summary
    print("\n[UNMATCHED PATTERNS]")
    for pattern, refs in sorted(patterns.items()):
        print(f"\n{pattern}: {len(refs)} references")
        # Show first 5 examples
        for ref in sorted(set(refs))[:5]:
            source_count = len(unmatched_refs[ref])
            print(f"  - '{ref}' (referenced by {source_count} documents)")
    
    # Find potential normalization issues
    print("\n[NORMALIZATION ISSUES]")
    normalization_issues = []
    
    for ref_id, sources in unmatched_refs.items():
        normalized = graph_builder.id_normalizer.normalize(ref_id)
        
        # Check if it's an Amentum doc that should exist
        if any(ref_id.startswith(prefix) for prefix in ['P', 'F', 'G', 'W', 'T', 'POL']):
            # Look for similar IDs in the graph
            similar = [doc_id for doc_id in graph_doc_ids if doc_id.startswith(ref_id[:5])]
            if similar:
                normalization_issues.append({
                    'reference': ref_id,
                    'normalized': normalized,
                    'similar_docs': similar[:3],
                    'source_count': len(sources)
                })
    
    if normalization_issues:
        print(f"Found {len(normalization_issues)} potential normalization issues:")
        for issue in normalization_issues[:10]:
            print(f"\n  Reference: '{issue['reference']}'")
            print(f"  Normalized to: '{issue['normalized']}'")
            print(f"  Similar docs in graph: {issue['similar_docs']}")
            print(f"  Referenced by {issue['source_count']} documents")
    
    return unmatched_refs


def test_id_normalization():
    """Test the ID normalization functionality."""
    normalizer = IDNormalizer()
    
    test_cases = [
        ("F1301.1 REV F", "F1301.1F"),
        ("F1301.1F r00", "F1301.1F"),
        ("F1301.1F r01", "F1301.1F"),
        ("POL4000 r02", "POL4000"),
        ("G8100.1A", "G8100.1A"),
        ("P7301.1", "P7301.1"),
    ]
    
    print("ID Normalization Tests:")
    print("-" * 50)
    for input_id, expected in test_cases:
        result = normalizer.normalize(input_id)
        status = "[SUCCESS]" if result == expected else "[FAIL]"
        print(f"{status} '{input_id}' → '{result}' (expected: '{expected}')")
        

if __name__ == "__main__":
    # Run normalization tests
    test_id_normalization()
    
    # Example usage with your data
    print("\n" + "="*50)
    print("Building graph with normalized IDs...")
    
    # Load your content results
    with open('test_results/simple_extract.json', 'r') as f:
        content_results = json.load(f)
    
    # Build graph
    builder = GraphBuilder()
    builder.build_from_content_results(content_results)
    
    # Get statistics
    stats = builder.get_statistics()
    print(f"\nGraph Statistics:")
    print(f"- Nodes: {stats['node_count']}")
    print(f"- Edges: {stats['edge_count']}")
    print(f"- Average degree: {stats['avg_degree']:.2f}")
    print(f"- Unmatched references: {stats['normalization_stats']['unmatched_references']}")
    
    print(f"\nMost Referenced Documents:")
    for doc_id, count in stats['most_referenced'][:5]:
        print(f"  {doc_id}: {count} references")
    
    # Test impact analysis
    if stats['most_referenced']:
        test_doc = stats['most_referenced'][0][0]
        print(f"\nImpact Analysis for {test_doc}:")
        impacts = builder.find_impact_path(test_doc, max_depth=3, direction="both")
        for level, docs in sorted(impacts.items()):
            if docs:
                print(f"  {level}: {len(docs)} documents")
    
    # Export for visualization
    builder.export_for_visualization('test_results/normalized_graph.json')