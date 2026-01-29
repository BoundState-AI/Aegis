import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { Loader2, Download, FlaskConical, Thermometer, Wind, Clock, AlertTriangle } from "lucide-react";
import { AnalyzeResponse } from "@/types/pfas";
import AnalysisResults from "@/components/pfas/AnalysisResults";
import ChemoursHeader from "@/components/layout/ChemoursHeader";
import helpContent from "@/config/helpContent";

const API_BASE = "http://localhost:8002";

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
  const { toast } = useToast();
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [results, setResults] = useState<AnalyzeResponse | null>(null);

  const [formData, setFormData] = useState({
    material: "PTFE",
    temperature: 385,
    atmosphere: "air",
    time: 6
  });

  const handleAnalyze = async () => {
    if (!formData.material) {
      toast({
        title: "Missing Material",
        description: "Please select a material to analyze",
        variant: "destructive"
      });
      return;
    }

    setIsAnalyzing(true);
    try {
      const response = await fetch(`${API_BASE}/api/pfas/evaluate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_compound: formData.material,
          context: {
            incident_temp_c: formData.temperature,
            atmosphere: formData.atmosphere,
            residence_time_s: formData.time * 3600
          }
        })
      });

      if (!response.ok) throw new Error("Analysis failed");

      const data: AnalyzeResponse = await response.json();
      setResults(data);

      toast({
        title: "Analysis Complete",
        description: `Evaluated ${data.compound_evaluated} - Found ${data.pfas_findings.length} potential PFAS pathways`
      });
    } catch (error) {
      toast({
        title: "Analysis Failed",
        description: "Could not connect to PFAS Engine backend on port 8001.",
        variant: "destructive"
      });
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleDownloadPDF = async () => {
    try {
      const response = await fetch(`${API_BASE}/pfas/analyze/pdf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          material: formData.material,
          conditions: {
            temperature: formData.temperature,
            atmosphere: formData.atmosphere,
            time_hours: formData.time
          }
        })
      });

      if (!response.ok) throw new Error("PDF generation failed");

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `pfas-analysis-${formData.material}-${Date.now()}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);

      toast({
        title: "Report Downloaded",
        description: "PDF report generated successfully"
      });
    } catch (error) {
      toast({
        title: "Download Failed",
        description: "Could not generate PDF report",
        variant: "destructive"
      });
    }
  };

  const getTempColor = (temp: number) => {
    if (temp >= 400) return "text-red-400";
    if (temp >= 300) return "text-orange-400";
    if (temp >= 200) return "text-yellow-400";
    return "text-green-400";
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <ChemoursHeader title="PFAS Degradation Analysis" subtitle="Evaluate thermal degradation pathways and PFAS formation" helpContent={helpContent.analysis} />

      <main className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Input Panel */}
          <Card className="bg-white border-gray-200 shadow-sm">
            <CardHeader>
              <CardTitle className="text-chemours-dark">Analysis Parameters</CardTitle>
              <CardDescription>Configure degradation conditions</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Material Selection */}
              <div>
                <Label className="text-gray-700">Material</Label>
                <Select value={formData.material} onValueChange={(val) => setFormData({ ...formData, material: val })}>
                  <SelectTrigger className="mt-2 bg-white border-gray-300">
                    <SelectValue placeholder="Select material" />
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
                    Temperature
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
                    High degradation risk
                  </div>
                )}
              </div>

              {/* Atmosphere */}
              <div>
                <Label className="text-gray-700 flex items-center gap-2">
                  <Wind className="h-4 w-4" />
                  Atmosphere
                </Label>
                <Select value={formData.atmosphere} onValueChange={(val) => setFormData({ ...formData, atmosphere: val })}>
                  <SelectTrigger className="mt-2 bg-white border-gray-300">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="air">Air (Oxidative)</SelectItem>
                    <SelectItem value="inert">Inert</SelectItem>
                    <SelectItem value="nitrogen">Nitrogen (N₂)</SelectItem>
                    <SelectItem value="oxygen">Oxygen (O₂)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Exposure Time */}
              <div>
                <Label className="text-gray-700 flex items-center gap-2">
                  <Clock className="h-4 w-4" />
                  Exposure Time (hours)
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
                className="w-full bg-gradient-to-r from-chemours-red to-chemours-orange hover:opacity-90 text-white"
              >
                {isAnalyzing ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <FlaskConical className="mr-2 h-4 w-4" />
                    Run Analysis
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
                  Download PDF Report
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
                      <CardTitle className="text-chemours-dark">{results.compound_evaluated} Analysis Results</CardTitle>
                      <Badge className="bg-gradient-to-r from-chemours-red to-chemours-orange text-white">{results.pfas_findings.length} Pathways</Badge>
                    </div>
                    <CardDescription>{results.summary}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-3 gap-4 text-center">
                      <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                        <p className="text-2xl font-bold text-chemours-dark">{formData.temperature}°C</p>
                        <p className="text-sm text-gray-500">Temperature</p>
                      </div>
                      <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                        <p className="text-2xl font-bold text-chemours-dark capitalize">{formData.atmosphere}</p>
                        <p className="text-sm text-gray-500">Atmosphere</p>
                      </div>
                      <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                        <p className="text-2xl font-bold text-chemours-dark">{formData.time}h</p>
                        <p className="text-sm text-gray-500">Exposure</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Detailed Results */}
                <Card className="bg-white border-gray-200 shadow-sm">
                  <CardHeader>
                    <CardTitle className="text-chemours-dark">PFAS Findings</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {results.pfas_findings.map((finding, i) => (
                        <div key={i} className="p-4 bg-gray-50 rounded-lg border-l-4 border-chemours-red">
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-medium text-chemours-dark text-lg">{finding.product}</span>
                            <Badge variant="outline" className="border-chemours-red text-chemours-red">
                              {(finding.overall_confidence * 100).toFixed(0)}% confidence
                            </Badge>
                          </div>

                          {finding.pathway.length > 0 && (
                            <div className="flex items-center gap-2 mb-2 text-sm">
                              <span className="text-gray-500">Pathway:</span>
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
                                Litigation Risk
                              </Badge>
                            )}
                            {finding.is_short_chain_pfas && (
                              <Badge className="bg-blue-100 text-blue-700 border border-blue-300">
                                Short-chain PFAS
                              </Badge>
                            )}
                          </div>
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
                  <h3 className="text-xl font-semibold text-gray-600 mb-2">PFAS Degradation Analysis</h3>
                  <p className="text-gray-500 max-w-md mx-auto">
                    Analyze fluoropolymers and refrigerants for PFAS degradation pathways under specified thermal conditions.
                  </p>
                  <div className="flex justify-center gap-6 mt-6">
                    <div className="text-center">
                      <p className="text-2xl font-bold text-chemours-red">6,141</p>
                      <p className="text-sm text-gray-500">Transformations</p>
                    </div>
                    <div className="text-center">
                      <p className="text-2xl font-bold text-chemours-red">228</p>
                      <p className="text-sm text-gray-500">Papers</p>
                    </div>
                    <div className="text-center">
                      <p className="text-2xl font-bold text-chemours-red">216</p>
                      <p className="text-sm text-gray-500">Compounds</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default PFASAnalysis;
