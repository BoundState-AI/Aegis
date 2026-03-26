import { useState, useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { Loader2, Download, FlaskConical, Thermometer, Wind, Clock, AlertTriangle, ExternalLink } from "lucide-react";
import AnalysisResults from "@/components/pfas/AnalysisResults";
import DaikinHeader from "@/components/layout/DaikinHeader";
import { PageChatProvider } from "@/components/chat/PageChatProvider";
import { useHelpContent } from "@/config/helpContent";
import { apiPost, apiPostBlob } from "@/lib/apiClient";
import { createAnalysisAnswerSurfaceHint } from "@/lib/chat/surfaces";
import { analyzeResponseSchema, type AnalyzeResponse } from "@/lib/apiSchemas";

const COMMON_MATERIALS = [
  "FEP",
  "PTFE",
  "PFA",
  "ETFE",
  "PVDF",
  "Opteon YF",
  "R-134a",
];

const PFASAnalysis = () => {
  const { t, i18n } = useTranslation();
  const { toast } = useToast();
  const helpContent = useHelpContent();
  const currentLanguage = i18n.resolvedLanguage ?? i18n.language ?? "en";
  const [results, setResults] = useState<AnalyzeResponse | null>(null);

  const [formData, setFormData] = useState({
    material: "PTFE",
    temperature: 385,
    atmosphere: "air",
    time: 6
  });

  const analyzeMutation = useMutation({
    mutationFn: () =>
      apiPost("/api/pfas/evaluate", analyzeResponseSchema, {
        source_compound: formData.material,
        locale: currentLanguage,
        context: {
          incident_temp_c: formData.temperature,
          atmosphere: formData.atmosphere,
          residence_time_s: formData.time * 3600,
        },
      }),
    onSuccess: (data) => {
      setResults(data);
      toast({
        title: t('common.analysisComplete'),
        description: t('analysis.evaluated', { compound: data.compound_evaluated, count: data.pfas_findings.length }),
      });
    },
    onError: () => {
      toast({
        title: t('common.analysisFailed'),
        description: t('common.couldNotConnect'),
        variant: "destructive",
      });
    },
  });

  // Auto-analyze on mount and when locale changes so backend-generated copy follows the active language.
  useEffect(() => {
    void handleAnalyze();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentLanguage]);

  const handleAnalyze = async () => {
    if (!formData.material) {
      toast({
        title: t('analysis.missingMaterial'),
        description: t('analysis.selectMaterialToAnalyze'),
        variant: "destructive"
      });
      return;
    }

    await analyzeMutation.mutateAsync();
  };

  const handleDownloadPDF = async () => {
    try {
      const blob = await apiPostBlob("/api/pfas/analyze/pdf", {
        material: formData.material,
        conditions: {
          temperature: formData.temperature,
          atmosphere: formData.atmosphere,
          time_hours: formData.time,
        },
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `pfas-analysis-${formData.material}-${Date.now()}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);

      toast({
        title: t('common.reportDownloaded'),
        description: t('analysis.pdfGenerated')
      });
    } catch {
      toast({
        title: t('common.downloadFailed'),
        description: t('analysis.pdfFailed'),
        variant: "destructive"
      });
    }
  };

  const isAnalyzing = analyzeMutation.isPending;
  const chatSurfaceHint = useMemo(() => createAnalysisAnswerSurfaceHint({
    locale: currentLanguage,
    starterQuestions: [
      t("chat.starters.analysis.findings"),
      t("chat.starters.analysis.inputs"),
      t("chat.starters.analysis.support"),
    ],
    material: formData.material,
    temperatureC: formData.temperature,
    atmosphere: formData.atmosphere,
    timeHours: formData.time,
    findingsCount: results?.pfas_findings.length ?? 0,
    summary: results?.summary ?? null,
    visibleFindings: (results?.pfas_findings || []).slice(0, 12).map((finding) => ({
      product: finding.product,
      screening_classification: finding.screening_classification,
      regulatory_flags_count: finding.regulatory_flags.length,
      evidence_strength: finding.evidence_strength ?? null,
    })),
  }), [currentLanguage, formData, results, t]);

  const getTempColor = (temp: number) => {
    if (temp >= 400) return "text-red-400";
    if (temp >= 300) return "text-orange-400";
    if (temp >= 200) return "text-yellow-400";
    return "text-green-400";
  };

  const getAtmosphereLabel = (atmosphere: string) => {
    const key = `analysis.atmosphereOptions.${atmosphere}`;
    const translated = t(key);
    return translated === key ? atmosphere : translated;
  };

  return (
    <PageChatProvider
      pageId="analysis"
      pageLabel={t("analysis.title")}
      surfaceHint={chatSurfaceHint}
    >
    <div className="min-h-screen bg-gray-50">
      <DaikinHeader title={t('analysis.title')} subtitle={t('analysis.subtitle')} helpContent={helpContent.analysis} />

      <main className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Input Panel */}
          <Card className="bg-white border-gray-200 shadow-sm">
            <CardHeader>
              <CardTitle className="text-daikin-dark">{t('analysis.analysisParameters')}</CardTitle>
              <CardDescription>{t('analysis.configureDegradationConditions')}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Material Selection */}
              <div>
                <Label className="text-gray-700">{t('common.material')}</Label>
                <Select value={formData.material} onValueChange={(val) => setFormData({ ...formData, material: val })}>
                  <SelectTrigger className="mt-2 bg-white border-gray-300">
                    <SelectValue placeholder={t('analysis.selectMaterial')} />
                  </SelectTrigger>
                  <SelectContent>
                    {COMMON_MATERIALS.map((mat) => (
                      <SelectItem key={mat} value={mat}>{mat}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Temperature */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <Label className="text-gray-700 flex items-center gap-2">
                    <Thermometer className="h-4 w-4" />
                    {t('common.temperature')}
                  </Label>
                  <span className={`text-lg font-bold ${getTempColor(formData.temperature)}`}>
                    {formData.temperature}°C
                  </span>
                </div>
                <Slider
                  min={0}
                  max={500}
                  step={5}
                  value={[formData.temperature]}
                  onValueChange={(val) => setFormData({ ...formData, temperature: val[0] })}
                  className="mt-2"
                />
                <div className="flex justify-between text-xs text-gray-400 mt-1">
                  <span>0°C</span>
                  <span>250°C</span>
                  <span>500°C</span>
                </div>
                {formData.temperature >= 400 && (
                  <div className="flex items-center gap-2 mt-2 text-red-500 text-sm">
                    <AlertTriangle className="h-4 w-4" />
                    {t('analysis.highDegradationRisk')}
                  </div>
                )}
              </div>

              {/* Atmosphere */}
              <div>
                <Label className="text-gray-700 flex items-center gap-2">
                  <Wind className="h-4 w-4" />
                  {t('common.atmosphere')}
                </Label>
                <Select value={formData.atmosphere} onValueChange={(val) => setFormData({ ...formData, atmosphere: val })}>
                  <SelectTrigger className="mt-2 bg-white border-gray-300">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="air">{t('analysis.atmosphereOptions.air')}</SelectItem>
                    <SelectItem value="inert">{t('analysis.atmosphereOptions.inert')}</SelectItem>
                    <SelectItem value="nitrogen">{t('analysis.atmosphereOptions.nitrogen')}</SelectItem>
                    <SelectItem value="oxygen">{t('analysis.atmosphereOptions.oxygen')}</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Exposure Time */}
              <div>
                <Label className="text-gray-700 flex items-center gap-2">
                  <Clock className="h-4 w-4" />
                  {t('analysis.exposureTime')}
                </Label>
                <Input
                  type="number"
                  min="0"
                  step="0.5"
                  value={formData.time}
                  onChange={(e) => setFormData({ ...formData, time: parseFloat(e.target.value) || 0 })}
                  className="mt-2 bg-white border-gray-300"
                />
              </div>

              {/* Analyze Button */}
              <Button
                onClick={handleAnalyze}
                disabled={isAnalyzing || !formData.material}
                className="w-full bg-gradient-to-r from-daikin-blue to-daikin-accent hover:opacity-90 text-white"
              >
                {isAnalyzing ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {t('common.analyzing')}
                  </>
                ) : (
                  <>
                    <FlaskConical className="mr-2 h-4 w-4" />
                    {t('analysis.runAnalysis')}
                  </>
                )}
              </Button>

              {results && (
                <Button
                  onClick={handleDownloadPDF}
                  variant="outline"
                  className="w-full border-gray-300 text-gray-600 hover:bg-gray-100"
                >
                  <Download className="mr-2 h-4 w-4" />
                  {t('analysis.downloadPdfReport')}
                </Button>
              )}
            </CardContent>
          </Card>

          {/* Results Panel */}
          <div className="lg:col-span-2 space-y-6">
            {results ? (
              <>
                {/* Summary Card */}
                <Card className="bg-white border-gray-200 shadow-sm">
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-daikin-dark">{results.compound_evaluated} {t('analysis.analysisResults')}</CardTitle>
                      <Badge className="bg-gradient-to-r from-daikin-blue to-daikin-accent text-white">{results.pfas_findings.length} {t('common.pathways')}</Badge>
                    </div>
                    <CardDescription>{results.summary}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-3 gap-4 text-center">
                      <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                        <p className="text-2xl font-bold text-daikin-dark">{formData.temperature}°C</p>
                        <p className="text-sm text-gray-500">{t('common.temperature')}</p>
                      </div>
                      <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                        <p className="text-2xl font-bold text-daikin-dark">{getAtmosphereLabel(formData.atmosphere)}</p>
                        <p className="text-sm text-gray-500">{t('common.atmosphere')}</p>
                      </div>
                      <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                        <p className="text-2xl font-bold text-daikin-dark">{formData.time}{t("analysis.hourShort")}</p>
                        <p className="text-sm text-gray-500">{t('common.exposure')}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Detailed Results */}
                <Card className="bg-white border-gray-200 shadow-sm">
                  <CardHeader>
                    <CardTitle className="text-daikin-dark">{t('analysis.pfasFindings')}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {results.pfas_findings.map((finding, i) => (
                        <div key={i} className="p-4 bg-gray-50 rounded-lg border-l-4 border-daikin-blue">
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-medium text-daikin-dark text-lg">{finding.product}</span>
                            <Badge variant="outline" className="border-daikin-blue text-daikin-blue">
                              {(finding.overall_confidence * 100).toFixed(0)}% {t('common.confidence')}
                            </Badge>
                          </div>

                          {finding.pathway.length > 0 && (
                            <div className="flex items-center gap-2 mb-2 text-sm">
                              <span className="text-gray-500">{t('analysis.pathway')}</span>
                              <div className="flex items-center gap-1">
                                {finding.pathway.map((step, j) => (
                                  <span key={j} className="flex items-center">
                                    <span className="text-gray-700">{step}</span>
                                    {j < finding.pathway.length - 1 && (
                                      <span className="text-gray-400 mx-1">→</span>
                                    )}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}

                          <div className="flex flex-wrap gap-2 mt-2">
                            {finding.regulatory_flags.map((flag, j) => (
                              <Badge key={j} className="bg-red-100 text-red-700 border border-red-300">
                                {flag}
                              </Badge>
                            ))}
                            {finding.litigation_flag && (
                              <Badge className="bg-orange-100 text-orange-700 border border-orange-300">
                                {t('analysis.litigationRisk')}
                              </Badge>
                            )}
                            {finding.is_short_chain_pfas && (
                              <Badge className="bg-blue-100 text-blue-700 border border-blue-300">
                                {t('analysis.shortChainPfas')}
                              </Badge>
                            )}
                          </div>

                          {/* Source DOI Links */}
                          {finding.evidence_refs?.length > 0 && finding.evidence_refs.some(e => e.doi) && (
                            <div className="flex items-center gap-2 flex-wrap text-sm mt-3 pt-3 border-t border-gray-200">
                              <span className="text-gray-500 font-medium">{t('common.sources')}:</span>
                              {[...new Set(finding.evidence_refs.map(e => e.doi).filter((doi): doi is string => !!doi))].slice(0, 3).map((doi, idx) => (
                                <a
                                  key={idx}
                                  href={`https://doi.org/${doi}`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-daikin-blue/10 text-daikin-blue hover:bg-daikin-blue/20 transition-colors"
                                >
                                  <ExternalLink className="h-3 w-3" />
                                  <span className="font-mono text-xs">{doi}</span>
                                </a>
                              ))}
                              {[...new Set(finding.evidence_refs.map(e => e.doi).filter((doi): doi is string => !!doi))].length > 3 && (
                                <span className="text-xs text-gray-400">
                                  {t("analysis.moreSources", {
                                    count: [...new Set(finding.evidence_refs.map(e => e.doi).filter((doi): doi is string => !!doi))].length - 3,
                                  })}
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Disclaimer */}
                <Card className="bg-yellow-50 border-yellow-300">
                  <CardContent className="py-4">
                    <p className="text-yellow-700 text-sm">{results.disclaimer}</p>
                  </CardContent>
                </Card>
              </>
            ) : (
              <Card className="bg-white border-gray-200 shadow-sm">
                <CardContent className="py-16 text-center">
                  <FlaskConical className="h-16 w-16 mx-auto mb-4 text-gray-400" />
                  <h3 className="text-xl font-semibold text-gray-600 mb-2">{t('analysis.title')}</h3>
                  <p className="text-gray-500 max-w-md mx-auto">
                    {t('analysis.emptyStateDescription')}
                  </p>
                  <div className="flex justify-center gap-6 mt-6">
                    <div className="text-center">
                      <p className="text-2xl font-bold text-daikin-blue">6,141</p>
                      <p className="text-sm text-gray-500">{t('analysis.transformations')}</p>
                    </div>
                    <div className="text-center">
                      <p className="text-2xl font-bold text-daikin-blue">228</p>
                      <p className="text-sm text-gray-500">{t('analysis.papers')}</p>
                    </div>
                    <div className="text-center">
                      <p className="text-2xl font-bold text-daikin-blue">216</p>
                      <p className="text-sm text-gray-500">{t('analysis.compounds')}</p>
                    </div>
                  </div>
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

export default PFASAnalysis;
