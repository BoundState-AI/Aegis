import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/hooks/use-toast";
import { Loader2, Shield, AlertTriangle, CheckCircle, XCircle, Calendar, Globe } from "lucide-react";
import ChemoursHeader from "@/components/layout/ChemoursHeader";
import helpContent from "@/config/helpContent";
import { API_BASE } from "@/config/api";

interface RegulatoryStatus {
  framework: string;
  status: string;
  limit_ppb: number | null;
  effective_date: string | null;
  notes: string;
}

interface RegulatoryCheck {
  material: string;
  degradation_products: string[];
  frameworks_checked: number;
  compliant: RegulatoryStatus[];
  non_compliant: RegulatoryStatus[];
  warnings: RegulatoryStatus[];
  overall_risk: string;
}

interface CascadePrediction {
  status: string;
  regulatory_stage: string;  // "enacted", "final_pending", "proposed", "under_consideration", "monitoring"
  source?: string;
  affected_products: string[];
}

interface CascadeResponse {
  material: string;
  forecast_year: number;
  predictions: Record<string, CascadePrediction>;
  recommendation: string;
}

const RegulatoryCompliance = () => {
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [material, setMaterial] = useState("PTFE");
  const [includeDegradation, setIncludeDegradation] = useState(true);
  const [checkResult, setCheckResult] = useState<RegulatoryCheck | null>(null);
  const [cascade, setCascade] = useState<CascadeResponse | null>(null);
  const [forecastYear, setForecastYear] = useState(2025);

  const handleCheck = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/regulatory/check?material=${material}&include_degradation=${includeDegradation}`
      );
      if (!res.ok) throw new Error("Check failed");

      const data: RegulatoryCheck = await res.json();
      setCheckResult(data);

      // Also get cascade
      const cascadeRes = await fetch(
        `${API_BASE}/api/v1/regulatory/cascade?material=${material}&forecast_year=${forecastYear}`
      );
      if (cascadeRes.ok) {
        setCascade(await cascadeRes.json());
      }

      toast({
        title: "Compliance Check Complete",
        description: `${data.material}: ${data.overall_risk} risk across ${data.frameworks_checked} frameworks`,
      });
    } catch (error) {
      toast({
        title: "Check Failed",
        description: "Could not connect to AEGIS API",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
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
      case "enacted": return "ENACTED";
      case "final_pending": return "FINAL PENDING";
      case "proposed": return "PROPOSED";
      case "under_consideration": return "UNDER CONSIDERATION";
      case "monitoring": return "MONITORING";
      default: return stage.toUpperCase();
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <ChemoursHeader title="Regulatory Compliance Checker" subtitle="EPA, EU REACH, CA Prop 65, Stockholm Convention" helpContent={helpContent.regulatory} />

      <main className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Input Panel */}
          <Card className="bg-white border-gray-200 shadow-sm">
            <CardHeader>
              <CardTitle className="text-chemours-dark">Check Compliance</CardTitle>
              <CardDescription>Enter material to check regulatory status</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label className="text-gray-700">Material</Label>
                <Input
                  value={material}
                  onChange={(e) => setMaterial(e.target.value.toUpperCase())}
                  placeholder="e.g., PTFE, FEP, PFOA"
                  className="bg-white border-gray-300"
                />
              </div>

              <div className="flex items-center justify-between">
                <Label className="text-gray-700">Include Degradation Products</Label>
                <Switch checked={includeDegradation} onCheckedChange={setIncludeDegradation} />
              </div>

              <div>
                <Label className="text-gray-700">Forecast Year</Label>
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
                disabled={isLoading || !material}
                className="w-full bg-gradient-to-r from-chemours-red to-chemours-orange hover:opacity-90 text-white"
              >
                {isLoading ? (
                  <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Checking...</>
                ) : (
                  <><Shield className="mr-2 h-4 w-4" /> Check Compliance</>
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
                      <CardTitle className="text-chemours-dark">{checkResult.material} Compliance Status</CardTitle>
                      <Badge className={getRiskColor(checkResult.overall_risk)}>{checkResult.overall_risk}</Badge>
                    </div>
                    <CardDescription>
                      Checked {checkResult.frameworks_checked} regulatory frameworks
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {checkResult.degradation_products.length > 0 && (
                      <div className="mb-4">
                        <p className="text-sm text-gray-500 mb-2">Degradation Products Checked:</p>
                        <div className="flex flex-wrap gap-2">
                          {checkResult.degradation_products.map((p) => (
                            <Badge key={p} variant="outline" className="border-gray-400 text-gray-600">{p}</Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="grid grid-cols-3 gap-4 text-center">
                      <div className="p-4 bg-red-50 rounded-lg border border-red-200">
                        <XCircle className="h-8 w-8 text-red-500 mx-auto mb-2" />
                        <p className="text-2xl font-bold text-red-600">{checkResult.non_compliant.length}</p>
                        <p className="text-sm text-gray-500">Non-Compliant</p>
                      </div>
                      <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                        <AlertTriangle className="h-8 w-8 text-yellow-500 mx-auto mb-2" />
                        <p className="text-2xl font-bold text-yellow-600">{checkResult.warnings.length}</p>
                        <p className="text-sm text-gray-500">Warnings</p>
                      </div>
                      <div className="p-4 bg-green-50 rounded-lg border border-green-200">
                        <CheckCircle className="h-8 w-8 text-green-500 mx-auto mb-2" />
                        <p className="text-2xl font-bold text-green-600">{checkResult.compliant.length}</p>
                        <p className="text-sm text-gray-500">Compliant</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Non-Compliant Details */}
                {checkResult.non_compliant.length > 0 && (
                  <Card className="bg-white border-gray-200 shadow-sm border-l-4 border-l-red-500">
                    <CardHeader>
                      <CardTitle className="text-red-600">Non-Compliant Regulations</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {checkResult.non_compliant.map((reg, i) => (
                          <div key={i} className="flex items-center justify-between p-3 bg-red-50 rounded-lg">
                            <div className="flex items-center gap-3">
                              {getStatusIcon(reg.status)}
                              <div>
                                <p className="font-medium text-chemours-dark">{reg.framework}</p>
                                <p className="text-sm text-gray-500">{reg.notes}</p>
                              </div>
                            </div>
                            <Badge className="bg-red-600">{reg.status.toUpperCase()}</Badge>
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
                      <CardTitle className="text-yellow-600">Regulatory Warnings</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {checkResult.warnings.map((reg, i) => (
                          <div key={i} className="flex items-center justify-between p-3 bg-yellow-50 rounded-lg">
                            <div className="flex items-center gap-3">
                              {getStatusIcon(reg.status)}
                              <div>
                                <p className="font-medium text-chemours-dark">{reg.framework}</p>
                                <p className="text-sm text-gray-500">{reg.notes}</p>
                                {reg.limit_ppb && <p className="text-xs text-yellow-600">Limit: {reg.limit_ppb} ppb</p>}
                              </div>
                            </div>
                            <Badge className="bg-yellow-600">{reg.status.toUpperCase()}</Badge>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Future Predictions */}
                {cascade && Object.keys(cascade.predictions).length > 0 && (
                  <Card className="bg-white border-gray-200 shadow-sm">
                    <CardHeader>
                      <CardTitle className="text-chemours-dark flex items-center gap-2">
                        <Calendar className="h-5 w-5 text-chemours-orange" />
                        {cascade.forecast_year} Regulatory Forecast
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {Object.entries(cascade.predictions).map(([key, pred]) => (
                          <div key={key} className="p-3 bg-gray-50 rounded-lg">
                            <div className="flex items-center justify-between mb-2">
                              <span className="font-medium text-chemours-dark">{key.replace(/_/g, " ")}</span>
                              <Badge className={getRegulatoryStageStyle(pred.regulatory_stage)}>
                                {getRegulatoryStageLabel(pred.regulatory_stage)}
                              </Badge>
                            </div>
                            <p className="text-sm text-gray-500">{pred.status}</p>
                            {pred.source && (
                              <p className="text-xs text-gray-400 mt-1 italic">Source: {pred.source}</p>
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
                      <p className="mt-4 text-sm text-chemours-red italic">{cascade.recommendation}</p>
                    </CardContent>
                  </Card>
                )}
              </>
            ) : (
              <Card className="bg-white border-gray-200 shadow-sm">
                <CardContent className="py-16 text-center">
                  <div className="h-16 w-16 mx-auto mb-4 rounded-full bg-gradient-to-r from-chemours-red to-chemours-orange flex items-center justify-center">
                    <Globe className="h-8 w-8 text-white" />
                  </div>
                  <h3 className="text-xl font-semibold text-chemours-dark mb-2">Regulatory Compliance Checker</h3>
                  <p className="text-gray-500 max-w-md mx-auto">
                    Check materials and their degradation products against EPA MCL, EU REACH, CA Prop 65, and Stockholm Convention.
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

export default RegulatoryCompliance;
