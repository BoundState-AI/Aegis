import { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useToast } from "@/hooks/use-toast";
import { Loader2, BookOpen, Link2, ExternalLink, Database, FileText } from "lucide-react";
import ChemoursHeader from "@/components/layout/ChemoursHeader";
import { useHelpContent } from "@/config/helpContent";
import { API_BASE } from "@/config/api";

interface EvidenceItem {
  source: string;
  doi: string | null;
  year: number;
  confidence: number;
  finding: string;
  compound: string;
}

interface EvidenceChainResponse {
  material: string;
  total_citations: number;
  evidence_chain: EvidenceItem[];
  confidence_score: number;
}

interface SourceStats {
  total_papers: number;
  extraction_method: string;
  sources: Array<{ type: string; count: number }>;
  coverage: {
    fluoropolymers: number;
    pfas_endpoints: number;
    transformations: number;
  };
}

const EvidenceChain = () => {
  const { t } = useTranslation();
  const { toast } = useToast();
  const helpContent = useHelpContent();
  const [isLoading, setIsLoading] = useState(false);
  const [material, setMaterial] = useState("PTFE");
  const [maxCitations, setMaxCitations] = useState(20);
  const [evidence, setEvidence] = useState<EvidenceChainResponse | null>(null);
  const [sourceStats, setSourceStats] = useState<SourceStats | null>(null);

  useEffect(() => {
    loadSourceStats();
  }, []);

  const loadSourceStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/evidence/sources`);
      if (res.ok) {
        setSourceStats(await res.json());
      }
    } catch (e) {
      console.error("Failed to load source stats:", e);
    }
  };

  const handleSearch = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/evidence/chain?material=${material}&max_citations=${maxCitations}`
      );
      if (!res.ok) throw new Error("Search failed");

      const data: EvidenceChainResponse = await res.json();
      setEvidence(data);

      toast({
        title: t('common.evidenceRetrieved'),
        description: `Found ${data.total_citations} citations for ${data.material}`,
      });
    } catch (error) {
      toast({
        title: t('common.searchFailed'),
        description: "Could not retrieve evidence",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return "text-green-400";
    if (confidence >= 0.7) return "text-yellow-400";
    return "text-orange-400";
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <ChemoursHeader title={t('evidence.title')} subtitle={t('evidence.subtitle')} helpContent={helpContent.evidence}>
        {sourceStats && (
          <>
            <div className="text-gray-600">
              <span className="text-chemours-red font-bold">{sourceStats.total_papers}</span> papers
            </div>
            <div className="text-gray-600">
              <span className="text-chemours-red font-bold">{(sourceStats.coverage?.transformations ?? 0).toLocaleString()}</span> {t('common.transformations').toLowerCase()}
            </div>
          </>
        )}
      </ChemoursHeader>

      <main className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Input Panel */}
          <Card className="bg-white border-gray-200 shadow-sm">
            <CardHeader>
              <CardTitle className="text-chemours-dark">{t('evidence.searchEvidence')}</CardTitle>
              <CardDescription>{t('evidence.findCitations')}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label className="text-gray-700">{t('common.material')}</Label>
                <Input
                  value={material}
                  onChange={(e) => setMaterial(e.target.value.toUpperCase())}
                  placeholder="e.g., PTFE, FEP"
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
                className="w-full bg-gradient-to-r from-chemours-red to-chemours-orange hover:opacity-90 text-white"
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
                      <CardTitle className="text-chemours-dark">{evidence.material} {t('evidence.evidenceChain')}</CardTitle>
                      <Badge className="bg-gradient-to-r from-chemours-red to-chemours-orange text-white">{evidence.total_citations} Citations</Badge>
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
                    <CardTitle className="text-chemours-dark flex items-center gap-2">
                      <Link2 className="h-5 w-5 text-chemours-red" />
                      {t('evidence.citationChain')}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {evidence.evidence_chain.map((item, i) => (
                        <div
                          key={i}
                          className="p-4 bg-gray-50 rounded-lg border-l-4 border-chemours-red"
                        >
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <FileText className="h-4 w-4 text-gray-500" />
                              <span className="font-medium text-chemours-dark">{item.source}</span>
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
                              className="inline-flex items-center gap-1 mt-2 text-xs text-chemours-red hover:text-chemours-orange"
                            >
                              <ExternalLink className="h-3 w-3" />
                              DOI: {item.doi}
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
                    Search for peer-reviewed citations supporting PFAS degradation pathways. All evidence is traceable to source publications.
                  </p>
                  {sourceStats && (
                    <div className="mt-6 flex justify-center gap-6">
                      <div className="text-center">
                        <p className="text-2xl font-bold text-chemours-red">{sourceStats.coverage.fluoropolymers}</p>
                        <p className="text-sm text-gray-500">{t('evidence.fluoropolymers')}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-2xl font-bold text-chemours-red">{sourceStats.coverage.pfas_endpoints}</p>
                        <p className="text-sm text-gray-500">{t('evidence.pfasEndpoints')}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-2xl font-bold text-chemours-red">{(sourceStats.coverage?.transformations ?? 0).toLocaleString()}</p>
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
  );
};

export default EvidenceChain;
