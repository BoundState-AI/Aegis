import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import { Loader2, AlertTriangle, DollarSign, TrendingUp, Scale, Eye, ShieldAlert, Quote, ArrowRight } from "lucide-react";
import ChemoursHeader from "@/components/layout/ChemoursHeader";
import helpContent from "@/config/helpContent";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Cell, ComposedChart, Line,
  Area,
} from "recharts";
import { API_BASE } from "@/config/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SentimentBreakdown {
  celebration: number;
  utility: number;
  detection: number;
  questioning: number;
  alarm: number;
  reckoning: number;
}

interface SentimentCategory {
  id: string;
  label: string;
  score: number;
  color: string;
  description: string;
}

interface TimelineEntry {
  year: number;
  publications: number;
  cumulative: number;
  phase: string;
  velocity: number;
  acceleration: number;
  alert_level: string;
  sentiment?: SentimentBreakdown;
  cumulative_sentiment?: number;
}

interface KeyEvent {
  year: number;
  type: string;
  label: string;
  description: string;
}

interface PhaseInfo {
  id: string;
  label: string;
  years: number[];
  color: string;
  description: string;
}

interface IndustryClaim {
  year: number;
  source: string;
  claim: string;
  reality: string;
  reality_year: number;
}

interface BacktestData {
  compound: string;
  total_publications: number;
  first_publication_year: number;
  first_lawsuit_year: number;
  lead_time_years: number;
  phases: PhaseInfo[];
  timeline: TimelineEntry[];
  key_events: KeyEvent[];
  industry_claims: IndustryClaim[];
  sentiment_categories?: SentimentCategory[];
  sentinel_reconstruction: {
    narrative: string;
    counterfactual: string;
    key_insight: string;
  };
  settlement_total_usd: number;
  affected_population: number;
  source_citations: string[];
}

