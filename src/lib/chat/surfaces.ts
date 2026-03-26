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
    visible_state: {
      parent: args.parent,
      temp_min: args.tempMin,
      temp_max: args.tempMax,
      atmosphere: args.atmosphere,
      min_observations: args.minObservations,
      total_transformations: args.totalTransformations,
      visible_transformations: args.visibleTransformations,
    },
    starter_questions: [
      "What degradation products are visible for this parent compound?",
      "Why is a visible product marked high hazard?",
      "How are the current filters affecting the visible pathway set?",
    ],
  };
}

export function createRegulatoryAnswerSurfaceHint(args: {
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
    starter_questions: [
      "What is the current overall risk on this page?",
      "How does the include degradation toggle affect the current screen?",
      "What forecast stage is visible for the selected year?",
    ],
  };
}
