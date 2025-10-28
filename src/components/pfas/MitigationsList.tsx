import { CheckCircle2 } from "lucide-react";

interface MitigationsListProps {
  mitigations: string[];
}

const MitigationsList = ({ mitigations }: MitigationsListProps) => {
  if (!mitigations || mitigations.length === 0) {
    return <p className="text-muted-foreground">No specific mitigations recommended for these conditions.</p>;
  }

  return (
    <ul className="space-y-3">
      {mitigations.map((mitigation, idx) => (
        <li key={idx} className="flex items-start gap-3">
          <CheckCircle2 className="h-5 w-5 text-primary mt-0.5 flex-shrink-0" />
          <span className="text-foreground leading-relaxed">{mitigation}</span>
        </li>
      ))}
    </ul>
  );
};

export default MitigationsList;