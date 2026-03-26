#!/usr/bin/env python3
"""
Deterministic response engine for AEGIS bounded chat MVP.
"""

from __future__ import annotations

from typing import Any

from boundstate_aegis.models.chat_models import AuthoritativeAnswerSurface, ChatDecision, ChatStatus


def _is_japanese(surface: AuthoritativeAnswerSurface) -> bool:
    return surface.locale.lower().startswith("ja")


def _human_bool(value: Any) -> str:
    return "on" if bool(value) else "off"


def _fate_capability(surface: AuthoritativeAnswerSurface) -> ChatDecision:
    response_text = (
        "このページでは、表示中の分解経路、現在のフィルター、表示されている有害性ラベル、"
        "および規制対象として表示されている生成物を説明できます。"
        "一方で、全社ポートフォリオのリスク順位付けや訴訟アドバイスは扱えません。"
        if _is_japanese(surface)
        else
        "This page can explain the visible degradation pathways, current filters, visible hazard labels, "
        "and which displayed products are marked regulated. It cannot rank enterprise portfolio risk or give litigation advice."
    )
    return ChatDecision(
        status=ChatStatus.SUPPORTED,
        question_type="help_capability",
        response_text=response_text,
        citations=["active_filters", "visible_transformations"],
        handoff_targets=surface.handoff_targets,
    )


def _regulatory_capability(surface: AuthoritativeAnswerSurface) -> ChatDecision:
    response_text = (
        "このページでは、表示中の規制リスク概要、読み込まれているフレームワーク判定、現在の予測年、"
        "および「分解生成物を含める」トグルの影響を説明できます。"
        "一方で、法的助言やポートフォリオの優先順位付けは行えません。"
        if _is_japanese(surface)
        else
        "This page can explain the visible regulatory risk summary, the loaded framework findings, the current "
        "forecast year, and the effect of the include degradation toggle. It cannot provide legal advice or portfolio prioritization."
    )
    return ChatDecision(
        status=ChatStatus.SUPPORTED,
        question_type="help_capability",
        response_text=response_text,
        citations=["regulatory_summary", "sample_findings", "cascade_predictions"],
        handoff_targets=surface.handoff_targets,
    )


def _litigation_capability(surface: AuthoritativeAnswerSurface) -> ChatDecision:
    response_text = (
        "このページでは、表示中の訴訟リスク予測、主要ドライバー、バックテスト文脈、"
        "および画面上の類似事例を説明できます。"
        "一方で、法的助言や画面外の和解予測は行えません。"
        if _is_japanese(surface)
        else
        "This page can explain the visible litigation forecast, key drivers, backtest context, and similar cases shown on screen. "
        "It cannot provide legal advice or make off-screen settlement predictions."
    )
    return ChatDecision(
        status=ChatStatus.SUPPORTED,
        question_type="help_capability",
        response_text=response_text,
        citations=["litigation_summary", "litigation_drivers", "litigation_cases"],
        handoff_targets=surface.handoff_targets,
    )


def _portfolio_capability(surface: AuthoritativeAnswerSurface) -> ChatDecision:
    response_text = (
        "このページでは、表示中のポートフォリオ概要、読み込まれている材料、総エクスポージャー、"
        "および画面上の材料別リスク行を説明できます。"
        "一方で、法的助言や根拠のない規制結論は提供できません。"
        if _is_japanese(surface)
        else
        "This page can explain the visible portfolio summary, loaded materials, exposure totals, and material-level risk rows on screen. "
        "It cannot provide legal advice or make unsupported regulatory conclusions."
    )
    return ChatDecision(
        status=ChatStatus.SUPPORTED,
        question_type="help_capability",
        response_text=response_text,
        citations=["portfolio_summary", "portfolio_items", "portfolio_results"],
        handoff_targets=surface.handoff_targets,
    )


def _reports_capability(surface: AuthoritativeAnswerSurface) -> ChatDecision:
    response_text = (
        "このページでは、表示中のレポート分類、含まれているセクション、"
        "および訴訟・規制トグルの状態を説明できます。"
        "一方で、画面にない新しい分析を作成することはできません。"
        if _is_japanese(surface)
        else
        "This page can explain the visible report classification, included sections, and the state of the litigation and regulatory toggles. "
        "It cannot create new analysis beyond the report content already on screen."
    )
    return ChatDecision(
        status=ChatStatus.SUPPORTED,
        question_type="help_capability",
        response_text=response_text,
        citations=["report_summary", "report_sections"],
        handoff_targets=surface.handoff_targets,
    )


