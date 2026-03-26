import { useState, useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";
import type { TFunction } from "i18next";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import { Loader2, AlertTriangle, DollarSign, TrendingUp, Scale, Eye, ShieldAlert, Quote, ArrowRight, Info, ExternalLink, X } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import DaikinHeader from "@/components/layout/DaikinHeader";
import { PageChatProvider } from "@/components/chat/PageChatProvider";
import { useHelpContent } from "@/config/helpContent";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Cell, ComposedChart, Line,
  Area,
} from "recharts";
import { apiGet, apiPost } from "@/lib/apiClient";
import { createLitigationAnswerSurfaceHint } from "@/lib/chat/surfaces";
import {
  litigationBacktestSchema,
  litigationBacktestsSchema,
  litigationForecastSchema,
  litigationPapersSchema,
} from "@/lib/apiSchemas";

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
  jerk: number;
  alert_level: string;
  sentiment?: SentimentBreakdown;
  cumulative_sentiment?: number;
  normalized_sentiment?: number;
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

interface SentimentPaper {
  pmid: string;
  title: string;
  journal: string;
  category: string;
  confidence: number;
  reasoning: string;
}

interface PapersResponse {
  compound_id: string;
  year: number;
  total: number;
  papers: SentimentPaper[];
}

interface BacktestData {
  compound: string;
  compound_id: string;
  total_publications: number;
  first_publication_year: number;
  first_lawsuit_year: number;
  first_elevated_year?: number;  // PFOA-specific
  first_critical_year?: number;  // PFOA-specific
  major_settlement_year?: number; // PFOA-specific
  lead_time_years: number;
  phases: PhaseInfo[];
  timeline: TimelineEntry[];
  key_events: KeyEvent[];
  industry_claims?: IndustryClaim[];
  sentiment_categories?: SentimentCategory[];
  sentinel_reconstruction: {
    narrative: string;
    counterfactual: string;
    key_insight: string;
  };
  settlement_total_usd: number;
  affected_population: number;
  source_citations: string[];
  validation_metrics?: {
    first_elevated_to_settlement_years?: number;
    first_critical_to_settlement_years?: number;
    velocity_at_first_lawsuit?: number;
    velocity_at_first_critical?: number;
  };
}

