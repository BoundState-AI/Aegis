import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AnalyzeResponse } from "@/types/pfas";

interface RiskScoreHeroProps {
  data: AnalyzeResponse;
}

const RiskScoreHero = ({ data }: RiskScoreHeroProps) => {
  const getRiskColor = (category: string) => {
    switch (category) {
      case "LOW": return "bg-risk-low";
      case "MEDIUM": return "bg-risk-medium";
      case "HIGH": return "bg-risk-high";
      case "CRITICAL": return "bg-risk-critical";
      default: return "bg-muted";
    }
  };

  const getRiskTextColor = (category: string) => {
    switch (category) {
      case "LOW": return "text-risk-low";
      case "MEDIUM": return "text-risk-medium";
      case "HIGH": return "text-risk-high";
      case "CRITICAL": return "text-risk-critical";
      default: return "text-foreground";
    }
  };

  return (
    <Card className="p-8 border-2">
      <div className="grid md:grid-cols-2 gap-8">
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <Badge variant="outline" className="text-lg px-4 py-1">
              {data.risk_category}
            </Badge>
            <span className="text-sm text-muted-foreground">
              Analysis completed in {data.search_time_ms}ms
            </span>
          </div>
          
          <div>
            <h2 className="text-4xl font-bold mb-2">
              <span className={getRiskTextColor(data.risk_category)}>{data.risk_score}</span>
              <span className="text-muted-foreground">/100</span>
            </h2>
            <p className="text-lg text-muted-foreground">Risk Score</p>
          </div>

          <div className="space-y-2">
            <p className="text-sm font-medium text-muted-foreground">Material & Conditions</p>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="font-semibold">Material:</span> {data.material}
              </div>
              <div>
                <span className="font-semibold">Temperature:</span> {data.conditions.temperature}°C
              </div>
              <div>
                <span className="font-semibold">Atmosphere:</span> {data.conditions.atmosphere}
              </div>
              <div>
                <span className="font-semibold">Duration:</span> {data.conditions.time_hours}h
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center">
          <div className="w-full space-y-3">
            <div className="h-12 bg-muted rounded-full overflow-hidden">
              <div 
                className={`h-full ${getRiskColor(data.risk_category)} transition-all duration-700 flex items-center justify-end pr-6`}
                style={{ width: `${data.risk_score}%` }}
              >
                <span className="text-white font-bold text-lg">{data.risk_category}</span>
              </div>
            </div>
            <div className="flex justify-between text-xs text-muted-foreground px-2">
              <span>0 (Minimal)</span>
              <span>25 (Low)</span>
              <span>50 (Moderate)</span>
              <span>75 (High)</span>
              <span>100 (Critical)</span>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
};

export default RiskScoreHero;