def _evidence_capability(surface: AuthoritativeAnswerSurface) -> ChatDecision:
    response_text = (
        "このページでは、表示中のエビデンス行、信頼度スコア、引用件数、"
        "および画面上の情報源カバレッジを説明できます。"
        "一方で、画面外のエビデンス推論やポートフォリオ判断はできません。"
        if _is_japanese(surface)
        else
        "This page can explain the visible evidence rows, confidence score, citation count, and source coverage shown on screen. "
        "It cannot infer off-screen evidence or make portfolio decisions."
    )
    return ChatDecision(
        status=ChatStatus.SUPPORTED,
        question_type="help_capability",
        response_text=response_text,
        citations=["evidence_summary", "evidence_rows"],
        handoff_targets=surface.handoff_targets,
    )


def _analysis_capability(surface: AuthoritativeAnswerSurface) -> ChatDecision:
    response_text = (
        "このページでは、現在の材料と条件に対して表示中のPFAS分析結果を説明できます。"
        "具体的には、表示されている生成物や分類が対象です。"
        "一方で、表示されていない経路の創作や法務・全社判断はできません。"
        if _is_japanese(surface)
        else
        "This page can explain the visible PFAS analysis findings for the current material and conditions, including displayed products and classifications. "
        "It cannot invent unshown pathways or give legal or enterprise advice."
    )
    return ChatDecision(
        status=ChatStatus.SUPPORTED,
        question_type="help_capability",
        response_text=response_text,
        citations=["analysis_summary", "analysis_findings"],
        handoff_targets=surface.handoff_targets,
    )


