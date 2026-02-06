import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useToast } from "@/hooks/use-toast";
import { Loader2, Package, Plus, Trash2, AlertTriangle, DollarSign, PieChart, Info } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import ChemoursHeader from "@/components/layout/ChemoursHeader";
import { useHelpContent } from "@/config/helpContent";
import { API_BASE } from "@/config/api";

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

interface PortfolioResponse {
  total_materials: number;
  high_risk_count: number;
  total_exposure_usd: number;
  results: PortfolioResult[];
  executive_summary: string;
  methodology_note?: string;
}

const SUGGESTED_MATERIALS = ["PTFE", "FEP", "PFA", "PVDF", "ETFE"];

const RISK_CATEGORY_DEFINITIONS = {
  LOW: {
    label: "Low",
    color: "bg-green-500",
    textColor: "text-green-600",
    description: "Compound shows minimal regulatory activity and no documented litigation exposure. Limited degradation pathways to regulated endpoints.",
  },
  MEDIUM: {
    label: "Medium",
    color: "bg-yellow-500",
    textColor: "text-yellow-600",
    description: "Compound has documented degradation pathways and active regulatory attention in 2+ jurisdictions. Not yet subject to compound-specific litigation.",
  },
  HIGH: {
    label: "High",
    color: "bg-red-500",
    textColor: "text-red-600",
    description: "Compound has established regulatory limits, documented litigation history, or known degradation to heavily regulated endpoints (e.g., PFOA, PFOS).",
  },
} as const;

