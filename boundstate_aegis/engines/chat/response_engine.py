#!/usr/bin/env python3
"""
Deterministic response engine for AEGIS bounded chat MVP.
"""

from __future__ import annotations

from typing import Any

from boundstate_aegis.models.chat_models import AuthoritativeAnswerSurface, ChatDecision, ChatStatus


def _human_bool(value: Any) -> str:
    return "on" if bool(value) else "off"


def _fate_capability(surface: AuthoritativeAnswerSurface) -> ChatDecision:
    return ChatDecision(
        status=ChatStatus.SUPPORTED,
        question_type="help_capability",
        response_text=(
            "This page can explain the visible degradation pathways, current filters, visible hazard labels, "
            "and which displayed products are marked regulated. It cannot rank enterprise portfolio risk or give litigation advice."
        ),
        citations=["active_filters", "visible_transformations"],
        handoff_targets=surface.handoff_targets,
    )


def _regulatory_capability(surface: AuthoritativeAnswerSurface) -> ChatDecision:
    return ChatDecision(
        status=ChatStatus.SUPPORTED,
        question_type="help_capability",
        response_text=(
            "This page can explain the visible regulatory risk summary, the loaded framework findings, the current "
            "forecast year, and the effect of the include degradation toggle. It cannot provide legal advice or portfolio prioritization."
        ),
        citations=["regulatory_summary", "sample_findings", "cascade_predictions"],
        handoff_targets=surface.handoff_targets,
    )


def _fate_response(question_type: str, evidence: dict[str, Any], surface: AuthoritativeAnswerSurface) -> ChatDecision:
    filters = evidence["filters"]
    visible_transformations = evidence["visible_transformations"]
    matched = evidence["matched_items"]

    if question_type == "help_capability":
        return _fate_capability(surface)

    if question_type == "page_summary":
        top = visible_transformations[:3]
        if top:
            preview = "; ".join(
                f"{row['product']} ({row.get('hazard_level') or 'UNKNOWN'} hazard, {row.get('source_count', 0)} source{'s' if row.get('source_count', 0) != 1 else ''})"
                for row in top
            )
        else:
            preview = "No visible transformations are loaded yet."
        return ChatDecision(
            status=ChatStatus.SUPPORTED,
            question_type=question_type,
            response_text=(
                f"Fate Explorer is currently screening {filters['parent']} from {filters['temp_min']} to {filters['temp_max']} C "
                f"with atmosphere '{filters['atmosphere']}' and minimum observations {filters['min_observations']}. "
                f"The current screen shows {evidence['total_transformations']} visible transformation(s). Top visible results: {preview}"
            ),
            citations=evidence["citations"],
            handoff_targets=surface.handoff_targets,
        )

    if question_type == "filter_guidance":
        return ChatDecision(
            status=ChatStatus.SUPPORTED,
            question_type=question_type,
            response_text=(
                f"The active filters are parent {filters['parent']}, temperature {filters['temp_min']} to {filters['temp_max']} C, "
                f"atmosphere '{filters['atmosphere']}', and minimum observations {filters['min_observations']}. "
                "Changing those controls will change which visible pathways remain on screen. Lowering the observation threshold usually broadens the visible set; tightening filters narrows it."
            ),
            citations=evidence["citations"],
            handoff_targets=surface.handoff_targets,
        )

    if question_type == "compare_visible_results":
        if len(matched) >= 2:
            first, second = matched[0], matched[1]
            return ChatDecision(
                status=ChatStatus.SUPPORTED,
                question_type=question_type,
                response_text=(
                    f"{first['product']} is shown with {first.get('hazard_level') or 'UNKNOWN'} hazard at confidence {first.get('confidence', 0):.2f}, "
                    f"while {second['product']} is shown with {second.get('hazard_level') or 'UNKNOWN'} hazard at confidence {second.get('confidence', 0):.2f}. "
                    f"Visible source counts are {first.get('source_count', 0)} versus {second.get('source_count', 0)}."
                ),
                citations=evidence["citations"],
                handoff_targets=surface.handoff_targets,
            )
        return ChatDecision(
            status=ChatStatus.PARTIAL,
            question_type=question_type,
            response_text="I can compare visible Fate Explorer results, but I need two displayed products named explicitly in the question.",
            citations=evidence["citations"],
            clarification_questions=["Which two visible products do you want compared?"],
            handoff_targets=surface.handoff_targets,
        )

    if matched:
        item = matched[0]
        regulated_text = "It is marked regulated on this screen." if item.get("is_regulated") else "It is not marked regulated on this screen."
        return ChatDecision(
            status=ChatStatus.SUPPORTED,
            question_type="explain_visible_result",
            response_text=(
                f"{item['product']} is visible on this screen with {item.get('hazard_level') or 'UNKNOWN'} hazard, confidence {item.get('confidence', 0):.2f}, "
                f"and {item.get('source_count', 0)} supporting source{'s' if item.get('source_count', 0) != 1 else ''}. "
                f"The visible pathway row shows temperature range {item.get('temp_range') or 'n/a'} and atmosphere '{item.get('atmosphere') or 'n/a'}'. {regulated_text}"
            ),
            citations=evidence["citations"],
            handoff_targets=surface.handoff_targets,
        )

    if visible_transformations:
        first = visible_transformations[0]
        return ChatDecision(
            status=ChatStatus.PARTIAL,
            question_type="explain_visible_result",
            response_text=(
                "I can explain visible pathway rows on this page, but I could not match a specific displayed product from your question. "
                f"For example, {first['product']} is currently visible with {first.get('hazard_level') or 'UNKNOWN'} hazard."
            ),
            citations=evidence["citations"],
            clarification_questions=["Which visible product do you want explained?"],
            handoff_targets=surface.handoff_targets,
        )

    return ChatDecision(
        status=ChatStatus.CLARIFICATION_REQUIRED,
        question_type="clarification",
        response_text="No visible Fate Explorer results are loaded yet, so I can only explain the page capabilities and active filters.",
        citations=evidence["citations"],
        clarification_questions=["Run a Fate Explorer search first, then ask about a visible product or filter."],
        handoff_targets=surface.handoff_targets,
    )