interface LitigationForecast {
  compound: string;
  probability_12_months: number;
  probability_24_months: number;
  probability_36_months: number;
  risk_level: string;
  confidence_low: number;
  confidence_high: number;
  key_drivers: string[];
  estimated_exposure_usd: number;
  similar_cases: Array<{
    case: string;
    settlement: number;
    year: number;
    relevance: number;
  }>;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const COMPOUNDS = ["PFOA", "PFOS", "GenX", "TFA", "PFNA", "PFHxA", "PTFE", "FEP", "PVDF"];
const PATHWAYS = ["water", "air", "soil", "consumer_products"];

const PHASE_COLORS: Record<string, string> = {
  celebrated: "#22c55e",
  detected: "#eab308",
  alarmed: "#f97316",
  exploding: "#ef4444",
  reckoning: "#991b1b",
};

const ALERT_BADGES: Record<string, { color: string; label: string }> = {
  DARK: { color: "bg-gray-400", label: "No Data" },
  NOVEL: { color: "bg-yellow-500", label: "Novel Compound" },
  WATCH: { color: "bg-blue-500", label: "Watching" },
  ELEVATED: { color: "bg-orange-500", label: "Elevated" },
  HIGH: { color: "bg-red-500", label: "High" },
  CRITICAL: { color: "bg-red-700", label: "Critical" },
};

const EVENT_COLORS: Record<string, string> = {
  industry: "#22c55e",
  regulatory: "#3b82f6",
  detection: "#eab308",
  publication: "#a855f7",
  litigation: "#ef4444",
  settlement: "#991b1b",
};

const ALERT_BAR_COLORS: Record<string, string> = {
  DARK: "#d1d5db",
  NOVEL: "#eab308",
  WATCH: "#3b82f6",
  ELEVATED: "#f97316",
  HIGH: "#ef4444",
  CRITICAL: "#991b1b",
};

// Sentiment stacked area colors (positive → negative)
const SENTIMENT_COLORS: Record<string, string> = {
  celebration: "#22c55e",
  utility: "#86efac",
  detection: "#eab308",
  questioning: "#f97316",
  alarm: "#ef4444",
  reckoning: "#991b1b",
};

const SENTIMENT_LABELS: Record<string, string> = {
  celebration: "Celebration",
  utility: "Methods & Utility",
  detection: "Detection",
  questioning: "Questioning",
  alarm: "Alarm",
  reckoning: "Reckoning",
};

// ---------------------------------------------------------------------------
// Custom chart tooltip
// ---------------------------------------------------------------------------

const BacktestTooltip = ({ active, payload, label, events }: any) => {
  if (!active || !payload?.length) return null;
  const entry = payload[0]?.payload as TimelineEntry | undefined;
  if (!entry) return null;

  const yearEvents = (events as KeyEvent[])?.filter((e: KeyEvent) => e.year === label) || [];
  const alertInfo = ALERT_BADGES[entry.alert_level] || ALERT_BADGES.DARK;

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3 max-w-xs">
      <div className="flex items-center justify-between mb-1">
        <span className="font-bold text-chemours-dark">{label}</span>
        <Badge className={`${alertInfo.color} text-xs`}>{alertInfo.label}</Badge>
      </div>
      <div className="text-sm text-gray-600 space-y-0.5">
        <div><span className="font-medium">{entry.publications}</span> publications</div>
        <div>Velocity: <span className="font-medium">{entry.velocity}</span> papers/yr</div>
        {entry.acceleration !== 0 && (
          <div>Acceleration: <span className={`font-medium ${entry.acceleration > 0 ? "text-red-600" : "text-green-600"}`}>
            {entry.acceleration > 0 ? "+" : ""}{entry.acceleration}
          </span></div>
        )}
      </div>
      {yearEvents.length > 0 && (
        <div className="mt-2 pt-2 border-t border-gray-100">
          {yearEvents.map((e: KeyEvent, i: number) => (
            <div key={i} className="text-xs text-gray-500 mt-1">
              <span className="font-medium" style={{ color: EVENT_COLORS[e.type] || "#666" }}>
                {e.label}
              </span>
              <p className="text-gray-400 mt-0.5">{e.description}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const SentimentTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  const entry = payload[0]?.payload as TimelineEntry | undefined;
  if (!entry?.sentiment) return null;

  const categories = ["celebration", "utility", "detection", "questioning", "alarm", "reckoning"] as const;
  const total = categories.reduce((s, c) => s + (entry.sentiment?.[c] || 0), 0);

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3 max-w-xs">
      <div className="flex items-center justify-between mb-2">
        <span className="font-bold text-chemours-dark">{label}</span>
        <span className="text-xs text-gray-500">{total} papers</span>
      </div>
      <div className="space-y-1">
        {categories.map(c => {
          const count = entry.sentiment?.[c] || 0;
          if (count === 0) return null;
          return (
            <div key={c} className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: SENTIMENT_COLORS[c] }} />
                <span className="text-gray-600">{SENTIMENT_LABELS[c]}</span>
              </div>
              <span className="font-medium text-gray-800">{count}</span>
            </div>
          );
        })}
      </div>
      {entry.cumulative_sentiment != null && (
        <div className="mt-2 pt-2 border-t border-gray-100 flex items-center justify-between text-xs">
          <span className="text-gray-500">Cumulative sentiment</span>
          <span className={`font-bold ${entry.cumulative_sentiment < 0 ? "text-red-600" : "text-green-600"}`}>
            {entry.cumulative_sentiment > 0 ? "+" : ""}{entry.cumulative_sentiment.toFixed(1)}
          </span>
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const LitigationRisk = () => {
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [forecast, setForecast] = useState<LitigationForecast | null>(null);
  const [backtest, setBacktest] = useState<BacktestData | null>(null);

  const [chartView, setChartView] = useState<"publications" | "signal" | "sentiment">("publications");
  const [formData, setFormData] = useState({
    compound: "PFOA",
    volume: 100000,
    pathways: ["water"] as string[],
  });

  // Load GenX backtest on mount
  useEffect(() => {
    loadBacktest();
  }, []);

  const loadBacktest = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/litigation/backtest/genx`);
      if (res.ok) {
        setBacktest(await res.json());
      }
    } catch (e) {
      console.error("Failed to load backtest:", e);
    }
  };

  const togglePathway = (pathway: string) => {
    setFormData(prev => ({
      ...prev,
      pathways: prev.pathways.includes(pathway)
        ? prev.pathways.filter(p => p !== pathway)
        : [...prev.pathways, pathway]
    }));
  };

  const handleForecast = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/litigation/forecast`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          compound: formData.compound,
          production_volume_lbs: formData.volume,
          exposure_pathways: formData.pathways,
        }),
      });

      if (!res.ok) throw new Error("Forecast failed");

      const data: LitigationForecast = await res.json();
      setForecast(data);

      toast({
        title: "Forecast Complete",
        description: `${data.compound}: ${data.risk_level} risk (${(data.probability_24_months * 100).toFixed(1)}% in 24mo)`,
      });
    } catch (error) {
      toast({
        title: "Forecast Failed",
        description: "Could not connect to AEGIS API. Make sure the backend is running on port 8002.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const getRiskColor = (level: string) => {
    switch (level) {
      case "CRITICAL": return "bg-red-600";
      case "HIGH": return "bg-red-500";
      case "MEDIUM": return "bg-yellow-500";
      case "LOW": return "bg-green-500";
      default: return "bg-gray-500";
    }
  };

  const formatCurrency = (value: number) => {
    if (value >= 1_000_000_000) return `$${(value / 1_000_000_000).toFixed(1)}B`;
    if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
    return `$${value.toLocaleString()}`;
  };

  // Key event years for reference lines on chart
  const litigationEvents = backtest?.key_events.filter(e => e.type === "litigation") || [];
  const settlementEvents = backtest?.key_events.filter(e => e.type === "settlement") || [];
  const industryEvents = backtest?.key_events.filter(e => e.type === "industry") || [];

  return (
    <div className="min-h-screen bg-gray-50">
      <ChemoursHeader title="AEGIS SENTINEL" subtitle="Litigation Early Warning System" helpContent={helpContent.litigation}>
        {backtest && (
          <>
            <div className="text-gray-600">
              <span className="text-chemours-red font-bold">{backtest.lead_time_years}</span>-year lead time
            </div>
            <div className="text-gray-600">
              <span className="text-chemours-red font-bold">{formatCurrency(backtest.settlement_total_usd)}</span> in settlements
            </div>
          </>
        )}
      </ChemoursHeader>

      <main className="container mx-auto px-4 py-8 space-y-8">
        <Tabs defaultValue="casestudy">
          <TabsList className="bg-white border border-gray-200 shadow-sm">
            <TabsTrigger value="casestudy" className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-chemours-red data-[state=active]:to-chemours-orange data-[state=active]:text-white">
              <Eye className="mr-2 h-4 w-4" />
              GenX Case Study
            </TabsTrigger>
            <TabsTrigger value="forecast" className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-chemours-red data-[state=active]:to-chemours-orange data-[state=active]:text-white">
              <ShieldAlert className="mr-2 h-4 w-4" />
              Risk Forecast
            </TabsTrigger>
          </TabsList>

          {/* ============================================================ */}
          {/* TAB 1: GenX Case Study                                       */}
          {/* ============================================================ */}
          <TabsContent value="casestudy" className="space-y-6 mt-6">
            {backtest ? (
              <>
                {/* Headline stats */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <Card className="bg-white border-gray-200 shadow-sm">
                    <CardContent className="p-4 text-center">
                      <p className="text-xs text-gray-500 uppercase tracking-wide">Publications</p>
                      <p className="text-3xl font-bold text-chemours-dark">{backtest.total_publications}</p>
                      <p className="text-xs text-gray-400">PubMed papers</p>
                    </CardContent>
                  </Card>
                  <Card className="bg-white border-gray-200 shadow-sm">
                    <CardContent className="p-4 text-center">
                      <p className="text-xs text-gray-500 uppercase tracking-wide">First Signal</p>
                      <p className="text-3xl font-bold text-yellow-600">{backtest.first_publication_year}</p>
                      <p className="text-xs text-gray-400">velocity from zero</p>
                    </CardContent>
                  </Card>
                  <Card className="bg-white border-gray-200 shadow-sm">
                    <CardContent className="p-4 text-center">
                      <p className="text-xs text-gray-500 uppercase tracking-wide">First Lawsuit</p>
                      <p className="text-3xl font-bold text-red-600">{backtest.first_lawsuit_year}</p>
                      <p className="text-xs text-gray-400">{backtest.lead_time_years}-yr after signal</p>
                    </CardContent>
                  </Card>
                  <Card className="bg-white border-gray-200 shadow-sm">
                    <CardContent className="p-4 text-center">
                      <p className="text-xs text-gray-500 uppercase tracking-wide">Total Settlements</p>
                      <p className="text-3xl font-bold text-chemours-red">{formatCurrency(backtest.settlement_total_usd)}</p>
                      <p className="text-xs text-gray-400">{backtest.affected_population.toLocaleString()} affected</p>
                    </CardContent>
                  </Card>
                </div>

                {/* Publication Timeline Chart */}
                <Card className="bg-white border-gray-200 shadow-sm">
                  <CardHeader>
                    <div className="flex items-center justify-between flex-wrap gap-3">
                      <div>
                        <CardTitle className="text-chemours-dark">
                          GenX (HFPO-DA) {chartView === "signal" ? "SENTINEL Signal" : chartView === "sentiment" ? "Sentiment Lifecycle" : "Publication Timeline"}
                        </CardTitle>
                        <CardDescription>
                          {chartView === "signal"
                            ? "3-year trailing velocity (papers/yr) colored by alert level. Orange line = acceleration (rate of change)."
                            : chartView === "sentiment"
                            ? "Research sentiment classified by AI from PubMed titles + abstracts. Stacked areas show the mood of the literature over time."
                            : "Peer-reviewed publications per year from PubMed. Bars colored by phase. Vertical lines mark key events."}
                        </CardDescription>
                      </div>
                      <div className="flex gap-1">
                        <Button
                          variant={chartView === "publications" ? "default" : "outline"}
                          size="sm"
                          className={chartView === "publications" ? "bg-chemours-dark text-white hover:bg-chemours-dark/90" : ""}
                          onClick={() => setChartView("publications")}
                        >
                          Publications
                        </Button>
                        <Button
                          variant={chartView === "signal" ? "default" : "outline"}
                          size="sm"
                          className={chartView === "signal" ? "bg-chemours-dark text-white hover:bg-chemours-dark/90" : ""}
                          onClick={() => setChartView("signal")}
                        >
                          SENTINEL Signal
                        </Button>
                        <Button
                          variant={chartView === "sentiment" ? "default" : "outline"}
                          size="sm"
                          className={chartView === "sentiment" ? "bg-chemours-dark text-white hover:bg-chemours-dark/90" : ""}
                          onClick={() => setChartView("sentiment")}
                        >
                          Sentiment
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[400px]">
                      <ResponsiveContainer width="100%" height="100%">
                        {chartView === "signal" ? (
                          <ComposedChart data={backtest.timeline} margin={{ top: 20, right: 40, bottom: 20, left: 20 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                            <XAxis
                              dataKey="year"
                              tick={{ fontSize: 11, fill: "#6b7280" }}
                              tickLine={false}
                            />
                            <YAxis
                              yAxisId="velocity"
                              tick={{ fontSize: 11, fill: "#6b7280" }}
                              tickLine={false}
                              label={{ value: "Velocity (papers/yr)", angle: -90, position: "insideLeft", style: { fontSize: 11, fill: "#9ca3af" } }}
                            />
                            <YAxis
                              yAxisId="acceleration"
                              orientation="right"
                              tick={{ fontSize: 11, fill: "#f97316" }}
                              tickLine={false}
                              label={{ value: "Acceleration", angle: 90, position: "insideRight", style: { fontSize: 11, fill: "#f97316" } }}
                            />
                            <Tooltip content={<BacktestTooltip events={backtest.key_events} />} />
                            {litigationEvents.map((e) => (
                              <ReferenceLine
                                key={`lit-${e.year}`}
                                x={e.year}
                                yAxisId="velocity"
                                stroke="#ef4444"
                                strokeWidth={2}
                                strokeDasharray="4 4"
                                label={{ value: e.label, position: "top", fill: "#ef4444", fontSize: 9, fontWeight: 600 }}
                              />
                            ))}
                            <ReferenceLine
                              x={backtest.first_publication_year}
                              yAxisId="velocity"
                              stroke="#eab308"
                              strokeWidth={2}
                              label={{ value: "SENTINEL SIGNAL", position: "insideTopRight", fill: "#eab308", fontSize: 10, fontWeight: 700 }}
                            />
                            <Bar yAxisId="velocity" dataKey="velocity" radius={[3, 3, 0, 0]}>
                              {backtest.timeline.map((entry, idx) => (
                                <Cell key={idx} fill={ALERT_BAR_COLORS[entry.alert_level] || "#d1d5db"} />
                              ))}
                            </Bar>
                            <Line
                              yAxisId="acceleration"
                              dataKey="acceleration"
                              stroke="#f97316"
                              strokeWidth={2}
                              dot={false}
                              type="monotone"
                            />
                          </ComposedChart>
                        ) : chartView === "sentiment" ? (
                          <ComposedChart data={backtest.timeline} margin={{ top: 20, right: 40, bottom: 20, left: 20 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                            <XAxis
                              dataKey="year"
                              tick={{ fontSize: 11, fill: "#6b7280" }}
                              tickLine={false}
                            />
                            <YAxis
                              yAxisId="papers"
                              tick={{ fontSize: 11, fill: "#6b7280" }}
                              tickLine={false}
                              label={{ value: "Papers", angle: -90, position: "insideLeft", style: { fontSize: 11, fill: "#9ca3af" } }}
                            />
                            <YAxis
                              yAxisId="cumulative"
                              orientation="right"
                              tick={{ fontSize: 11, fill: "#ef4444" }}
                              tickLine={false}
                              label={{ value: "Cumulative Sentiment", angle: 90, position: "insideRight", style: { fontSize: 11, fill: "#ef4444" } }}
                            />
                            <Tooltip content={<SentimentTooltip />} />
                            {industryEvents.map((e) => (
                              <ReferenceLine
                                key={`ind-${e.year}`}
                                x={e.year}
                                yAxisId="papers"
                                stroke="#22c55e"
                                strokeWidth={2}
                                strokeDasharray="4 4"
                                label={{ value: e.label, position: "top", fill: "#22c55e", fontSize: 9, fontWeight: 600 }}
                              />
                            ))}
                            {litigationEvents.map((e) => (
                              <ReferenceLine
                                key={`lit-${e.year}`}
                                x={e.year}
                                yAxisId="papers"
                                stroke="#ef4444"
                                strokeWidth={1.5}
                                strokeDasharray="4 4"
                                label={{ value: e.label, position: "insideTopLeft", fill: "#ef4444", fontSize: 9 }}
                              />
                            ))}
                            <Area yAxisId="papers" type="monotone" dataKey="sentiment.reckoning" stackId="sentiment" fill={SENTIMENT_COLORS.reckoning} stroke={SENTIMENT_COLORS.reckoning} fillOpacity={0.85} />
                            <Area yAxisId="papers" type="monotone" dataKey="sentiment.alarm" stackId="sentiment" fill={SENTIMENT_COLORS.alarm} stroke={SENTIMENT_COLORS.alarm} fillOpacity={0.85} />
                            <Area yAxisId="papers" type="monotone" dataKey="sentiment.questioning" stackId="sentiment" fill={SENTIMENT_COLORS.questioning} stroke={SENTIMENT_COLORS.questioning} fillOpacity={0.85} />
                            <Area yAxisId="papers" type="monotone" dataKey="sentiment.detection" stackId="sentiment" fill={SENTIMENT_COLORS.detection} stroke={SENTIMENT_COLORS.detection} fillOpacity={0.85} />
                            <Area yAxisId="papers" type="monotone" dataKey="sentiment.utility" stackId="sentiment" fill={SENTIMENT_COLORS.utility} stroke={SENTIMENT_COLORS.utility} fillOpacity={0.85} />
                            <Area yAxisId="papers" type="monotone" dataKey="sentiment.celebration" stackId="sentiment" fill={SENTIMENT_COLORS.celebration} stroke={SENTIMENT_COLORS.celebration} fillOpacity={0.85} />
                            <Line
                              yAxisId="cumulative"
                              type="monotone"
                              dataKey="cumulative_sentiment"
                              stroke="#dc2626"
                              strokeWidth={2.5}
                              dot={false}
                              strokeDasharray="6 3"
                            />
                          </ComposedChart>
                        ) : (
                          <BarChart data={backtest.timeline} margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                            <XAxis
                              dataKey="year"
                              tick={{ fontSize: 11, fill: "#6b7280" }}
                              tickLine={false}
                            />
                            <YAxis
                              tick={{ fontSize: 11, fill: "#6b7280" }}
                              tickLine={false}
                              label={{ value: "Publications", angle: -90, position: "insideLeft", style: { fontSize: 11, fill: "#9ca3af" } }}
                            />
                            <Tooltip content={<BacktestTooltip events={backtest.key_events} />} />
                            {litigationEvents.map((e) => (
                              <ReferenceLine
                                key={`lit-${e.year}`}
                                x={e.year}
                                stroke="#ef4444"
                                strokeWidth={2}
                                strokeDasharray="4 4"
                                label={{ value: e.label, position: "top", fill: "#ef4444", fontSize: 9, fontWeight: 600 }}
                              />
                            ))}
                            {settlementEvents.map((e) => (
                              <ReferenceLine
                                key={`set-${e.year}`}
                                x={e.year}
                                stroke="#991b1b"
                                strokeWidth={1.5}
                                strokeDasharray="4 4"
                                label={{ value: e.label, position: "top", fill: "#991b1b", fontSize: 9 }}
                              />
                            ))}
                            <ReferenceLine
                              x={backtest.first_publication_year}
                              stroke="#eab308"
                              strokeWidth={2}
                              label={{ value: "SENTINEL SIGNAL", position: "insideTopRight", fill: "#eab308", fontSize: 10, fontWeight: 700 }}
                            />
                            <Bar dataKey="publications" radius={[3, 3, 0, 0]}>
                              {backtest.timeline.map((entry, idx) => (
                                <Cell key={idx} fill={PHASE_COLORS[entry.phase] || "#9ca3af"} />
                              ))}
                            </Bar>
                          </BarChart>
                        )}
                      </ResponsiveContainer>
                    </div>

                    {/* Legend — changes based on view */}
                    <div className="flex flex-wrap gap-4 mt-4 justify-center">
                      {chartView === "signal" ? (
                        <>
                          {Object.entries(ALERT_BADGES).map(([key, info]) => (
                            <div key={key} className="flex items-center gap-1.5">
                              <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: ALERT_BAR_COLORS[key] }} />
                              <span className="text-xs text-gray-600">{info.label}</span>
                            </div>
                          ))}
                          <div className="flex items-center gap-1.5">
                            <div className="w-6 h-0.5 bg-orange-500 rounded" />
                            <span className="text-xs text-gray-600">Acceleration</span>
                          </div>
                        </>
                      ) : chartView === "sentiment" ? (
                        <>
                          {(["celebration", "utility", "detection", "questioning", "alarm", "reckoning"] as const).map(c => (
                            <div key={c} className="flex items-center gap-1.5">
                              <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: SENTIMENT_COLORS[c] }} />
                              <span className="text-xs text-gray-600">{SENTIMENT_LABELS[c]}</span>
                            </div>
                          ))}
                          <div className="flex items-center gap-1.5">
                            <div className="w-6 h-0.5 rounded" style={{ borderTop: "2px dashed #dc2626" }} />
                            <span className="text-xs text-gray-600">Cumulative Sentiment</span>
                          </div>
                        </>
                      ) : (
                        backtest.phases.map((p) => (
                          <div key={p.id} className="flex items-center gap-1.5">
                            <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: p.color }} />
                            <span className="text-xs text-gray-600">{p.label} ({p.years[0]}-{p.years[1]})</span>
                          </div>
                        ))
                      )}
                    </div>

                    {/* Sentiment annotation */}
                    {chartView === "sentiment" && (
                      <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                        <p className="text-xs text-amber-900 leading-relaxed">
                          <span className="font-semibold">Key finding:</span> No independent celebration papers exist for GenX.
                          The first peer-reviewed publications were detection and alarm studies.
                          The only positive narrative was manufacturer-controlled (DuPont brochure, 2008-2010).
                          Cumulative research sentiment went negative immediately and never recovered.
                        </p>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Industry Claims vs. Reality */}
                {backtest.industry_claims?.length > 0 && (
                  <Card className="bg-white border-gray-200 shadow-sm">
                    <CardHeader>
                      <CardTitle className="text-chemours-dark flex items-center gap-2">
                        <Quote className="h-5 w-5 text-green-600" />
                        The Claims vs. The Reality
                      </CardTitle>
                      <CardDescription>
                        DuPont's own marketing language (2008-2010) juxtaposed with documented outcomes
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        {backtest.industry_claims.map((claim, i) => (
                          <div key={i} className="grid grid-cols-1 md:grid-cols-[1fr,auto,1fr] gap-3 items-start p-4 rounded-lg bg-gray-50 border border-gray-100">
                            {/* The Claim */}
                            <div>
                              <div className="flex items-center gap-2 mb-2">
                                <Badge className="bg-green-100 text-green-800 text-xs font-medium">{claim.year}</Badge>
                                <span className="text-xs text-gray-400 uppercase tracking-wide">Claim</span>
                              </div>
                              <p className="text-sm text-gray-800 italic">"{claim.claim}"</p>
                              <p className="text-xs text-gray-400 mt-1">{claim.source}</p>
                            </div>
                            {/* Arrow */}
                            <div className="hidden md:flex items-center justify-center pt-4">
                              <ArrowRight className="h-5 w-5 text-red-400" />
                            </div>
                            {/* The Reality */}
                            <div>
                              <div className="flex items-center gap-2 mb-2">
                                <Badge className="bg-red-100 text-red-800 text-xs font-medium">{claim.reality_year}</Badge>
                                <span className="text-xs text-gray-400 uppercase tracking-wide">Reality</span>
                              </div>
                              <p className="text-sm text-red-900">{claim.reality}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* SENTINEL Reconstruction narrative */}
                <Card className="bg-gradient-to-r from-gray-900 to-gray-800 border-0 shadow-lg">
                  <CardHeader>
                    <CardTitle className="text-white flex items-center gap-2">
                      <ShieldAlert className="h-5 w-5 text-yellow-400" />
                      SENTINEL Reconstruction
                    </CardTitle>
                    <CardDescription className="text-gray-400">
                      What SENTINEL would have shown before the lawsuits
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <p className="text-gray-300 text-sm leading-relaxed">
                      {backtest.sentinel_reconstruction.narrative}
                    </p>
                    <div className="p-3 bg-white/5 rounded-lg border border-white/10">
                      <p className="text-yellow-400 text-xs font-semibold uppercase tracking-wider mb-1">Key Insight</p>
                      <p className="text-white text-sm">
                        {backtest.sentinel_reconstruction.key_insight}
                      </p>
                    </div>
                    <div className="p-3 bg-white/5 rounded-lg border border-white/10">
                      <p className="text-blue-400 text-xs font-semibold uppercase tracking-wider mb-1">Counterfactual</p>
                      <p className="text-gray-300 text-sm">
                        {backtest.sentinel_reconstruction.counterfactual}
                      </p>
                    </div>
                  </CardContent>
                </Card>

                {/* Event Timeline */}
                <Card className="bg-white border-gray-200 shadow-sm">
                  <CardHeader>
                    <CardTitle className="text-chemours-dark">Event Timeline</CardTitle>
                    <CardDescription>Key events from EPA filings, court records, and public sources</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {backtest.key_events.map((event, i) => (
                        <div key={i} className="flex gap-3 items-start">
                          <div className="flex-shrink-0 w-12 text-right">
                            <span className="text-sm font-bold text-chemours-dark">{event.year}</span>
                          </div>
                          <div
                            className="flex-shrink-0 w-2 h-2 mt-1.5 rounded-full"
                            style={{ backgroundColor: EVENT_COLORS[event.type] || "#9ca3af" }}
                          />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-800">{event.label}</p>
                            <p className="text-xs text-gray-500 mt-0.5">{event.description}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                    <div className="mt-4 pt-3 border-t border-gray-100">
                      <p className="text-xs text-gray-400">
                        Sources: {backtest.source_citations.slice(0, 3).join("; ")}; and {backtest.source_citations.length - 3} more.
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </>
            ) : (
              <Card className="bg-white border-gray-200 shadow-sm">
                <CardContent className="py-16 text-center">
                  <Loader2 className="h-8 w-8 mx-auto mb-4 animate-spin text-chemours-red" />
                  <p className="text-gray-500">Loading GenX case study...</p>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* ============================================================ */}
          {/* TAB 2: Risk Forecast (existing functionality)                 */}
          {/* ============================================================ */}
          <TabsContent value="forecast" className="mt-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Input Panel */}
              <Card className="bg-white border-gray-200 shadow-sm">
                <CardHeader>
                  <CardTitle className="text-chemours-dark">Forecast Parameters</CardTitle>
                  <CardDescription>Configure litigation risk assessment</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label className="text-gray-700">Compound</Label>
                    <Select value={formData.compound} onValueChange={(v) => setFormData({ ...formData, compound: v })}>
                      <SelectTrigger className="bg-white border-gray-300">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {COMPOUNDS.map((c) => (
                          <SelectItem key={c} value={c}>{c}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label className="text-gray-700">Production Volume (lbs/year)</Label>
                    <Input
                      type="number"
                      value={formData.volume}
                      onChange={(e) => setFormData({ ...formData, volume: parseInt(e.target.value) || 0 })}
                      className="bg-white border-gray-300"
                    />
                  </div>

                  <div>
                    <Label className="text-gray-700">Exposure Pathways</Label>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {PATHWAYS.map((p) => (
                        <Badge
                          key={p}
                          variant={formData.pathways.includes(p) ? "default" : "outline"}
                          className={`cursor-pointer ${formData.pathways.includes(p) ? "bg-chemours-red text-white" : "border-gray-400 text-gray-600"}`}
                          onClick={() => togglePathway(p)}
                        >
                          {p}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  <Button
                    onClick={handleForecast}
                    disabled={isLoading}
                    className="w-full bg-gradient-to-r from-chemours-red to-chemours-orange hover:opacity-90 text-white"
                  >
                    {isLoading ? (
                      <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Calculating...</>
                    ) : (
                      <><TrendingUp className="mr-2 h-4 w-4" /> Calculate Risk</>
                    )}
                  </Button>
                </CardContent>
              </Card>

              {/* Results Panel */}
              <div className="lg:col-span-2 space-y-6">
                {forecast ? (
                  <>
                    {/* Risk Summary */}
                    <Card className="bg-white border-gray-200 shadow-sm">
                      <CardHeader>
                        <div className="flex items-center justify-between">
                          <CardTitle className="text-chemours-dark">{forecast.compound} Litigation Forecast</CardTitle>
                          <Badge className={getRiskColor(forecast.risk_level)}>{forecast.risk_level} RISK</Badge>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-3 gap-4 mb-6">
                          <div className="text-center">
                            <p className="text-sm text-gray-500">12 Months</p>
                            <p className="text-2xl font-bold text-chemours-dark">{(forecast.probability_12_months * 100).toFixed(1)}%</p>
                            <Progress value={forecast.probability_12_months * 100} className="mt-2" />
                          </div>
                          <div className="text-center">
                            <p className="text-sm text-gray-500">24 Months</p>
                            <p className="text-2xl font-bold text-chemours-red">{(forecast.probability_24_months * 100).toFixed(1)}%</p>
                            <Progress value={forecast.probability_24_months * 100} className="mt-2" />
                          </div>
                          <div className="text-center">
                            <p className="text-sm text-gray-500">36 Months</p>
                            <p className="text-2xl font-bold text-chemours-dark">{(forecast.probability_36_months * 100).toFixed(1)}%</p>
                            <Progress value={forecast.probability_36_months * 100} className="mt-2" />
                          </div>
                        </div>

                        <div className="flex items-center justify-between p-4 bg-gray-100 rounded-lg">
                          <div className="flex items-center gap-2">
                            <DollarSign className="h-6 w-6 text-green-600" />
                            <span className="text-gray-600">Estimated Exposure</span>
                          </div>
                          <span className="text-2xl font-bold text-green-600">{formatCurrency(forecast.estimated_exposure_usd)}</span>
                        </div>

                        <div className="mt-4 text-sm text-gray-500">
                          Confidence Interval: {(forecast.confidence_low * 100).toFixed(1)}% - {(forecast.confidence_high * 100).toFixed(1)}%
                        </div>
                      </CardContent>
                    </Card>

                    {/* Key Drivers */}
                    <Card className="bg-white border-gray-200 shadow-sm">
                      <CardHeader>
                        <CardTitle className="text-chemours-dark flex items-center gap-2">
                          <AlertTriangle className="h-5 w-5 text-chemours-orange" />
                          Key Risk Drivers
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <ul className="space-y-2">
                          {forecast.key_drivers.map((driver, i) => (
                            <li key={i} className="flex items-start gap-2 text-gray-600">
                              <span className="text-chemours-orange">•</span>
                              {driver}
                            </li>
                          ))}
                        </ul>
                      </CardContent>
                    </Card>

                    {/* Similar Cases */}
                    <Card className="bg-white border-gray-200 shadow-sm">
                      <CardHeader>
                        <CardTitle className="text-chemours-dark">Similar Cases</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-3">
                          {forecast.similar_cases.map((c, i) => (
                            <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                              <div>
                                <p className="font-medium text-chemours-dark">{c.case}</p>
                                <p className="text-sm text-gray-500">Year: {c.year} | Relevance: {(c.relevance * 100).toFixed(0)}%</p>
                              </div>
                              <span className="text-lg font-bold text-green-600">{formatCurrency(c.settlement)}</span>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  </>
                ) : (
                  <Card className="bg-white border-gray-200 shadow-sm">
                    <CardContent className="py-16 text-center">
                      <div className="h-16 w-16 mx-auto mb-4 rounded-full bg-gradient-to-r from-chemours-red to-chemours-orange flex items-center justify-center">
                        <Scale className="h-8 w-8 text-white" />
                      </div>
                      <h3 className="text-xl font-semibold text-chemours-dark mb-2">Compound Risk Forecast</h3>
                      <p className="text-gray-500 max-w-md mx-auto">
                        Calculate litigation probability based on publication velocity, historical settlements, and exposure pathways.
                      </p>
                    </CardContent>
                  </Card>
                )}
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
};

export default LitigationRisk;
