import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { Loader2, FileText, Download, Lock, ChevronRight } from "lucide-react";
import ChemoursHeader from "@/components/layout/ChemoursHeader";
import helpContent from "@/config/helpContent";
import { API_BASE } from "@/config/api";

interface ReportSection {
  title: string;
  content: string;
  data?: Record<string, any>;
  flags?: string[];
  similar_cases?: string[];
}

interface ExecutiveReport {
  title: string;
  generated: string;
  classification: string;
  material: string;
  sections: ReportSection[];
}

const ExecutiveReports = () => {
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [material, setMaterial] = useState("PTFE");
  const [includeLitigation, setIncludeLitigation] = useState(true);
  const [includeRegulatory, setIncludeRegulatory] = useState(true);
  const [report, setReport] = useState<ExecutiveReport | null>(null);

  const handleGenerate = async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams({
        material,
        include_litigation: includeLitigation.toString(),
        include_regulatory: includeRegulatory.toString(),
      });

      const res = await fetch(`${API_BASE}/api/v1/reports/executive?${params}`);
      if (!res.ok) throw new Error("Report generation failed");

      const data: ExecutiveReport = await res.json();
      setReport(data);

      toast({
        title: "Report Generated",
        description: `Executive report for ${data.material} ready`,
      });
    } catch (error) {
      toast({
        title: "Generation Failed",
        description: "Could not generate report",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownload = () => {
    if (!report) return;

    // Create text content
    let content = `${report.title}\n`;
    content += `${"=".repeat(report.title.length)}\n\n`;
    content += `Generated: ${new Date(report.generated).toLocaleString()}\n`;
    content += `Classification: ${report.classification}\n\n`;

    report.sections.forEach((section) => {
      content += `\n${section.title}\n`;
      content += `${"-".repeat(section.title.length)}\n`;
      content += `${section.content}\n`;

      if (section.flags && section.flags.length > 0) {
        content += `\nRegulatory Flags:\n`;
        section.flags.forEach((f) => (content += `  - ${f}\n`));
      }

      if (section.similar_cases && section.similar_cases.length > 0) {
        content += `\nSimilar Cases:\n`;
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
      title: "Report Downloaded",
      description: "Executive report saved to downloads",
    });
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <ChemoursHeader title="Executive Reports" subtitle="Generate comprehensive risk reports" helpContent={helpContent.reports} />

      <main className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Input Panel */}
          <Card className="bg-white border-gray-200 shadow-sm">
            <CardHeader>
              <CardTitle className="text-chemours-dark">Report Configuration</CardTitle>
              <CardDescription>Configure report parameters</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label className="text-gray-700">Material</Label>
                <Input
                  value={material}
                  onChange={(e) => setMaterial(e.target.value.toUpperCase())}
                  placeholder="e.g., PTFE, FEP"
                  className="bg-white border-gray-300"
                />
              </div>

              <div className="flex items-center justify-between">
                <Label className="text-gray-700">Include Litigation Analysis</Label>
                <Switch checked={includeLitigation} onCheckedChange={setIncludeLitigation} />
              </div>

              <div className="flex items-center justify-between">
                <Label className="text-gray-700">Include Regulatory Status</Label>
                <Switch checked={includeRegulatory} onCheckedChange={setIncludeRegulatory} />
              </div>

              <Button
                onClick={handleGenerate}
                disabled={isLoading || !material}
                className="w-full bg-gradient-to-r from-chemours-red to-chemours-orange hover:opacity-90 text-white"
              >
                {isLoading ? (
                  <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Generating...</>
                ) : (
                  <><FileText className="mr-2 h-4 w-4" /> Generate Report</>
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
                        <CardTitle className="text-chemours-dark">{report.title}</CardTitle>
                        <CardDescription>
                          Generated: {new Date(report.generated).toLocaleString()}
                        </CardDescription>
                      </div>
                      <Button variant="outline" onClick={handleDownload} className="border-gray-300 text-gray-600 hover:bg-gray-100">
                        <Download className="mr-2 h-4 w-4" /> Download
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center gap-2 p-3 bg-red-50 rounded-lg border border-red-200">
                      <Lock className="h-5 w-5 text-red-600" />
                      <span className="text-red-600 font-medium">{report.classification}</span>
                    </div>
                  </CardContent>
                </Card>

                {/* Report Sections */}
                {report.sections.map((section, i) => (
                  <Card key={i} className="bg-white border-gray-200 shadow-sm">
                    <CardHeader>
                      <CardTitle className="text-chemours-dark flex items-center gap-2">
                        <ChevronRight className="h-5 w-5 text-chemours-orange" />
                        {section.title}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <p className="text-gray-600 whitespace-pre-wrap">{section.content}</p>

                      {section.data?.products && (
                        <div>
                          <p className="text-sm text-gray-500 mb-2">Degradation Products:</p>
                          <div className="flex flex-wrap gap-2">
                            {section.data.products.map((p: string) => (
                              <Badge key={p} variant="outline" className="border-chemours-orange text-chemours-orange">{p}</Badge>
                            ))}
                          </div>
                        </div>
                      )}

                      {section.flags && section.flags.length > 0 && (
                        <div className="p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                          <p className="text-sm text-yellow-700 mb-2 font-medium">Regulatory Flags:</p>
                          <ul className="space-y-1">
                            {section.flags.map((f, j) => (
                              <li key={j} className="text-gray-600 text-sm flex items-start gap-2">
                                <span className="text-yellow-600">•</span>
                                {f}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {section.similar_cases && section.similar_cases.length > 0 && (
                        <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                          <p className="text-sm text-blue-700 mb-2 font-medium">Similar Cases:</p>
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
                  <h3 className="text-xl font-semibold text-gray-600 mb-2">Executive Reports</h3>
                  <p className="text-gray-500 max-w-md mx-auto">
                    Generate comprehensive PFAS risk reports with degradation analysis, regulatory status, litigation risk, and recommendations.
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

export default ExecutiveReports;