def _regulatory_response(question_type: str, evidence: dict[str, Any], surface: AuthoritativeAnswerSurface) -> ChatDecision:
    summary = evidence["summary"]
    matched = evidence["matched_items"]
    predictions = evidence["cascade_predictions"]

    if question_type == "help_capability":
        return _regulatory_capability(surface)

    if question_type == "page_summary":
        return ChatDecision(
            status=ChatStatus.SUPPORTED,
            question_type=question_type,
            response_text=(
                f"Regulatory Compliance is currently showing {summary['material']} in subview '{summary['active_subview']}' with overall risk {summary['overall_risk'] or 'UNKNOWN'}. "
                f"Frameworks checked: {summary['frameworks_checked']}. Counts on screen: {summary['non_compliant_count']} non-compliant, "
                f"{summary['warning_count']} warning, {summary['compliant_count']} compliant. "
                f"Include degradation is {_human_bool(summary['include_degradation'])} and the forecast year is {summary['forecast_year']}."
            ),
            citations=evidence["citations"],
            handoff_targets=surface.handoff_targets,
        )

    if question_type == "filter_guidance":
        return ChatDecision(
            status=ChatStatus.SUPPORTED,
            question_type=question_type,
            response_text=(
                f"The include degradation toggle is currently {_human_bool(summary['include_degradation'])}. "
                f"The active forecast year is {summary['forecast_year']}, and the active subview is '{summary['active_subview']}'. "
                "Changing those controls changes which regulatory findings and forecast results are visible on this page."
            ),
            citations=evidence["citations"],
            handoff_targets=surface.handoff_targets,
        )

    if question_type == "compare_visible_results":
        if len(matched) >= 2:
            first, second = matched[0], matched[1]
            return ChatDecision(
                status=ChatStatus.SUPPORTED,
                question_type=question_type,
                response_text=(
                    f"{first['framework']} is currently shown as {first['status']}, while {second['framework']} is shown as {second['status']}. "
                    f"Visible notes are '{first['notes'] or 'n/a'}' versus '{second['notes'] or 'n/a'}'."
                ),
                citations=evidence["citations"],
                handoff_targets=surface.handoff_targets,
            )
        return ChatDecision(
            status=ChatStatus.PARTIAL,
            question_type=question_type,
            response_text="I can compare visible framework findings, but I need two displayed frameworks named explicitly in the question.",
            citations=evidence["citations"],
            clarification_questions=["Which two visible frameworks do you want compared?"],
            handoff_targets=surface.handoff_targets,
        )

    if matched:
        item = matched[0]
        return ChatDecision(
            status=ChatStatus.SUPPORTED,
            question_type="explain_visible_result",
            response_text=(
                f"{item['framework']} is currently shown on this page with status {item['status']}. "
                f"Visible notes for that framework are: {item['notes'] or 'No notes are shown.'}"
            ),
            citations=evidence["citations"],
            handoff_targets=surface.handoff_targets,
        )

    if predictions:
        first_key = next(iter(predictions.keys()))
        first_prediction = predictions[first_key]
        return ChatDecision(
            status=ChatStatus.SUPPORTED,
            question_type="explain_visible_result",
            response_text=(
                f"The current overall risk on this page is {summary['overall_risk'] or 'UNKNOWN'}. "
                f"For the visible forecast year {summary['forecast_year']}, {first_key} is shown with stage "
                f"{first_prediction.get('regulatory_stage') or 'unknown'} and status {first_prediction.get('status') or 'unknown'}."
            ),
            citations=evidence["citations"],
            handoff_targets=surface.handoff_targets,
        )

    return ChatDecision(
        status=ChatStatus.PARTIAL,
        question_type="explain_visible_result",
        response_text=(
            f"The current overall risk on this page is {summary['overall_risk'] or 'UNKNOWN'}, but I could not match a specific visible framework from your question."
        ),
        citations=evidence["citations"],
        clarification_questions=["Ask about the overall risk, a visible framework, or the active forecast year."],
        handoff_targets=surface.handoff_targets,
    )


