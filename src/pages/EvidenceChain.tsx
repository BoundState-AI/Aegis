import { useState, useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/hooks/use-toast";
import { Loader2, BookOpen, Link2, ExternalLink, Database, FileText } from "lucide-react";
import DaikinHeader from "@/components/layout/DaikinHeader";
import { PageChatProvider } from "@/components/chat/PageChatProvider";
import { useHelpContent } from "@/config/helpContent";
import { apiGet } from "@/lib/apiClient";
import { createEvidenceAnswerSurfaceHint } from "@/lib/chat/surfaces";
import {
  evidenceChainSchema,
  evidenceSourceStatsSchema,
  type EvidenceChainResponse,
  type EvidenceSourceStats,
} from "@/lib/apiSchemas";

interface EvidenceItem {
  source: string;
  doi: string | null;
  year: number;
  confidence: number;
  finding: string;
  compound: string;
}

interface EvidenceViewResponse extends EvidenceChainResponse {
  evidence_chain: EvidenceItem[];
}

interface SourceStats extends EvidenceSourceStats {}

const EvidenceChain = () => {
  const { t, i18n } = useTranslation();
  const { toast } = useToast();
  const helpContent = useHelpContent();
  const currentLanguage = i18n.resolvedLanguage ?? i18n.language ?? "en";
  const [material, setMaterial] = useState("PTFE");
  const [maxCitations, setMaxCitations] = useState(20);
  const [evidence, setEvidence] = useState<EvidenceViewResponse | null>(null);

  const sourceStatsQuery = useQuery({
    queryKey: ["evidenceSourceStats"],
    queryFn: () => apiGet("/api/v1/evidence/sources", evidenceSourceStatsSchema),
    staleTime: 60_000,
    retry: 1,
  });

  const evidenceMutation = useMutation({
    mutationFn: () =>
      apiGet(
        `/api/v1/evidence/chain?material=${encodeURIComponent(material)}&max_citations=${maxCitations}`,
        evidenceChainSchema,
      ),
    onSuccess: (data) => {
      const typed = data as EvidenceViewResponse;
      setEvidence(typed);
      toast({
        title: t('common.evidenceRetrieved'),
        description: t('evidence.foundCitations', { count: typed.total_citations, material: typed.material }),
      });
    },
    onError: () => {
      toast({
        title: t('common.searchFailed'),
        description: t('common.couldNotConnect'),
        variant: "destructive",
      });
    },
  });

  useEffect(() => {
    // Auto-load PTFE evidence on mount
    void handleSearch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSearch = async () => {
    await evidenceMutation.mutateAsync();
  };

  const sourceStats: SourceStats | null = sourceStatsQuery.data ?? null;
  const isLoading = evidenceMutation.isPending;
  const chatSurfaceHint = useMemo(() => createEvidenceAnswerSurfaceHint({
    locale: currentLanguage,
    starterQuestions: [
      t("chat.starters.evidence.visible"),
      t("chat.starters.evidence.confidence"),
      t("chat.starters.evidence.source"),
    ],
    material,
    maxCitations,
    totalCitations: evidence?.total_citations ?? 0,
    confidenceScore: evidence?.confidence_score ?? null,
    databaseTotalPapers: sourceStats?.total_papers ?? 0,
    totalPathwayCitations: sourceStats?.coverage?.total_pathway_citations ?? 0,
    visibleEvidence: (evidence?.evidence_chain || []).slice(0, 12).map((item) => ({
      source: item.source,
      year: item.year,
      confidence: item.confidence,
      compound: item.compound,
    })),
  }), [currentLanguage, evidence, material, maxCitations, sourceStats, t]);

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return "text-green-400";
    if (confidence >= 0.7) return "text-yellow-400";
    return "text-orange-400";
  };

  return (
    <PageChatProvider
      pageId="evidence"
      pageLabel={t("evidence.title")}
      surfaceHint={chatSurfaceHint}
    >
    <div className="min-h-screen bg-gray-50">
      <DaikinHeader title={t('evidence.title')} subtitle={t('evidence.subtitle')} helpContent={helpContent.evidence}>
        {sourceStats && (
          <>
            <div className="text-gray-600">
              <span className="text-daikin-blue font-bold">{sourceStats.total_papers}</span> {t('common.papers')}
            </div>
            <div className="text-gray-600">
              <span className="text-daikin-blue font-bold">{(sourceStats.coverage?.total_pathway_citations ?? 0).toLocaleString()}</span> {t('common.transformations').toLowerCase()}
            </div>
          </>
        )}
      </DaikinHeader>

      <main className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Input Panel */}
          <Card className="bg-white border-gray-200 shadow-sm">
            <CardHeader>
              <CardTitle className="text-daikin-dark">{t('evidence.searchEvidence')}</CardTitle>
              <CardDescription>{t('evidence.findCitations')}</CardDescription>
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

              <div>
                <Label className="text-gray-700">{t('evidence.maxCitations')}</Label>
                <Input
                  type="number"
                  value={maxCitations}
                  onChange={(e) => setMaxCitations(parseInt(e.target.value) || 10)}
                  min={1}
                  max={100}
                  className="bg-white border-gray-300"
                />
              </div>

              <Button
                onClick={handleSearch}
                disabled={isLoading || !material}
                className="w-full bg-gradient-to-r from-daikin-blue to-daikin-accent hover:opacity-90 text-white"
              >
                {isLoading ? (
                  <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> {t('common.searching')}</>
                ) : (
                  <><BookOpen className="mr-2 h-4 w-4" /> {t('evidence.findEvidence')}</>
                )}
              </Button>

              {/* Source Stats */}
              {sourceStats && (
                <div className="border-t border-gray-200 pt-4">
                  <p className="text-sm text-gray-500 mb-2">{t('evidence.databaseCoverage')}</p>
                  <div className="space-y-2">
                    {sourceStats.sources.map((s) => (
                      <div key={s.type} className="flex items-center justify-between">
                        <span className="text-gray-600 text-sm capitalize">{s.type.replace(/_/g, " ")}</span>
                        <Badge variant="outline" className="border-gray-400">{s.count}</Badge>
                      </div>
                    ))}
                  </div>
                  <p className="text-xs text-gray-400 mt-2">
                    {t('evidence.extractedVia')} {sourceStats.extraction_method}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Results Panel */}
          <div className="lg:col-span-2 space-y-6">
            {evidence ? (
              <>
                {/* Summary Card */}
                <Card className="bg-white border-gray-200 shadow-sm">
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-daikin-dark">{evidence.material} {t('evidence.evidenceChain')}</CardTitle>
                      <Badge className="bg-gradient-to-r from-daikin-blue to-daikin-accent text-white">{evidence.total_citations} {t('common.citations')}</Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center gap-4">
                      <div className="flex-1">
                        <p className="text-sm text-gray-500 mb-1">{t('evidence.overallConfidence')}</p>
                        <Progress value={evidence.confidence_score * 100} className="h-3" />
                      </div>
                      <span className={`text-2xl font-bold ${getConfidenceColor(evidence.confidence_score)}`}>
                        {(evidence.confidence_score * 100).toFixed(0)}%
                      </span>
                    </div>
                  </CardContent>
                </Card>

                {/* Evidence Items */}
                <Card className="bg-white border-gray-200 shadow-sm">
                  <CardHeader>
                    <CardTitle className="text-daikin-dark flex items-center gap-2">
                      <Link2 className="h-5 w-5 text-daikin-blue" />
                      {t('evidence.citationChain')}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {evidence.evidence_chain.map((item, i) => (
                        <div
                          key={i}
                          className="p-4 bg-gray-50 rounded-lg border-l-4 border-daikin-blue"
                        >
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <FileText className="h-4 w-4 text-gray-500" />
                              <span className="font-medium text-daikin-dark">{item.source}</span>
                              <Badge variant="outline" className="text-xs border-gray-400">{item.year}</Badge>
                            </div>
                            <div className="flex items-center gap-2">
                              <Badge className="bg-gray-200 text-gray-700">{item.compound}</Badge>
                              <span className={`text-sm font-medium ${getConfidenceColor(item.confidence)}`}>
                                {(item.confidence * 100).toFixed(0)}%
                              </span>
                            </div>
                          </div>
                          <p className="text-gray-600 text-sm">{item.finding}</p>
                          {item.doi && (
                            <a
                              href={`https://doi.org/${item.doi}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 mt-2 text-xs text-daikin-blue hover:text-daikin-accent"
                            >
                              <ExternalLink className="h-3 w-3" />
                              {t('evidence.doi')} {item.doi}
                            </a>
                          )}
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </>
            ) : (
              <Card className="bg-white border-gray-200 shadow-sm">
                <CardContent className="py-16 text-center">
                  <Database className="h-16 w-16 mx-auto mb-4 text-gray-400" />
                  <h3 className="text-xl font-semibold text-gray-600 mb-2">{t('evidence.evidenceChain')}</h3>
                  <p className="text-gray-500 max-w-md mx-auto">
                    {t('evidence.description')}
                  </p>
                  {sourceStats && (
                    <div className="mt-6 flex justify-center gap-6">
                      <div className="text-center">
                        <p className="text-2xl font-bold text-daikin-blue">{sourceStats.coverage.polymers}</p>
                        <p className="text-sm text-gray-500">{t('evidence.fluoropolymers')}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-2xl font-bold text-daikin-blue">{sourceStats.coverage.pfas_endpoints}</p>
                        <p className="text-sm text-gray-500">{t('evidence.pfasEndpoints')}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-2xl font-bold text-daikin-blue">{(sourceStats.coverage?.total_pathway_citations ?? 0).toLocaleString()}</p>
                        <p className="text-sm text-gray-500">{t('common.transformations')}</p>
                      </div>
                    </div>
                  )}
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

export default EvidenceChain;