const PortfolioAssessment = () => {
  const { t } = useTranslation();
  const { toast } = useToast();
  const helpContent = useHelpContent();
  const [isLoading, setIsLoading] = useState(false);
  const [items, setItems] = useState<PortfolioItem[]>([
    { material: "PTFE", volume_lbs: 100000 },
    { material: "FEP", volume_lbs: 50000 },
  ]);
  const [newMaterial, setNewMaterial] = useState("");
  const [newVolume, setNewVolume] = useState(10000);
  const [assessment, setAssessment] = useState<PortfolioResponse | null>(null);

  // Auto-assess pre-populated portfolio on mount
  useEffect(() => {
    handleAssess();
  }, []);

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
        title: t('portfolio.noMaterials'),
        description: t('portfolio.addMaterialsToAssess'),
        variant: "destructive",
      });
      return;
    }

    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/portfolio/assess`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ items }),
      });

      if (!res.ok) throw new Error("Assessment failed");

      const data: PortfolioResponse = await res.json();
      setAssessment(data);

      toast({
        title: t('common.assessmentComplete'),
        description: `Analyzed ${data.total_materials} materials - ${data.high_risk_count} high risk`,
      });
    } catch (error) {
      toast({
        title: t('common.assessmentFailed'),
        description: "Could not connect to AEGIS API",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const getRiskColor = (category: string) => {
    switch (category) {
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

  return (
    <div className="min-h-screen bg-gray-50">
      <ChemoursHeader title={t('portfolio.title')} subtitle={t('portfolio.subtitle')} helpContent={helpContent.portfolio} />

      <main className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Input Panel */}
          <Card className="bg-white border-gray-200 shadow-sm">
            <CardHeader>
              <CardTitle className="text-chemours-dark">{t('portfolio.productPortfolio')}</CardTitle>
              <CardDescription>{t('portfolio.addMaterialsToAssess')}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Current Items */}
              <div className="space-y-2">
                {items.map((item, i) => (
                  <div key={i} className="flex items-center justify-between p-2 bg-gray-50 rounded-lg">
                    <div>
                      <span className="text-chemours-dark font-medium">{item.material}</span>
                      <span className="text-gray-500 text-sm ml-2">({item.volume_lbs.toLocaleString()} lbs)</span>
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => removeItem(i)}>
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </div>
                ))}
              </div>

              {/* Add New */}
              <div className="border-t border-gray-200 pt-4">
                <Label className="text-gray-700">{t('portfolio.addMaterial')}</Label>
                <div className="flex gap-2 mt-2">
                  <Input
                    value={newMaterial}
                    onChange={(e) => setNewMaterial(e.target.value.toUpperCase())}
                    placeholder="Material"
                    className="bg-white border-gray-300"
                  />
                  <Input
                    type="number"
                    value={newVolume}
                    onChange={(e) => setNewVolume(parseInt(e.target.value) || 0)}
                    placeholder="Volume"
                    className="w-28 bg-white border-gray-300"
                  />
                  <Button onClick={addItem} size="icon" className="bg-chemours-red hover:bg-chemours-red/90">
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              {/* Quick Add */}
              <div>
                <Label className="text-gray-600 text-sm">{t('portfolio.quickAdd')}</Label>
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
                className="w-full bg-gradient-to-r from-chemours-red to-chemours-orange hover:opacity-90 text-white"
              >
                {isLoading ? (
                  <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> {t('common.assessing')}</>
                ) : (
                  <><PieChart className="mr-2 h-4 w-4" /> {t('portfolio.assessPortfolio')}</>
                )}
              </Button>
            </CardContent>
          </Card>

          {/* Results Panel */}
          <div className="lg:col-span-2 space-y-6">
            {assessment ? (
              <>
                {/* Summary Cards */}
                <div className="grid grid-cols-3 gap-4">
                  <Card className="bg-white border-gray-200 shadow-sm">
                    <CardContent className="pt-6 text-center">
                      <Package className="h-8 w-8 text-chemours-red mx-auto mb-2" />
                      <p className="text-3xl font-bold text-chemours-dark">{assessment.total_materials}</p>
                      <p className="text-sm text-gray-500">{t('portfolio.materials')}</p>
                    </CardContent>
                  </Card>
                  <Card className="bg-white border-gray-200 shadow-sm">
                    <CardContent className="pt-6 text-center">
                      <AlertTriangle className="h-8 w-8 text-red-500 mx-auto mb-2" />
                      <p className="text-3xl font-bold text-red-500">{assessment.high_risk_count}</p>
                      <p className="text-sm text-gray-500">{t('portfolio.highRisk')}</p>
                    </CardContent>
                  </Card>
                  <Card className="bg-white border-gray-200 shadow-sm">
                    <CardContent className="pt-6 text-center">
                      <DollarSign className="h-8 w-8 text-green-500 mx-auto mb-2" />
                      <p className="text-3xl font-bold text-green-600">{formatCurrency(assessment.total_exposure_usd)}</p>
                      <p className="text-sm text-gray-500">{t('portfolio.totalExposure')}</p>
                    </CardContent>
                  </Card>
                </div>

                {/* Results Table */}
                <Card className="bg-white border-gray-200 shadow-sm">
                  <CardHeader>
                    <CardTitle className="text-chemours-dark">{t('portfolio.assessmentResults')}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {/* Risk Category Legend */}
                    <div className="flex items-center gap-4 text-sm text-gray-600 mb-4 pb-4 border-b border-gray-100">
                      <span className="font-medium">Risk Categories:</span>
                      <TooltipProvider>
                        {(Object.keys(RISK_CATEGORY_DEFINITIONS) as Array<keyof typeof RISK_CATEGORY_DEFINITIONS>).map((key) => {
                          const cat = RISK_CATEGORY_DEFINITIONS[key];
                          return (
                            <Tooltip key={key}>
                              <TooltipTrigger asChild>
                                <div className="flex items-center gap-1.5 cursor-help">
                                  <Badge className={`${cat.color} text-white text-xs`}>{key}</Badge>
                                </div>
                              </TooltipTrigger>
                              <TooltipContent side="bottom" className="max-w-xs p-3">
                                <p className="font-semibold mb-1">{cat.label} Risk</p>
                                <p className="text-sm text-muted-foreground">{cat.description}</p>
                              </TooltipContent>
                            </Tooltip>
                          );
                        })}
                      </TooltipProvider>
                    </div>
                    <Table>
                      <TableHeader>
                        <TableRow className="border-gray-200">
                          <TableHead className="text-gray-600">{t('portfolio.tableHeaders.material')}</TableHead>
                          <TableHead className="text-gray-600">{t('portfolio.tableHeaders.riskScore')}</TableHead>
                          <TableHead className="text-gray-600">
                            <span className="flex items-center gap-1">
                              {t('portfolio.tableHeaders.category')}
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Info className="h-4 w-4 text-gray-400 cursor-help" />
                                  </TooltipTrigger>
                                  <TooltipContent side="bottom" className="max-w-sm p-3">
                                    <p className="font-semibold mb-2">Risk Category Definitions</p>
                                    <div className="space-y-2 text-sm">
                                      <div><span className="font-medium text-green-600">LOW:</span> <span className="text-muted-foreground">{RISK_CATEGORY_DEFINITIONS.LOW.description}</span></div>
                                      <div><span className="font-medium text-yellow-600">MEDIUM:</span> <span className="text-muted-foreground">{RISK_CATEGORY_DEFINITIONS.MEDIUM.description}</span></div>
                                      <div><span className="font-medium text-red-600">HIGH:</span> <span className="text-muted-foreground">{RISK_CATEGORY_DEFINITIONS.HIGH.description}</span></div>
                                    </div>
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            </span>
                          </TableHead>
                          <TableHead className="text-gray-600">{t('portfolio.tableHeaders.pfasProducts')}</TableHead>
                          <TableHead className="text-gray-600">{t('portfolio.tableHeaders.regFlags')}</TableHead>
                          <TableHead className="text-gray-600">{t('portfolio.tableHeaders.litigationPercent')}</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {assessment.results.map((r, i) => (
                          <TableRow key={i} className="border-gray-200">
                            <TableCell className="font-medium text-chemours-dark">{r.material}</TableCell>
                            <TableCell>
                              <div className="flex items-center gap-2">
                                <Progress value={r.risk_score} className="w-16" />
                                <span className="text-gray-600 text-sm">{r.risk_score.toFixed(0)}</span>
                              </div>
                            </TableCell>
                            <TableCell>
                              <Badge className={getRiskColor(r.risk_category)}>{r.risk_category}</Badge>
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
                    <CardTitle className="text-chemours-dark">{t('portfolio.executiveSummary')}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <pre className="text-gray-600 whitespace-pre-wrap font-mono text-sm bg-gray-50 p-4 rounded-lg border border-gray-200">
                      {assessment.executive_summary}
                    </pre>
                  </CardContent>
                </Card>

                {/* Methodology Note */}
                <p className="text-xs text-gray-400 text-center mt-4">
                  {assessment.methodology_note || "Risk assessments incorporate regulatory status, compound characteristics, and historical patterns. Site-specific factors may affect actual values."}
                </p>
              </>
            ) : (
              <Card className="bg-white border-gray-200 shadow-sm">
                <CardContent className="py-16 text-center">
                  <Package className="h-16 w-16 mx-auto mb-4 text-gray-400" />
                  <h3 className="text-xl font-semibold text-gray-600 mb-2">{t('portfolio.portfolioAssessment')}</h3>
                  <p className="text-gray-500 max-w-md mx-auto">
                    {t('portfolio.emptyStateDescription')}
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default PortfolioAssessment;
