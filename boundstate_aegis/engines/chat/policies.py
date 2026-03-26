#!/usr/bin/env python3
"""
Static page policies for bounded AEGIS chat.
"""

from __future__ import annotations

from typing import Any


PAGE_POLICIES: dict[str, dict[str, Any]] = {
    "fate-explorer": {
        "page_label": "Fate Explorer",
        "supported_question_types": [
            "help_capability",
            "page_summary",
            "explain_visible_result",
            "compare_visible_results",
            "filter_guidance",
        ],
        "forbidden_question_types": [
            "portfolio_risk",
            "legal_advice",
            "enterprise_strategy",
        ],
        "clarification_fields": [
            {"field": "parent", "required_for": ["page_summary", "explain_visible_result"], "source": "visible_state"},
            {"field": "temp_min", "required_for": ["filter_guidance"], "source": "visible_state"},
            {"field": "temp_max", "required_for": ["filter_guidance"], "source": "visible_state"},
            {"field": "atmosphere", "required_for": ["filter_guidance"], "source": "visible_state"},
            {"field": "min_observations", "required_for": ["filter_guidance"], "source": "visible_state"},
        ],
        "allowed_actions": ["read_only"],
        "handoff_targets": ["regulatory", "litigation", "portfolio"],
        "handoff_keywords": {
            "portfolio": ["portfolio", "prioritize", "priority", "riskiest", "exposure"],
            "regulatory": ["regulated", "regulation", "compliance", "echa", "eu", "japan", "restriction"],
            "litigation": ["litigation", "lawsuit", "settlement", "legal", "sue"],
        },
        "allowed_visible_state_keys": {
            "parent",
            "temp_min",
            "temp_max",
            "atmosphere",
            "min_observations",
            "total_transformations",
            "visible_transformations",
        },
        "starter_questions": [
            "What degradation products are visible for this parent compound?",
            "Why is a visible product marked high hazard?",
            "How are the current filters affecting the visible pathway set?",
        ],
    },
    "regulatory": {
        "page_label": "Regulatory Compliance",
        "supported_question_types": [
            "help_capability",
            "page_summary",
            "explain_visible_result",
            "compare_visible_results",
            "filter_guidance",
        ],
        "forbidden_question_types": [
            "legal_advice",
            "portfolio_risk",
            "policy_recommendation",
        ],
        "clarification_fields": [
            {"field": "material", "required_for": ["page_summary", "explain_visible_result"], "source": "visible_state"},
            {"field": "forecast_year", "required_for": ["filter_guidance"], "source": "visible_state"},
            {
                "field": "include_degradation",
                "required_for": ["filter_guidance"],
                "source": "visible_state",
                "allowed_values": ["true", "false"],
            },
            {"field": "active_subview", "required_for": ["page_summary"], "source": "visible_state"},
        ],
        "allowed_actions": ["read_only"],
        "handoff_targets": ["reports", "portfolio"],
        "handoff_keywords": {
            "reports": ["report", "briefing", "executive summary", "memo", "deck"],
            "portfolio": ["portfolio", "prioritize", "priority", "exposure"],
        },
        "allowed_visible_state_keys": {
            "material",
            "include_degradation",
            "forecast_year",
            "active_subview",
            "overall_risk",
            "frameworks_checked",
            "compliant_count",
            "warning_count",
            "non_compliant_count",
            "sample_findings",
            "cascade_predictions",
        },
        "starter_questions": [
            "What is the current overall risk on this page?",
            "How does the include degradation toggle affect the current screen?",
            "What forecast stage is visible for the selected year?",
        ],
    },
    "litigation": {
        "page_label": "Litigation Risk",
        "supported_question_types": [
            "help_capability",
            "page_summary",
            "explain_visible_result",
            "compare_visible_results",
            "filter_guidance",
        ],
        "forbidden_question_types": [
            "legal_advice",
            "settlement_prediction",
            "enterprise_strategy",
        ],
        "clarification_fields": [
            {"field": "selected_compound", "required_for": ["page_summary", "explain_visible_result"], "source": "visible_state"},
            {"field": "chart_view", "required_for": ["filter_guidance"], "source": "visible_state"},
        ],
        "allowed_actions": ["read_only"],
        "handoff_targets": ["reports", "regulatory", "portfolio"],
        "handoff_keywords": {
            "reports": ["report", "briefing", "memo", "deck"],
            "regulatory": ["compliance", "regulation", "regulated", "restriction"],
            "portfolio": ["portfolio", "prioritize", "priority", "exposure mix"],
        },
        "allowed_visible_state_keys": {
            "selected_compound",
            "chart_view",
            "available_backtests",
            "forecast_risk_level",
            "probability_12_months",
            "probability_24_months",
            "probability_36_months",
            "estimated_exposure_usd",
            "key_drivers",
            "visible_similar_cases",
            "backtest_publications",
            "first_lawsuit_year",
            "lead_time_years",
            "paper_drilldown_year",
            "paper_drilldown_total",
        },
        "starter_questions": [
            "What is the visible litigation risk forecast for this compound?",
            "What does the current backtest show on this page?",
            "Which similar cases are visible right now?",
        ],
    },
    "portfolio": {
        "page_label": "Portfolio Assessment",
        "supported_question_types": [
            "help_capability",
            "page_summary",
            "explain_visible_result",
            "compare_visible_results",
            "filter_guidance",
        ],
        "forbidden_question_types": [
            "legal_advice",
            "regulatory_conclusion",
            "workflow_submission",
        ],
        "clarification_fields": [
            {"field": "items", "required_for": ["page_summary"], "source": "visible_state"},
            {"field": "top_results", "required_for": ["explain_visible_result"], "source": "visible_state"},
        ],
        "allowed_actions": ["read_only"],
        "handoff_targets": ["reports", "regulatory", "litigation"],
        "handoff_keywords": {
            "reports": ["report", "briefing", "memo", "deck"],
            "regulatory": ["compliance", "regulation", "restricted", "banned"],
            "litigation": ["lawsuit", "settlement", "litigation", "legal"],
        },
        "allowed_visible_state_keys": {
            "items",
            "total_materials",
            "high_risk_count",
            "total_exposure_usd",
            "top_results",
        },
        "starter_questions": [
            "What is the current portfolio summary on this page?",
            "Which visible material is highest risk here?",
            "How much exposure is shown on the current portfolio screen?",
        ],
    },
    "reports": {
        "page_label": "Executive Reports",
        "supported_question_types": [
            "help_capability",
            "page_summary",
            "explain_visible_result",
            "compare_visible_results",
            "filter_guidance",
        ],
        "forbidden_question_types": [
            "legal_advice",
            "portfolio_rebalancing",
            "workflow_submission",
        ],
        "clarification_fields": [
            {"field": "material", "required_for": ["page_summary"], "source": "visible_state"},
            {"field": "visible_sections", "required_for": ["explain_visible_result"], "source": "visible_state"},
        ],
        "allowed_actions": ["read_only"],
        "handoff_targets": ["regulatory", "litigation", "portfolio"],
        "handoff_keywords": {
            "regulatory": ["compliance", "regulation", "regulated", "restriction"],
            "litigation": ["lawsuit", "settlement", "litigation", "legal"],
            "portfolio": ["portfolio", "prioritize", "priority", "exposure"],
        },
        "allowed_visible_state_keys": {
            "material",
            "include_litigation",
            "include_regulatory",
            "generated",
            "classification",
            "visible_sections",
        },
        "starter_questions": [
            "What sections are visible in the current report?",
            "What is the current report classification?",
            "How do the litigation and regulatory toggles affect this report?",
        ],
    },
    "evidence": {
        "page_label": "Evidence Chain",
        "supported_question_types": [
            "help_capability",
            "page_summary",
            "explain_visible_result",
            "compare_visible_results",
            "filter_guidance",
        ],
        "forbidden_question_types": [
            "legal_advice",
            "portfolio_risk",
            "workflow_submission",
        ],
        "clarification_fields": [
            {"field": "material", "required_for": ["page_summary"], "source": "visible_state"},
            {"field": "visible_evidence", "required_for": ["explain_visible_result"], "source": "visible_state"},
            {"field": "max_citations", "required_for": ["filter_guidance"], "source": "visible_state"},
        ],
        "allowed_actions": ["read_only"],
        "handoff_targets": ["analysis", "fate-explorer", "reports"],
        "handoff_keywords": {
            "analysis": ["analyze", "formation", "conditions", "temperature"],
            "fate-explorer": ["pathway", "degradation", "product", "atmosphere"],
            "reports": ["report", "briefing", "memo"],
        },
        "allowed_visible_state_keys": {
            "material",
            "max_citations",
            "total_citations",
            "confidence_score",
            "database_total_papers",
            "total_pathway_citations",
            "visible_evidence",
        },
        "starter_questions": [
            "What evidence is visible for this material?",
            "What is the current evidence confidence on this page?",
            "Which source is shown with the strongest visible support?",
        ],
    },
    "analysis": {
        "page_label": "PFAS Analysis",
        "supported_question_types": [
            "help_capability",
            "page_summary",
            "explain_visible_result",
            "compare_visible_results",
            "filter_guidance",
        ],
        "forbidden_question_types": [
            "legal_advice",
            "enterprise_strategy",
            "workflow_submission",
        ],
        "clarification_fields": [
            {"field": "material", "required_for": ["page_summary"], "source": "visible_state"},
            {"field": "visible_findings", "required_for": ["explain_visible_result"], "source": "visible_state"},
            {"field": "temperature_c", "required_for": ["filter_guidance"], "source": "visible_state"},
            {"field": "atmosphere", "required_for": ["filter_guidance"], "source": "visible_state"},
            {"field": "time_hours", "required_for": ["filter_guidance"], "source": "visible_state"},
        ],
        "allowed_actions": ["read_only"],
        "handoff_targets": ["evidence", "fate-explorer", "regulatory"],
        "handoff_keywords": {
            "evidence": ["citation", "paper", "doi", "evidence"],
            "fate-explorer": ["pathway", "network", "degradation pathway"],
            "regulatory": ["regulation", "compliance", "restricted", "banned"],
        },
        "allowed_visible_state_keys": {
            "material",
            "temperature_c",
            "atmosphere",
            "time_hours",
            "findings_count",
            "summary",
            "visible_findings",
        },
        "starter_questions": [
            "What degradation findings are visible for these conditions?",
            "How do the current analysis inputs affect this screen?",
            "Which visible product has the strongest support here?",
        ],
    },
    "tier1": {
        "page_label": "Structural Similarity",
        "supported_question_types": [
            "help_capability",
            "page_summary",
            "explain_visible_result",
            "compare_visible_results",
            "filter_guidance",
        ],
        "forbidden_question_types": [
            "legal_advice",
            "enterprise_strategy",
            "workflow_submission",
        ],
        "clarification_fields": [
            {"field": "compound_name", "required_for": ["page_summary"], "source": "visible_state"},
            {"field": "similar_compounds", "required_for": ["explain_visible_result"], "source": "visible_state"},
        ],
        "allowed_actions": ["read_only"],
        "handoff_targets": ["evidence", "fate-explorer", "regulatory"],
        "handoff_keywords": {
            "evidence": ["citation", "paper", "doi", "evidence"],
            "fate-explorer": ["pathway", "degradation", "product"],
            "regulatory": ["regulation", "compliance", "restricted", "banned"],
        },
        "allowed_visible_state_keys": {
            "compound_name",
            "query_smiles",
            "risk_signal",
            "neighbors_with_pathways",
            "avg_similarity",
            "top_endpoints",
            "similar_compounds",
            "tier2_pattern_count",
            "tier2_rule_total",
            "coverage_resolution_rate",
        },
        "starter_questions": [
            "What structural risk signal is visible for this query?",
            "Which similar compounds are currently shown?",
            "What endpoint patterns are visible on this page?",
        ],
    },
}


def get_page_policy(page_id: str) -> dict[str, Any] | None:
    return PAGE_POLICIES.get(page_id)
