import { z } from "zod";

export const regulatoryStatusSchema = z.object({
  framework: z.string(),
  status: z.string(),
  limit_ppb: z.number().nullable(),
  effective_date: z.string().nullable(),
  notes: z.string(),
});

export const apacAssertionSummarySchema = z.object({
  id: z.string(),
  assertion: z.string(),
  country: z.string(),
  status: z.string(),
  normalized_status: z.string(),
  confidence: z.number(),
  effective_date: z.string().nullable(),
  threshold_value: z.string().nullable(),
  jerk_signal: z.boolean(),
  litigation_relevance: z.string(),
  compound_class: z.string(),
  citation_tier: z.string(),
});

export const regulatoryCheckSchema = z.object({
  material: z.string(),
  degradation_products: z.array(z.string()),
  degradation_pathway_count: z.number(),
  degradation_paper_count: z.number(),
  degradation_sample_dois: z.array(z.string()),
  degradation_source: z.string(),
  frameworks_checked: z.number(),
  compliant: z.array(regulatoryStatusSchema),
  non_compliant: z.array(regulatoryStatusSchema),
  warnings: z.array(regulatoryStatusSchema),
  overall_risk: z.string(),
  apac_assertions: z.array(apacAssertionSummarySchema).optional(),
  apac_jurisdiction_count: z.number().optional(),
  fluoropolymer_exposure: z.string().nullable().optional(),
});

export const cascadePredictionSchema = z.object({
  status: z.string(),
  regulatory_stage: z.string(),
  source: z.string().optional(),
  affected_products: z.array(z.string()),
});

export const cascadeSchema = z.object({
  material: z.string(),
  forecast_year: z.number(),
  predictions: z.record(cascadePredictionSchema),
  recommendation: z.string(),
});

export const signalRowSchema = z.object({
  signal_id: z.string(),
  detected_at: z.string().optional(),
  source_label: z.string().optional(),
  country: z.string().optional(),
  classification: z.string().optional(),
  severity: z.string().optional(),
  summary: z.string().optional(),
});

export const signalListSchema = z.object({
  total: z.number(),
  signals: z.array(signalRowSchema),
});

export const pendingItemSchema = z.object({
  resolution_id: z.string(),
  gate_status: z.enum(["PENDING_REVIEW", "PENDING_APPROVAL", "APPROVED", "DISMISSED"]),
  human_review_required: z.boolean().optional(),
  warnings: z.array(z.string()).optional(),
  summary: z
    .object({
      compound: z.string().optional(),
      critical_flags: z.number().optional(),
    })
    .optional(),
});

export const pendingListSchema = z.object({
  count: z.number(),
  items: z.array(pendingItemSchema),
});

export const accessRequestCreateSchema = z.object({
  request_id: z.string(),
  status: z.enum(["pending", "approved", "rejected"]),
  email_sent: z.boolean(),
  message: z.string().optional(),
});

export const accessRequestStatusSchema = z.object({
  request_id: z.string(),
  status: z.enum(["pending", "approved", "rejected"]),
  created_at: z.string(),
  decided_at: z.string().nullable().optional(),
});

export const resolveResponseSchema = z.object({
  resolution_id: z.string(),
  gate_status: z.string(),
  warnings: z.array(z.string()).optional(),
  result: z
    .object({
      query_compound: z
        .object({
          preferred_name: z.string().optional(),
          cas: z.string().optional(),
        })
        .optional(),
      total_exposure: z
        .object({
          assertions_triggered: z.number().optional(),
          trajectory: z.string().optional(),
        })
        .optional(),
      threat_flags: z
        .array(
          z.object({
            flag_type: z.string().optional(),
            severity: z.string().optional(),
          }),
        )
        .optional(),
    })
    .passthrough(),
});

export const seedDemoSchema = z.object({
  inserted: z.number(),
  skipped: z.number(),
  signal_ids: z.array(z.string()),
  dry_run: z.boolean().optional(),
});

export const clearDemoSchema = z.object({
  deleted: z.number(),
  prefix: z.string(),
});

export const gateActionSchema = z.object({
  resolution_id: z.string().optional(),
  gate_status: z.string().optional(),
  action: z.string().optional(),
  status: z.string().optional(),
}).passthrough();

export const healthSchema = z.object({
  status: z.string(),
}).passthrough();

export const parentsSchema = z.object({
  parents: z.array(z.string()).optional().default([]),
}).passthrough();

export const graphSummarySchema = z.object({
  total_nodes: z.number(),
  total_edges: z.number(),
  parent_compounds: z.number(),
  endpoint_compounds: z.number(),
  haiku_records: z.number(),
});

const transformationSchema = z.object({
  parent: z.string(),
  child: z.string(),
  observations: z.number(),
  score: z.number(),
  temp_range: z.string(),
  atmosphere: z.string(),
  degradation_types: z.array(z.string()),
  hazard_level: z.string().nullable(),
  is_regulated: z.boolean(),
  source_count: z.number(),
  citations: z.array(z.string()),
});

