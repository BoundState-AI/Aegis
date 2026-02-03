import { Info } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface Product {
  name: string;
  /** Literature-derived evidence strength (0-1) */
  evidence_strength: number;
  /** Literature agreement range */
  support_lower: number;
  support_upper: number;
  /** Number of observations (optional) */
  observation_count?: number;
  /** Number of papers (optional) */
  paper_count?: number;
  // Legacy fields for backwards compatibility
  probability_mean?: number;
  ci_lower?: number;
  ci_upper?: number;
}

interface ProbabilityChartProps {
  products: Product[];
}

const ProbabilityChart = ({ products }: ProbabilityChartProps) => {
  if (!products || products.length === 0) {
    return <p className="text-muted-foreground">No PFAS products detected under these conditions.</p>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 text-sm text-muted-foreground border-b pb-3">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center gap-1 cursor-help">
                <Info className="h-4 w-4" />
                <span>About Evidence Strength</span>
              </div>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="max-w-sm p-3">
              <p className="text-sm">
                <strong>Evidence Strength</strong> reflects agreement across peer-reviewed sources.
                A score of 0.91 indicates strong consensus across multiple independent studies that
                this degradation pathway occurs under specified conditions.
              </p>
              <p className="text-sm mt-2 text-muted-foreground">
                Based on observations from published literature.
                <strong> Not a statistical probability of formation.</strong>
              </p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      {products.map((product, idx) => {
        // Support both new and legacy field names
        const strength = product.evidence_strength ?? product.probability_mean ?? 0;
        const lower = product.support_lower ?? product.ci_lower ?? 0;
        const upper = product.support_upper ?? product.ci_upper ?? 1;

        return (
          <div key={idx} className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-lg">{product.name}</span>
              <span className="text-sm font-medium">
                Evidence Strength: {(strength * 100).toFixed(1)}%
              </span>
            </div>

            <div className="relative h-12 bg-muted rounded-lg overflow-hidden">
              <div
                className="absolute h-full bg-primary/20"
                style={{
                  left: `${lower * 100}%`,
                  width: `${(upper - lower) * 100}%`
                }}
              />

              <div
                className="absolute h-full w-1 bg-primary"
                style={{ left: `${strength * 100}%` }}
              />
            </div>

            <div className="flex justify-between text-xs text-muted-foreground">
              <span>
                Literature Agreement Range: [{(lower * 100).toFixed(1)}% – {(upper * 100).toFixed(1)}%]
                {product.paper_count && ` (${product.paper_count} papers)`}
              </span>
              <span>Evidence Scale: 0% → 100%</span>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default ProbabilityChart;
