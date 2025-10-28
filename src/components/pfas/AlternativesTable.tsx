import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { AlternativeOption } from "@/types/pfas";

interface AlternativesTableProps {
  alternatives: AlternativeOption[];
}

const AlternativesTable = ({ alternatives }: AlternativesTableProps) => {
  if (!alternatives || alternatives.length === 0) {
    return null;
  }

  const getRiskColor = (score: number) => {
    if (score <= 25) return "bg-risk-low";
    if (score <= 50) return "bg-risk-medium";
    if (score <= 75) return "bg-risk-high";
    return "bg-risk-critical";
  };

  const getRiskCategory = (score: number) => {
    if (score <= 25) return "LOW";
    if (score <= 50) return "MEDIUM";
    if (score <= 75) return "HIGH";
    return "CRITICAL";
  };

  return (
    <Card className="p-6">
      <h2 className="text-2xl font-bold mb-4">Alternative Materials</h2>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="font-semibold">Material</TableHead>
            <TableHead className="font-semibold">Risk Score</TableHead>
            <TableHead className="font-semibold">Advantages</TableHead>
            <TableHead className="font-semibold">Tradeoffs</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {alternatives.map((alt, idx) => (
            <TableRow key={idx}>
              <TableCell className="font-medium">{alt.material}</TableCell>
              <TableCell>
                <div className="flex items-center gap-2">
                  <div className={`h-2 w-16 rounded-full ${getRiskColor(alt.risk_score)}`} />
                  <span className="font-semibold">{alt.risk_score}</span>
                  <Badge variant="outline" className="ml-2">
                    {getRiskCategory(alt.risk_score)}
                  </Badge>
                </div>
              </TableCell>
              <TableCell className="text-risk-low">{alt.pro}</TableCell>
              <TableCell className="text-risk-high">{alt.con}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  );
};

export default AlternativesTable;
