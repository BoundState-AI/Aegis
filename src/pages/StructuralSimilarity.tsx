import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/hooks/use-toast";
import {
  Loader2, Search, Fingerprint, FlaskConical, ExternalLink,
  AlertTriangle, CheckCircle, ShieldAlert, ChevronDown, ChevronUp,
  Atom, FileText, Beaker, Shapes, TrendingUp, Database, Info,
} from "lucide-react";
import DaikinHeader from "@/components/layout/DaikinHeader";
import { useHelpContent } from "@/config/helpContent";
import { apiGet, apiPost } from "@/lib/apiClient";
import {
  tier1ResultSchema,
  tier1SummarySchema,
  tier2CoverageSchema,
  tier2ResultSchema,
  tier2RulesSchema,
} from "@/lib/apiSchemas";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface EndpointEntry {
  endpoint: string;
  count: number;
  fraction: number;
}

interface EpaNeighbor {
  name: string;
  cas: string | null;
  similarity: number;
  f_count: number;
  c_count: number;
  mw: number;
}

interface PathwayNeighbor {
  name: string;
  similarity: number;
  pathways_count: number;
  endpoints: string[];
  evidence_count: number;
}

interface CitationEntry {
  doi: string;
  precursor: string;
  product: string;
  quote: string;
  location: string;
}

interface Tier1Result {
  query_name: string;
  query_smiles: string;
  risk_signal: string;
  n_neighbors_with_pathways: number;
  avg_similarity: number;
  top_endpoints: EndpointEntry[];
  mechanisms: Record<string, number>;
  similar_in_epa: EpaNeighbor[];
  similar_with_pathways: PathwayNeighbor[];
  evidence_citations: CitationEntry[];
  disclaimer: string;
}

interface Tier1Summary {
  epa_compounds: number;
  fate_compounds: number;
  pathways: number;
  compounds_with_fingerprints: number;
}

// ---------------------------------------------------------------------------
// Tier 2 Types
// ---------------------------------------------------------------------------

interface Tier2PatternMatch {
  pattern_name: string;
  pattern_type: string;
  value: string | null;
}

interface Tier2EndpointCorrelation {
  endpoint_bucket: string;
  confidence: number;
  ci_low: number;
  ci_high: number;
  n_precursors: number;
  k_with_endpoint: number;
  supporting_patterns: string[];
  example_products: string[];
}

interface Tier2Result {
  query_smiles: string;
  patterns_detected: Tier2PatternMatch[];
  fluorine_metrics: Record<string, number | boolean>;
  endpoint_correlations: Tier2EndpointCorrelation[];
  coverage_info: Record<string, number | string>;
  disclaimer: string;
}

interface Tier2Coverage {
  total_precursors: number;
  resolvable_precursors: number;
  resolved_precursors: number;
  resolution_rate: number;
  total_pathways: number;
  pathways_with_resolved_precursor: number;
  unresolved_precursors: Array<{ name: string; pathway_count: number }>;
  non_resolvable_count: number;
  non_resolvable_examples: string[];
  patterns_with_support: Record<string, number>;
  patterns_insufficient_support: Record<string, number>;
}

interface Tier2Rule {
  pattern_name: string;
  endpoint_bucket: string;
  n_precursors: number;
  k_with_endpoint: number;
  confidence: number;
  ci_low: number;
  ci_high: number;
  example_precursors: string[];
  example_products: string[];
}

// ---------------------------------------------------------------------------
// Reference compounds with known SMILES
// ---------------------------------------------------------------------------

