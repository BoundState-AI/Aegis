export interface AnalyzeRequest {
  material: string;
  conditions: {
    temperature: number;
    atmosphere: string;
    time_hours: number;
  };
  mode?: string;
  n_samples?: number;
}

export interface Evidence {
  source: string;
  page?: string;
  fragment: string;
  year?: number;
  doi?: string;
}

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
  probability_mean: number;
  probability_ci_90: {
    low: number;
    high: number;
  };
  plausible: boolean;
  plausibility_notes: string;
  regulatory_status: RegulatoryStatus;
  evidence: Evidence[];
}

export interface AlternativeOption {
  material: string;
  risk_score: number;
  pro: string;
  con: string;
}

export interface AnalyzeResponse {
  material: string;
  conditions: {
    temperature: number;
    atmosphere: string;
    time_hours: number;
  };
  risk_score: number;
  risk_category: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  pathways: PathwayResult[];
  alternatives: AlternativeOption[];
  search_time_ms: number;
}
