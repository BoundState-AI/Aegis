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
}


def get_page_policy(page_id: str) -> dict[str, Any] | None:
    return PAGE_POLICIES.get(page_id)
