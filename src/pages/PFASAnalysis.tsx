import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { useToast } from "@/hooks/use-toast";
import { Loader2, Download } from "lucide-react";
import { AnalyzeResponse } from "@/types/pfas";
import RiskScoreHero from "@/components/pfas/RiskScoreHero";
import PathwayCard from "@/components/pfas/PathwayCard";
import AlternativesTable from "@/components/pfas/AlternativesTable";

const COMMON_MATERIALS = [
  "FEP",
  "PTFE", 
  "PFA",
  "ETFE",
  "PVDF",
  "Opteon YF",
  "R-134a",
  "Custom"
];

const PFASAnalysis = () => {
  const { toast } = useToast();
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [results, setResults] = useState<AnalyzeResponse | null>(null);
  
  const [formData, setFormData] = useState({
    material: "",
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
      const response = await fetch("http://localhost:8000/pfas/analyze", {
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

      if (!response.ok) throw new Error("Analysis failed");
      
      const data = await response.json();
      setResults(data);
      
      toast({
        title: "Analysis Complete",
        description: `Found ${data.pathways?.length || 0} degradation pathways`
      });
    } catch (error) {
      toast({
        title: "Analysis Failed",
        description: "Could not connect to PFAS Engine backend. Ensure the FastAPI server is running on localhost:8000",
        variant: "destructive"
      });
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleDownloadPDF = async () => {
    try {
      const response = await fetch("http://localhost:8000/pfas/analyze/pdf", {
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

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto py-8 px-4 max-w-7xl">
        <header className="mb-8 border-b pb-6">
          <h1 className="text-5xl font-bold text-foreground mb-3">PFAS Engine</h1>
          <p className="text-muted-foreground text-xl">Fluorochemical Risk Intelligence & Degradation Analysis</p>
        </header>

        <Card className="p-8 mb-8 bg-card shadow-lg">
          <h2 className="text-3xl font-bold mb-6">Analysis Parameters</h2>
          
          <div className="space-y-6">
            <div>
              <Label htmlFor="material" className="text-base font-semibold">Material</Label>
              <Select value={formData.material} onValueChange={(val) => setFormData({ ...formData, material: val })}>
                <SelectTrigger id="material" className="mt-2 h-12">
                  <SelectValue placeholder="Select fluoropolymer or refrigerant" />
                </SelectTrigger>
                <SelectContent>
                  {COMMON_MATERIALS.map((mat) => (
                    <SelectItem key={mat} value={mat}>{mat}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <Label htmlFor="temperature" className="text-base font-semibold">Temperature</Label>
                <span className="text-lg font-bold text-primary">{formData.temperature}°C</span>
              </div>
              <Slider
                id="temperature"
                min={0}
                max={500}
                step={5}
                value={[formData.temperature]}
                onValueChange={(val) => setFormData({ ...formData, temperature: val[0] })}
                className="mt-2"
              />
              <div className="flex justify-between text-xs text-muted-foreground mt-1">
                <span>0°C</span>
                <span>250°C</span>
                <span>500°C</span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <Label htmlFor="atmosphere" className="text-base font-semibold">Atmosphere</Label>
                <Select value={formData.atmosphere} onValueChange={(val) => setFormData({ ...formData, atmosphere: val })}>
                  <SelectTrigger id="atmosphere" className="mt-2 h-12">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="air">Air</SelectItem>
                    <SelectItem value="inert">Inert</SelectItem>
                    <SelectItem value="nitrogen">Nitrogen (N₂)</SelectItem>
                    <SelectItem value="oxygen">Oxygen (O₂)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="time" className="text-base font-semibold">Exposure Time (hours)</Label>
                <Input
                  id="time"
                  type="number"
                  min="0"
                  step="0.5"
                  value={formData.time}
                  onChange={(e) => setFormData({ ...formData, time: parseFloat(e.target.value) || 0 })}
                  className="mt-2 h-12 text-lg"
                />
              </div>
            </div>
          </div>

          <div className="mt-8 flex gap-4">
            <Button 
              onClick={handleAnalyze} 
              disabled={isAnalyzing}
              size="lg"
              className="min-w-[200px] h-12 text-lg"
            >
              {isAnalyzing ? (
                <>
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  Analyzing...
                </>
              ) : "Run Analysis"}
            </Button>

            {results && (
              <Button 
                onClick={handleDownloadPDF} 
                variant="outline"
                size="lg"
                className="h-12"
              >
                <Download className="mr-2 h-5 w-5" />
                Download PDF Report
              </Button>
            )}
          </div>
        </Card>

        {results && (
          <div className="space-y-8">
            <RiskScoreHero data={results} />

            <div>
              <h2 className="text-3xl font-bold mb-6">Degradation Pathways ({results.pathways?.length || 0})</h2>
              <div className="space-y-6">
                {results.pathways?.map((pathway, idx) => (
                  <PathwayCard key={idx} pathway={pathway} />
                ))}
              </div>
            </div>

            <AlternativesTable alternatives={results.alternatives || []} />
          </div>
        )}
      </div>
    </div>
  );
};

export default PFASAnalysis;