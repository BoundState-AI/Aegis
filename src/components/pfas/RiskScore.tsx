import { Card } from "@/components/ui/card";

interface RiskScoreProps {
  score: number;
}

const RiskScore = ({ score }: RiskScoreProps) => {
  const getRiskLevel = (score: number) => {
    if (score >= 75) return { label: "HIGH", color: "bg-destructive" };
    if (score >= 50) return { label: "MEDIUM", color: "bg-yellow-500" };
    return { label: "LOW", color: "bg-green-500" };
  };

  const risk = getRiskLevel(score);

  return (
    <Card className="p-6">
      <h2 className="text-xl font-semibold mb-4">Risk Assessment</h2>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <span className="text-lg font-medium">Overall Risk Score</span>
          <span className="text-3xl font-bold">{score}/100</span>
        </div>
        
        <div className="w-full bg-muted rounded-full h-8 overflow-hidden">
          <div 
            className={`h-full ${risk.color} transition-all duration-500 flex items-center justify-end pr-4`}
            style={{ width: `${score}%` }}
          >
            <span className="text-white font-semibold text-sm">{risk.label}</span>
          </div>
        </div>

        <p className="text-sm text-muted-foreground">
          Risk score based on PFAS formation probability, regulatory status, and exposure potential
        </p>
      </div>
    </Card>
  );
};

export default RiskScore;