export const fateQuerySchema = z.object({
  query: z.string(),
  total_transformations: z.number(),
  transformations: z.array(transformationSchema),
  compounds_involved: z.array(z.string()),
  compound_found: z.boolean(),
});

const endpointEntrySchema = z.object({
  endpoint: z.string(),
  count: z.number(),
  fraction: z.number(),
});

const epaNeighborSchema = z.object({
  name: z.string(),
  cas: z.string().nullable(),
  similarity: z.number(),
  f_count: z.number(),
  c_count: z.number(),
  mw: z.number(),
});

const pathwayNeighborSchema = z.object({
  name: z.string(),
  similarity: z.number(),
  pathways_count: z.number(),
  endpoints: z.array(z.string()),
  evidence_count: z.number(),
});

const citationEntrySchema = z.object({
  doi: z.string(),
  precursor: z.string(),
  product: z.string(),
  quote: z.string(),
  location: z.string(),
});

export const tier1SummarySchema = z.object({
  epa_compounds: z.number(),
  fate_compounds: z.number(),
  pathways: z.number(),
  compounds_with_fingerprints: z.number(),
});

export const tier1ResultSchema = z.object({
  query_name: z.string(),
  query_smiles: z.string(),
  risk_signal: z.string(),
  n_neighbors_with_pathways: z.number(),
  avg_similarity: z.number(),
  top_endpoints: z.array(endpointEntrySchema),
  mechanisms: z.record(z.number()),
  similar_in_epa: z.array(epaNeighborSchema),
  similar_with_pathways: z.array(pathwayNeighborSchema),
  evidence_citations: z.array(citationEntrySchema),
  disclaimer: z.string(),
});

const tier2PatternMatchSchema = z.object({
  pattern_name: z.string(),
  pattern_type: z.string(),
  value: z.string().nullable(),
});

const tier2EndpointCorrelationSchema = z.object({
  endpoint_bucket: z.string(),
  confidence: z.number(),
  ci_low: z.number(),
  ci_high: z.number(),
  n_precursors: z.number(),
  k_with_endpoint: z.number(),
  supporting_patterns: z.array(z.string()),
  example_products: z.array(z.string()),
});

export const tier2ResultSchema = z.object({
  query_smiles: z.string(),
  patterns_detected: z.array(tier2PatternMatchSchema),
  fluorine_metrics: z.record(z.union([z.number(), z.boolean()])),
  endpoint_correlations: z.array(tier2EndpointCorrelationSchema),
  coverage_info: z.record(z.union([z.number(), z.string()])),
  disclaimer: z.string(),
});

export const tier2CoverageSchema = z.object({
  total_precursors: z.number(),
  resolvable_precursors: z.number(),
  resolved_precursors: z.number(),
  resolution_rate: z.number(),
  total_pathways: z.number(),
  pathways_with_resolved_precursor: z.number(),
  unresolved_precursors: z.array(
    z.object({
      name: z.string(),
      pathway_count: z.number(),
    }),
  ),
  non_resolvable_count: z.number(),
  non_resolvable_examples: z.array(z.string()),
  patterns_with_support: z.record(z.number()),
  patterns_insufficient_support: z.record(z.number()),
});

const tier2RuleSchema = z.object({
  pattern_name: z.string(),
  endpoint_bucket: z.string(),
  n_precursors: z.number(),
  k_with_endpoint: z.number(),
  confidence: z.number(),
  ci_low: z.number(),
  ci_high: z.number(),
  example_precursors: z.array(z.string()),
  example_products: z.array(z.string()),
});

export const tier2RulesSchema = z.object({
  rules: z.array(tier2RuleSchema),
  total: z.number(),
}).passthrough();

const portfolioResultSchema = z.object({
  material: z.string(),
  risk_score: z.number(),
  risk_category: z.string(),
  pfas_count: z.number(),
  regulatory_flags: z.number(),
  litigation_probability: z.number(),
});

export const portfolioResponseSchema = z.object({
  total_materials: z.number(),
  high_risk_count: z.number(),
  total_exposure_usd: z.number(),
  results: z.array(portfolioResultSchema),
  executive_summary: z.string(),
  methodology_note: z.string().optional(),
});

const reportSectionSchema = z.object({
  title: z.string(),
  content: z.string(),
  data: z.record(z.unknown()).optional(),
  flags: z.array(z.string()).optional(),
  similar_cases: z.array(z.string()).optional(),
});

export const executiveReportSchema = z.object({
  title: z.string(),
  generated: z.string(),
  classification: z.string(),
  material: z.string(),
  sections: z.array(reportSectionSchema),
  data_sources: z.record(z.number()).optional(),
});

const evidenceItemSchema = z.object({
  source: z.string(),
  doi: z.string().nullable(),
  year: z.number().nullable(),
  confidence: z.number(),
  finding: z.string(),
  compound: z.string(),
});

