import type { AnswerSurfaceHint } from "@/lib/chat/types";

type FateVisibleTransformation = {
  product: string;
  hazard_level: string | null;
  confidence: number;
  source_count: number;
  is_regulated: boolean;
  temp_range: string;
  atmosphere: string;
};

export function createFateAnswerSurfaceHint(args: {
  locale?: string;
  starterQuestions?: string[];
  parent: string;
  tempMin: number;
  tempMax: number;
  atmosphere: string;
  minObservations: number;
  totalTransformations: number;
  visibleTransformations: FateVisibleTransformation[];
}): AnswerSurfaceHint {
  return {
    page_id: "fate-explorer",
    locale: args.locale,
    visible_state: {
      parent: args.parent,
      temp_min: args.tempMin,
      temp_max: args.tempMax,
      atmosphere: args.atmosphere,
      min_observations: args.minObservations,
      total_transformations: args.totalTransformations,
      visible_transformations: args.visibleTransformations,
    },
    starter_questions: args.starterQuestions ?? [
      "What degradation products are visible for this parent compound?",
      "Why is a visible product marked high hazard?",
      "How are the current filters affecting the visible pathway set?",
    ],
  };
}

type LitigationVisibleCase = {
  case: string;
  year: number;
  settlement: number;
  relevance: number;
};

type PortfolioVisibleItem = {
  material: string;
  volume_lbs: number;
};

type PortfolioVisibleResult = {
  material: string;
  risk_category: string;
  risk_score: number;
  pfas_count: number;
  regulatory_flags: number;
  litigation_probability: number;
};

type ReportVisibleSection = {
  title: string;
  flags_count: number;
  similar_cases_count: number;
  product_count: number;
};

type EvidenceVisibleItem = {
  source: string;
  year: number | null;
  confidence: number;
  compound: string;
};

type AnalysisVisibleFinding = {
  product: string;
  screening_classification: string;
  regulatory_flags_count: number;
  evidence_strength: number | null;
};

type SimilarityVisibleEndpoint = {
  endpoint: string;
  count: number;
  fraction: number;
};

type SimilarityVisibleNeighbor = {
  name: string;
  similarity: number;
  evidence_count?: number;
};

export function createRegulatoryAnswerSurfaceHint(args: {
  locale?: string;
  starterQuestions?: string[];
  material: string;
  includeDegradation: boolean;
  forecastYear: number;
  activeSubview: string;
  overallRisk: string | null;
  frameworksChecked: number;
  compliantCount: number;
  warningCount: number;
  nonCompliantCount: number;
  sampleFindings: Array<{ framework: string; status: string; notes: string }>;
  cascadePredictions: Record<string, { status: string; regulatory_stage: string; affected_products: string[] }>;
}): AnswerSurfaceHint {
  return {
    page_id: "regulatory",
    locale: args.locale,
    visible_state: {
      material: args.material,
      include_degradation: args.includeDegradation,
      forecast_year: args.forecastYear,
      active_subview: args.activeSubview,
      overall_risk: args.overallRisk,
      frameworks_checked: args.frameworksChecked,
      compliant_count: args.compliantCount,
      warning_count: args.warningCount,
      non_compliant_count: args.nonCompliantCount,
      sample_findings: args.sampleFindings,
      cascade_predictions: args.cascadePredictions,
    },
    starter_questions: args.starterQuestions ?? [
      "What is the current overall risk on this page?",
      "How does the include degradation toggle affect the current screen?",
      "What forecast stage is visible for the selected year?",
    ],
  };
}

export function createLitigationAnswerSurfaceHint(args: {
  locale?: string;
  starterQuestions?: string[];
  selectedCompound: string;
  chartView: string;
  availableBacktests: number;
  forecastRiskLevel: string | null;
  probability12Months: number | null;
  probability24Months: number | null;
  probability36Months: number | null;
  estimatedExposureUsd: number | null;
  keyDrivers: string[];
  visibleSimilarCases: LitigationVisibleCase[];
  backtestPublications: number | null;
  firstLawsuitYear: number | null;
  leadTimeYears: number | null;
  paperDrilldownYear: number | null;
  paperDrilldownTotal: number | null;
}): AnswerSurfaceHint {
  return {
    page_id: "litigation",
    locale: args.locale,
    visible_state: {
      selected_compound: args.selectedCompound,
      chart_view: args.chartView,
      available_backtests: args.availableBacktests,
      forecast_risk_level: args.forecastRiskLevel,
      probability_12_months: args.probability12Months,
      probability_24_months: args.probability24Months,
      probability_36_months: args.probability36Months,
      estimated_exposure_usd: args.estimatedExposureUsd,
      key_drivers: args.keyDrivers,
      visible_similar_cases: args.visibleSimilarCases,
      backtest_publications: args.backtestPublications,
      first_lawsuit_year: args.firstLawsuitYear,
      lead_time_years: args.leadTimeYears,
      paper_drilldown_year: args.paperDrilldownYear,
      paper_drilldown_total: args.paperDrilldownTotal,
    },
    starter_questions: args.starterQuestions ?? [
      "What is the visible litigation risk forecast for this compound?",
      "What does the current backtest show on this page?",
      "Which similar cases are visible right now?",
    ],
  };
}