def handoff_response(surface: AuthoritativeAnswerSurface, target: str | None) -> ChatDecision:
    target_label = target or "another module"
    return ChatDecision(
        status=ChatStatus.HANDOFF_REQUIRED,
        question_type="handoff",
        response_text=(
            f"This question belongs in {target_label}. {surface.page_label} can explain the evidence visible on this page, "
            f"but it does not own that decision surface."
        ),
        handoff_targets=[target_label],
    )


def refused_response() -> ChatDecision:
    return ChatDecision(
        status=ChatStatus.REFUSED,
        question_type="prompt_injection",
        response_text="I cannot follow instruction-override or injection-style requests. Ask about the active AEGIS page instead.",
    )


def out_of_scope_response(surface: AuthoritativeAnswerSurface) -> ChatDecision:
    return ChatDecision(
        status=ChatStatus.OUT_OF_SCOPE,
        question_type="off_topic",
        response_text=(
            f"This chat is limited to {surface.page_label} and adjacent PFAS workflow questions. "
            "It cannot help with unrelated personal, coding, or general-purpose requests."
        ),
        handoff_targets=surface.handoff_targets,
    )


def clarification_response(surface: AuthoritativeAnswerSurface) -> ChatDecision:
    return ChatDecision(
        status=ChatStatus.CLARIFICATION_REQUIRED,
        question_type="clarification",
        response_text=(
            f"I need a more page-specific question. Ask about a visible result, the active filters, or what this {surface.page_label} page can explain."
        ),
        clarification_questions=surface.starter_questions[:2],
        handoff_targets=surface.handoff_targets,
    )


def build_deterministic_response(
    surface: AuthoritativeAnswerSurface,
    question_type: str,
    evidence: dict[str, Any],
) -> ChatDecision:
    if surface.page_id == "fate-explorer":
        return _fate_response(question_type, evidence, surface)
    if surface.page_id == "regulatory":
        return _regulatory_response(question_type, evidence, surface)
    return clarification_response(surface)
