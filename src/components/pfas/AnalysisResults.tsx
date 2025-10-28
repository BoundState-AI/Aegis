import { Card } from "@/components/ui/card";
import RiskScore from "./RiskScore";
import ProbabilityChart from "./ProbabilityChart";
import RegulatoryTable from "./RegulatoryTable";
import MitigationsList from "./MitigationsList";
import EvidenceList from "./EvidenceList";

interface AnalysisResultsProps {
  data: any;
}

const AnalysisResults = ({ data }: AnalysisResultsProps) => {
  return (
    <div className="space-y-6">
      <Card className="p-6 bg-accent">
        <h2 className="text-xl font-semibold mb-4">Analysis Summary</h2>
        <p className="text-lg leading-relaxed">{data.summary || "Analysis complete. Review detailed results below."}</p>
      </Card>

      <RiskScore score={data.risk_score || 0} />

      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">PFAS Formation Probability</h2>
        <ProbabilityChart products={data.products || []} />
      </Card>

      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">Regulatory Status</h2>
        <RegulatoryTable products={data.products || []} />
      </Card>

      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">Operational Mitigations</h2>
        <MitigationsList mitigations={data.mitigations || []} />
      </Card>

      <Card className="p-6">
        <h2 className="text-xl font-semibold mb-4">Evidence & Citations</h2>
        <EvidenceList evidence={data.evidence || []} />
      </Card>
    </div>
  );
};

export default AnalysisResults;