export function createPortfolioAnswerSurfaceHint(args: {
  locale?: string;
  starterQuestions?: string[];
  items: PortfolioVisibleItem[];
  totalMaterials: number;
  highRiskCount: number;
  totalExposureUsd: number;
  topResults: PortfolioVisibleResult[];
}): AnswerSurfaceHint {
  return {
    page_id: "portfolio",
    locale: args.locale,
    visible_state: {
      items: args.items,
      total_materials: args.totalMaterials,
      high_risk_count: args.highRiskCount,
      total_exposure_usd: args.totalExposureUsd,
      top_results: args.topResults,
    },
    starter_questions: args.starterQuestions ?? [
      "What is the current portfolio summary on this page?",
      "Which visible material is highest risk here?",
      "How much exposure is shown on the current portfolio screen?",
    ],
  };
}

export function createReportsAnswerSurfaceHint(args: {
  locale?: string;
  starterQuestions?: string[];
  material: string;
  includeLitigation: boolean;
  includeRegulatory: boolean;
  generated: string | null;
  classification: string | null;
  visibleSections: ReportVisibleSection[];
}): AnswerSurfaceHint {
  return {
    page_id: "reports",
    locale: args.locale,
    visible_state: {
      material: args.material,
      include_litigation: args.includeLitigation,
      include_regulatory: args.includeRegulatory,
      generated: args.generated,
      classification: args.classification,
      visible_sections: args.visibleSections,
    },
    starter_questions: args.starterQuestions ?? [
      "What sections are visible in the current report?",
      "What is the current report classification?",
      "How do the litigation and regulatory toggles affect this report?",
    ],
  };
}

export function createEvidenceAnswerSurfaceHint(args: {
  locale?: string;
  starterQuestions?: string[];
  material: string;
  maxCitations: number;
  totalCitations: number;
  confidenceScore: number | null;
  databaseTotalPapers: number;
  totalPathwayCitations: number;
  visibleEvidence: EvidenceVisibleItem[];
}): AnswerSurfaceHint {
  return {
    page_id: "evidence",
    locale: args.locale,
    visible_state: {
      material: args.material,
      max_citations: args.maxCitations,
      total_citations: args.totalCitations,
      confidence_score: args.confidenceScore,
      database_total_papers: args.databaseTotalPapers,
      total_pathway_citations: args.totalPathwayCitations,
      visible_evidence: args.visibleEvidence,
    },
    starter_questions: args.starterQuestions ?? [
      "What evidence is visible for this material?",
      "What is the current evidence confidence on this page?",
      "Which source is shown with the strongest visible support?",
    ],
  };
}

export function createAnalysisAnswerSurfaceHint(args: {
  locale?: string;
  starterQuestions?: string[];
  material: string;
  temperatureC: number;
  atmosphere: string;
  timeHours: number;
  findingsCount: number;
  summary: string | null;
  visibleFindings: AnalysisVisibleFinding[];
}): AnswerSurfaceHint {
  return {
    page_id: "analysis",
    locale: args.locale,
    visible_state: {
      material: args.material,
      temperature_c: args.temperatureC,
      atmosphere: args.atmosphere,
      time_hours: args.timeHours,
      findings_count: args.findingsCount,
      summary: args.summary,
      visible_findings: args.visibleFindings,
    },
    starter_questions: args.starterQuestions ?? [
      "What degradation findings are visible for these conditions?",
      "How do the current analysis inputs affect this screen?",
      "Which visible product has the strongest support here?",
    ],
  };
}

export function createSimilarityAnswerSurfaceHint(args: {
  locale?: string;
  starterQuestions?: string[];
  compoundName: string;
  querySmiles: string;
  riskSignal: string | null;
  neighborsWithPathways: number | null;
  avgSimilarity: number | null;
  topEndpoints: SimilarityVisibleEndpoint[];
  similarCompounds: SimilarityVisibleNeighbor[];
  tier2PatternCount: number;
  tier2RuleTotal: number;
  coverageResolutionRate: number | null;
}): AnswerSurfaceHint {
  return {
    page_id: "tier1",
    locale: args.locale,
    visible_state: {
      compound_name: args.compoundName,
      query_smiles: args.querySmiles,
      risk_signal: args.riskSignal,
      neighbors_with_pathways: args.neighborsWithPathways,
      avg_similarity: args.avgSimilarity,
      top_endpoints: args.topEndpoints,
      similar_compounds: args.similarCompounds,
      tier2_pattern_count: args.tier2PatternCount,
      tier2_rule_total: args.tier2RuleTotal,
      coverage_resolution_rate: args.coverageResolutionRate,
    },
    starter_questions: args.starterQuestions ?? [
      "What structural risk signal is visible for this query?",
      "Which similar compounds are currently shown?",
      "What endpoint patterns are visible on this page?",
    ],
  };
}
