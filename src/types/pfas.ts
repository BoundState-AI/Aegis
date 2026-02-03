/**
 * AEGIS PFAS Analysis Types
 */

export interface AnalyzeRequest {
  compound: string;
  scenario?: {
    service_temp_c?: number;
    incident_temp_c?: number;
    atmosphere?: string;
  };
  max_depth?: number;
}

export interface Evidence {
  property: string;
  value: string | number;
  source: string;
  test_method: string;
  date: string;
  confidence: number;
  notes?: string;
}

export interface PathwayCondition {
  step: string;
  mechanism?: string;
  min_temp_c?: number;
  max_temp_c?: number;
  atmosphere?: string;
  residence_time_s?: number;
}

export interface Finding {
  product: string;
  screening_classification: string;
  conditions_where_it_forms: PathwayCondition[];
  confidence: number;
  regulatory_flags: string[];
  evidence_refs: Evidence[];
}

export interface AnalyzeResponse {
  compound_evaluated: string;
  scenario_context: Record<string, unknown>;
  pfas_findings: Finding[];
  summary: string;
}

// Legacy types for backward compatibility with existing components
export interface RegulatoryStatus {
  pfas_name: string;
  is_regulated: boolean;
  jurisdictions: Array<{
    name: string;
    status: string;
  }>;
  litigation: Array<{
    case: string;
    context: string;
  }>;
  effective_date?: string;
}

export interface PathwayResult {
  product: string;
  pathway: string[];
  mechanism: string;
  /** Literature-derived evidence strength score (0-1), NOT a statistical probability */
  evidence_strength: number;
  /** Range of agreement across peer-reviewed sources, NOT a frequentist CI */
  literature_agreement: {
    low: number;
    high: number;
  };
  plausible: boolean;
  plausibility_notes: string;
  regulatory_status: RegulatoryStatus;
  evidence: Evidence[];
  /** Number of independent observations supporting this pathway */
  observation_count?: number;
  /** Number of peer-reviewed papers documenting this pathway */
  paper_count?: number;
  // Legacy field aliases for backwards compatibility
  /** @deprecated Use evidence_strength instead */
  probability_mean: number;
  /** @deprecated Use literature_agreement instead */
  probability_ci_90: {
    low: number;
    high: number;
  };
}

export interface AlternativeOption {
  material: string;
  risk_score: number;
  pro: string;
  con: string;
}

// Adapter to convert AEGIS response to legacy format for existing UI components
export function adaptAegisResponse(response: AnalyzeResponse): {
  material: string;
  risk_score: number;
  risk_category: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  pathways: PathwayResult[];
  alternatives: AlternativeOption[];
} {
  const avgConfidence = response.pfas_findings.length > 0
    ? response.pfas_findings.reduce((sum, f) => sum + f.confidence, 0) / response.pfas_findings.length
    : 0;

  const hasRegulatoryFlags = response.pfas_findings.some(f => f.regulatory_flags.length > 0);

  let risk_category: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" = "LOW";
  let risk_score = avgConfidence * 100;

  if (hasRegulatoryFlags) {
    risk_category = "HIGH";
    risk_score = Math.max(risk_score, 70);
  } else if (response.pfas_findings.length > 3) {
    risk_category = "MEDIUM";
    risk_score = Math.max(risk_score, 40);
  } else if (response.pfas_findings.length > 0) {
    risk_category = "LOW";
    risk_score = Math.max(risk_score, 20);
  }

  const pathways: PathwayResult[] = response.pfas_findings.map(finding => {
    // Evidence strength reflects literature agreement, not statistical probability
    const evidenceStrength = finding.confidence;
    // Agreement range based on evidence variability (±0.2 is placeholder;
    // ideally this would come from actual variance in the literature data)
    const agreementLow = Math.max(0, evidenceStrength - 0.2);
    const agreementHigh = Math.min(1, evidenceStrength + 0.2);

    return {
      product: finding.product,
      pathway: finding.conditions_where_it_forms.map(c => c.step),
      mechanism: finding.conditions_where_it_forms[0]?.mechanism || "thermal",
      // New honest terminology
      evidence_strength: evidenceStrength,
      literature_agreement: {
        low: agreementLow,
        high: agreementHigh,
      },
      // Legacy fields for backwards compatibility
      probability_mean: evidenceStrength,
      probability_ci_90: {
        low: agreementLow,
        high: agreementHigh,
      },
      plausible: evidenceStrength > 0.3,
      plausibility_notes: finding.screening_classification,
      regulatory_status: {
        pfas_name: finding.product,
        is_regulated: finding.regulatory_flags.length > 0,
        jurisdictions: finding.regulatory_flags.map(flag => ({
          name: flag,
          status: "regulated",
        })),
        litigation: [],
      },
      evidence: finding.evidence_refs.map(e => ({
        source: e.source,
        fragment: e.notes || `${e.property}: ${e.value}`,
        property: e.property,
        value: e.value,
        test_method: e.test_method,
        date: e.date,
        confidence: e.confidence,
      })),
    };
  });

  return {
    material: response.compound_evaluated,
    risk_score,
    risk_category,
    pathways,
    alternatives: [],
  };
}
