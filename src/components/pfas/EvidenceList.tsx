import { Card } from "@/components/ui/card";
import { ExternalLink } from "lucide-react";

interface Evidence {
  source: string;
  citation?: string;
  snippet?: string;
  url?: string;
}

interface EvidenceListProps {
  evidence: Evidence[];
}

const EvidenceList = ({ evidence }: EvidenceListProps) => {
  if (!evidence || evidence.length === 0) {
    return <p className="text-muted-foreground">No evidence citations available.</p>;
  }

  return (
    <div className="space-y-4">
      {evidence.map((item, idx) => (
        <Card key={idx} className="p-4 bg-muted/50">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 space-y-2">
              <p className="font-semibold text-foreground">{item.source}</p>
              {item.citation && (
                <p className="text-sm text-muted-foreground italic">{item.citation}</p>
              )}
              {item.snippet && (
                <p className="text-sm leading-relaxed border-l-2 border-primary pl-3 mt-2">
                  "{item.snippet}"
                </p>
              )}
            </div>
            {item.url && (
              <a 
                href={item.url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-primary hover:text-primary/80 transition-colors"
              >
                <ExternalLink className="h-5 w-5" />
              </a>
            )}
          </div>
        </Card>
      ))}
    </div>
  );
};

export default EvidenceList;