import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/hooks/use-toast";
import { Loader2, Shield, AlertTriangle, CheckCircle, XCircle, Calendar, Globe, Zap } from "lucide-react";
import DaikinHeader from "@/components/layout/DaikinHeader";
import { useHelpContent } from "@/config/helpContent";
import { TermWithTooltip } from "@/components/ui/term-with-tooltip";
import Intelligence, { type IntelligenceTabKey } from "./Intelligence";
import { apiGet } from "@/lib/apiClient";
import { cascadeSchema, regulatoryCheckSchema, type CascadeResponse, type RegulatoryCheck } from "@/lib/apiSchemas";

type RegulatorySubview = "landscape" | "signals" | "resolver" | "queue";

const mapViewParam = (value: string | null): RegulatorySubview => {
  if (value === "signals" || value === "resolver" || value === "queue") {
    return value;
  }
  return "landscape";
};

const RegulatoryCompliance = () => {
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const { toast } = useToast();
  const helpContent = useHelpContent();
  const [subview, setSubview] = useState<RegulatorySubview>(() => mapViewParam(searchParams.get("view")));
  const [material, setMaterial] = useState("PTFE");
  const [includeDegradation, setIncludeDegradation] = useState(true);
  const [checkResult, setCheckResult] = useState<RegulatoryCheck | null>(null);
  const [cascade, setCascade] = useState<CascadeResponse | null>(null);
  const [forecastYear, setForecastYear] = useState(2025);

  // Auto-load PTFE compliance on mount
  useEffect(() => {
    void handleCheck();
    // Intentionally run once on mount to pre-populate default compliance view.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const fromUrl = mapViewParam(searchParams.get("view"));
    if (fromUrl !== subview) {
      setSubview(fromUrl);
    }
  }, [searchParams, subview]);

  const selectSubview = (next: RegulatorySubview) => {
    setSubview(next);
    const params = new URLSearchParams(searchParams);
    if (next === "landscape") {
      params.delete("view");
    } else {
      params.set("view", next);
    }
    setSearchParams(params, { replace: true });
  };

  const checkMutation = useMutation({
    mutationFn: async (params: { material: string; includeDegradation: boolean; forecastYear: number }) => {
      const check = await apiGet(
        `/api/v1/regulatory/check?material=${encodeURIComponent(params.material)}&include_degradation=${params.includeDegradation}`,
        regulatoryCheckSchema,
      );
      const forecast = await apiGet(
        `/api/v1/regulatory/cascade?material=${encodeURIComponent(params.material)}&forecast_year=${params.forecastYear}`,
        cascadeSchema,
      );
      return { check, forecast };
    },
    onSuccess: ({ check, forecast }) => {
      setCheckResult(check);
      setCascade(forecast);
      toast({
        title: t("common.complianceCheckComplete"),
        description: t("regulatory.riskAcross", {
          material: check.material,
          risk: getRiskLabel(check.overall_risk),
          count: check.frameworks_checked,
        }),
      });
    },
    onError: () => {
      toast({
        title: t("common.checkFailed"),
        description: t("common.couldNotConnect"),
        variant: "destructive",
      });
    },
  });

  const handleCheck = async () => {
    await checkMutation.mutateAsync({
      material,
      includeDegradation,
      forecastYear,
    });
  };

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case "HIGH": return "bg-red-500";
      case "MEDIUM": return "bg-yellow-500";
      case "LOW": return "bg-blue-500";
      case "COMPLIANT": return "bg-green-500";
      default: return "bg-gray-500";
    }
  };

  const getStatusIcon = (status: string) => {
    if (["banned", "POP"].includes(status)) return <XCircle className="h-4 w-4 text-red-500" />;
    if (["regulated", "restricted"].includes(status)) return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
    return <CheckCircle className="h-4 w-4 text-green-500" />;
  };

  const getRegulatoryStageStyle = (stage: string) => {
    switch (stage) {
      case "enacted": return "bg-red-600 text-white";
      case "final_pending": return "bg-orange-500 text-white";
      case "proposed": return "bg-yellow-500 text-black";
      case "under_consideration": return "bg-blue-500 text-white";
      case "monitoring": return "bg-gray-500 text-white";
      default: return "bg-gray-400 text-white";
    }
  };

  const getRegulatoryStageLabel = (stage: string) => {
    switch (stage) {
      case "enacted": return t("regulatory.regulatoryStages.enacted");
      case "final_pending": return t("regulatory.regulatoryStages.finalPending");
      case "proposed": return t("regulatory.regulatoryStages.proposed");
      case "under_consideration": return t("regulatory.regulatoryStages.underConsideration");
      case "monitoring": return t("regulatory.regulatoryStages.monitoring");
      default: return stage.toUpperCase();
    }
  };

  const getRiskLabel = (risk: string) => {
    switch (risk.toUpperCase()) {
      case "HIGH": return t("regulatory.riskLabels.high");
      case "MEDIUM": return t("regulatory.riskLabels.medium");
      case "LOW": return t("regulatory.riskLabels.low");
      case "COMPLIANT": return t("regulatory.riskLabels.compliant");
      default: return risk;
    }
  };

  const getStatusLabel = (status: string) => {
    const normalized = status.trim().toLowerCase();
    const labels: Record<string, string> = {
      banned: t("regulatory.statusLabels.banned"),
      pop: t("regulatory.statusLabels.pop"),
      regulated: t("regulatory.statusLabels.regulated"),
      restricted: t("regulatory.statusLabels.restricted"),
      enforceable: t("regulatory.statusLabels.enforceable"),
      advisory: t("regulatory.statusLabels.advisory"),
      monitored: t("regulatory.statusLabels.monitored"),
      monitoring: t("regulatory.statusLabels.monitoring"),
      proposed: t("regulatory.statusLabels.proposed"),
      consultation: t("regulatory.statusLabels.consultation"),
      enacted: t("regulatory.statusLabels.enacted"),
      compliant: t("regulatory.statusLabels.compliant"),
    };
    return labels[normalized] || status.toUpperCase();
  };

  const isApacJurisdiction = (framework: string) =>
    /japan|korea|south korea|china|australia|singapore|taiwan|india|apac/i.test(framework);

  const getApacConfidenceBadgeClass = (confidence: number) => {
    if (confidence >= 0.9) return "bg-green-100 text-green-700 border-green-300";
    if (confidence >= 0.7) return "bg-yellow-100 text-yellow-700 border-yellow-300";
    return "bg-red-100 text-red-700 border-red-300";
  };

  const intelligenceTabBySubview: Record<Exclude<RegulatorySubview, "landscape">, IntelligenceTabKey> = {
    signals: "signals",
    resolver: "resolver",
    queue: "queue",
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <DaikinHeader title={t('regulatory.title')} subtitle={t('regulatory.subtitle')} helpContent={helpContent.regulatory} />

      <main className="container mx-auto px-4 py-8">
        <div className="mb-6 flex flex-wrap gap-2">
          <Button
            size="sm"
            variant={subview === "landscape" ? "default" : "outline"}
            onClick={() => selectSubview("landscape")}
          >
            {t("regulatory.subviews.landscape")}
          </Button>
          <Button
            size="sm"
            variant={subview === "signals" ? "default" : "outline"}
            onClick={() => selectSubview("signals")}
          >
            {t("intelligence.tabs.signals")}
          </Button>
          <Button
            size="sm"
            variant={subview === "resolver" ? "default" : "outline"}
            onClick={() => selectSubview("resolver")}
          >
            {t("intelligence.tabs.resolver")}
          </Button>
          <Button
            size="sm"
            variant={subview === "queue" ? "default" : "outline"}
            onClick={() => selectSubview("queue")}
          >
            {t("intelligence.tabs.reviewQueue")}
          </Button>
        </div>

        {subview !== "landscape" ? (
          <Intelligence embedded singleTab={intelligenceTabBySubview[subview]} hideSummaryCards />
        ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Input Panel */}
          <Card className="bg-white border-gray-200 shadow-sm">
            <CardHeader>
              <CardTitle className="text-daikin-dark">{t('regulatory.checkCompliance')}</CardTitle>
              <CardDescription>{t('regulatory.enterMaterial')}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label className="text-gray-700">{t('common.material')}</Label>
                <Input
                  value={material}
                  onChange={(e) => setMaterial(e.target.value.toUpperCase())}
                  placeholder={t("regulatory.materialPlaceholder")}
                  className="bg-white border-gray-300"
                />
              </div>

              <div className="flex items-center justify-between">
                <Label className="text-gray-700">{t('regulatory.includeDegradationProducts')}</Label>
                <Switch checked={includeDegradation} onCheckedChange={setIncludeDegradation} />
              </div>

              <div>
                <Label className="text-gray-700">{t('regulatory.forecastYear')}</Label>
                <Input
                  type="number"
                  value={forecastYear}
                  onChange={(e) => setForecastYear(parseInt(e.target.value) || 2025)}
                  min={2024}
                  max={2030}
                  className="bg-white border-gray-300"
                />
              </div>

                <Button
                  onClick={handleCheck}
                  disabled={checkMutation.isPending || !material}
                  className="w-full bg-gradient-to-r from-daikin-blue to-daikin-accent hover:opacity-90 text-white"
                >
                {checkMutation.isPending ? (
                  <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> {t('common.checking')}</>
                ) : (
                  <><Shield className="mr-2 h-4 w-4" /> {t('regulatory.checkCompliance')}</>
                )}
              </Button>
            </CardContent>
          </Card>

          {/* Results Panel */}
          <div className="lg:col-span-2 space-y-6">
            {checkResult ? (
              <>
                {/* Summary Card */}
                <Card className="bg-white border-gray-200 shadow-sm">
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-daikin-dark">{checkResult.material} {t('regulatory.complianceStatus')}</CardTitle>
                      <Badge className={getRiskColor(checkResult.overall_risk)}>{getRiskLabel(checkResult.overall_risk)}</Badge>
                    </div>
                    <CardDescription>
                      {t("regulatory.screenedAgainst", { count: checkResult.frameworks_checked })}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {checkResult.degradation_products.length > 0 && (
                      <div className="mb-4">
                        <div className="flex items-center gap-2 mb-2">
                          <TermWithTooltip explanationKey="tooltips.degradationProducts" className="text-sm text-gray-500">
                            {t("regulatory.degradationProducts")}
                          </TermWithTooltip>
                          {checkResult.degradation_pathway_count > 0 && (
                            <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium">
                              {t("regulatory.pathwaysFromPapers", {
                                pathways: checkResult.degradation_pathway_count,
                                papers: checkResult.degradation_paper_count,
                              })}
                            </span>
                          )}
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {checkResult.degradation_products.map((p) => (
                            <Badge key={p} variant="outline" className="border-gray-400 text-gray-600">{p}</Badge>
                          ))}
                        </div>
                        {checkResult.degradation_source && (
                          <p className="text-xs text-gray-400 mt-2 italic">{t("regulatory.source")} {checkResult.degradation_source}</p>
                        )}
                        {checkResult.degradation_sample_dois.length > 0 && (
                          <p className="text-xs text-blue-500 mt-1">
                            {t("regulatory.sampleDOIs")} {checkResult.degradation_sample_dois.slice(0, 2).join(", ")}
                          </p>
                        )}
                      </div>
                    )}

                    <div className="grid grid-cols-3 gap-4 text-center">
                      <div className="p-4 bg-red-50 rounded-lg border border-red-200">
                        <XCircle className="h-8 w-8 text-red-500 mx-auto mb-2" />
                        <p className="text-2xl font-bold text-red-600">{checkResult.non_compliant.length}</p>
                        <p className="text-sm text-gray-500">{t('regulatory.nonCompliant')}</p>
                      </div>
                      <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                        <AlertTriangle className="h-8 w-8 text-yellow-500 mx-auto mb-2" />
                        <p className="text-2xl font-bold text-yellow-600">{checkResult.warnings.length}</p>
                        <p className="text-sm text-gray-500">{t('regulatory.warnings')}</p>
                      </div>
                      <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                        <CheckCircle className="h-8 w-8 text-green-500 mx-auto mb-2" />
                        <p className="text-2xl font-bold text-green-600">{checkResult.compliant.length}</p>
                        <p className="text-sm text-gray-500">{t('regulatory.compliant')}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Non-Compliant Details */}
                {checkResult.non_compliant.length > 0 && (
                  <Card className="bg-white border-gray-200 shadow-sm border-l-4 border-l-red-500">
                    <CardHeader>
                      <CardTitle className="text-red-600">{t("regulatory.nonCompliantRegulations")}</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {checkResult.non_compliant.map((reg, i) => (
                          <div key={i} className="flex items-center justify-between p-3 bg-red-50 rounded-lg">
                            <div className="flex items-center gap-3">
                              {getStatusIcon(reg.status)}
                              <div>
                                <p className="font-medium text-daikin-dark">{reg.framework}</p>
                                {isApacJurisdiction(reg.framework) && (
                                  <Badge variant="outline" className="mt-1 text-xs bg-amber-50 text-amber-700 border-amber-200">
                                    {t("regulatory.apac")}
                                  </Badge>
                                )}
                                <p className="text-sm text-gray-500">{reg.notes}</p>
                              </div>
                            </div>
                            <Badge className="bg-red-600">{getStatusLabel(reg.status)}</Badge>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Warnings */}
                {checkResult.warnings.length > 0 && (
                  <Card className="bg-white border-gray-200 shadow-sm border-l-4 border-l-yellow-500">
                    <CardHeader>
                      <CardTitle className="text-yellow-600">{t("regulatory.regulatoryWarnings")}</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {checkResult.warnings.map((reg, i) => (
                          <div key={i} className="flex items-center justify-between p-3 bg-yellow-50 rounded-lg">
                            <div className="flex items-center gap-3">
                              {getStatusIcon(reg.status)}
                              <div>
                                <p className="font-medium text-daikin-dark">{reg.framework}</p>
                                {isApacJurisdiction(reg.framework) && (
                                  <Badge variant="outline" className="mt-1 text-xs bg-amber-50 text-amber-700 border-amber-200">
                                    {t("regulatory.apac")}
                                  </Badge>
                                )}
                                <p className="text-sm text-gray-500">{reg.notes}</p>
                                {reg.limit_ppb && <p className="text-xs text-yellow-600">{t("regulatory.limit")} {reg.limit_ppb} ppb</p>}
                              </div>
                            </div>
                            <Badge className="bg-yellow-600">{getStatusLabel(reg.status)}</Badge>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}

                {(checkResult.apac_assertions?.length ?? 0) > 0 && (
                  <Card className="bg-white border-gray-200 shadow-sm border-l-4 border-l-amber-500">
                    <CardHeader>
                      <CardTitle className="text-amber-700 flex items-center gap-2">
                        <Globe className="h-5 w-5" />
                        {t("regulatory.apacTitle")}
                      </CardTitle>
                      <CardDescription>
                        {t("regulatory.apacAssertionsAcross", {
                          count: checkResult.apac_assertions?.length ?? 0,
                          jurisdictions: checkResult.apac_jurisdiction_count ?? 0,
                        })}
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      {checkResult.fluoropolymer_exposure && (
                        <div className="p-3 rounded-lg border border-amber-200 bg-amber-50 text-sm text-amber-900">
                          <span className="font-semibold">{t("regulatory.fluoropolymerExposure")}</span> {checkResult.fluoropolymer_exposure}
                        </div>
                      )}
                      {(checkResult.apac_assertions ?? []).slice(0, 10).map((item) => (
                        <div key={item.id} className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                          <div className="flex flex-wrap items-center gap-2 mb-1">
                            <span className="font-semibold text-daikin-dark">{item.country}</span>
                            <Badge variant="outline" className="text-xs border-gray-300">{getStatusLabel(item.status)}</Badge>
                            <Badge variant="outline" className={`text-xs ${getApacConfidenceBadgeClass(item.confidence)}`}>
                              {item.confidence.toFixed(2)}
                            </Badge>
                            {item.jerk_signal && (
                              <Badge variant="outline" className="text-xs bg-orange-100 text-orange-700 border-orange-300">
                                <Zap className="h-3 w-3 mr-1" /> {t("regulatory.jerk")}
                              </Badge>
                            )}
                            {item.confidence < 0.7 && (
                              <Badge variant="outline" className="text-xs bg-red-100 text-red-700 border-red-300">
                                {t("regulatory.verificationNeeded")}
                              </Badge>
                            )}
                          </div>
                          <p className="text-sm text-gray-700">{item.assertion}</p>
                          <p className="text-xs text-gray-500 mt-1">
                            {t("regulatory.class")}: {item.compound_class} | {t("regulatory.litigationRelevance")}: {item.litigation_relevance}
                            {item.effective_date ? ` | ${t("regulatory.effective")}: ${item.effective_date}` : ""}
                            {item.threshold_value ? ` | ${t("regulatory.threshold")}: ${item.threshold_value}` : ""}
                          </p>
                        </div>
                      ))}
                    </CardContent>
                  </Card>
                )}

                {/* Future Predictions */}
                {cascade && Object.keys(cascade.predictions).length > 0 && (
                  <Card className="bg-white border-gray-200 shadow-sm">
                    <CardHeader>
                      <CardTitle className="text-daikin-dark flex items-center gap-2">
                        <Calendar className="h-5 w-5 text-daikin-accent" />
                        {cascade.forecast_year} {t("regulatory.regulatoryForecast")}
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {Object.entries(cascade.predictions).map(([key, pred]) => (
                          <div key={key} className="p-3 bg-gray-50 rounded-lg">
                            <div className="flex items-center justify-between mb-2">
                              <span className="font-medium text-daikin-dark">{key.replace(/_/g, " ")}</span>
                              <Badge className={getRegulatoryStageStyle(pred.regulatory_stage)}>
                                {getRegulatoryStageLabel(pred.regulatory_stage)}
                              </Badge>
                            </div>
                            <p className="text-sm text-gray-500">{pred.status}</p>
                            {pred.source && (
                              <p className="text-xs text-gray-400 mt-1 italic">{t("regulatory.source")} {pred.source}</p>
                            )}
                            {pred.affected_products.length > 0 && (
                              <div className="flex gap-1 mt-2">
                                {pred.affected_products.map((p) => (
                                  <Badge key={p} variant="outline" className="text-xs border-gray-400">{p}</Badge>
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                      <p className="mt-4 text-sm text-daikin-blue italic">{cascade.recommendation}</p>
                    </CardContent>
                  </Card>
                )}
              </>
            ) : (
              <Card className="bg-white border-gray-200 shadow-sm">
                <CardContent className="py-16 text-center">
                  <div className="h-16 w-16 mx-auto mb-4 rounded-full bg-gradient-to-r from-daikin-blue to-daikin-accent flex items-center justify-center">
                    <Globe className="h-8 w-8 text-white" />
                  </div>
                  <h3 className="text-xl font-semibold text-daikin-dark mb-2">{t('regulatory.title')}</h3>
                  <p className="text-gray-500 max-w-md mx-auto">
                    {t("regulatory.description")}
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
        )}
      </main>
    </div>
  );
};

export default RegulatoryCompliance;
