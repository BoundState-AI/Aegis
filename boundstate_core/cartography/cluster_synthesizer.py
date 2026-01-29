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
BoundState Document Cartography - Cluster Synthesizer
Compliance: SWE-013, SWE-033

Analyzes document graph to detect semantic clusters, conflicts, and insights.
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Set, Any, Optional

import networkx as nx
import networkx.algorithms.community as nx_comm

from boundstate_core.cartography.graph_builder import GraphBuilder, DocumentNode

__all__ = ["DocumentCluster", "ConflictReport", "CartographyReport", "ClusterSynthesizer", "complete_cartography"]

logger = logging.getLogger(__name__)


@dataclass
class DocumentCluster:
    """Represents a cluster of semantically related documents."""
    
    cluster_id: str
    intent: str
    documents: List[str]
    dominant_tags: List[str]
    key_standards: List[str]
    hub_documents: List[str]
    label: str = ""
    confidence: float = 1.0
    risk_level: str = "normal"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConflictReport:
    """Represents a detected conflict between documents."""
    
    conflict_type: str  # 'version_conflict', 'circular_reference', etc.
    severity: str  # 'high', 'medium', 'low'
    documents: List[str]
    description: str
    suggested_action: str


@dataclass
class CartographyReport:
    """Complete document landscape analysis report."""
    
    total_documents: int
    total_connections: int
    unique_intents: List[str]
    clusters: List[DocumentCluster]
    conflicts: List[ConflictReport]
    high_risk_orphans: List[str]
    orphan_documents: List[str]
    missing_references: Dict[str, int]
    key_insights: List[str]
    next_actions: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class ClusterSynthesizer:
    """
    Synthesizes document clusters and generates insights.
    
    Compliance: SWE-033 - Document traceability
    """
    
    def __init__(self, graph_builder: GraphBuilder):
        self.graph_builder = graph_builder  # Store reference to access unmatched_references
        self.graph = graph_builder.graph
        self.nodes = graph_builder.nodes
        self.clusters: List[DocumentCluster] = []
        self.conflicts: List[ConflictReport] = []
        self.doc_to_cluster: Dict[str, str] = {}
        
        # Define intent patterns for classification
        self.intent_patterns = {
            'specification': ['specification', 'spec', 'requirement', 'standard'],
            'procedure': ['procedure', 'process', 'method', 'instruction'],
            'policy': ['policy', 'governance', 'guideline', 'directive'],
            'contract': ['contract', 'agreement', 'purchase', 'order'],
            'training': ['training', 'course', 'certification', 'qualification'],
            'safety': ['safety', 'hazard', 'risk', 'incident', 'accident'],
            'quality': ['quality', 'inspection', 'audit', 'nonconformance'],
            'maintenance': ['maintenance', 'repair', 'service', 'calibration'],
            'engineering': ['design', 'drawing', 'analysis', 'calculation'],
            'compliance': ['compliance', 'regulatory', 'approval', 'certification'],
            'hr': ['employee', 'personnel', 'hiring', 'benefits', 'payroll'],
            'finance': ['budget', 'cost', 'invoice', 'payment', 'expense'],
            'procurement': ['procurement', 'vendor', 'supplier', 'rfp', 'rfq'],
            'operations': ['operations', 'production', 'workflow', 'schedule'],
            'environmental': ['environmental', 'waste', 'emissions', 'sustainability'],
            'security': ['security', 'access', 'classified', 'confidential'],
            'research': ['research', 'development', 'test', 'prototype'],
            'documentation': ['manual', 'guide', 'reference', 'documentation']
        }
        
    def synthesize(self) -> CartographyReport:
        """Generate complete document landscape analysis."""
        logger.info("[INFO] Starting document cartography synthesis")
        
        # Detect semantic clusters
        self.clusters = self._detect_semantic_clusters()
        
        # Find conflicts
        self.conflicts = self._find_conflicts()
        
        # Identify orphans
        orphans = self._find_orphan_documents()
        
        # Identify high-risk orphans
        high_risk_orphans = []
        for orphan in orphans:
            if orphan in self.nodes:
                tags = self.nodes[orphan].tags
                risk = self._assess_cluster_risk(tags)
                if risk != 'normal':
                    high_risk_orphans.append(orphan)
        
        # Analyze missing references
        missing_refs = self._analyze_missing_references()
        
        # Generate insights
        insights = self._generate_insights()
        
        # Collect unique intents
        all_intents = set()
        for cluster in self.clusters:
            all_intents.add(cluster.intent)
            
        # Create report
        report = CartographyReport(
            total_documents=self.graph.number_of_nodes(),
            total_connections=self.graph.number_of_edges(),
            unique_intents=sorted(list(all_intents)),
            clusters=self.clusters,
            conflicts=self.conflicts,
            high_risk_orphans=high_risk_orphans,
            orphan_documents=orphans,
            missing_references=missing_refs,
            key_insights=insights,
            next_actions=self._suggest_next_actions(high_risk_orphans),
            metadata={
                'synthesis_complete': True,
                'version': '1.0'
            }
        )
        
        return report
    
    def _detect_semantic_clusters(self) -> List[DocumentCluster]:
        """Detect natural document clusters using community detection."""
        clusters = []  # Compliance: SWE-033
        
        # Skip if graph is empty
        if not self.graph.number_of_nodes():
            return clusters
        
        # Use Louvain community detection
        try:
            # Check for edge weights
            use_weights = any('weight' in data for _, _, data in self.graph.edges(data=True))
            if use_weights:
                communities = nx_comm.louvain_communities(self.graph.to_undirected(), weight='weight')
            else:
                communities = nx_comm.louvain_communities(self.graph.to_undirected())
        except:
            # Fallback for disconnected graphs
            communities = list(nx.connected_components(self.graph.to_undirected()))
        
        # Add singleton communities for orphan nodes
        all_nodes = set(self.graph.nodes())
        nodes_in_communities = set.union(*communities) if communities else set()
        
        orphans = all_nodes - nodes_in_communities
        for orphan in orphans:
            communities.append({orphan})
            
        # Build doc_to_cluster for later use
        self.doc_to_cluster = {}
        for i, community in enumerate(communities):
            cluster_id = f"cluster_{i+1}"
            for doc in community:
                self.doc_to_cluster[doc] = cluster_id
        
        # Analyze each community
        for i, community in enumerate(communities):
            if len(community) < 2:
                continue  # Skip singletons for cluster analysis
                
            cluster_id = f"cluster_{i+1}"
            cluster = self._analyze_community(community, cluster_id)
            clusters.append(cluster)
            
        return clusters
    
    def _analyze_community(self, community: Set[str], cluster_id: str) -> DocumentCluster:
        """Analyze a community to create a DocumentCluster."""
        docs = list(community)
        
        # Collect all text and metadata
        all_text = []
        all_tags = []
        all_types = []
        all_standards = []
        
        for doc_id in docs:
            if doc_id in self.nodes:
                node = self.nodes[doc_id]
                all_text.append(node.title.lower())
                all_text.append(node.doc_type.lower())
                all_tags.extend(node.tags)
                all_types.append(node.doc_type)
                
                # Extract standards from tags
                for tag in node.tags:
                    if any(std in tag for std in ['mil-std', 'nasa-std', 'astm', 'iso']):
                        all_standards.append(tag)
                        
        # Determine dominant intent
        intent_scores = defaultdict(int)
        combined_text = ' '.join(all_text)
        
        for intent, keywords in self.intent_patterns.items():
            for keyword in keywords:
                if keyword in combined_text:
                    intent_scores[intent] += combined_text.count(keyword)
                    
        # Get dominant intent
        if intent_scores:
            dominant_intent = max(intent_scores.items(), key=lambda x: x[1])[0]
        else:
            dominant_intent = 'general'
            
        # Get dominant tags
        tag_counts = Counter(all_tags)
        dominant_tags = [tag for tag, _ in tag_counts.most_common(5)]
        
        # Find hub documents (highest degree centrality in subgraph)
        # Compliance: SWE-013
        subgraph = self.graph.subgraph(community)
        centrality = nx.degree_centrality(subgraph)
        hub_docs = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:3]
        hub_docs = [doc for doc, _ in hub_docs]
        
        # Assess risk level
        risk_level = self._assess_cluster_risk(all_tags)
        
        # Calculate intent confidence
        total_scores = sum(intent_scores.values())
        confidence = intent_scores[dominant_intent] / total_scores if total_scores > 0 else 0.0
        
        # Generate label from hub title
        label = cluster_id
        if hub_docs:
            hub_node = self.nodes.get(hub_docs[0])
            if hub_node and hub_node.title:
                label = hub_node.title.strip()[:50]
        
        # Calculate reference density
        total_outbound = sum(self.graph.out_degree(n) for n in docs)
        
        # Create cluster
        cluster = DocumentCluster(
            cluster_id=cluster_id,
            intent=dominant_intent,
            documents=docs,
            dominant_tags=dominant_tags,
            key_standards=list(set(all_standards)),
            hub_documents=hub_docs,
            label=label,
            confidence=confidence,
            risk_level=risk_level,
            metadata={
                'size': len(docs),
                'density': nx.density(subgraph),
                'doc_types': Counter(all_types),
                'reference_density': total_outbound / len(docs) if len(docs) > 0 else 0.0
            }
        )
        
        return cluster
    
    def _assess_cluster_risk(self, tags: List[str]) -> str:
        """Assess risk level based on tags."""
        high_risk_keywords = ['deprecated', 'obsolete', 'draft', 'preliminary', 'unapproved']
        medium_risk_keywords = ['review', 'update', 'revision', 'pending']
        
        tags_lower = [tag.lower() for tag in tags]
        
        for keyword in high_risk_keywords:
            if any(keyword in tag for tag in tags_lower):
                return 'high'
                
        for keyword in medium_risk_keywords:
            if any(keyword in tag for tag in tags_lower):
                return 'medium'
                
        return 'normal'
    
    def _find_conflicts(self) -> List[ConflictReport]:
        """Detect various types of conflicts in the document graph."""
        conflicts = []
        
        # Check for version conflicts
        version_groups = defaultdict(list)
        for doc_id, node in self.nodes.items():
            version_groups[node.base_doc_id].append((doc_id, node))
            
        for base_id, versions in version_groups.items():
            if len(versions) > 1:
                # Sort by version
                versions.sort(key=lambda x: x[1].version_tuple, reverse=True)
                
                # Check if multiple versions are referenced
                referenced_versions = []
                for doc_id, node in versions:
                    if self.graph.in_degree(doc_id) > 0:
                        referenced_versions.append(doc_id)
                        
                if len(referenced_versions) > 1:
                    conflicts.append(ConflictReport(
                        conflict_type='version_conflict',
                        severity='high',
                        documents=referenced_versions,
                        description=f"Multiple versions of {base_id} are actively referenced",
                        suggested_action="Standardize to latest version or document version-specific requirements"
                    ))
                    
        # Check for version drift across clusters
        if hasattr(self, 'doc_to_cluster'):
            version_groups = defaultdict(list)
            for doc_id, node in self.nodes.items():
                version_groups[node.base_doc_id].append(doc_id)
            
            for base_id, versions in version_groups.items():
                if len(versions) > 1:
                    clusters = set(self.doc_to_cluster.get(v, '') for v in versions)
                    clusters.discard('')  # Remove empty cluster IDs
                    if len(clusters) > 1:
                        conflicts.append(ConflictReport(
                            conflict_type='version_drift',
                            severity='medium',
                            documents=versions,
                            description=f"Versions of {base_id} spread across {len(clusters)} clusters",
                            suggested_action="Investigate divergent usage or ownership"
                        ))
        
        # Check for circular references
        try:
            cycles = list(nx.simple_cycles(self.graph))
            if cycles:
                for cycle in cycles[:5]:  # Limit to first 5
                    conflicts.append(ConflictReport(
                        conflict_type='circular_reference',
                        severity='medium',
                        documents=cycle,
                        description=f"Circular reference chain: {' -> '.join(cycle)}",
                        suggested_action="Review dependency structure and break circular dependencies"
                    ))
        except:
            pass  # Graph might not support cycle detection
            
        # Check for potential duplicates
        title_groups = defaultdict(list)
        for doc_id, node in self.nodes.items():
            # Normalize title for comparison
            normalized = node.title.lower().strip()
            title_groups[normalized].append(doc_id)
            
        for title, docs in title_groups.items():
            if len(docs) > 1:
                conflicts.append(ConflictReport(
                    conflict_type='potential_duplicate',
                    severity='low',
                    documents=docs,
                    description=f"Multiple documents with similar title: '{title}'",
                    suggested_action="Verify if these are duplicates or need title clarification"
                ))
                
        return conflicts
    
    def _find_orphan_documents(self) -> List[str]:
        """Find documents with no connections."""
        orphans = []
        
        for node in self.graph.nodes():
            if self.graph.degree(node) == 0:
                orphans.append(node)
                
        return orphans
    
    def _analyze_missing_references(self) -> Dict[str, int]:
        """Analyze references to missing documents."""
        missing_refs = defaultdict(int)
        
        # Access unmatched references from GraphBuilder
        if hasattr(self.graph_builder, 'unmatched_references'):
            # Count occurrences of each unmatched reference
            for ref_id, sources in self.graph_builder.unmatched_references.items():
                missing_refs[ref_id] = len(sources)
        
        return dict(missing_refs)
    
    def _generate_insights(self) -> List[str]:
        """Generate key insights from the analysis."""
        insights = []
        
        # Cluster insights
        if self.clusters:
            largest_cluster = max(self.clusters, key=lambda c: len(c.documents))
            insights.append(
                f"Largest cluster: {largest_cluster.intent} with {len(largest_cluster.documents)} documents"
            )
            
            # Intent diversity
            intents = set(c.intent for c in self.clusters)
            insights.append(f"Document corpus spans {len(intents)} distinct intents")
            
        # Risk insights
        high_risk_clusters = [c for c in self.clusters if c.risk_level == 'high']
        if high_risk_clusters:
            insights.append(
                f"{len(high_risk_clusters)} clusters contain high-risk documents (draft/deprecated)"
            )
            
        # Connectivity insights
        if self.graph.number_of_nodes() > 0:
            avg_degree = 2 * self.graph.number_of_edges() / self.graph.number_of_nodes()
            insights.append(f"Average document connectivity: {avg_degree:.1f} references per document")
            
        # Standards usage
        all_standards = set()
        for cluster in self.clusters:
            all_standards.update(cluster.key_standards)
        if all_standards:
            insights.append(f"References {len(all_standards)} different standards/specifications")
            
        return insights
    
    def _suggest_next_actions(self, high_risk_orphans: List[str]) -> List[str]:
        """Suggest actionable next steps based on analysis."""
        actions = []
        
        # Actions for conflicts
        if self.conflicts:
            high_severity = [c for c in self.conflicts if c.severity == 'high']
            if high_severity:
                actions.append(
                    f"Resolve {len(high_severity)} high-severity conflicts (version conflicts, etc.)"
                )
                
            drift_conflicts = [c for c in self.conflicts if c.conflict_type == 'version_drift']
            if drift_conflicts:
                actions.append(f"Investigate {len(drift_conflicts)} version drift cases across clusters")
        
        # Actions for orphans
        orphan_count = len(self._find_orphan_documents())
        if orphan_count > 10:
            actions.append(
                f"Review {orphan_count} orphan documents for potential archival or connection"
            )
            
        # Action for high-risk orphans
        if high_risk_orphans:
            actions.append(f"Prioritize review of {len(high_risk_orphans)} high-risk orphan documents")
            
        # Action for risk items
        risk_clusters = [c for c in self.clusters if c.risk_level in ['high', 'medium']]
        if risk_clusters:
            actions.append(
                f"Update or finalize documents in {len(risk_clusters)} at-risk clusters"
            )
            
        # Action for small clusters
        small_clusters = [c for c in self.clusters if len(c.documents) < 3]
        if len(small_clusters) > 5:
            actions.append(
                f"Consider consolidating {len(small_clusters)} small clusters (< 3 documents)"
            )
            
        return actions
    
    def print_report(self, report: CartographyReport):
        """Print a formatted report to console."""
        print("\n" + "="*60)
        print("📊 DOCUMENT CARTOGRAPHY SYNTHESIS REPORT")
        print("="*60)
        
        print(f"\n📈 Overview:")
        print(f"   {report.total_documents} documents analyzed")
        print(f"   {report.total_connections} connections mapped")
        print(f"   {len(report.unique_intents)} unique intents")
        print(f"   {len(report.clusters)} dominant clusters:")
        
        for cluster in sorted(report.clusters[:4], key=lambda c: c.confidence, reverse=True):
            print(f"\n   [+] {cluster.intent.title()} ({len(cluster.documents)} documents)")
            print(f"      Tags: {', '.join(cluster.dominant_tags[:3])}")
            if cluster.key_standards:
                print(f"      Standards: {', '.join(cluster.key_standards[:3])}")
            print(f"      Hub: {cluster.hub_documents[0] if cluster.hub_documents else 'None'}")
            
        if report.conflicts:
            print(f"\n[!] Conflicts Detected: {len(report.conflicts)}")
            print(f"   High-risk orphans: {len(report.high_risk_orphans)}")
            for conflict in report.conflicts[:3]:
                print(f"   - {conflict.description}")
                
        if report.orphan_documents:
            print(f"\n📄 Orphan Documents: {len(report.orphan_documents)}")
            print(f"   Examples: {', '.join(report.orphan_documents[:5])}")
            
        if report.missing_references:
            print(f"\n[?] Missing References:")
            if report.clusters:
                print(f"   Reference density in largest cluster: {report.clusters[0].metadata.get('reference_density', 0):.2f}")
            for ref, count in list(report.missing_references.items())[:3]:
                print(f"   - '{ref}' referenced {count} times")
                
        print(f"\n[+] Key Insights:")
        for insight in report.key_insights:
            print(f"   - {insight}")
            
        print(f"\n🎯 Recommended Actions:")
        for action in report.next_actions:
            print(f"   1. {action}")
            
        print("\n" + "="*60 + "\n")


def complete_cartography(graph_builder: GraphBuilder) -> CartographyReport:
    """
    Complete the document cartography process.
    
    Args:
        graph_builder: Populated GraphBuilder instance
        
    Returns:
        CartographyReport with full analysis
        
    Compliance: SWE-033
    """
    synthesizer = ClusterSynthesizer(graph_builder)
    report = synthesizer.synthesize()
    
    # Optional: print report
    synthesizer.print_report(report)
    
    return report