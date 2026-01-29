#!/usr/bin/env python3
"""
Module: knowledge
Purpose: AEGIS knowledge graph components for PFAS degradation pathways.
    Exports PFASKnowledgeGraph, build_graph, trace_pathways, and
    get_downstream_products for pathway analysis and risk assessment.

    Rev History:
        1.0.0 - Initial knowledge graph package

BoundState AI 2025
Version: 1.0.0
Classification: BoundState Proprietary

Authored-By: Dr. Joseph Wilde, BoundState AI
Oracle 1: ClaudeOpus 4.5 <noreply@anthropic.com>
Oracle 2: Fran OpenAI 5.2 <noreply@openai.com>
Oracle 3: Grok 4.0 <noreply@x.ai>

"""

from boundstate_aegis.knowledge.graph_builder import PFASKnowledgeGraph, build_graph
from boundstate_aegis.knowledge.graph_queries import trace_pathways, get_downstream_products

__all__ = [
    "PFASKnowledgeGraph",
    "build_graph",
    "trace_pathways",
    "get_downstream_products",
]
