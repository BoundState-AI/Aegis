import { useState, useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useToast } from "@/hooks/use-toast";
import { Loader2, Package, Plus, Trash2, AlertTriangle, PieChart, Info } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { SpicyTooltipBody } from "@/components/ui/spicy-tooltip-body";
import DaikinHeader from "@/components/layout/DaikinHeader";
import { PageChatProvider } from "@/components/chat/PageChatProvider";
import { useHelpContent } from "@/config/helpContent";
import { apiPost } from "@/lib/apiClient";
import { createPortfolioAnswerSurfaceHint } from "@/lib/chat/surfaces";
import { portfolioResponseSchema, type PortfolioResponse } from "@/lib/apiSchemas";

interface PortfolioItem {
  material: string;
  volume_lbs: number;
}

interface PortfolioResult {
  material: string;
  risk_score: number;
  risk_category: string;
  pfas_count: number;
  regulatory_flags: number;
  litigation_probability: number;
}

interface PortfolioViewResponse extends PortfolioResponse {
  results: PortfolioResult[];
}

const SUGGESTED_MATERIALS = ["PTFE", "FEP", "PFA", "PVDF", "ETFE"];

const PortfolioAssessment = () => {
  const { t, i18n } = useTranslation();
  const { toast } = useToast();
  const helpContent = useHelpContent();
  const currentLanguage = i18n.resolvedLanguage ?? i18n.language ?? "en";
  const isJapanese = currentLanguage.startsWith("ja");
  const tp = (key: string, fallbackEn: string, fallbackJa: string, options?: Record<string, unknown>) =>
    t(key, {
      ...options,
      defaultValue: isJapanese ? fallbackJa : fallbackEn,
    });
  const riskCategoryDefinitions = {
    LOW: {
      label: tp("portfolio.riskCategories.LOW.label", "Low", "低"),
      color: "bg-green-500",
      textColor: "text-green-600",
      description: tp(
        "portfolio.riskCategories.LOW.description",
        "Compound shows minimal regulatory activity and no documented litigation exposure. Limited degradation pathways to regulated endpoints.",
        "規制上の動きが少なく、訴訟エクスポージャーの文書化もありません。規制対象エンドポイントへの分解経路も限定的です。",
      ),
    },
    MEDIUM: {
      label: tp("portfolio.riskCategories.MEDIUM.label", "Medium", "中"),
      color: "bg-yellow-500",
      textColor: "text-yellow-600",
      description: tp(
        "portfolio.riskCategories.MEDIUM.description",
        "Compound has documented degradation pathways and active regulatory attention in 2+ jurisdictions. Not yet subject to compound-specific litigation.",
        "分解経路が文書化されており、2件以上の法域で規制上の注目があります。まだ化合物固有の訴訟対象ではありません。",
      ),
    },
    HIGH: {
      label: tp("portfolio.riskCategories.HIGH.label", "High", "高"),
      color: "bg-red-500",
      textColor: "text-red-600",
      description: tp(
        "portfolio.riskCategories.HIGH.description",
        "Compound has established regulatory limits, documented litigation history, or known degradation to heavily regulated endpoints (e.g., PFOA, PFOS).",
        "規制値が既に設定されている、訴訟履歴がある、またはPFOA/PFOSのような強く規制されるエンドポイントへの既知の分解経路があります。",
      ),
    },
  } as const;
  const [items, setItems] = useState<PortfolioItem[]>([
    { material: "PTFE", volume_lbs: 100000 },
    { material: "FEP", volume_lbs: 50000 },
  ]);
  const [newMaterial, setNewMaterial] = useState("");
  const [newVolume, setNewVolume] = useState(10000);
  const [assessment, setAssessment] = useState<PortfolioViewResponse | null>(null);

  const assessMutation = useMutation({
    mutationFn: () => apiPost("/api/v1/portfolio/assess", portfolioResponseSchema, { items, locale: currentLanguage }),
    onSuccess: (data) => {
      const typed = data as PortfolioViewResponse;
      setAssessment(typed);
      toast({
        title: t('common.assessmentComplete'),
        description: tp(
          'portfolio.analyzed',
          'Analyzed {{count}} materials - {{highRisk}} high risk',
          '{{count}}件の材料を分析 - {{highRisk}}件が高リスク',
          { count: typed.total_materials, highRisk: typed.high_risk_count },
        ),
      });
    },
    onError: () => {
      toast({
        title: t('common.assessmentFailed'),
        description: t('common.couldNotConnect'),
        variant: "destructive",
      });
    },
  });

  // Auto-assess on mount and when locale changes so backend-generated copy follows the active language.
  useEffect(() => {
    void handleAssess();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentLanguage]);

  const addItem = () => {
    if (!newMaterial) return;
    setItems([...items, { material: newMaterial.toUpperCase(), volume_lbs: newVolume }]);
    setNewMaterial("");
    setNewVolume(10000);
  };

  const removeItem = (index: number) => {
    setItems(items.filter((_, i) => i !== index));
  };

  const handleAssess = async () => {
    if (items.length === 0) {
      toast({
        title: tp('portfolio.noMaterials', 'No Materials', '材料なし'),
        description: tp('portfolio.addMaterialsToAssess', 'Add materials to assess', '評価する材料を追加'),
        variant: "destructive",
      });
      return;
    }

    await assessMutation.mutateAsync();
  };

  const getRiskColor = (category: string) => {
    switch (category) {
      case "HIGH": return "bg-red-500";
      case "MEDIUM": return "bg-yellow-500";
      case "LOW": return "bg-green-500";
      default: return "bg-gray-500";
    }
  };

  const isLoading = assessMutation.isPending;
  const chatSurfaceHint = useMemo(() => createPortfolioAnswerSurfaceHint({
    locale: currentLanguage,
    starterQuestions: [
      t("chat.starters.portfolio.summary"),
      t("chat.starters.portfolio.highestRisk"),
      t("chat.starters.portfolio.exposure"),
    ],
    items: items.slice(0, 12).map((item) => ({
      material: item.material,
      volume_lbs: item.volume_lbs,
    })),
    totalMaterials: assessment?.total_materials ?? items.length,
    highRiskCount: assessment?.high_risk_count ?? 0,
    totalExposureUsd: assessment?.total_exposure_usd ?? 0,
    topResults: (assessment?.results || []).slice(0, 12).map((row) => ({
      material: row.material,
      risk_category: row.risk_category,
      risk_score: row.risk_score,
      pfas_count: row.pfas_count,
      regulatory_flags: row.regulatory_flags,
      litigation_probability: row.litigation_probability,
    })),
  }), [assessment, currentLanguage, items, t]);

  return (
    <PageChatProvider
      pageId="portfolio"
      pageLabel={tp("portfolio.title", "Portfolio Risk Assessment", "ポートフォリオリスク評価")}
      surfaceHint={chatSurfaceHint}
    >
    <div className="min-h-screen bg-gray-50">
      <DaikinHeader
        title={tp('portfolio.title', 'Portfolio Risk Assessment', 'ポートフォリオリスク評価')}
        subtitle={tp('portfolio.subtitle', 'Batch analysis of multiple materials', '複数材料の一括分析')}
        helpContent={helpContent.portfolio}
      />

      <main className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Input Panel */}
          <Card className="bg-white border-gray-200 shadow-sm">
            <CardHeader>
              <CardTitle className="text-daikin-dark">{tp('portfolio.productPortfolio', 'Product Portfolio', '製品ポートフォリオ')}</CardTitle>
              <CardDescription>{tp('portfolio.addMaterialsToAssess', 'Add materials to assess', '評価する材料を追加')}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Current Items */}
              <div className="space-y-2">
                {items.map((item, i) => (
                  <div key={i} className="flex items-center justify-between p-2 bg-gray-50 rounded-lg">
                    <div>
                      <span className="text-daikin-dark font-medium">{item.material}</span>
                      <span className="text-gray-500 text-sm ml-2">({item.volume_lbs.toLocaleString()} {tp("portfolio.volumeUnitShort", "lbs", "ポンド")})</span>
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => removeItem(i)}>
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </div>
                ))}
              </div>

              {/* Add New */}
              <div className="border-t border-gray-200 pt-4">
                <Label className="text-gray-700">{tp('portfolio.addMaterial', 'Add Material', '材料を追加')}</Label>
                <div className="flex gap-2 mt-2">
                  <Input
                    value={newMaterial}
                    onChange={(e) => setNewMaterial(e.target.value.toUpperCase())}
                    placeholder={tp('portfolio.materialPlaceholder', 'Material', '材料')}
                    className="bg-white border-gray-300"
                  />
                  <Input
                    type="number"
                    value={newVolume}
                    onChange={(e) => setNewVolume(parseInt(e.target.value) || 0)}
                    placeholder={tp('portfolio.volumePlaceholder', 'Volume', '数量')}
                    className="w-28 bg-white border-gray-300"
                  />
                  <Button onClick={addItem} size="icon" className="bg-daikin-blue hover:bg-daikin-blue/90">
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              {/* Quick Add */}
              <div>
                <Label className="text-gray-600 text-sm">{tp('portfolio.quickAdd', 'Quick Add:', 'クイック追加：')}</Label>
                <div className="flex flex-wrap gap-1 mt-1">
                  {SUGGESTED_MATERIALS.filter(m => !items.find(i => i.material === m)).map((m) => (
                    <Badge
                      key={m}
                      variant="outline"
                      className="cursor-pointer border-gray-400 text-gray-600 hover:bg-gray-100"
                      onClick={() => setItems([...items, { material: m, volume_lbs: 10000 }])}
                    >
                      + {m}
                    </Badge>
                  ))}
                </div>
              </div>

              <Button
                onClick={handleAssess}
                disabled={isLoading || items.length === 0}
                className="w-full bg-gradient-to-r from-daikin-blue to-daikin-accent hover:opacity-90 text-white"
              >
                {isLoading ? (
                  <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> {t('common.assessing')}</>
                ) : (
                  <><PieChart className="mr-2 h-4 w-4" /> {tp('portfolio.assessPortfolio', 'Assess Portfolio', 'ポートフォリオを評価')}</>
                )}
              </Button>
            </CardContent>
          </Card>

          {/* Results Panel */}
          <div className="lg:col-span-2 space-y-6">
            {assessment ? (
              <>
                {/* Summary Cards */}
                <div className="grid grid-cols-2 gap-4">
                  <Card className="bg-white border-gray-200 shadow-sm">
                    <CardContent className="pt-6 text-center">
                      <Package className="h-8 w-8 text-daikin-blue mx-auto mb-2" />
                      <p className="text-3xl font-bold text-daikin-dark">{assessment.total_materials}</p>
                      <p className="text-sm text-gray-500">{tp('portfolio.materials', 'Materials', '材料')}</p>
                    </CardContent>
                  </Card>
                  <Card className="bg-white border-gray-200 shadow-sm">
                    <CardContent className="pt-6 text-center">
                      <AlertTriangle className="h-8 w-8 text-red-500 mx-auto mb-2" />
                      <p className="text-3xl font-bold text-red-500">{assessment.high_risk_count}</p>
                      <p className="text-sm text-gray-500">{tp('portfolio.highRisk', 'High Risk', '高リスク')}</p>
                    </CardContent>
                  </Card>
                </div>

                {/* Results Table */}
                <Card className="bg-white border-gray-200 shadow-sm">
                  <CardHeader>
                    <CardTitle className="text-daikin-dark">{tp('portfolio.assessmentResults', 'Assessment Results', '評価結果')}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {/* Risk Category Legend */}
                    <div className="flex items-center gap-4 text-sm text-gray-600 mb-4 pb-4 border-b border-gray-100">
                      <span className="font-medium">{tp("portfolio.riskCategoriesLabel", "Risk Categories:", "リスク区分：")}</span>
                      <TooltipProvider>
                        {(Object.keys(riskCategoryDefinitions) as Array<keyof typeof riskCategoryDefinitions>).map((key) => {
                          const cat = riskCategoryDefinitions[key];
                          return (
                            <Tooltip key={key}>
                              <TooltipTrigger asChild>
                                <div className="flex items-center gap-1.5 cursor-help">
                                  <Badge className={`${cat.color} text-white text-xs`}>{cat.label}</Badge>
                                </div>
                              </TooltipTrigger>
                              <TooltipContent side="bottom" className="max-w-xs p-3">
                                <SpicyTooltipBody>
                                  <p className="font-semibold">
                                    {tp("portfolio.riskCategoryTooltipTitle", "{{label}} Risk", "{{label}}リスク", { label: cat.label })}
                                  </p>
                                  <p className="text-sm text-muted-foreground">{cat.description}</p>
                                </SpicyTooltipBody>
                              </TooltipContent>
                            </Tooltip>
                          );
                        })}
                      </TooltipProvider>
                    </div>
                    <Table>
                      <TableHeader>
                        <TableRow className="border-gray-200">
                          <TableHead className="text-gray-600">{tp('portfolio.tableHeaders.material', 'Material', '材料')}</TableHead>
                          <TableHead className="text-gray-600">
                            <span className="flex items-center gap-1">
                              {tp('portfolio.tableHeaders.category', 'Category', 'カテゴリ')}
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Info className="h-4 w-4 text-gray-400 cursor-help" />
                                  </TooltipTrigger>
                                  <TooltipContent side="bottom" className="max-w-sm p-3">
                                    <SpicyTooltipBody>
                                      <p className="font-semibold">{tp("portfolio.riskCategoryDefinitionsTitle", "Risk Category Definitions", "リスク区分の定義")}</p>
                                      <div className="space-y-2 text-sm">
                                        <div>
                                          <span className="font-medium text-green-600">{riskCategoryDefinitions.LOW.label}:</span>{" "}
                                          <span className="text-muted-foreground">{riskCategoryDefinitions.LOW.description}</span>
                                        </div>
                                        <div>
                                          <span className="font-medium text-yellow-600">{riskCategoryDefinitions.MEDIUM.label}:</span>{" "}
                                          <span className="text-muted-foreground">{riskCategoryDefinitions.MEDIUM.description}</span>
                                        </div>
                                        <div>
                                          <span className="font-medium text-red-600">{riskCategoryDefinitions.HIGH.label}:</span>{" "}
                                          <span className="text-muted-foreground">{riskCategoryDefinitions.HIGH.description}</span>
                                        </div>
                                      </div>
                                    </SpicyTooltipBody>
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            </span>
                          </TableHead>
                          <TableHead className="text-gray-600">{tp('portfolio.tableHeaders.pfasProducts', 'PFAS Products', 'PFAS生成物')}</TableHead>
                          <TableHead className="text-gray-600">{tp('portfolio.tableHeaders.regFlags', 'Reg. Flags', '規制フラグ')}</TableHead>
                          <TableHead className="text-gray-600">{tp('portfolio.tableHeaders.litigationPercent', 'Litigation %', '訴訟確率')}</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {assessment.results.map((r, i) => (
                          <TableRow key={i} className="border-gray-200">
                            <TableCell className="font-medium text-daikin-dark">{r.material}</TableCell>
                            <TableCell>
                              <Badge className={getRiskColor(r.risk_category)}>
                                {riskCategoryDefinitions[r.risk_category as keyof typeof riskCategoryDefinitions]?.label ?? r.risk_category}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-gray-600">{r.pfas_count}</TableCell>
                            <TableCell className="text-gray-600">{r.regulatory_flags}</TableCell>
                            <TableCell className="text-gray-600">{(r.litigation_probability * 100).toFixed(1)}%</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>

                {/* Executive Summary */}
                <Card className="bg-white border-gray-200 shadow-sm">
                  <CardHeader>
                    <CardTitle className="text-daikin-dark">{tp('portfolio.executiveSummary', 'Executive Summary', 'エグゼクティブサマリー')}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-gray-600 whitespace-pre-wrap text-sm leading-relaxed">
                      {assessment.executive_summary}
                    </p>
                  </CardContent>
                </Card>

                {/* Methodology Note */}
                <p className="text-xs text-gray-400 text-center mt-4">
                  {assessment.methodology_note || tp(
                    'portfolio.disclaimer',
                    'Risk scores incorporate compound-specific degradation data, regulatory exposure, and litigation history. Site-specific factors should be evaluated by qualified professionals.',
                    'リスクスコアは化合物固有の分解データ、規制上の曝露、訴訟履歴を組み込んでいます。サイト固有の要因は資格のある専門家によって評価されるべきです。',
                  )}
                </p>
              </>
            ) : (
              <Card className="bg-white border-gray-200 shadow-sm">
                <CardContent className="py-16 text-center">
                  <Package className="h-16 w-16 mx-auto mb-4 text-gray-400" />
                  <h3 className="text-xl font-semibold text-gray-600 mb-2">{tp('portfolio.title', 'Portfolio Risk Assessment', 'ポートフォリオリスク評価')}</h3>
                  <p className="text-gray-500 max-w-md mx-auto">
                    {tp(
                      'portfolio.description',
                      'Add materials to your portfolio and get a comprehensive risk assessment with PFAS counts, regulatory flags, and litigation probability.',
                      'ポートフォリオに材料を追加し、PFASカウント、規制フラグ、訴訟確率を含む包括的なリスク評価を取得。',
                    )}
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </main>
    </div>
    </PageChatProvider>
  );
};

export default PortfolioAssessment;