def _tier1_capability(surface: AuthoritativeAnswerSurface) -> ChatDecision:
    response_text = (
        "このページでは、表示中の構造リスクシグナル、類似化合物、エンドポイント傾向、"
        "およびTier 2カバレッジを説明できます。"
        "一方で、隠れたエビデンスの推論や根拠のないコンプライアンス結論はできません。"
        if _is_japanese(surface)
        else
        "This page can explain the visible structural risk signal, similar compounds, endpoint patterns, and Tier 2 coverage shown on screen. "
        "It cannot infer hidden evidence or make unsupported compliance conclusions."
    )
    return ChatDecision(
        status=ChatStatus.SUPPORTED,
        question_type="help_capability",
        response_text=response_text,
        citations=["tier1_summary", "tier1_endpoints", "tier1_neighbors"],
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


def _litigation_response(question_type: str, evidence: dict[str, Any], surface: AuthoritativeAnswerSurface) -> ChatDecision:
    summary = evidence["summary"]
    matched = evidence["matched_items"]
    visible_cases = evidence["visible_similar_cases"]
    key_drivers = evidence["key_drivers"]

    if question_type == "help_capability":
        return _litigation_capability(surface)

    if question_type == "page_summary":
        driver_preview = ", ".join(key_drivers[:3]) if key_drivers else "No visible drivers are loaded."
        return ChatDecision(
            status=ChatStatus.SUPPORTED,
            question_type=question_type,
            response_text=(
                f"Litigation Risk is currently focused on {summary['selected_compound']} with chart view '{summary['chart_view']}'. "
                f"The visible forecast risk level is {summary['forecast_risk_level'] or 'UNKNOWN'} with 12/24/36 month probabilities "
                f"of {summary['probability_12_months'] or 0:.2f}, {summary['probability_24_months'] or 0:.2f}, and {summary['probability_36_months'] or 0:.2f}. "
                f"Estimated exposure shown on screen is ${summary['estimated_exposure_usd'] or 0:,.0f}. "
                f"Backtest publications: {summary['backtest_publications'] or 0}; visible lead time: {summary['lead_time_years'] or 0} years. "
                f"Top visible drivers: {driver_preview}"
            ),
            citations=evidence["citations"],
            handoff_targets=surface.handoff_targets,
        )

    if question_type == "filter_guidance":
        return ChatDecision(
            status=ChatStatus.SUPPORTED,
            question_type=question_type,
            response_text=(
                f"The current compound is {summary['selected_compound']} and the active chart view is '{summary['chart_view']}'. "
                "Changing the selected compound or chart view changes which forecast, backtest, and case details remain visible on this page."
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
                    f"{first['case']} is shown with settlement ${first.get('settlement', 0):,.0f}, year {first.get('year', 0)}, and relevance {first.get('relevance', 0):.2f}, "
                    f"while {second['case']} is shown with settlement ${second.get('settlement', 0):,.0f}, year {second.get('year', 0)}, and relevance {second.get('relevance', 0):.2f}."
                ),
                citations=evidence["citations"],
                handoff_targets=surface.handoff_targets,
            )
        return ChatDecision(
            status=ChatStatus.PARTIAL,
            question_type=question_type,
            response_text="I can compare visible similar cases, but I need two displayed cases named explicitly in the question.",
            citations=evidence["citations"],
            clarification_questions=["Which two visible similar cases do you want compared?"],
            handoff_targets=surface.handoff_targets,
        )

    if matched:
        item = matched[0]
        return ChatDecision(
            status=ChatStatus.SUPPORTED,
            question_type="explain_visible_result",
            response_text=(
                f"{item['case']} is visible on this page with settlement ${item.get('settlement', 0):,.0f}, year {item.get('year', 0)}, "
                f"and relevance {item.get('relevance', 0):.2f} to the active compound."
            ),
            citations=evidence["citations"],
            handoff_targets=surface.handoff_targets,
        )

    if visible_cases:
        return ChatDecision(
            status=ChatStatus.PARTIAL,
            question_type="explain_visible_result",
            response_text=(
                "I can explain visible similar cases on this page, but I could not match a specific displayed case from your question."
            ),
            citations=evidence["citations"],
            clarification_questions=["Which visible similar case do you want explained?"],
            handoff_targets=surface.handoff_targets,
        )

    return ChatDecision(
        status=ChatStatus.PARTIAL,
        question_type="explain_visible_result",
        response_text=(
            f"The visible forecast risk level is {summary['forecast_risk_level'] or 'UNKNOWN'}, but no similar cases are currently loaded on screen."
        ),
        citations=evidence["citations"],
        clarification_questions=["Ask about the visible forecast or backtest context on this page."],
        handoff_targets=surface.handoff_targets,
    )


def _portfolio_response(question_type: str, evidence: dict[str, Any], surface: AuthoritativeAnswerSurface) -> ChatDecision:
    summary = evidence["summary"]
    matched = evidence["matched_items"]
    results = evidence["top_results"]
    items = evidence["items"]

    if question_type == "help_capability":
        return _portfolio_capability(surface)

    if question_type == "page_summary":
        return ChatDecision(
            status=ChatStatus.SUPPORTED,
            question_type=question_type,
            response_text=(
                f"Portfolio Assessment currently shows {summary['total_materials'] or 0} material(s), "
                f"{summary['high_risk_count'] or 0} high-risk item(s), and visible total exposure of ${summary['total_exposure_usd'] or 0:,.0f}. "
                f"The current input list contains {len(items)} visible portfolio row(s)."
            ),
            citations=evidence["citations"],
            handoff_targets=surface.handoff_targets,
        )

    if question_type == "filter_guidance":
        return ChatDecision(
            status=ChatStatus.SUPPORTED,
            question_type=question_type,
            response_text=(
                "This page reflects the materials and volumes currently loaded into the portfolio input list. "
                "Adding, removing, or resizing those items changes the visible risk ranking and exposure totals."
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
                    f"{first['material']} is shown as {first['risk_category']} risk with score {first.get('risk_score', 0):.2f}, "
                    f"while {second['material']} is shown as {second['risk_category']} risk with score {second.get('risk_score', 0):.2f}. "
                    f"Visible PFAS counts are {first.get('pfas_count', 0)} versus {second.get('pfas_count', 0)}."
                ),
                citations=evidence["citations"],
                handoff_targets=surface.handoff_targets,
            )
        return ChatDecision(
            status=ChatStatus.PARTIAL,
            question_type=question_type,
            response_text="I can compare visible portfolio rows, but I need two displayed materials named explicitly in the question.",
            citations=evidence["citations"],
            clarification_questions=["Which two visible materials do you want compared?"],
            handoff_targets=surface.handoff_targets,
        )

    if matched:
        item = matched[0]
        return ChatDecision(
            status=ChatStatus.SUPPORTED,
            question_type="explain_visible_result",
            response_text=(
                f"{item['material']} is visible on this page with {item.get('risk_category') or 'UNKNOWN'} risk, "
                f"risk score {item.get('risk_score', 0):.2f}, {item.get('pfas_count', 0)} PFAS product(s), "
                f"{item.get('regulatory_flags', 0)} regulatory flag(s), and litigation probability {item.get('litigation_probability', 0):.2f}."
            ),
            citations=evidence["citations"],
            handoff_targets=surface.handoff_targets,
        )

    if results:
        return ChatDecision(
            status=ChatStatus.PARTIAL,
            question_type="explain_visible_result",
            response_text="I can explain visible portfolio rows, but I could not match a specific displayed material from your question.",
            citations=evidence["citations"],
            clarification_questions=["Which visible material do you want explained?"],
            handoff_targets=surface.handoff_targets,
        )

    return clarification_response(surface)


def _reports_response(question_type: str, evidence: dict[str, Any], surface: AuthoritativeAnswerSurface) -> ChatDecision:
    summary = evidence["summary"]
    matched = evidence["matched_items"]
    sections = evidence["visible_sections"]

    if question_type == "help_capability":
        return _reports_capability(surface)

    if question_type == "page_summary":
        return ChatDecision(
            status=ChatStatus.SUPPORTED,
            question_type=question_type,
            response_text=(
                f"Executive Reports is currently configured for {summary['material']} with classification "
                f"{summary['classification'] or 'UNKNOWN'}. Litigation is {_human_bool(summary['include_litigation'])}, "
                f"regulatory is {_human_bool(summary['include_regulatory'])}, and {len(sections)} visible section(s) are loaded."
            ),
            citations=evidence["citations"],
            handoff_targets=surface.handoff_targets,
        )

    if question_type == "filter_guidance":
        return ChatDecision(
            status=ChatStatus.SUPPORTED,
            question_type=question_type,
            response_text=(
                f"The report is currently set to include litigation {_human_bool(summary['include_litigation'])} and regulatory {_human_bool(summary['include_regulatory'])}. "
                "Changing those toggles changes which sections and flags are visible in the generated report."
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
                    f"{first['title']} shows {first.get('flags_count', 0)} flag(s), {first.get('similar_cases_count', 0)} similar case(s), and {first.get('product_count', 0)} product(s), "
                    f"while {second['title']} shows {second.get('flags_count', 0)} flag(s), {second.get('similar_cases_count', 0)} similar case(s), and {second.get('product_count', 0)} product(s)."
                ),
                citations=evidence["citations"],
                handoff_targets=surface.handoff_targets,
            )
        return ChatDecision(
            status=ChatStatus.PARTIAL,
            question_type=question_type,
            response_text="I can compare visible report sections, but I need two displayed section titles named explicitly in the question.",
            citations=evidence["citations"],
            clarification_questions=["Which two visible report sections do you want compared?"],
            handoff_targets=surface.handoff_targets,
        )

    if matched:
        item = matched[0]
        return ChatDecision(
            status=ChatStatus.SUPPORTED,
            question_type="explain_visible_result",
            response_text=(
                f"{item['title']} is visible on this report with {item.get('flags_count', 0)} regulatory flag(s), "
                f"{item.get('similar_cases_count', 0)} similar case(s), and {item.get('product_count', 0)} product(s) shown."
            ),
            citations=evidence["citations"],
            handoff_targets=surface.handoff_targets,
        )

    if sections:
        return ChatDecision(
            status=ChatStatus.PARTIAL,
            question_type="explain_visible_result",
            response_text="I can explain visible report sections, but I could not match a specific displayed section from your question.",
            citations=evidence["citations"],
            clarification_questions=["Which visible section do you want explained?"],
            handoff_targets=surface.handoff_targets,
        )

    return clarification_response(surface)


def _evidence_response(question_type: str, evidence: dict[str, Any], surface: AuthoritativeAnswerSurface) -> ChatDecision:
    summary = evidence["summary"]
    matched = evidence["matched_items"]
    visible_evidence = evidence["visible_evidence"]

    if question_type == "help_capability":
        return _evidence_capability(surface)

    if question_type == "page_summary":
        return ChatDecision(
            status=ChatStatus.SUPPORTED,
            question_type=question_type,
            response_text=(
                f"Evidence Chain is currently showing {summary['material']} with {summary['total_citations'] or 0} visible citation(s), "
                f"confidence score {(summary['confidence_score'] or 0):.2f}, database coverage of {summary['database_total_papers'] or 0} papers, "
                f"and {summary['total_pathway_citations'] or 0} total pathway citations."
            ),
            citations=evidence["citations"],
            handoff_targets=surface.handoff_targets,
        )

    if question_type == "filter_guidance":
        return ChatDecision(
            status=ChatStatus.SUPPORTED,
            question_type=question_type,
            response_text=(
                f"The current material is {summary['material']} and the max citations setting is {summary['max_citations'] or 0}. "
                "Changing those controls changes how many evidence rows remain visible on this page."
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
                    f"{first['source']} is shown with confidence {first.get('confidence', 0):.2f} and year {first.get('year') or 'n/a'}, "
                    f"while {second['source']} is shown with confidence {second.get('confidence', 0):.2f} and year {second.get('year') or 'n/a'}."
                ),
                citations=evidence["citations"],
                handoff_targets=surface.handoff_targets,
            )
        return ChatDecision(
            status=ChatStatus.PARTIAL,
            question_type=question_type,
            response_text="I can compare visible evidence rows, but I need two displayed sources named explicitly in the question.",
            citations=evidence["citations"],
            clarification_questions=["Which two visible evidence sources do you want compared?"],
            handoff_targets=surface.handoff_targets,
        )

    if matched:
        item = matched[0]
        return ChatDecision(
            status=ChatStatus.SUPPORTED,
            question_type="explain_visible_result",
            response_text=(
                f"{item['source']} is visible on this page for compound {item.get('compound') or 'UNKNOWN'} with confidence {item.get('confidence', 0):.2f} "
                f"and year {item.get('year') or 'n/a'}."
            ),
            citations=evidence["citations"],
            handoff_targets=surface.handoff_targets,
        )

    if visible_evidence:
        return ChatDecision(
            status=ChatStatus.PARTIAL,
            question_type="explain_visible_result",
            response_text="I can explain visible evidence rows, but I could not match a specific displayed source from your question.",
            citations=evidence["citations"],
            clarification_questions=["Which visible evidence source do you want explained?"],
            handoff_targets=surface.handoff_targets,
        )

    return clarification_response(surface)


def _analysis_response(question_type: str, evidence: dict[str, Any], surface: AuthoritativeAnswerSurface) -> ChatDecision:
    summary = evidence["summary"]
    matched = evidence["matched_items"]
    visible_findings = evidence["visible_findings"]

    if question_type == "help_capability":
        return _analysis_capability(surface)

    if question_type == "page_summary":
        return ChatDecision(
            status=ChatStatus.SUPPORTED,
            question_type=question_type,
            response_text=(
                f"PFAS Analysis is currently evaluating {summary['material']} at {summary['temperature_c'] or 0} C in atmosphere "
                f"'{summary['atmosphere'] or 'n/a'}' for {summary['time_hours'] or 0} hour(s). "
                f"The page shows {summary['findings_count'] or 0} visible finding(s). {summary['summary'] or ''}".strip()
            ),
            citations=evidence["citations"],
            handoff_targets=surface.handoff_targets,
        )

    if question_type == "filter_guidance":
        return ChatDecision(
            status=ChatStatus.SUPPORTED,
            question_type=question_type,
            response_text=(
                f"The current inputs are material {summary['material']}, temperature {summary['temperature_c'] or 0} C, "
                f"atmosphere '{summary['atmosphere'] or 'n/a'}', and time {summary['time_hours'] or 0} hour(s). "
                "Changing those inputs changes which visible findings remain on this page."
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
                    f"{first['product']} is shown as {first.get('screening_classification') or 'UNKNOWN'} with "
                    f"{first.get('regulatory_flags_count', 0)} regulatory flag(s), while {second['product']} is shown as "
                    f"{second.get('screening_classification') or 'UNKNOWN'} with {second.get('regulatory_flags_count', 0)} regulatory flag(s)."
                ),
                citations=evidence["citations"],
                handoff_targets=surface.handoff_targets,
            )
        return ChatDecision(
            status=ChatStatus.PARTIAL,
            question_type=question_type,
            response_text="I can compare visible analysis findings, but I need two displayed products named explicitly in the question.",
            citations=evidence["citations"],
            clarification_questions=["Which two visible products do you want compared?"],
            handoff_targets=surface.handoff_targets,
        )

    if matched:
        item = matched[0]
        strength = item.get("evidence_strength")
        strength_text = f" and evidence strength {strength:.2f}" if isinstance(strength, (int, float)) else ""
        return ChatDecision(
            status=ChatStatus.SUPPORTED,
            question_type="explain_visible_result",
            response_text=(
                f"{item['product']} is visible on this page with classification {item.get('screening_classification') or 'UNKNOWN'}, "
                f"{item.get('regulatory_flags_count', 0)} regulatory flag(s){strength_text}."
            ),
            citations=evidence["citations"],
            handoff_targets=surface.handoff_targets,
        )

    if visible_findings:
        return ChatDecision(
            status=ChatStatus.PARTIAL,
            question_type="explain_visible_result",
            response_text="I can explain visible analysis findings, but I could not match a specific displayed product from your question.",
            citations=evidence["citations"],
            clarification_questions=["Which visible product do you want explained?"],
            handoff_targets=surface.handoff_targets,
        )

    return clarification_response(surface)


def _tier1_response(question_type: str, evidence: dict[str, Any], surface: AuthoritativeAnswerSurface) -> ChatDecision:
    summary = evidence["summary"]
    matched = evidence["matched_items"]
    neighbors = evidence["similar_compounds"]
    endpoints = evidence["top_endpoints"]

    if question_type == "help_capability":
        return _tier1_capability(surface)

    if question_type == "page_summary":
        return ChatDecision(
            status=ChatStatus.SUPPORTED,
            question_type=question_type,
            response_text=(
                f"Structural Similarity is currently showing {summary['compound_name'] or 'the active query'} with risk signal "
                f"{summary['risk_signal'] or 'UNKNOWN'}, {summary['neighbors_with_pathways'] or 0} neighbor(s) with pathways, "
                f"average similarity {(summary['avg_similarity'] or 0):.2f}, Tier 2 pattern count {summary['tier2_pattern_count'] or 0}, "
                f"and Tier 2 rule total {summary['tier2_rule_total'] or 0}."
            ),
            citations=evidence["citations"],
            handoff_targets=surface.handoff_targets,
        )

    if question_type == "filter_guidance":
        return ChatDecision(
            status=ChatStatus.SUPPORTED,
            question_type=question_type,
            response_text=(
                f"The active structural query is {summary['compound_name'] or 'the current compound'} with the current SMILES loaded on screen. "
                "Changing the query compound or SMILES changes the visible neighbors, endpoints, and risk signal."
            ),
            citations=evidence["citations"],
            handoff_targets=surface.handoff_targets,
        )

    if question_type == "compare_visible_results":
        if len(matched) >= 2:
            first, second = matched[0], matched[1]
            first_label = first.get("name") or first.get("endpoint") or "first result"
            second_label = second.get("name") or second.get("endpoint") or "second result"
            first_metric = first.get("similarity", first.get("fraction", 0))
            second_metric = second.get("similarity", second.get("fraction", 0))
            return ChatDecision(
                status=ChatStatus.SUPPORTED,
                question_type=question_type,
                response_text=(
                    f"{first_label} is shown with metric {first_metric:.2f}, while {second_label} is shown with metric {second_metric:.2f}."
                ),
                citations=evidence["citations"],
                handoff_targets=surface.handoff_targets,
            )
        return ChatDecision(
            status=ChatStatus.PARTIAL,
            question_type=question_type,
            response_text="I can compare visible similar compounds or endpoint rows, but I need two displayed labels named explicitly in the question.",
            citations=evidence["citations"],
            clarification_questions=["Which two visible compounds or endpoints do you want compared?"],
            handoff_targets=surface.handoff_targets,
        )

    if matched:
        item = matched[0]
        if item.get("name"):
            return ChatDecision(
                status=ChatStatus.SUPPORTED,
                question_type="explain_visible_result",
                response_text=(
                    f"{item['name']} is visible on this page with similarity {item.get('similarity', 0):.2f} "
                    f"and evidence count {item.get('evidence_count', 0)}."
                ),
                citations=evidence["citations"],
                handoff_targets=surface.handoff_targets,
            )
        return ChatDecision(
            status=ChatStatus.SUPPORTED,
            question_type="explain_visible_result",
            response_text=(
                f"{item['endpoint']} is visible on this page with count {item.get('count', 0)} and fraction {item.get('fraction', 0):.2f}."
            ),
            citations=evidence["citations"],
            handoff_targets=surface.handoff_targets,
        )

    if neighbors or endpoints:
        return ChatDecision(
            status=ChatStatus.PARTIAL,
            question_type="explain_visible_result",
            response_text="I can explain visible similar compounds or endpoint patterns, but I could not match a specific displayed label from your question.",
            citations=evidence["citations"],
            clarification_questions=["Which visible similar compound or endpoint do you want explained?"],
            handoff_targets=surface.handoff_targets,
        )

    return clarification_response(surface)


def handoff_response(surface: AuthoritativeAnswerSurface, target: str | None) -> ChatDecision:
    target_label = target or "another module"
    response_text = (
        f"この質問は {target_label} が担当する領域です。{surface.page_label} ではこのページに表示されているエビデンスは説明できますが、"
        "その判断面自体は所管していません。"
        if _is_japanese(surface)
        else
        f"This question belongs in {target_label}. {surface.page_label} can explain the evidence visible on this page, "
        f"but it does not own that decision surface."
    )
    return ChatDecision(
        status=ChatStatus.HANDOFF_REQUIRED,
        question_type="handoff",
        response_text=response_text,
        handoff_targets=[target_label],
    )


def refused_response(locale: str = "en") -> ChatDecision:
    response_text = (
        "指示上書きやインジェクション型の要求には従えません。代わりに、現在表示中のAEGISページについて質問してください。"
        if locale.lower().startswith("ja")
        else
        "I cannot follow instruction-override or injection-style requests. Ask about the active AEGIS page instead."
    )
    return ChatDecision(
        status=ChatStatus.REFUSED,
        question_type="prompt_injection",
        response_text=response_text,
    )


def out_of_scope_response(surface: AuthoritativeAnswerSurface) -> ChatDecision:
    response_text = (
        f"このチャットは {surface.page_label} と、その周辺のPFASワークフローに関する質問に限定されています。"
        "個人的な相談、コーディング支援、一般的な雑談には対応できません。"
        if _is_japanese(surface)
        else
        f"This chat is limited to {surface.page_label} and adjacent PFAS workflow questions. "
        "It cannot help with unrelated personal, coding, or general-purpose requests."
    )
    return ChatDecision(
        status=ChatStatus.OUT_OF_SCOPE,
        question_type="off_topic",
        response_text=response_text,
        handoff_targets=surface.handoff_targets,
    )


def clarification_response(surface: AuthoritativeAnswerSurface) -> ChatDecision:
    response_text = (
        f"もう少しこのページに即した質問が必要です。表示中の結果、現在のフィルター、または {surface.page_label} ページで説明できる内容について質問してください。"
        if _is_japanese(surface)
        else
        f"I need a more page-specific question. Ask about a visible result, the active filters, or what this {surface.page_label} page can explain."
    )
    return ChatDecision(
        status=ChatStatus.CLARIFICATION_REQUIRED,
        question_type="clarification",
        response_text=response_text,
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
    if surface.page_id == "litigation":
        return _litigation_response(question_type, evidence, surface)
    if surface.page_id == "portfolio":
        return _portfolio_response(question_type, evidence, surface)
    if surface.page_id == "reports":
        return _reports_response(question_type, evidence, surface)
    if surface.page_id == "evidence":
        return _evidence_response(question_type, evidence, surface)
    if surface.page_id == "analysis":
        return _analysis_response(question_type, evidence, surface)
    if surface.page_id == "tier1":
        return _tier1_response(question_type, evidence, surface)
    return clarification_response(surface)
