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
BoundState Document Cartography Pipeline
Complete integration of all cartography components.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

from boundstate.cartographer import (
    ContentMiner,
    GraphBuilder,
    complete_cartography,
    PhraseExtractor,
    calculate_semantic_overlap
)
from boundstate_core.cartography.compliance_mapping import ComplianceMapper

logger = logging.getLogger(__name__)


class CartographyPipeline:
    """Complete document cartography pipeline."""
    
    def __init__(self, output_dir: str = "cartography_output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.content_miner = ContentMiner()
        self.phrase_extractor = PhraseExtractor()
        self.graph_builder = None
        self.report = None
        
    def analyze_corpus(self, documents: List[Dict[str, Any]], as9100_text: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze a complete document corpus.
        
        Args:
            documents: List of document dicts with 'doc_id', 'text', 'metadata'
            as9100_text: Optional AS9100 standard text for compliance mapping
            
        Returns:
            Complete analysis results
        """
        logger.info(f"Starting cartography analysis of {len(documents)} documents")
        
        # Phase 1: Content Mining
        logger.info("Phase 1: Mining content from documents")
        content_results = self._mine_all_content(documents)
        
        # Phase 2: Phrase Extraction (for semantic overlap)
        logger.info("Phase 2: Extracting phrases for semantic analysis")
        phrase_results = self._extract_all_phrases(documents)
        
        # Phase 3: Build Graph
        logger.info("Phase 3: Building document relationship graph")
        self.graph_builder = self._build_graph(content_results)
        
        # Phase 4: Cluster Synthesis
        logger.info("Phase 4: Synthesizing clusters and insights")
        self.report = complete_cartography(self.graph_builder)
        
        # Phase 5: Enhance with semantic overlaps
        logger.info("Phase 5: Computing semantic overlaps")
        semantic_edges = self._compute_semantic_overlaps(phrase_results)
        
        # Save all outputs
        self._save_outputs(content_results, phrase_results, semantic_edges)
        
        result = {
            "content_results": content_results,
            "graph_stats": self.graph_builder.get_statistics(),
            "cartography_report": self.report,
            "semantic_edges": semantic_edges
        }
        
        # Phase 6: AS9100 Compliance Mapping (if standard provided)
        if as9100_text:
            logger.info("Phase 6: AS9100 compliance mapping")
            compliance_report = self._map_as9100_compliance(
                phrase_results, 
                as9100_text
            )
            
            # Add to outputs
            with open(self.output_dir / "as9100_compliance.json", "w") as f:
                json.dump(compliance_report, f, indent=2)
                
            result["as9100_compliance"] = compliance_report
            
        return result
    
    def _mine_all_content(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Mine content from all documents."""
        results = {
            "results": [],
            "summary": {
                "total_documents": len(documents),
                "total_references": 0,
                "total_entities": 0
            }
        }
        
        for doc in documents:
            doc_id = doc.get("doc_id", "unknown")
            text = doc.get("text", "")
            
            if not text:
                logger.warning(f"No text for document {doc_id}")
                continue
                
            try:
                content = self.content_miner.mine_content(text, doc.get("metadata"))
                
                result = {
                    "doc_id": doc_id,
                    "status": "success",
                    "references": content.references,
                    "entities": content.entities,
                    "tags": content.tags,
                    "issues": content.issues,
                    "confidence": content.confidence
                }
                
                results["results"].append(result)
                results["summary"]["total_references"] += len(content.references)
                results["summary"]["total_entities"] += sum(
                    len(ents) for ents in content.entities["verified"].values()
                )
                
            except Exception as e:
                logger.error(f"Error mining content from {doc_id}: {e}")
                results["results"].append({
                    "doc_id": doc_id,
                    "status": "error",
                    "error": str(e)
                })
                
        return results
    
    def _extract_all_phrases(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract phrases from all documents."""
        phrase_results = {}
        
        for doc in documents:
            doc_id = doc.get("doc_id", "unknown")
            text = doc.get("text", "")
            
            if not text:
                continue
                
            try:
                phrases = self.phrase_extractor.extract(
                    text=text,
                    source=doc_id
                )
                phrase_results[doc_id] = phrases
                
            except Exception as e:
                logger.error(f"Error extracting phrases from {doc_id}: {e}")
                
        return phrase_results
    
    def _build_graph(self, content_results: Dict[str, Any]) -> GraphBuilder:
        """Build document graph from content results."""
        builder = GraphBuilder()
        
        # First add all documents as nodes
        for result in content_results["results"]:
            if result.get("status") == "success":
                builder.add_document(
                    doc_id=result["doc_id"],
                    doc_type="unknown",  # Would need to infer or get from metadata
                    title=result.get("doc_id", ""),
                    metadata={}
                )
        
        # Then build from content results (adds edges)
        builder.build_from_content_results(content_results)
        
        return builder
    
    def _compute_semantic_overlaps(
        self, 
        phrase_results: Dict[str, Any],
        min_overlap: float = 0.4
    ) -> List[Dict[str, Any]]:
        """Compute semantic overlaps between documents."""
        semantic_edges = []
        doc_ids = list(phrase_results.keys())
        
        for i, doc1_id in enumerate(doc_ids):
            for doc2_id in doc_ids[i+1:]:
                overlap = calculate_semantic_overlap(
                    phrase_results[doc1_id],
                    phrase_results[doc2_id],
                    min_overlap=min_overlap
                )
                
                if overlap["is_significant"]:
                    semantic_edges.append({
                        "source": doc1_id,
                        "target": doc2_id,
                        "type": "semantic_overlap",
                        "overlap_ratio": overlap["overlap_ratio"],
                        "shared_terms": overlap["shared_terms"][:10],  # Top 10
                        "shared_compliance": overlap["shared_compliance_refs"]
                    })
                    
        return semantic_edges
    
    def _save_outputs(
        self,
        content_results: Dict[str, Any],
        phrase_results: Dict[str, Any],
        semantic_edges: List[Dict[str, Any]]
    ):
        """Save all outputs to files."""
        # Save content mining results
        with open(self.output_dir / "content_mining.json", "w") as f:
            json.dump(content_results, f, indent=2)
            
        # Save phrase extraction results
        with open(self.output_dir / "phrase_extraction.json", "w") as f:
            json.dump(
                {k: v.model_dump() if hasattr(v, 'model_dump') else v 
                 for k, v in phrase_results.items()},
                f, indent=2
            )
            
        # Save graph for visualization
        if self.graph_builder:
            self.graph_builder.export_for_visualization(
                str(self.output_dir / "document_graph.json")
            )
            
        # Save semantic edges
        with open(self.output_dir / "semantic_edges.json", "w") as f:
            json.dump(semantic_edges, f, indent=2)
            
        # Save cartography report
        if self.report:
            with open(self.output_dir / "cartography_report.json", "w") as f:
                json.dump({
                    "total_documents": self.report.total_documents,
                    "total_connections": self.report.total_connections,
                    "unique_intents": self.report.unique_intents,
                    "clusters": [
                        {
                            "cluster_id": c.cluster_id,
                            "intent": c.intent,
                            "size": len(c.documents),
                            "label": c.label,
                            "confidence": c.confidence,
                            "risk_level": c.risk_level,
                            "hub_documents": c.hub_documents[:3]
                        }
                        for c in self.report.clusters
                    ],
                    "conflicts": [
                        {
                            "type": c.conflict_type,
                            "severity": c.severity,
                            "description": c.description
                        }
                        for c in self.report.conflicts
                    ],
                    "insights": self.report.key_insights,
                    "actions": self.report.next_actions
                }, f, indent=2)
    
    def _map_as9100_compliance(
        self,
        phrase_results: Dict[str, Any],
        as9100_text: str
    ) -> Dict[str, Any]:
        """Map documents to AS9100 compliance requirements."""
        # Initialize compliance mapper
        compliance_mapper = ComplianceMapper(as9100_text)
        
        # Map documents to clauses
        document_mappings = compliance_mapper.map_documents_to_clauses(
            phrase_results,
            min_overlap=0.3
        )
        
        # Generate compliance matrix
        compliance_matrix = compliance_mapper.generate_compliance_matrix(
            document_mappings,
            self.graph_builder
        )
        
        # Create compliance report
        compliance_report = {
            "as9100_version": getattr(compliance_mapper.analyzer, 'version', 'Unknown'),
            "total_clauses": len(compliance_mapper.analyzer.clauses),
            "covered_clauses": len([c for c in compliance_matrix if compliance_matrix[c]['documents']]),
            "coverage_percentage": (len([c for c in compliance_matrix if compliance_matrix[c]['documents']]) / 
                                  len(compliance_mapper.analyzer.clauses) * 100) if compliance_mapper.analyzer.clauses else 0,
            "document_mappings": {
                doc_id: [
                    {
                        "clause_id": clause_id,
                        "overlap_score": score,
                        "clause_title": getattr(compliance_mapper.analyzer.clause_map.get(clause_id), 'title', '')
                    }
                    for clause_id, score in mappings
                ]
                for doc_id, mappings in document_mappings.items()
            },
            "compliance_matrix": compliance_matrix,
            "gaps": [
                {
                    "clause_id": clause_id,
                    "clause_title": clause_data.get('title', ''),
                    "importance": clause_data.get('importance', 'Medium')
                }
                for clause_id, clause_data in compliance_matrix.items()
                if not clause_data['documents']
            ]
        }
        
        logger.info(f"AS9100 compliance mapping complete: {compliance_report['coverage_percentage']:.1f}% coverage")
        
        return compliance_report


# Integration with your existing BoundState system
def integrate_with_boundstate():
    """Example of integrating with existing BoundState index."""
    from boundstate_core.storage.index import SemanticIndex
    
    # Load existing documents from BoundState index
    semantic_index = SemanticIndex()
    
    # Get all documents
    documents = []
    for doc_id, sections in semantic_index.sections.items():
        # Combine sections into full document text
        full_text = "\n\n".join(sec["text"] for sec in sections)
        documents.append({
            "doc_id": doc_id,
            "text": full_text,
            "metadata": {
                "doc_type": sections[0].get("doc_type", "unknown"),
                "tags": sections[0].get("tags", [])
            }
        })
    
    # Run cartography pipeline
    pipeline = CartographyPipeline()
    results = pipeline.analyze_corpus(documents)
    
    return results


if __name__ == "__main__":
    # Example usage with your test data
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--from-index":
        # Run on existing BoundState index
        results = integrate_with_boundstate()
        print(f"Analyzed {results['cartography_report'].total_documents} documents")
        print(f"Found {len(results['cartography_report'].clusters)} clusters")
        
    else:
        # Run on test extraction results
        with open("test_results/simple_extract.json", "r") as f:
            content_results = json.load(f)
            
        # Convert to document format
        documents = []
        for result in content_results.get("results", []):
            if result.get("status") == "success":
                documents.append({
                    "doc_id": result["doc_id"],
                    "text": result.get("text", ""),  # Would need actual text
                    "metadata": {}
                })
        
        pipeline = CartographyPipeline()
        results = pipeline.analyze_corpus(documents)
        
        print("Cartography analysis complete!")
        print(f"Outputs saved to: {pipeline.output_dir}")