interface BacktestSummary {
  compound_id: string;
  compound: string;
  total_publications: number;
  first_lawsuit_year: number;
  lead_time_years: number;
  settlement_total_usd: number;
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

const ALERT_BADGES: Record<string, { color: string; labelKey: string }> = {
  DARK: { color: "bg-gray-400", labelKey: "litigation.alertLabels.dark" },
  NOVEL: { color: "bg-yellow-500", labelKey: "litigation.alertLabels.novel" },
  WATCH: { color: "bg-blue-500", labelKey: "litigation.alertLabels.watch" },
  ELEVATED: { color: "bg-orange-500", labelKey: "litigation.alertLabels.elevated" },
  HIGH: { color: "bg-red-500", labelKey: "litigation.alertLabels.high" },
  CRITICAL: { color: "bg-red-700", labelKey: "litigation.alertLabels.critical" },
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

const getSentimentLabel = (t: TFunction, category: string) =>
  t(`litigation.sentimentLabels.${category}`, { defaultValue: category });

type BacktestLocalization = {
  phases: Record<string, string>;
  events: Record<string, { label: string; description: string }>;
};

const BACKTEST_JA_COPY: Record<string, BacktestLocalization> = {
  genx: {
    phases: {
      celebrated: "解決策",
      detected: "最初のシグナル",
      alarmed: "公的発覚",
      exploding: "研究の急増",
      reckoning: "清算の段階",
    },
    events: {
      "2006:industry": {
        label: "PFOA自主削減プログラム",
        description: "EPAが自主プログラムを開始。8社が2015年までにPFOAを廃止すると約束し、DuPontのCEOは『代替技術を開発中』と表明した。",
      },
      "2008:industry": {
        label: "GenXのPMNをEPAへ提出",
        description: "DuPontがTSCAの下でHFPO-DAとそのアンモニウム塩の製造前届出を提出し、『良好な毒性プロファイルと非常に速い生体排出』を主張した。",
      },
      "2009:regulatory": {
        label: "EPA同意命令",
        description: "EPAがTSCA同意命令を締結し、DuPontにGenX化合物の99%回収・破壊を要求。DuPontは顧客切替を開始した。",
      },
      "2010:industry": {
        label: "GenX特許と販促資料",
        description: "2010年にDuPontが特許と販促資料を公表し、『良好な毒性プロファイル』『非常に速い生体排出』『独自の環境暴露制御技術』を主張。Fayetteville WorksでPFOAをGenXへ置換すると説明した。",
      },
      "2012:detection": {
        label: "初検出（未公表）",
        description: "EPA研究者がFayetteville Works下流のCape Fear川でGenXを検出。結果は会議で共有されたが、まだ査読論文にはなっていなかった。",
      },
      "2013:detection": {
        label: "飲料水で検出",
        description: "浄水処理の前後でGenXが検出され、濃度は変わらず。標準的な処理では除去できず、DuPontはPFOAからGenXへの移行を完了した。",
      },
      "2015:publication": {
        label: "最初の査読論文",
        description: "StrynarらがCape Fear川でGenXと11種の新規PFECAを発見した論文を発表。ChemoursはDuPontから分社化され、GenXは中国とドイツの水系でも検出された。",
      },
      "2017:litigation": {
        label: "報道と訴訟",
        description: "Wilmington Star-Newsが30万人の飲料水中GenXを報道。CFPUAとNC DEQが提訴し、連邦大陪審の召喚状も発行された。",
      },
      "2019:regulatory": {
        label: "同意命令",
        description: "Chemours、NC DEQ、Cape Fear River Watchが浄化の同意命令に署名し、熱酸化装置が年末に設置された。",
      },
      "2020:regulatory": {
        label: "EPA監察総監報告",
        description: "EPA監察総監は、連絡不全により2009年同意命令違反のGenX排出が8年間続いたと指摘した。",
      },
      "2021:regulatory": {
        label: "EPA毒性評価",
        description: "EPAがHFPO-DAの最終ヒト健康毒性評価を公表し、NCDEQはChemoursと1300万ドルで和解した。",
      },
      "2022:settlement": {
        label: "22億ドルのChemours和解",
        description: "Chemoursが22億ドルの環境修復和解に同意した。",
      },
      "2023:settlement": {
        label: "103億ドルの3M和解 + 集団認定",
        description: "3Mが103億ドルのPFAS公共水道和解に合意し、連邦判事がノースカロライナ州のGenX住民10万人超の集団認定を許可した。",
      },
      "2024:regulatory": {
        label: "EPA飲料水規則",
        description: "EPAがHFPO-DA（GenX）に対する国家一次飲料水規則を最終化し、代替化学物質そのものが規制対象となった。",
      },
    },
  },
  pfoa: {
    phases: {
      industrial: "産業利用",
      discovery: "発見",
      investigation: "調査",
      litigation: "訴訟",
      regulation: "規制",
    },
    events: {
      "1999:regulatory": {
        label: "EPA調査開始",
        description: "EPAがDuPontによるPFOA汚染データの取り扱いについて調査を開始した。",
      },
      "2001:litigation": {
        label: "Tennant対DuPont",
        description: "Wilbur Tennantが、PFOA汚染に関連する牛の死亡についてDuPontを提訴した。",
      },
      "2002:regulatory": {
        label: "3MのPFOS撤退",
        description: "3MがPFOS生産の自主的終了を発表し、業界がリスクを認識していたことを示した。",
      },
      "2004:settlement": {
        label: "3.43億ドル集団訴訟",
        description: "DuPontが3.43億ドルで集団訴訟を和解し、C8 Science Panelを設立した。",
      },
      "2005:regulatory": {
        label: "EPA罰金1650万ドル",
        description: "EPAがPFOAの健康リスク報告義務違反でDuPontに1650万ドルの罰金を科した。",
      },
      "2006:science": {
        label: "C8 Science Panel",
        description: "独立したC8 Science Panelが、7万人の曝露住民を対象とする7年間の研究を開始した。",
      },
      "2009:regulatory": {
        label: "EPA健康勧告",
        description: "EPAが飲料水中PFOAに対し400 pptの暫定健康勧告を発表した。",
      },
      "2012:science": {
        label: "6つの疾病関連",
        description: "C8 Panelが、腎臓がん、精巣がん、甲状腺疾患、潰瘍性大腸炎、高コレステロール、妊娠高血圧との関連を確認した。",
      },
      "2013:litigation": {
        label: "MDL設立",
        description: "MDL 2433が設立され、数千件の人身傷害請求が統合された。",
      },
      "2017:settlement": {
        label: "6.707億ドル和解",
        description: "DuPont/Chemoursが約3500件の人身傷害請求について6.707億ドルで和解した。",
      },
      "2019:regulatory": {
        label: "ストックホルム条約",
        description: "PFOAが残留性有機汚染物質に関するストックホルム条約に追加された。",
      },
      "2022:regulatory": {
        label: "EPA健康勧告",
        description: "EPAがPFOAに対し0.004 pptの暫定健康勧告を発表した。",
      },
      "2024:regulatory": {
        label: "EPA MCL最終化",
        description: "EPAが飲料水中PFOAの最大汚染物質基準4 pptを最終化した。",
      },
    },
  },
};

const getLocalizedPhaseLabel = (language: string, compoundId: string, phase: PhaseInfo) => {
  if (!language.startsWith("ja")) return phase.label;
  return BACKTEST_JA_COPY[compoundId.toLowerCase()]?.phases?.[phase.id] ?? phase.label;
};

const getLocalizedEvent = (language: string, compoundId: string, event: KeyEvent): KeyEvent => {
  if (!language.startsWith("ja")) return event;
  const localized = BACKTEST_JA_COPY[compoundId.toLowerCase()]?.events?.[`${event.year}:${event.type}`];
  return localized ? { ...event, ...localized } : event;
};

// ---------------------------------------------------------------------------
// Custom chart tooltip
// ---------------------------------------------------------------------------

const BacktestTooltip = ({ active, payload, label, events, compoundId, language }: any) => {
  const { t } = useTranslation();
  if (!active || !payload?.length) return null;
  const entry = payload[0]?.payload as TimelineEntry | undefined;
  if (!entry) return null;

  const yearEvents = (events as KeyEvent[])?.filter((e: KeyEvent) => e.year === label) || [];
  const alertInfo = ALERT_BADGES[entry.alert_level] || ALERT_BADGES.DARK;

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3 max-w-xs">
      <div className="flex items-center justify-between mb-1">
        <span className="font-bold text-daikin-dark">{label}</span>
        <Badge className={`${alertInfo.color} text-xs`}>{t(alertInfo.labelKey)}</Badge>
      </div>
      <div className="text-sm text-gray-600 space-y-0.5">
        <div>{t("litigation.publicationsCount", { count: entry.publications })}</div>
        <div>{t("litigation.velocity")}: <span className="font-medium">{entry.velocity}</span> {t("litigation.papersPerYear")}</div>
        {entry.acceleration !== 0 && (
          <div>{t("litigation.acceleration")}: <span className={`font-medium ${entry.acceleration > 0 ? "text-red-600" : "text-green-600"}`}>
            {entry.acceleration > 0 ? "+" : ""}{entry.acceleration}
          </span></div>
        )}
        {entry.jerk !== 0 && (
          <div>{t("litigation.jerk")}: <span className={`font-medium ${entry.jerk > 0 ? "text-orange-600" : "text-blue-600"}`}>
            {entry.jerk > 0 ? "+" : ""}{entry.jerk}
          </span> <span className="text-gray-400 text-xs">({t("litigation.inflection")})</span></div>
        )}
      </div>
      {yearEvents.length > 0 && (
        <div className="mt-2 pt-2 border-t border-gray-100">
          {yearEvents.map((e: KeyEvent, i: number) => {
            const localizedEvent = getLocalizedEvent(language, compoundId, e);
            return (
              <div key={i} className="text-xs text-gray-500 mt-1">
                <span className="font-medium" style={{ color: EVENT_COLORS[e.type] || "#666" }}>
                  {localizedEvent.label}
                </span>
                <p className="text-gray-400 mt-0.5">{localizedEvent.description}</p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

const SentimentTooltip = ({ active, payload, label }: any) => {
  const { t } = useTranslation();
  if (!active || !payload?.length) return null;
  const entry = payload[0]?.payload as TimelineEntry | undefined;
  if (!entry?.sentiment) return null;

  const categories = ["celebration", "utility", "detection", "questioning", "alarm", "reckoning"] as const;
  const total = categories.reduce((s, c) => s + (entry.sentiment?.[c] || 0), 0);

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3 max-w-xs">
      <div className="flex items-center justify-between mb-2">
        <span className="font-bold text-daikin-dark">{label}</span>
        <span className="text-xs text-gray-500">{t("litigation.paperCount", { count: total })}</span>
      </div>
      <div className="space-y-1">
        {categories.map(c => {
          const count = entry.sentiment?.[c] || 0;
          if (count === 0) return null;
          return (
            <div key={c} className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: SENTIMENT_COLORS[c] }} />
                <span className="text-gray-600">{getSentimentLabel(t, c)}</span>
              </div>
              <span className="font-medium text-gray-800">{count}</span>
            </div>
          );
        })}
      </div>
      {entry.normalized_sentiment != null && (
        <div className="mt-2 pt-2 border-t border-gray-100 flex items-center justify-between text-xs">
          <span className="text-gray-500">{t("litigation.sentimentThreeYearAverage")}</span>
          <span className={`font-bold ${entry.normalized_sentiment < 0 ? "text-red-600" : "text-green-600"}`}>
            {entry.normalized_sentiment > 0 ? "+" : ""}{entry.normalized_sentiment.toFixed(2)}
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
  const { t, i18n } = useTranslation();
  const { toast } = useToast();
  const helpContent = useHelpContent();
  const currentLanguage = i18n.resolvedLanguage ?? i18n.language;
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingBacktest, setIsLoadingBacktest] = useState(false);
  const [isLoadingBacktests, setIsLoadingBacktests] = useState(true);
  const [forecast, setForecast] = useState<LitigationForecast | null>(null);
  const [backtest, setBacktest] = useState<BacktestData | null>(null);
  const [availableBacktests, setAvailableBacktests] = useState<BacktestSummary[]>([]);
  const [selectedCompound, setSelectedCompound] = useState<string>("pfoa");

  const [chartView, setChartView] = useState<"publications" | "signal" | "sentiment">("publications");
  const [paperDrilldown, setPaperDrilldown] = useState<PapersResponse | null>(null);
  const [isLoadingPapers, setIsLoadingPapers] = useState(false);
  const [formData, setFormData] = useState({
    compound: "PFOA",
    volume: 100000,
    pathways: ["water"] as string[],
  });

  // Load available backtests on mount
  useEffect(() => {
    loadAvailableBacktests();
  }, []);

  // Load selected compound backtest when selection changes
  useEffect(() => {
    if (selectedCompound) {
      loadBacktest(selectedCompound);
    }
  }, [selectedCompound]);

  const loadAvailableBacktests = async () => {
    setIsLoadingBacktests(true);
    try {
      const data = await apiGet("/api/sentinel/backtests", litigationBacktestsSchema);
      const backtests = (data.available_backtests || []) as BacktestSummary[];
      setAvailableBacktests(backtests);
      // Default to PFOA if available
      if (backtests.some((b) => b.compound_id === "pfoa")) {
        setSelectedCompound("pfoa");
      } else if (backtests.length > 0) {
        setSelectedCompound(backtests[0].compound_id);
      }
    } catch {
      // Fallback to default compound on error
      setSelectedCompound("genx");
    } finally {
      setIsLoadingBacktests(false);
    }
  };

  const loadBacktest = async (compoundId: string) => {
    setIsLoadingBacktest(true);
    try {
      // Try new sentinel endpoint first
      try {
        const data = await apiGet(`/api/sentinel/backtest/${compoundId}`, litigationBacktestSchema);
        setBacktest(data as BacktestData);
      } catch {
        // Fallback to legacy litigation endpoint for genx
        const data = await apiGet(`/api/v1/litigation/backtest/${compoundId}`, litigationBacktestSchema);
        setBacktest(data as BacktestData);
      }
    } catch {
      // Silently handle - UI will show empty state
    } finally {
      setIsLoadingBacktest(false);
    }
  };

  const loadPapersForYear = async (year: number) => {
    if (!selectedCompound) return;
    setIsLoadingPapers(true);
    try {
      const data = await apiGet(
        `/api/sentinel/backtest/${selectedCompound}/papers/${year}`,
        litigationPapersSchema,
      );
      setPaperDrilldown(data as PapersResponse);
    } catch {
      // Silently handle
    } finally {
      setIsLoadingPapers(false);
    }
  };

  const handleSentimentChartClick = (data: any) => {
    if (data?.activePayload?.[0]?.payload) {
      const entry = data.activePayload[0].payload as TimelineEntry;
      const categories = ["celebration", "utility", "detection", "questioning", "alarm", "reckoning"] as const;
      const total = categories.reduce((s, c) => s + (entry.sentiment?.[c] || 0), 0);
      if (total > 0) {
        loadPapersForYear(entry.year);
      }
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
      const data = await apiPost("/api/v1/litigation/forecast", litigationForecastSchema, {
        compound: formData.compound,
        production_volume_lbs: formData.volume,
        exposure_pathways: formData.pathways,
      });
      setForecast(data);

      toast({
        title: t('common.forecastComplete'),
        description: `${data.compound}: ${data.risk_level} risk (${(data.probability_24_months * 100).toFixed(1)}% in 24mo)`,
      });
    } catch {
      toast({
        title: t('common.forecastFailed'),
        description: t('common.couldNotConnect'),
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
  const chatSurfaceHint = useMemo(() => createLitigationAnswerSurfaceHint({
    locale: currentLanguage,
    starterQuestions: [
      t("chat.starters.litigation.forecast"),
      t("chat.starters.litigation.backtest"),
      t("chat.starters.litigation.cases"),
    ],
    selectedCompound: formData.compound,
    chartView,
    availableBacktests: availableBacktests.length,
    forecastRiskLevel: forecast?.risk_level ?? null,
    probability12Months: forecast?.probability_12_months ?? null,
    probability24Months: forecast?.probability_24_months ?? null,
    probability36Months: forecast?.probability_36_months ?? null,
    estimatedExposureUsd: forecast?.estimated_exposure_usd ?? null,
    keyDrivers: (forecast?.key_drivers || []).slice(0, 6),
    visibleSimilarCases: (forecast?.similar_cases || []).slice(0, 6).map((item) => ({
      case: item.case,
      year: item.year,
      settlement: item.settlement,
      relevance: item.relevance,
    })),
    backtestPublications: backtest?.total_publications ?? null,
    firstLawsuitYear: backtest?.first_lawsuit_year ?? null,
    leadTimeYears: backtest?.lead_time_years ?? null,
    paperDrilldownYear: paperDrilldown?.year ?? null,
    paperDrilldownTotal: paperDrilldown?.total ?? null,
  }), [availableBacktests.length, backtest, chartView, currentLanguage, forecast, formData.compound, paperDrilldown, t]);

  return (
    <PageChatProvider
      pageId="litigation"
      pageLabel={t("litigation.title")}
      surfaceHint={chatSurfaceHint}
    >
    <div className="min-h-screen bg-gray-50">
      <DaikinHeader title={t('litigation.title')} subtitle={t('litigation.subtitle')} helpContent={helpContent.litigation}>
        {backtest && (
          <>
            <div className="text-gray-600">
              <span className="text-daikin-blue font-bold">{backtest.lead_time_years}</span>{t('litigation.yearLeadTime')}
            </div>
            <div className="text-gray-600">
              <span className="text-daikin-blue font-bold">{formatCurrency(backtest.settlement_total_usd)}</span> {t('litigation.inSettlements')}
            </div>
          </>
        )}
      </DaikinHeader>

      <main className="container mx-auto px-4 py-8 space-y-8">
        <Tabs defaultValue="casestudy">
          <TabsList className="bg-white border border-gray-200 shadow-sm">
            <TabsTrigger value="casestudy" className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-daikin-blue data-[state=active]:to-daikin-accent data-[state=active]:text-white">
              <Eye className="mr-2 h-4 w-4" />
              {t('litigation.validationCaseStudies')}
            </TabsTrigger>
            <TabsTrigger value="forecast" className="data-[state=active]:bg-gradient-to-r data-[state=active]:from-daikin-blue data-[state=active]:to-daikin-accent data-[state=active]:text-white">
              <ShieldAlert className="mr-2 h-4 w-4" />
              {t('litigation.riskForecast')}
            </TabsTrigger>
          </TabsList>

          {/* ============================================================ */}
          {/* TAB 1: GenX Case Study                                       */}
          {/* ============================================================ */}
          <TabsContent value="casestudy" className="space-y-6 mt-6">
            {/* Compound Selector */}
            {isLoadingBacktests ? (
              <div className="flex items-center gap-2 p-4 bg-white border border-gray-200 rounded-lg shadow-sm">
                <Loader2 className="h-4 w-4 animate-spin text-daikin-blue" />
                <span className="text-sm text-gray-500">{t('litigation.loadingCaseStudies')}</span>
              </div>
            ) : availableBacktests.length > 0 && (
              <div className="flex items-center gap-4 p-4 bg-white border border-gray-200 rounded-lg shadow-sm">
                <span className="text-sm font-medium text-gray-600">{t('litigation.selectCompound')}</span>
                <div className="flex gap-2">
                  {availableBacktests.map((bt) => (
                    <Button
                      key={bt.compound_id}
                      variant={selectedCompound === bt.compound_id ? "default" : "outline"}
                      size="sm"
                      disabled={isLoadingBacktest}
                      className={selectedCompound === bt.compound_id
                        ? "bg-daikin-blue hover:bg-daikin-blue/90 text-white"
                        : "border-gray-300"}
                      onClick={() => setSelectedCompound(bt.compound_id)}
                    >
                      {isLoadingBacktest && selectedCompound === bt.compound_id && (
                        <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                      )}
                      {bt.compound_id.toUpperCase()}
                      <Badge className="ml-2 bg-white/20 text-xs">
                        {bt.lead_time_years}yr
                      </Badge>
                    </Button>
                  ))}
                </div>
                {backtest?.compound_id === "pfoa" && !isLoadingBacktest && (
                  <Badge className="bg-green-100 text-green-800 ml-auto">
                    {t('litigation.strongestValidation')}
                  </Badge>
                )}
              </div>
            )}

            {backtest ? (
              <>
                {/* Headline stats */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <Card className="bg-white border-gray-200 shadow-sm">
                    <CardContent className="p-4 text-center">
                      <p className="text-xs text-gray-500 uppercase tracking-wide">{t('litigation.publications')}</p>
                      <p className="text-3xl font-bold text-daikin-dark">{backtest.total_publications}</p>
                      <p className="text-xs text-gray-400">{t('litigation.pubmedPapers')}</p>
                    </CardContent>
                  </Card>
                  <Card className="bg-white border-gray-200 shadow-sm">
                    <CardContent className="p-4 text-center">
                      <p className="text-xs text-gray-500 uppercase tracking-wide">
                        {backtest.first_elevated_year ? t('litigation.firstElevated') : t('litigation.firstSignal')}
                      </p>
                      <p className="text-3xl font-bold text-yellow-600">
                        {backtest.first_elevated_year || backtest.first_publication_year}
                      </p>
                      <p className="text-xs text-gray-400">
                        {backtest.first_elevated_year ? t('litigation.accelerationDetected') : t('litigation.velocityFromZero')}
                      </p>
                    </CardContent>
                  </Card>
                  <Card className="bg-white border-gray-200 shadow-sm">
                    <CardContent className="p-4 text-center">
                      <p className="text-xs text-gray-500 uppercase tracking-wide">
                        {backtest.first_critical_year ? t('litigation.firstCritical') : t('litigation.firstLawsuit')}
                      </p>
                      <p className="text-3xl font-bold text-red-600">
                        {backtest.first_critical_year || backtest.first_lawsuit_year}
                      </p>
                      <p className="text-xs text-gray-400">
                        {backtest.first_critical_year
                          ? `${backtest.major_settlement_year ? backtest.major_settlement_year - backtest.first_critical_year : backtest.lead_time_years}${t('litigation.yrBeforeSettlement')}`
                          : `${backtest.lead_time_years}${t('litigation.yrAfterSignal')}`}
                      </p>
                    </CardContent>
                  </Card>
                  <Card className="bg-white border-gray-200 shadow-sm">
                    <CardContent className="p-4 text-center">
                      <p className="text-xs text-gray-500 uppercase tracking-wide">{t('litigation.totalSettlements')}</p>
                      <p className="text-3xl font-bold text-daikin-blue">{formatCurrency(backtest.settlement_total_usd)}</p>
                      <p className="text-xs text-gray-400">{backtest.affected_population.toLocaleString()} {t('litigation.affected')}</p>
                    </CardContent>
                  </Card>
                </div>

                {/* Publication Timeline Chart */}
                <Card className="bg-white border-gray-200 shadow-sm">
                  <CardHeader>
                    <div className="flex items-center justify-between flex-wrap gap-3">
                      <div>
                        <CardTitle className="text-daikin-dark">
                          {backtest.compound} {chartView === "signal" ? t('litigation.sentinelSignal') : chartView === "sentiment" ? t('litigation.sentimentLifecycle') : t('litigation.publicationTimeline')}
                        </CardTitle>
                        <CardDescription>
                          {chartView === "signal"
                            ? t('litigation.chartDescriptions.signal')
                            : chartView === "sentiment"
                            ? t('litigation.chartDescriptions.sentiment')
                            : t('litigation.chartDescriptions.publications')}
                        </CardDescription>
                      </div>
                      <div className="flex gap-1">
                        <Button
                          variant={chartView === "publications" ? "default" : "outline"}
                          size="sm"
                          className={chartView === "publications" ? "bg-daikin-dark text-white hover:bg-daikin-dark/90" : ""}
                          onClick={() => setChartView("publications")}
                        >
                          {t('litigation.publications')}
                        </Button>
                        <Button
                          variant={chartView === "signal" ? "default" : "outline"}
                          size="sm"
                          className={chartView === "signal" ? "bg-daikin-dark text-white hover:bg-daikin-dark/90" : ""}
                          onClick={() => setChartView("signal")}
                        >
                          {t('litigation.sentinelSignal')}
                        </Button>
                        <Button
                          variant={chartView === "sentiment" ? "default" : "outline"}
                          size="sm"
                          className={chartView === "sentiment" ? "bg-daikin-dark text-white hover:bg-daikin-dark/90" : ""}
                          onClick={() => setChartView("sentiment")}
                        >
                          {t("litigation.sentiment")}
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[400px]">
                      <ResponsiveContainer width="100%" height="100%">
                        {chartView === "signal" ? (
                          <ComposedChart data={backtest.timeline} margin={{ top: 60, right: 60, bottom: 20, left: 20 }}>
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
                              label={{ value: t("litigation.velocityPapersPerYear"), angle: -90, position: "insideLeft", style: { fontSize: 11, fill: "#9ca3af" } }}
                            />
                            <YAxis
                              yAxisId="acceleration"
                              orientation="right"
                              tick={{ fontSize: 11, fill: "#f97316" }}
                              tickLine={false}
                              label={{ value: t("litigation.acceleration"), angle: 90, position: "insideRight", style: { fontSize: 11, fill: "#f97316" } }}
                            />
                            <Tooltip content={<BacktestTooltip events={backtest.key_events} compoundId={backtest.compound_id} language={currentLanguage} />} />
                            {litigationEvents.map((e, idx) => (
                              <ReferenceLine
                                key={`lit-${e.year}`}
                                x={e.year}
                                yAxisId="velocity"
                                stroke="#ef4444"
                                strokeWidth={2}
                                strokeDasharray="4 4"
                                label={{ value: getLocalizedEvent(currentLanguage, backtest.compound_id, e).label, position: "top", fill: "#ef4444", fontSize: 8, fontWeight: 600, dy: idx % 2 === 0 ? -5 : -20 }}
                              />
                            ))}
                            <ReferenceLine
                              x={backtest.first_publication_year}
                              yAxisId="velocity"
                              stroke="#eab308"
                              strokeWidth={2}
                              label={{ value: t("litigation.sentinelSignal"), position: "insideTopRight", fill: "#eab308", fontSize: 9, fontWeight: 700 }}
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
                          <ComposedChart data={backtest.timeline} margin={{ top: 60, right: 60, bottom: 20, left: 20 }} onClick={handleSentimentChartClick} style={{ cursor: "pointer" }}>
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
                              label={{ value: t("litigation.papersAxis"), angle: -90, position: "insideLeft", style: { fontSize: 11, fill: "#9ca3af" } }}
                            />
                            <YAxis
                              yAxisId="cumulative"
                              orientation="right"
                              domain={[-1, 1]}
                              tick={{ fontSize: 11, fill: "#ef4444" }}
                              tickLine={false}
                              tickFormatter={(v) => v.toFixed(1)}
                              label={{ value: t("litigation.sentimentThreeYearAverage"), angle: 90, position: "insideRight", style: { fontSize: 11, fill: "#ef4444" } }}
                            />
                            <Tooltip content={<SentimentTooltip />} />
                            {industryEvents.map((e, idx) => (
                              <ReferenceLine
                                key={`ind-${e.year}`}
                                x={e.year}
                                yAxisId="papers"
                                stroke="#22c55e"
                                strokeWidth={2}
                                strokeDasharray="4 4"
                                label={{ value: getLocalizedEvent(currentLanguage, backtest.compound_id, e).label, position: "top", fill: "#22c55e", fontSize: 8, fontWeight: 600, dy: idx % 2 === 0 ? -5 : -20 }}
                              />
                            ))}
                            {litigationEvents.map((e, idx) => (
                              <ReferenceLine
                                key={`lit-${e.year}`}
                                x={e.year}
                                yAxisId="papers"
                                stroke="#ef4444"
                                strokeWidth={1.5}
                                strokeDasharray="4 4"
                                label={{ value: getLocalizedEvent(currentLanguage, backtest.compound_id, e).label, position: "top", fill: "#ef4444", fontSize: 8, dy: (idx + industryEvents.length) % 2 === 0 ? -5 : -20 }}
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
                              dataKey="normalized_sentiment"
                              stroke="#dc2626"
                              strokeWidth={2.5}
                              dot={false}
                              strokeDasharray="6 3"
                            />
                          </ComposedChart>
                        ) : (
                          <BarChart data={backtest.timeline} margin={{ top: 60, right: 60, bottom: 20, left: 20 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                            <XAxis
                              dataKey="year"
                              tick={{ fontSize: 11, fill: "#6b7280" }}
                              tickLine={false}
                            />
                            <YAxis
                              tick={{ fontSize: 11, fill: "#6b7280" }}
                              tickLine={false}
                              label={{ value: t("litigation.publications"), angle: -90, position: "insideLeft", style: { fontSize: 11, fill: "#9ca3af" } }}
                            />
                            <Tooltip content={<BacktestTooltip events={backtest.key_events} compoundId={backtest.compound_id} language={currentLanguage} />} />
                            {litigationEvents.map((e, idx) => (
                              <ReferenceLine
                                key={`lit-${e.year}`}
                                x={e.year}
                                stroke="#ef4444"
                                strokeWidth={2}
                                strokeDasharray="4 4"
                                label={{ value: getLocalizedEvent(currentLanguage, backtest.compound_id, e).label, position: "top", fill: "#ef4444", fontSize: 8, fontWeight: 600, dy: idx % 2 === 0 ? -5 : -20 }}
                              />
                            ))}
                            {settlementEvents.map((e, idx) => (
                              <ReferenceLine
                                key={`set-${e.year}`}
                                x={e.year}
                                stroke="#991b1b"
                                strokeWidth={1.5}
                                strokeDasharray="4 4"
                                label={{ value: getLocalizedEvent(currentLanguage, backtest.compound_id, e).label, position: "top", fill: "#991b1b", fontSize: 8, dy: (idx + litigationEvents.length) % 2 === 0 ? -5 : -20 }}
                              />
                            ))}
                            <ReferenceLine
                              x={backtest.first_publication_year}
                              stroke="#eab308"
                              strokeWidth={2}
                              label={{ value: t("litigation.sentinelSignal"), position: "insideTopRight", fill: "#eab308", fontSize: 9, fontWeight: 700 }}
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
                              <span className="text-xs text-gray-600">{t(info.labelKey)}</span>
                            </div>
                          ))}
                          <div className="flex items-center gap-1.5">
                            <div className="w-6 h-0.5 bg-orange-500 rounded" />
                            <span className="text-xs text-gray-600">{t('litigation.acceleration')}</span>
                          </div>
                        </>
                      ) : chartView === "sentiment" ? (
                        <>
                          {(["celebration", "utility", "detection", "questioning", "alarm", "reckoning"] as const).map(c => (
                            <div key={c} className="flex items-center gap-1.5">
                              <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: SENTIMENT_COLORS[c] }} />
                              <span className="text-xs text-gray-600">{getSentimentLabel(t, c)}</span>
                            </div>
                          ))}
                          <div className="flex items-center gap-1.5">
                            <div className="w-6 h-0.5 rounded" style={{ borderTop: "2px dashed #dc2626" }} />
                            <span className="text-xs text-gray-600">{t("litigation.sentimentThreeYearAverage")}</span>
                          </div>
                        </>
                      ) : (
                        backtest.phases.map((p) => (
                          <div key={p.id} className="flex items-center gap-1.5">
                            <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: p.color }} />
                            <span className="text-xs text-gray-600">{getLocalizedPhaseLabel(currentLanguage, backtest.compound_id, p)} ({p.years[0]}-{p.years[1]})</span>
                          </div>
                        ))
                      )}
                    </div>

                    {/* Click hint for sentiment view */}
                    {chartView === "sentiment" && (
                      <p className="text-center text-xs text-blue-400 mt-2">{t("litigation.clickYearToExplorePapers")}</p>
                    )}

                    {/* Sentiment annotation */}
                    {chartView === "sentiment" && (
                      <div className="mt-4 p-3 bg-daikin-blue/5 border border-daikin-blue/20 rounded-lg">
                        <p className="text-xs text-daikin-dark leading-relaxed">
                          <span className="font-semibold">{t('litigation.sentimentKeyFinding')}</span> {t('litigation.sentimentAnnotation')}
                        </p>
                      </div>
                    )}

                    {/* Paper drill-down panel */}
                    {chartView === "sentiment" && (paperDrilldown || isLoadingPapers) && (
                      <div className="mt-4 border border-gray-200 rounded-lg overflow-hidden">
                        <div className="flex items-center justify-between px-4 py-3 bg-gray-50 border-b border-gray-200">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-sm text-daikin-dark">
                              {paperDrilldown ? t("litigation.yearPapers", { year: paperDrilldown.year }) : t("common.loading")}
                            </span>
                            {paperDrilldown && (
                              <Badge variant="outline" className="text-xs">
                                {t("litigation.paperCount", { count: paperDrilldown.total })}
                              </Badge>
                            )}
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 w-7 p-0"
                            onClick={() => setPaperDrilldown(null)}
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        </div>
                        {isLoadingPapers ? (
                          <div className="p-6 text-center">
                            <Loader2 className="h-5 w-5 mx-auto animate-spin text-daikin-blue" />
                          </div>
                        ) : paperDrilldown?.papers && (
                          <div className="max-h-[320px] overflow-y-auto divide-y divide-gray-100">
                            {paperDrilldown.papers.map((paper, i) => (
                              <div key={paper.pmid || i} className="px-4 py-3 hover:bg-gray-50 transition-colors">
                                <div className="flex items-start justify-between gap-3">
                                  <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 mb-1">
                                      <Badge
                                        className="text-[10px] px-1.5 py-0"
                                        style={{
                                          backgroundColor: SENTIMENT_COLORS[paper.category.toLowerCase()] || "#9ca3af",
                                          color: ["celebration", "utility", "detection"].includes(paper.category.toLowerCase()) ? "#1f2937" : "#ffffff",
                                        }}
                                      >
                                        {getSentimentLabel(t, paper.category.toLowerCase())}
                                      </Badge>
                                      {paper.confidence >= 0.8 && (
                                        <span className="text-[10px] text-gray-400">{t("litigation.highConfidence")}</span>
                                      )}
                                    </div>
                                    <p className="text-sm text-gray-800 leading-snug">{paper.title}</p>
                                    <p className="text-xs text-gray-400 mt-1">
                                      {paper.journal}
                                      {paper.reasoning && (
                                        <span className="text-gray-300"> &mdash; {paper.reasoning}</span>
                                      )}
                                    </p>
                                  </div>
                                  {paper.pmid && (
                                    <a
                                      href={`https://pubmed.ncbi.nlm.nih.gov/${paper.pmid}/`}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="flex-shrink-0 text-blue-500 hover:text-blue-700 transition-colors"
                                      title={t("litigation.viewOnPubMed")}
                                    >
                                      <ExternalLink className="h-3.5 w-3.5" />
                                    </a>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Industry Claims vs. Reality */}
                {backtest.industry_claims && backtest.industry_claims.length > 0 && (
                  <Card className="bg-white border-gray-200 shadow-sm">
                    <CardHeader>
                      <CardTitle className="text-daikin-dark flex items-center gap-2">
                        <Quote className="h-5 w-5 text-green-600" />
                        {t('litigation.claimsVsReality')}
                      </CardTitle>
                      <CardDescription>
                        {t('litigation.claimsDescription')}
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
                                <span className="text-xs text-gray-400 uppercase tracking-wide">{t('litigation.claim')}</span>
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
                                <span className="text-xs text-gray-400 uppercase tracking-wide">{t('litigation.reality')}</span>
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
                      {t('litigation.sentinelReconstruction')}
                    </CardTitle>
                    <CardDescription className="text-gray-400">
                      {t('litigation.whatSentinelWouldShow')}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <p className="text-gray-300 text-sm leading-relaxed">
                      {backtest.sentinel_reconstruction.narrative}
                    </p>
                    <div className="p-3 bg-white/5 rounded-lg border border-white/10">
                      <p className="text-yellow-400 text-xs font-semibold uppercase tracking-wider mb-1">{t('litigation.keyInsight')}</p>
                      <p className="text-white text-sm">
                        {backtest.sentinel_reconstruction.key_insight}
                      </p>
                    </div>
                    <div className="p-3 bg-white/5 rounded-lg border border-white/10">
                      <p className="text-blue-400 text-xs font-semibold uppercase tracking-wider mb-1">{t('litigation.counterfactual')}</p>
                      <p className="text-gray-300 text-sm">
                        {backtest.sentinel_reconstruction.counterfactual}
                      </p>
                    </div>
                  </CardContent>
                </Card>

                {/* Event Timeline */}
                <Card className="bg-white border-gray-200 shadow-sm">
                  <CardHeader>
                    <CardTitle className="text-daikin-dark">{t('litigation.eventTimeline')}</CardTitle>
                    <CardDescription>{t('litigation.eventTimelineDescription')}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {backtest.key_events.map((event, i) => (
                        <div key={i} className="flex gap-3 items-start">
                          <div className="flex-shrink-0 w-12 text-right">
                            <span className="text-sm font-bold text-daikin-dark">{event.year}</span>
                          </div>
                          <div
                            className="flex-shrink-0 w-2 h-2 mt-1.5 rounded-full"
                            style={{ backgroundColor: EVENT_COLORS[event.type] || "#9ca3af" }}
                          />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-800">{getLocalizedEvent(currentLanguage, backtest.compound_id, event).label}</p>
                            <p className="text-xs text-gray-500 mt-0.5">{getLocalizedEvent(currentLanguage, backtest.compound_id, event).description}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                    <div className="mt-4 pt-3 border-t border-gray-100">
                      <p className="text-xs text-gray-400">
                        Sources: {backtest.source_citations.slice(0, 3).join("; ")}; {t('litigation.andMore', { count: backtest.source_citations.length - 3 })}
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </>
            ) : (
              <Card className="bg-white border-gray-200 shadow-sm">
                <CardContent className="py-16 text-center">
                  <Loader2 className="h-8 w-8 mx-auto mb-4 animate-spin text-daikin-blue" />
                  <p className="text-gray-500">{t('litigation.loadingCaseStudy', { compound: selectedCompound.toUpperCase() })}</p>
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
                  <CardTitle className="text-daikin-dark">{t('litigation.forecastParameters')}</CardTitle>
                  <CardDescription>{t('litigation.configureRiskAssessment')}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label className="text-gray-700">{t('litigation.compound')}</Label>
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
                    <Label className="text-gray-700">{t('litigation.productionVolume')}</Label>
                    <Input
                      type="number"
                      value={formData.volume}
                      onChange={(e) => setFormData({ ...formData, volume: parseInt(e.target.value) || 0 })}
                      className="bg-white border-gray-300"
                    />
                  </div>

                  <div>
                    <Label className="text-gray-700">{t('litigation.exposurePathways')}</Label>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {PATHWAYS.map((p) => (
                        <Badge
                          key={p}
                          variant={formData.pathways.includes(p) ? "default" : "outline"}
                          className={`cursor-pointer ${formData.pathways.includes(p) ? "bg-daikin-blue text-white" : "border-gray-400 text-gray-600"}`}
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
                    className="w-full bg-gradient-to-r from-daikin-blue to-daikin-accent hover:opacity-90 text-white"
                  >
                    {isLoading ? (
                      <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> {t('common.calculating')}</>
                    ) : (
                      <><TrendingUp className="mr-2 h-4 w-4" /> {t('litigation.calculateRisk')}</>
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
                          <CardTitle className="text-daikin-dark">{forecast.compound} {t('litigation.litigationForecast')}</CardTitle>
                          <Badge className={getRiskColor(forecast.risk_level)}>{forecast.risk_level} {t('litigation.risk')}</Badge>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <div className="grid grid-cols-3 gap-4 mb-6">
                          <div className="text-center">
                            <p className="text-sm text-gray-500">{t('litigation.months12')}</p>
                            <p className="text-2xl font-bold text-daikin-dark">{(forecast.probability_12_months * 100).toFixed(1)}%</p>
                            <Progress value={forecast.probability_12_months * 100} className="mt-2" />
                          </div>
                          <div className="text-center">
                            <p className="text-sm text-gray-500">{t('litigation.months24')}</p>
                            <p className="text-2xl font-bold text-daikin-blue">{(forecast.probability_24_months * 100).toFixed(1)}%</p>
                            <Progress value={forecast.probability_24_months * 100} className="mt-2" />
                          </div>
                          <div className="text-center">
                            <p className="text-sm text-gray-500">{t('litigation.months36')}</p>
                            <p className="text-2xl font-bold text-daikin-dark">{(forecast.probability_36_months * 100).toFixed(1)}%</p>
                            <Progress value={forecast.probability_36_months * 100} className="mt-2" />
                          </div>
                        </div>

                        <div className="flex items-center justify-between p-4 bg-gray-100 rounded-lg">
                          <div className="flex items-center gap-2">
                            <DollarSign className="h-6 w-6 text-green-600" />
                            <span className="text-gray-600">{t('litigation.estimatedExposure')}</span>
                          </div>
                          <span className="text-2xl font-bold text-green-600">{formatCurrency(forecast.estimated_exposure_usd)}</span>
                        </div>

                        <div className="mt-4 text-sm text-gray-500">
                          {t('litigation.confidenceInterval')}: {(forecast.confidence_low * 100).toFixed(1)}% - {(forecast.confidence_high * 100).toFixed(1)}%
                        </div>
                      </CardContent>
                    </Card>

                    {/* Key Drivers */}
                    <Card className="bg-white border-gray-200 shadow-sm">
                      <CardHeader>
                        <CardTitle className="text-daikin-dark flex items-center gap-2">
                          <AlertTriangle className="h-5 w-5 text-daikin-accent" />
                          {t('litigation.keyRiskDrivers')}
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <ul className="space-y-2">
                          {forecast.key_drivers.map((driver, i) => (
                            <li key={i} className="flex items-start gap-2 text-gray-600">
                              <span className="text-daikin-accent">•</span>
                              {driver}
                            </li>
                          ))}
                        </ul>
                      </CardContent>
                    </Card>

                    {/* Similar Cases */}
                    <Card className="bg-white border-gray-200 shadow-sm">
                      <CardHeader>
                        <CardTitle className="text-daikin-dark">{t('litigation.similarCases')}</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="space-y-3">
                          {forecast.similar_cases.map((c, i) => (
                            <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                              <div>
                                <p className="font-medium text-daikin-dark">{c.case}</p>
                                <p className="text-sm text-gray-500">{t('common.year')}: {c.year} | {t('litigation.relevance')}: {(c.relevance * 100).toFixed(0)}%</p>
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
                      <div className="h-16 w-16 mx-auto mb-4 rounded-full bg-gradient-to-r from-daikin-blue to-daikin-accent flex items-center justify-center">
                        <Scale className="h-8 w-8 text-white" />
                      </div>
                      <h3 className="text-xl font-semibold text-daikin-dark mb-2">{t('litigation.compoundRiskForecast')}</h3>
                      <p className="text-gray-500 max-w-md mx-auto">
                        {t('litigation.forecastDescription')}
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
    </PageChatProvider>
  );
};

export default LitigationRisk;