const REFERENCE_COMPOUNDS: Array<{ name: string; smiles: string }> = [
  { name: "GenX", smiles: "OC(=O)C(F)(OC(F)(F)C(F)(F)C(F)(F)F)C(F)(F)F" },
  { name: "PFOA", smiles: "OC(=O)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)F" },
  { name: "PFOS", smiles: "OS(=O)(=O)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)F" },
  { name: "6:2 FTOH", smiles: "OCCC(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)C(F)(F)F" },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const getRiskColor = (signal: string) => {
  switch (signal) {
    case "HIGH": return "bg-red-500";
    case "MEDIUM": return "bg-yellow-500";
    case "LOW": return "bg-green-500";
    default: return "bg-gray-400";
  }
};

const getRiskBorderColor = (signal: string) => {
  switch (signal) {
    case "HIGH": return "border-red-500";
    case "MEDIUM": return "border-yellow-500";
    case "LOW": return "border-green-500";
    default: return "border-gray-300";
  }
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const StructuralSimilarity = () => {
  const { t } = useTranslation();
  const { toast } = useToast();
  const helpContent = useHelpContent();
  const [isLoading, setIsLoading] = useState(false);
  const [smiles, setSmiles] = useState(REFERENCE_COMPOUNDS[0].smiles); // Default to GenX
  const [compoundName, setCompoundName] = useState(REFERENCE_COMPOUNDS[0].name);
  const [result, setResult] = useState<Tier1Result | null>(null);
  const [summary, setSummary] = useState<Tier1Summary | null>(null);
  const [showEvidence, setShowEvidence] = useState(false);
  const [showSimilar, setShowSimilar] = useState(false);

  // Tier 2 state
  const [tier2Result, setTier2Result] = useState<Tier2Result | null>(null);
  const [tier2Coverage, setTier2Coverage] = useState<Tier2Coverage | null>(null);
  const [tier2Rules, setTier2Rules] = useState<Tier2Rule[]>([]);
  const [tier2RulesTotal, setTier2RulesTotal] = useState(0);
  const [showCorrelations, setShowCorrelations] = useState(false);
  const [showRulesExplorer, setShowRulesExplorer] = useState(false);
  const [isLoadingRules, setIsLoadingRules] = useState(false);

  useEffect(() => {
    void loadSummary();
    void loadTier2Coverage();
    // Auto-query on mount
    void handleQuery();
    // Intentionally run once on mount to pre-populate default query/coverage.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadSummary = async () => {
    try {
      const data = await apiGet("/api/v1/tier1/summary", tier1SummarySchema);
      setSummary(data as Tier1Summary);
    } catch {
      // Engine not loaded yet — will init on first query
    }
  };

  const loadTier2Coverage = async () => {
    try {
      const data = await apiGet("/api/v1/tier2/coverage", tier2CoverageSchema);
      setTier2Coverage(data as Tier2Coverage);
    } catch {
      // Tier 2 engine not loaded yet
    }
  };

  const loadTier2Rules = async () => {
    if (tier2Rules.length > 0) return; // Already loaded
    setIsLoadingRules(true);
    try {
      const data = await apiGet("/api/v1/tier2/rules?limit=200", tier2RulesSchema);
      setTier2Rules(data.rules as Tier2Rule[]);
      setTier2RulesTotal(data.total);
    } catch {
      // Tier 2 engine not available
    } finally {
      setIsLoadingRules(false);
    }
  };

  const handleQuery = async () => {
    if (!smiles.trim()) {
      toast({
        title: t('common.smilesRequired'),
        description: t('tier1.enterSmilesOrSelect'),
        variant: "destructive",
      });
      return;
    }

    setIsLoading(true);
    setResult(null);
    setTier2Result(null);

    try {
      // Fire Tier 1 and Tier 2 queries in parallel
      const [tier1Res, tier2Res] = await Promise.all([
        apiPost("/api/v1/tier1/query", tier1ResultSchema, {
          smiles: smiles.trim(),
          compound_name: compoundName.trim() || undefined,
          top_k: 10,
          min_similarity: 0.4,
        }),
        apiPost("/api/v1/tier2/predict", tier2ResultSchema, {
          smiles: smiles.trim(),
        }).catch(() => null), // Tier 2 failure is non-fatal
      ]);

      const data = tier1Res as Tier1Result;
      setResult(data);

      // Parse Tier 2 if available
      if (tier2Res) {
        const t2data = tier2Res as Tier2Result;
        setTier2Result(t2data);
      }

      // Refresh summary/coverage after first query (engines may have just initialized)
      if (!summary) loadSummary();
      if (!tier2Coverage) loadTier2Coverage();

      toast({
        title: t('common.analysisComplete'),
        description: `${data.query_name}: ${data.risk_signal} risk signal (${data.n_neighbors_with_pathways} neighbors with pathway data)`,
      });
    } catch {
      toast({
        title: t('common.queryFailed'),
        description: t('tier1.couldNotConnect'),
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const selectDemo = (compound: { name: string; smiles: string }) => {
    setSmiles(compound.smiles);
    setCompoundName(compound.name);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <DaikinHeader
        title={t('tier1.title')}
        subtitle={t('tier1.subtitle')}
        helpContent={helpContent.tier1}
      >
        {summary && (
          <>
            <div className="text-gray-600">
              <span className="text-daikin-blue font-bold">{summary.epa_compounds.toLocaleString()}</span> {t('tier1.epaCompounds')}
            </div>
            <div className="text-gray-600">
              <span className="text-daikin-blue font-bold">{summary.pathways.toLocaleString()}</span> {t('common.pathways')}
            </div>
            <div className="text-gray-600">
              <span className="text-daikin-blue font-bold">{summary.compounds_with_fingerprints}</span> {t('tier1.fingerprinted')}
            </div>
            {tier2Coverage && (
              <div className="text-gray-600">
                <span className="text-daikin-blue font-bold">
                  {tier2Coverage.resolved_precursors}/{tier2Coverage.resolvable_precursors}
                </span>{" "}
                {t('tier1.resolved')} ({(tier2Coverage.resolution_rate * 100).toFixed(0)}%)
              </div>
            )}
          </>
        )}
      </DaikinHeader>

      <main className="container mx-auto px-4 py-8 space-y-6">
        {/* Input Section */}
        <Card className="bg-white border-gray-200 shadow-sm">
          <CardHeader>
            <CardTitle className="text-daikin-dark flex items-center gap-2">
              <Fingerprint className="h-5 w-5 text-daikin-blue" />
              {t('tier1.compoundQuery')}
            </CardTitle>
            <CardDescription>
              {t('tier1.queryDescription')}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label className="text-gray-700">{t('tier1.smiles')}</Label>
              <Input
                value={smiles}
                onChange={(e) => setSmiles(e.target.value)}
                placeholder="e.g. OC(=O)C(F)(OC(F)(F)C(F)(F)C(F)(F)F)C(F)(F)F"
                className="bg-white border-gray-300 font-mono text-sm"
              />
            </div>

            <div>
              <Label className="text-gray-700">{t('tier1.compoundName')}</Label>
              <Input
                value={compoundName}
                onChange={(e) => setCompoundName(e.target.value)}
                placeholder="e.g. GenX"
                className="bg-white border-gray-300"
              />
            </div>

            <div>
              <Label className="text-gray-700 text-xs">{t('tier1.quickSelect')}</Label>
              <div className="flex flex-wrap gap-2 mt-1">
                {REFERENCE_COMPOUNDS.map((c) => (
                  <Badge
                    key={c.name}
                    variant={smiles === c.smiles ? "default" : "outline"}
                    className={`cursor-pointer ${
                      smiles === c.smiles
                        ? "bg-daikin-blue text-white"
                        : "border-gray-400 text-gray-600 hover:border-daikin-blue hover:text-daikin-blue"
                    }`}
                    onClick={() => selectDemo(c)}
                  >
                    {c.name}
                  </Badge>
                ))}
              </div>
            </div>

            <Button
              onClick={handleQuery}
              disabled={isLoading || !smiles.trim()}
              className="w-full bg-gradient-to-r from-daikin-blue to-daikin-accent hover:opacity-90 text-white"
            >
              {isLoading ? (
                <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> {t('tier1.analyzingStructure')}</>
              ) : (
                <><Search className="mr-2 h-4 w-4" /> {t('tier1.analyzeCompound')}</>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Results */}
        {result && (
          <>
            {/* Risk Signal Banner */}
            <Card className={`border-2 ${getRiskBorderColor(result.risk_signal)} shadow-sm`}>
              <CardContent className="py-6">
                <div className="flex items-center justify-between flex-wrap gap-4">
                  <div className="flex items-center gap-4">
                    <Badge className={`${getRiskColor(result.risk_signal)} text-white text-lg px-4 py-1`}>
                      {result.risk_signal}
                    </Badge>
                    <div>
                      <p className="text-lg font-bold text-daikin-dark">{result.query_name}</p>
                      <p className="text-xs text-gray-400 font-mono truncate max-w-md">{result.query_smiles}</p>
                    </div>
                  </div>
                  <div className="flex gap-6 text-center">
                    <div>
                      <p className="text-2xl font-bold text-daikin-dark">{result.n_neighbors_with_pathways}</p>
                      <p className="text-xs text-gray-500">Neighbors with pathways</p>
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-daikin-dark">{(result.avg_similarity * 100).toFixed(0)}%</p>
                      <p className="text-xs text-gray-500">Avg similarity</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Main Results Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Top Endpoints */}
              <Card className="bg-white border-gray-200 shadow-sm">
                <CardHeader>
                  <CardTitle className="text-daikin-dark flex items-center gap-2">
                    <FlaskConical className="h-5 w-5 text-daikin-accent" />
                    {t('tier1.degradationEndpoints')}
                  </CardTitle>
                  <CardDescription>
                    {t('tier1.endpointsDescription')}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {result.top_endpoints.length > 0 ? (
                    <div className="space-y-3">
                      {result.top_endpoints.map((ep, i) => (
                        <div key={i} className="flex items-center justify-between">
                          <div className="flex items-center gap-2 flex-1">
                            <span className="text-sm font-medium text-daikin-dark w-32 truncate">{ep.endpoint}</span>
                            <Progress value={ep.fraction * 100} className="flex-1 h-2" />
                          </div>
                          <div className="text-right ml-3">
                            <span className="text-sm font-bold text-daikin-dark">{ep.count}</span>
                            <span className="text-xs text-gray-400 ml-1">({(ep.fraction * 100).toFixed(0)}%)</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500">No pathway endpoints found for structural neighbors.</p>
                  )}
                </CardContent>
              </Card>

              {/* Mechanisms */}
              <Card className="bg-white border-gray-200 shadow-sm">
                <CardHeader>
                  <CardTitle className="text-daikin-dark flex items-center gap-2">
                    <Beaker className="h-5 w-5 text-daikin-accent" />
                    {t('tier1.degradationMechanisms')}
                  </CardTitle>
                  <CardDescription>
                    {t('tier1.mechanismsDescription')}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {Object.keys(result.mechanisms).length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(result.mechanisms)
                        .sort(([, a], [, b]) => b - a)
                        .map(([mechanism, count]) => (
                          <Badge
                            key={mechanism}
                            variant="outline"
                            className="border-daikin-dark/30 text-daikin-dark"
                          >
                            {mechanism.replace(/_/g, " ")} ({count})
                          </Badge>
                        ))}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500">No mechanism data available.</p>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* Tier 2: Substructure Fingerprint */}
            {tier2Result && tier2Result.patterns_detected.length > 0 && (
              <Card className="bg-white border-gray-200 shadow-sm">
                <CardHeader>
                  <CardTitle className="text-daikin-dark flex items-center gap-2">
                    <Shapes className="h-5 w-5 text-daikin-accent" />
                    {t('tier1.substructureFingerprint')}
                  </CardTitle>
                  <CardDescription>
                    {t('tier1.patternsDetected')}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Pattern badges grouped by type */}
                  <div>
                    <div className="flex flex-wrap gap-2">
                      {tier2Result.patterns_detected.map((p, i) => (
                        <Badge
                          key={i}
                          variant="outline"
                          className={
                            p.pattern_type === "smarts"
                              ? "border-blue-400 text-blue-700 bg-blue-50"
                              : p.pattern_type === "algorithmic"
                              ? "border-emerald-400 text-emerald-700 bg-emerald-50"
                              : "border-purple-400 text-purple-700 bg-purple-50"
                          }
                        >
                          {p.pattern_name.replace(/_/g, " ")}
                          {p.value && (
                            <span className="ml-1 opacity-70 text-xs">({p.value})</span>
                          )}
                        </Badge>
                      ))}
                    </div>
                    <div className="flex gap-4 mt-2 text-xs text-gray-400">
                      <span className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-blue-400" /> SMARTS
                      </span>
                      <span className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-emerald-400" /> Algorithmic
                      </span>
                      <span className="flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-purple-400" /> Classification
                      </span>
                    </div>
                  </div>

                  {/* Fluorine metrics row */}
                  {tier2Result.fluorine_metrics && (
                    <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
                      {[
                        { label: "Chain", value: tier2Result.fluorine_metrics.perfluoro_chain_len_max, unit: "C" },
                        { label: "F/C Ratio", value: typeof tier2Result.fluorine_metrics.f_to_c_ratio === "number" ? (tier2Result.fluorine_metrics.f_to_c_ratio as number).toFixed(2) : "—" },
                        { label: "CF\u2082", value: tier2Result.fluorine_metrics.cf2_count },
                        { label: "CF\u2083", value: tier2Result.fluorine_metrics.has_cf3_terminal ? "\u2713" : "\u2717" },
                        { label: "F atoms", value: tier2Result.fluorine_metrics.f_count },
                        { label: "C atoms", value: tier2Result.fluorine_metrics.c_count },
                        { label: "PF Carbons", value: tier2Result.fluorine_metrics.perfluoro_carbon_count },
                      ].map((m, i) => (
                        <div key={i} className="bg-gray-50 rounded-lg p-2 text-center">
                          <p className="text-lg font-bold text-daikin-dark">{m.value}{m.unit ? ` ${m.unit}` : ""}</p>
                          <p className="text-xs text-gray-500">{m.label}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Tier 2: Pattern-Based Endpoint Correlations */}
            {tier2Result && tier2Result.endpoint_correlations.length > 0 && (
              <Card className="bg-white border-gray-200 shadow-sm">
                <CardHeader
                  className="cursor-pointer"
                  onClick={() => setShowCorrelations(!showCorrelations)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <TrendingUp className="h-5 w-5 text-daikin-accent" />
                      <CardTitle className="text-daikin-dark">
                        {t('tier1.patternBasedCorrelations')} ({tier2Result.endpoint_correlations.length})
                      </CardTitle>
                    </div>
                    {showCorrelations
                      ? <ChevronUp className="h-5 w-5 text-gray-400" />
                      : <ChevronDown className="h-5 w-5 text-gray-400" />
                    }
                  </div>
                  <CardDescription>
                    {t('tier1.correlationsDescription')}
                    {tier2Result.coverage_info.resolved_precursors != null && (
                      <span className="ml-1">
                        Based on {tier2Result.coverage_info.resolved_precursors as number} resolved precursors.
                      </span>
                    )}
                  </CardDescription>
                </CardHeader>
                {showCorrelations && (
                  <CardContent>
                    <div className="space-y-4">
                      {tier2Result.endpoint_correlations.map((ec, i) => (
                        <div key={i} className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-sm font-semibold text-daikin-dark">
                              {ec.endpoint_bucket.replace(/_/g, " ")}
                            </span>
                            <div className="text-right">
                              <span className="text-lg font-bold text-daikin-dark">
                                {(ec.confidence * 100).toFixed(0)}%
                              </span>
                              <span className="text-xs text-gray-400 ml-1">
                                [{(ec.ci_low * 100).toFixed(0)}, {(ec.ci_high * 100).toFixed(0)}]
                              </span>
                            </div>
                          </div>

                          {/* Confidence bar with CI range */}
                          <div className="relative h-3 bg-gray-200 rounded-full overflow-hidden mb-2">
                            {/* CI range background */}
                            <div
                              className="absolute h-full bg-daikin-accent/20 rounded-full"
                              style={{
                                left: `${ec.ci_low * 100}%`,
                                width: `${(ec.ci_high - ec.ci_low) * 100}%`,
                              }}
                            />
                            {/* Point estimate */}
                            <div
                              className="absolute h-full bg-gradient-to-r from-daikin-blue to-daikin-accent rounded-full"
                              style={{ width: `${ec.confidence * 100}%` }}
                            />
                          </div>

                          <div className="flex items-center justify-between text-xs text-gray-500">
                            <div className="flex flex-wrap gap-1">
                              {ec.supporting_patterns.map((p, j) => (
                                <Badge key={j} variant="outline" className="text-xs border-gray-300 px-1.5 py-0">
                                  {p.replace(/_/g, " ")}
                                </Badge>
                              ))}
                            </div>
                            <span>n={ec.n_precursors}, k={ec.k_with_endpoint}</span>
                          </div>

                          {ec.example_products.length > 0 && (
                            <div className="mt-2 text-xs text-gray-400">
                              Examples: {ec.example_products.join(", ")}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </CardContent>
                )}
              </Card>
            )}

            {/* EPA Similar Compounds */}
            <Card className="bg-white border-gray-200 shadow-sm">
              <CardHeader
                className="cursor-pointer"
                onClick={() => setShowSimilar(!showSimilar)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Atom className="h-5 w-5 text-daikin-accent" />
                    <CardTitle className="text-daikin-dark">
                      {t('tier1.structurallySimilarCompounds')} ({result.similar_in_epa.length} EPA + {result.similar_with_pathways.length} {t('tier1.withPathways')})
                    </CardTitle>
                  </div>
                  {showSimilar ? <ChevronUp className="h-5 w-5 text-gray-400" /> : <ChevronDown className="h-5 w-5 text-gray-400" />}
                </div>
              </CardHeader>
              {showSimilar && (
                <CardContent>
                  {/* Pathway Neighbors */}
                  {result.similar_with_pathways.length > 0 && (
                    <div className="mb-6">
                      <h4 className="text-sm font-semibold text-gray-700 mb-3">Compounds with Known Degradation Pathways</h4>
                      <div className="space-y-2">
                        {result.similar_with_pathways.map((n, i) => (
                          <div
                            key={i}
                            className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 cursor-pointer"
                            onClick={() => {
                              // Resolve and query the neighbor
                              setCompoundName(n.name);
                              toast({ title: "Hint", description: `To query ${n.name}, resolve its SMILES via the API first.` });
                            }}
                          >
                            <div>
                              <p className="font-medium text-daikin-dark">{n.name}</p>
                              <p className="text-xs text-gray-500">
                                {n.pathways_count} pathways | {n.evidence_count} citations
                              </p>
                            </div>
                            <div className="text-right">
                              <p className="text-lg font-bold text-daikin-dark">{(n.similarity * 100).toFixed(0)}%</p>
                              <p className="text-xs text-gray-400">similarity</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* EPA Neighbors */}
                  {result.similar_in_epa.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold text-gray-700 mb-3">EPA PFAS Database Neighbors</h4>
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-gray-200">
                              <th className="text-left py-2 text-gray-600">Name</th>
                              <th className="text-left py-2 text-gray-600">CAS</th>
                              <th className="text-right py-2 text-gray-600">Similarity</th>
                              <th className="text-right py-2 text-gray-600">F atoms</th>
                              <th className="text-right py-2 text-gray-600">MW</th>
                            </tr>
                          </thead>
                          <tbody>
                            {result.similar_in_epa.map((n, i) => (
                              <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                                <td className="py-2 text-daikin-dark font-medium truncate max-w-[200px]">{n.name}</td>
                                <td className="py-2 text-gray-500 font-mono text-xs">{n.cas || "—"}</td>
                                <td className="py-2 text-right font-bold text-daikin-dark">{(n.similarity * 100).toFixed(1)}%</td>
                                <td className="py-2 text-right text-gray-600">{n.f_count}</td>
                                <td className="py-2 text-right text-gray-600">{n.mw.toFixed(0)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </CardContent>
              )}
            </Card>

            {/* Evidence Citations */}
            <Card className="bg-white border-gray-200 shadow-sm">
              <CardHeader
                className="cursor-pointer"
                onClick={() => setShowEvidence(!showEvidence)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <FileText className="h-5 w-5 text-daikin-accent" />
                    <CardTitle className="text-daikin-dark">
                      {t('tier1.evidenceCitations')} ({result.evidence_citations.length} DOIs)
                    </CardTitle>
                  </div>
                  {showEvidence ? <ChevronUp className="h-5 w-5 text-gray-400" /> : <ChevronDown className="h-5 w-5 text-gray-400" />}
                </div>
              </CardHeader>
              {showEvidence && (
                <CardContent>
                  {result.evidence_citations.length > 0 ? (
                    <div className="space-y-4">
                      {result.evidence_citations.map((cite, i) => (
                        <div key={i} className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                          <div className="flex items-start justify-between gap-3 mb-2">
                            <div className="flex items-center gap-2">
                              <Badge variant="outline" className="text-xs border-daikin-dark/30">
                                {cite.precursor} &rarr; {cite.product}
                              </Badge>
                            </div>
                            {cite.doi && (
                              <a
                                href={`https://doi.org/${cite.doi}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs text-blue-600 hover:underline flex items-center gap-1 flex-shrink-0"
                              >
                                <ExternalLink className="h-3 w-3" />
                                {cite.doi}
                              </a>
                            )}
                          </div>
                          {cite.quote && (
                            <p className="text-sm text-gray-600 italic border-l-2 border-daikin-accent/30 pl-3">
                              "{cite.quote}"
                            </p>
                          )}
                          {cite.location && (
                            <p className="text-xs text-gray-400 mt-1">{cite.location}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500">No evidence citations found for structural neighbors.</p>
                  )}
                </CardContent>
              )}
            </Card>

            {/* Corpus Rules Explorer */}
            <Card className="bg-white border-gray-200 shadow-sm">
              <CardHeader
                className="cursor-pointer"
                onClick={() => {
                  const next = !showRulesExplorer;
                  setShowRulesExplorer(next);
                  if (next) loadTier2Rules();
                }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Database className="h-5 w-5 text-daikin-accent" />
                    <CardTitle className="text-daikin-dark">
                      {t('tier1.corpusRulesExplorer')}
                      {tier2Coverage && (
                        <span className="text-sm font-normal text-gray-500 ml-2">
                          {tier2RulesTotal || "..."} {t('tier1.rules')} | {tier2Coverage.resolved_precursors}/{tier2Coverage.resolvable_precursors} {t('tier1.precursorsResolved')}
                        </span>
                      )}
                    </CardTitle>
                  </div>
                  {showRulesExplorer
                    ? <ChevronUp className="h-5 w-5 text-gray-400" />
                    : <ChevronDown className="h-5 w-5 text-gray-400" />
                  }
                </div>
                <CardDescription>
                  {t('tier1.browseAllRules')}
                </CardDescription>
              </CardHeader>
              {showRulesExplorer && (
                <CardContent>
                  {isLoadingRules ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="h-6 w-6 animate-spin text-daikin-blue" />
                      <span className="ml-2 text-gray-500">Loading rules...</span>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {/* Coverage summary */}
                      {tier2Coverage && (
                        <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                          <div className="flex items-start gap-2">
                            <Info className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
                            <div className="text-sm text-blue-900">
                              <p className="font-medium">
                                Coverage: {tier2Coverage.resolved_precursors} of {tier2Coverage.resolvable_precursors} resolvable precursors resolved to SMILES ({(tier2Coverage.resolution_rate * 100).toFixed(1)}%)
                              </p>
                              <p className="text-xs mt-1">
                                {tier2Coverage.pathways_with_resolved_precursor} of {tier2Coverage.total_pathways} pathways have resolved precursors.
                                {" "}{tier2Coverage.non_resolvable_count} non-resolvable terms filtered (class names, mixtures, substrates).
                                {" "}Rules are derived only from resolved precursors.
                              </p>
                              {tier2Coverage.unresolved_precursors.length > 0 && (
                                <p className="text-xs mt-1 text-blue-700">
                                  Top unresolved: {tier2Coverage.unresolved_precursors.slice(0, 5).map(u => `${u.name} (${u.pathway_count})`).join(", ")}
                                </p>
                              )}
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Pattern support summary */}
                      {tier2Coverage && Object.keys(tier2Coverage.patterns_with_support).length > 0 && (
                        <div>
                          <h4 className="text-sm font-semibold text-gray-700 mb-2">Patterns with Support</h4>
                          <div className="flex flex-wrap gap-2">
                            {Object.entries(tier2Coverage.patterns_with_support)
                              .sort(([, a], [, b]) => b - a)
                              .map(([name, n]) => (
                                <Badge key={name} variant="outline" className="border-emerald-400 text-emerald-700 bg-emerald-50">
                                  {name.replace(/_/g, " ")} (n={n})
                                </Badge>
                              ))}
                            {Object.entries(tier2Coverage.patterns_insufficient_support)
                              .sort(([, a], [, b]) => b - a)
                              .map(([name, n]) => (
                                <Badge key={name} variant="outline" className="border-gray-300 text-gray-400">
                                  {name.replace(/_/g, " ")} (n={n})
                                </Badge>
                              ))}
                          </div>
                        </div>
                      )}

                      {/* Rules table */}
                      {tier2Rules.length > 0 && (
                        <div>
                          <h4 className="text-sm font-semibold text-gray-700 mb-2">
                            All Rules ({tier2RulesTotal})
                          </h4>
                          <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                              <thead>
                                <tr className="border-b border-gray-200">
                                  <th className="text-left py-2 text-gray-600">Pattern</th>
                                  <th className="text-left py-2 text-gray-600">Endpoint</th>
                                  <th className="text-right py-2 text-gray-600">Confidence</th>
                                  <th className="text-right py-2 text-gray-600">CI</th>
                                  <th className="text-right py-2 text-gray-600">n</th>
                                  <th className="text-right py-2 text-gray-600">k</th>
                                </tr>
                              </thead>
                              <tbody>
                                {tier2Rules.map((rule, i) => (
                                  <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
                                    <td className="py-2 text-daikin-dark font-medium">
                                      {rule.pattern_name.replace(/_/g, " ")}
                                    </td>
                                    <td className="py-2 text-gray-600">
                                      {rule.endpoint_bucket.replace(/_/g, " ")}
                                    </td>
                                    <td className="py-2 text-right font-bold text-daikin-dark">
                                      {(rule.confidence * 100).toFixed(0)}%
                                    </td>
                                    <td className="py-2 text-right text-gray-400 text-xs">
                                      [{(rule.ci_low * 100).toFixed(0)}, {(rule.ci_high * 100).toFixed(0)}]
                                    </td>
                                    <td className="py-2 text-right text-gray-600">{rule.n_precursors}</td>
                                    <td className="py-2 text-right text-gray-600">{rule.k_with_endpoint}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
              )}
            </Card>

            {/* Disclaimer */}
            <Card className="bg-amber-50 border-amber-200 shadow-sm">
              <CardContent className="py-4">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
                  <div className="text-sm text-amber-900 space-y-1">
                    <p>{result.disclaimer}</p>
                    {tier2Result && (
                      <p>{tier2Result.disclaimer}</p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </>
        )}

        {/* Placeholder when no results */}
        {!result && !isLoading && (
          <Card className="bg-white border-gray-200 shadow-sm">
            <CardContent className="py-16 text-center">
              <div className="h-16 w-16 mx-auto mb-4 rounded-full bg-gradient-to-r from-daikin-blue to-daikin-accent flex items-center justify-center">
                <Fingerprint className="h-8 w-8 text-white" />
              </div>
              <h3 className="text-xl font-semibold text-daikin-dark mb-2">{t('tier1.structuralSimilaritySearch')}</h3>
              <p className="text-gray-500 max-w-lg mx-auto">
                {t('tier1.searchDescription')}
              </p>
              {summary && (
                <div className="flex justify-center gap-8 mt-6 text-sm text-gray-500 flex-wrap">
                  <div>
                    <span className="font-bold text-daikin-dark">{summary.epa_compounds.toLocaleString()}</span> {t('tier1.epaCompoundsLower')}
                  </div>
                  <div>
                    <span className="font-bold text-daikin-dark">{summary.pathways.toLocaleString()}</span> {t('common.pathwaysLower')}
                  </div>
                  <div>
                    <span className="font-bold text-daikin-dark">{summary.fate_compounds.toLocaleString()}</span> {t('tier1.fateCompounds')}
                  </div>
                  {tier2Coverage && (
                    <div>
                      <span className="font-bold text-daikin-dark">
                        {tier2Coverage.resolved_precursors}/{tier2Coverage.resolvable_precursors}
                      </span> {t('tier1.resolvedPrecursors')}
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
};

export default StructuralSimilarity;