export const evidenceChainSchema = z.object({
  material: z.string(),
  total_citations: z.number(),
  evidence_chain: z.array(evidenceItemSchema),
  confidence_score: z.number(),
});

export const evidenceSourceStatsSchema = z.object({
  total_papers: z.number(),
  extraction_method: z.string(),
  sources: z.array(
    z.object({
      type: z.string(),
      count: z.number(),
    }),
  ),
  coverage: z.object({
    polymers: z.number(),
    pfas_endpoints: z.number(),
    total_pathway_citations: z.number(),
  }),
});

const analyzeFindingSchema = z.object({
  product: z.string(),
  screening_classification: z.string(),
  conditions_where_it_forms: z.array(z.record(z.unknown())),
  regulatory_flags: z.array(z.string()),
  evidence_refs: z.array(z.record(z.unknown())),
  evidence_strength: z.number().optional(),
  support_lower: z.number().optional(),
  support_upper: z.number().optional(),
  confidence: z.number().optional(),
  literature_support: z.number().optional(),
  overall_confidence: z.number(),
  pathway: z.array(z.string()),
  litigation_flag: z.boolean(),
  is_short_chain_pfas: z.boolean(),
  observation_count: z.number().optional(),
  paper_count: z.number().optional(),
  source_dois: z.array(z.string()).optional(),
});

export const analyzeResponseSchema = z.object({
  compound_evaluated: z.string(),
  scenario_context: z.record(z.unknown()),
  pfas_findings: z.array(analyzeFindingSchema),
  summary: z.string(),
  data_source: z.string().optional(),
  papers_in_corpus: z.number().optional(),
  disclaimer: z.string().optional(),
});

export const litigationBacktestsSchema = z.object({
  available_backtests: z.array(
    z.object({
      compound_id: z.string(),
      compound: z.string(),
      total_publications: z.number().optional(),
      first_lawsuit_year: z.number().optional(),
      lead_time_years: z.number().optional(),
      settlement_total_usd: z.number().optional(),
    }).passthrough(),
  ).default([]),
}).passthrough();

export const litigationBacktestSchema = z.object({
  compound: z.string(),
  compound_id: z.string(),
  total_publications: z.number(),
  first_publication_year: z.number(),
  first_lawsuit_year: z.number(),
  lead_time_years: z.number(),
  phases: z.array(z.record(z.unknown())),
  timeline: z.array(z.record(z.unknown())),
  key_events: z.array(z.record(z.unknown())),
  sentinel_reconstruction: z.object({
    narrative: z.string(),
    counterfactual: z.string(),
    key_insight: z.string(),
  }),
  settlement_total_usd: z.number(),
  affected_population: z.number(),
  source_citations: z.array(z.string()),
}).passthrough();

export const litigationPapersSchema = z.object({
  compound_id: z.string(),
  year: z.number(),
  total: z.number(),
  papers: z.array(
    z.object({
      pmid: z.string(),
      title: z.string(),
      journal: z.string(),
      category: z.string(),
      confidence: z.number(),
      reasoning: z.string(),
    }),
  ),
});

export const litigationForecastSchema = z.object({
  compound: z.string(),
  probability_12_months: z.number(),
  probability_24_months: z.number(),
  probability_36_months: z.number(),
  risk_level: z.string(),
  confidence_low: z.number(),
  confidence_high: z.number(),
  key_drivers: z.array(z.string()),
  estimated_exposure_usd: z.number(),
  similar_cases: z.array(
    z.object({
      case: z.string(),
      settlement: z.number(),
      year: z.number(),
      relevance: z.number(),
    }),
  ),
});

export type RegulatoryCheck = z.infer<typeof regulatoryCheckSchema>;
export type CascadeResponse = z.infer<typeof cascadeSchema>;
export type SignalRow = z.infer<typeof signalRowSchema>;
export type PendingItem = z.infer<typeof pendingItemSchema>;
export type ResolveResponse = z.infer<typeof resolveResponseSchema>;
export type GraphSummary = z.infer<typeof graphSummarySchema>;
export type FateQueryResponse = z.infer<typeof fateQuerySchema>;
export type Tier1Summary = z.infer<typeof tier1SummarySchema>;
export type Tier1Result = z.infer<typeof tier1ResultSchema>;
export type Tier2Result = z.infer<typeof tier2ResultSchema>;
export type Tier2Coverage = z.infer<typeof tier2CoverageSchema>;
export type PortfolioResponse = z.infer<typeof portfolioResponseSchema>;
export type ExecutiveReport = z.infer<typeof executiveReportSchema>;
export type EvidenceChainResponse = z.infer<typeof evidenceChainSchema>;
export type EvidenceSourceStats = z.infer<typeof evidenceSourceStatsSchema>;
export type AnalyzeResponse = z.infer<typeof analyzeResponseSchema>;
