import { useState, useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { Loader2, FileText, Download, Lock, ChevronRight } from "lucide-react";
import DaikinHeader from "@/components/layout/DaikinHeader";
import { PageChatProvider } from "@/components/chat/PageChatProvider";
import { useHelpContent } from "@/config/helpContent";
import { apiGet } from "@/lib/apiClient";
import { createReportsAnswerSurfaceHint } from "@/lib/chat/surfaces";
import { executiveReportSchema, type ExecutiveReport } from "@/lib/apiSchemas";
import { TermWithTooltip } from "@/components/ui/term-with-tooltip";

const ExecutiveReports = () => {
  const { t } = useTranslation();
  const { toast } = useToast();
  const helpContent = useHelpContent();
  const [material, setMaterial] = useState("PTFE");
  const [includeLitigation, setIncludeLitigation] = useState(true);
  const [includeRegulatory, setIncludeRegulatory] = useState(true);
  const [report, setReport] = useState<ExecutiveReport | null>(null);

  const normalizeEnumKey = (value: string) => value.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_");

  const getReportTitle = (reportValue: ExecutiveReport) =>
    t("reports.aegisRiskAssessmentTitle", { material: reportValue.material });

  const getReportClassificationLabel = (value: string) => {
    const key = `reports.classificationLabels.${normalizeEnumKey(value)}`;
    const translated = t(key);
    return translated === key ? value : translated;
  };

  const getSectionTitle = (value: string) => {
    const key = `reports.sectionTitles.${normalizeEnumKey(value)}`;
    const translated = t(key);
    return translated === key ? value : translated;
  };

  const generateMutation = useMutation({
    mutationFn: async () => {
      const params = new URLSearchParams({
        material,
        include_litigation: includeLitigation.toString(),
        include_regulatory: includeRegulatory.toString(),
      });
      return apiGet(`/api/v1/reports/executive?${params.toString()}`, executiveReportSchema);
    },
    onSuccess: (data) => {
      setReport(data);
      toast({
        title: t('common.reportGenerated'),
        description: t('reports.reportReady', { material: data.material }),
      });
    },
    onError: () => {
      toast({
        title: t('common.reportFailed'),
        description: t('common.couldNotGenerate'),
        variant: "destructive",
      });
    },
  });

  // Auto-generate PTFE report on mount
  useEffect(() => {
    void handleGenerate();
    // Intentionally run once on mount to pre-populate default report.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleGenerate = async () => {
    await generateMutation.mutateAsync();
  };

  const handleDownload = () => {
    if (!report) return;

    // Create text content
    const reportTitle = getReportTitle(report);
    let content = `${reportTitle}\n`;
    content += `${"=".repeat(reportTitle.length)}\n\n`;
    content += `${t('reports.generated')} ${new Date(report.generated).toLocaleString()}\n`;
    content += `${t('reports.classification')}: ${getReportClassificationLabel(report.classification)}\n\n`;

    report.sections.forEach((section) => {
      const sectionTitle = getSectionTitle(section.title);
      content += `\n${sectionTitle}\n`;
      content += `${"-".repeat(sectionTitle.length)}\n`;
      content += `${section.content}\n`;

      if (section.flags && section.flags.length > 0) {
        content += `\n${t('reports.regulatoryFlags')}\n`;
        section.flags.forEach((f) => (content += `  - ${f}\n`));
      }

      if (section.similar_cases && section.similar_cases.length > 0) {
        content += `\n${t('reports.similarCases')}\n`;
        section.similar_cases.forEach((c) => (content += `  - ${c}\n`));
      }
    });

    // Download
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `AEGIS-Report-${report.material}-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);

    toast({
      title: t('common.reportDownloaded'),
      description: t('reports.savedToDownloads'),
    });
  };

  const isLoading = generateMutation.isPending;
  const chatSurfaceHint = useMemo(() => createReportsAnswerSurfaceHint({
    material,
    includeLitigation,
    includeRegulatory,
    generated: report?.generated ?? null,
    classification: report?.classification ?? null,
    visibleSections: (report?.sections || []).slice(0, 12).map((section) => ({
      title: section.title,
      flags_count: section.flags?.length ?? 0,
      similar_cases_count: section.similar_cases?.length ?? 0,
      product_count: Array.isArray(section.data?.products) ? section.data.products.length : 0,
    })),
  }), [includeLitigation, includeRegulatory, material, report]);

  return (
    <PageChatProvider
      pageId="reports"
      pageLabel={t("reports.title")}
      surfaceHint={chatSurfaceHint}
    >
    <div className="min-h-screen bg-gray-50">
      <DaikinHeader title={t('reports.title')} subtitle={t('reports.subtitle')} helpContent={helpContent.reports} />

      <main className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Input Panel */}
          <Card className="bg-white border-gray-200 shadow-sm">
            <CardHeader>
              <CardTitle className="text-daikin-dark">{t('reports.reportConfiguration')}</CardTitle>
              <CardDescription>{t('reports.configureParameters')}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label className="text-gray-700">{t('common.material')}</Label>
                <Input
                  value={material}
                  onChange={(e) => setMaterial(e.target.value.toUpperCase())}
                  placeholder={t('common.exampleMaterials')}
                  className="bg-white border-gray-300"
                />
              </div>

              <div className="flex items-center justify-between">
                <Label className="text-gray-700">{t('reports.includeLitigationAnalysis')}</Label>
                <Switch checked={includeLitigation} onCheckedChange={setIncludeLitigation} />
              </div>

              <div className="flex items-center justify-between">
                <Label className="text-gray-700">{t('reports.includeRegulatoryStatus')}</Label>
                <Switch checked={includeRegulatory} onCheckedChange={setIncludeRegulatory} />
              </div>

              <Button
                onClick={handleGenerate}
                disabled={isLoading || !material}
                className="w-full bg-gradient-to-r from-daikin-blue to-daikin-accent hover:opacity-90 text-white"
              >
                {isLoading ? (
                  <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> {t('common.generating')}</>
                ) : (
                  <><FileText className="mr-2 h-4 w-4" /> {t('reports.generateReport')}</>
                )}
              </Button>
            </CardContent>
          </Card>

          {/* Report Panel */}
          <div className="lg:col-span-2 space-y-6">
            {report ? (
              <>
                {/* Report Header */}
                <Card className="bg-white border-gray-200 shadow-sm">
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div>
                        <CardTitle className="text-daikin-dark">{getReportTitle(report)}</CardTitle>
                        <CardDescription>
                          {t('reports.generated')} {new Date(report.generated).toLocaleString()}
                        </CardDescription>
                      </div>
                      <Button variant="outline" onClick={handleDownload} className="border-gray-300 text-gray-600 hover:bg-gray-100">
                        <Download className="mr-2 h-4 w-4" /> {t('common.download')}
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center gap-2 p-3 bg-red-50 rounded-lg border border-red-200">
                      <Lock className="h-5 w-5 text-red-600" />
                      <span className="text-red-600 font-medium">{getReportClassificationLabel(report.classification)}</span>
                    </div>
                  </CardContent>
                </Card>

                {/* Report Sections */}
                {report.sections.map((section, i) => (
                  <Card key={i} className="bg-white border-gray-200 shadow-sm">
                    <CardHeader>
                      <CardTitle className="text-daikin-dark flex items-center gap-2">
                        <ChevronRight className="h-5 w-5 text-daikin-accent" />
                        {getSectionTitle(section.title)}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <p className="text-gray-600 whitespace-pre-wrap">{section.content}</p>

                      {section.data?.products && (
                        <div>
                          <p className="text-sm text-gray-500 mb-2">
                            <TermWithTooltip explanationKey="tooltips.degradationProducts">
                              {t('reports.degradationProducts')}
                            </TermWithTooltip>
                          </p>
                          <div className="flex flex-wrap gap-2">
                            {section.data.products.map((p: string) => (
                              <Badge key={p} variant="outline" className="border-daikin-accent text-daikin-accent">{p}</Badge>
                            ))}
                          </div>
                        </div>
                      )}

                      {section.flags && section.flags.length > 0 && (
                        <div className="p-3 bg-daikin-blue/5 rounded-lg border border-daikin-blue/20">
                          <p className="text-sm text-daikin-accent mb-2 font-medium">{t('reports.regulatoryFlags')}</p>
                          <ul className="space-y-1">
                            {section.flags.map((f, j) => (
                              <li key={j} className="text-gray-600 text-sm flex items-start gap-2">
                                <span className="text-daikin-blue">•</span>
                                {f}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {section.similar_cases && section.similar_cases.length > 0 && (
                        <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                          <p className="text-sm text-blue-700 mb-2 font-medium">{t('reports.similarCases')}</p>
                          <div className="flex flex-wrap gap-2">
                            {section.similar_cases.map((c) => (
                              <Badge key={c} className="bg-blue-600 text-white">{c}</Badge>
                            ))}
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </>
            ) : (
              <Card className="bg-white border-gray-200 shadow-sm">
                <CardContent className="py-16 text-center">
                  <FileText className="h-16 w-16 mx-auto mb-4 text-gray-400" />
                  <h3 className="text-xl font-semibold text-gray-600 mb-2">{t('reports.title')}</h3>
                  <p className="text-gray-500 max-w-md mx-auto">
                    {t('reports.subtitle')}
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

export default ExecutiveReports;
