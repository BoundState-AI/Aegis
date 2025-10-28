import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { Loader2 } from "lucide-react";
import AnalysisResults from "@/components/pfas/AnalysisResults";

const PFASAnalysis = () => {
  const { toast } = useToast();
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [results, setResults] = useState(null);
  
  const [formData, setFormData] = useState({
    material: "",
    temperature: "",
    atmosphere: "air",
    time: ""
  });

  const handleAnalyze = async () => {
    if (!formData.material || !formData.temperature || !formData.time) {
      toast({
        title: "Missing inputs",
        description: "Please fill in all required fields",
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
          temperature: parseFloat(formData.temperature),
          atmosphere: formData.atmosphere,
          time: parseFloat(formData.time)
        })
      });

      if (!response.ok) throw new Error("Analysis failed");
      
      const data = await response.json();
      setResults(data);
    } catch (error) {
      toast({
        title: "Analysis failed",
        description: "Could not connect to PFAS Engine backend",
        variant: "destructive"
      });
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleDownloadPDF = async () => {
    try {
      const response = await fetch("http://localhost:8000/pfas/analyze?format=pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          material: formData.material,
          temperature: parseFloat(formData.temperature),
          atmosphere: formData.atmosphere,
          time: parseFloat(formData.time)
        })
      });

      if (!response.ok) throw new Error("PDF generation failed");
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `pfas-analysis-${formData.material}-${Date.now()}.pdf`;
      a.click();
      
      toast({
        title: "Report downloaded",
        description: "PDF report generated successfully"
      });
    } catch (error) {
      toast({
        title: "Download failed",
        description: "Could not generate PDF report",
        variant: "destructive"
      });
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto py-8 px-4 max-w-7xl">
        <header className="mb-8">
          <h1 className="text-4xl font-bold text-foreground mb-2">PFAS Engine</h1>
          <p className="text-muted-foreground text-lg">Fluorochemical Risk Intelligence & Degradation Analysis</p>
        </header>

        <Card className="p-6 mb-8">
          <h2 className="text-2xl font-semibold mb-6">Analysis Parameters</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <Label htmlFor="material">Material</Label>
              <Input
                id="material"
                placeholder="e.g., FEP, PTFE"
                value={formData.material}
                onChange={(e) => setFormData({ ...formData, material: e.target.value })}
                className="mt-2"
              />
            </div>

            <div>
              <Label htmlFor="temperature">Temperature (°C)</Label>
              <Input
                id="temperature"
                type="number"
                placeholder="e.g., 385"
                value={formData.temperature}
                onChange={(e) => setFormData({ ...formData, temperature: e.target.value })}
                className="mt-2"
              />
            </div>

            <div>
              <Label htmlFor="atmosphere">Atmosphere</Label>
              <Select value={formData.atmosphere} onValueChange={(val) => setFormData({ ...formData, atmosphere: val })}>
                <SelectTrigger id="atmosphere" className="mt-2">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="air">Air</SelectItem>
                  <SelectItem value="inert">Inert</SelectItem>
                  <SelectItem value="nitrogen">Nitrogen</SelectItem>
                  <SelectItem value="oxygen">Oxygen</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label htmlFor="time">Time (hours)</Label>
              <Input
                id="time"
                type="number"
                placeholder="e.g., 6"
                value={formData.time}
                onChange={(e) => setFormData({ ...formData, time: e.target.value })}
                className="mt-2"
              />
            </div>
          </div>

          <div className="mt-6 flex gap-4">
            <Button 
              onClick={handleAnalyze} 
              disabled={isAnalyzing}
              size="lg"
              className="min-w-[200px]"
            >
              {isAnalyzing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Analyzing...
                </>
              ) : "Run Analysis"}
            </Button>

            {results && (
              <Button 
                onClick={handleDownloadPDF} 
                variant="outline"
                size="lg"
              >
                Download PDF Report
              </Button>
            )}
          </div>
        </Card>

        {results && <AnalysisResults data={results} />}
      </div>
    </div>
  );
};

export default PFASAnalysis;