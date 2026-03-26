import { Info } from "lucide-react";
import { useTranslation } from "react-i18next";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { SpicyTooltipBody } from "@/components/ui/spicy-tooltip-body";

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
  const { t } = useTranslation();

  if (!products || products.length === 0) {
    return <p className="text-muted-foreground">{t("analysis.noPfasProductsDetected")}</p>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2 text-sm text-muted-foreground border-b pb-3">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center gap-1 cursor-help">
                <Info className="h-4 w-4" />
                <span>{t("analysis.aboutEvidenceStrength")}</span>
              </div>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="max-w-sm p-3">
              <SpicyTooltipBody>
                <p className="text-sm">
                  <strong>{t("analysis.evidenceStrength")}</strong> {t("analysis.evidenceStrengthTooltipPrimary")}
                </p>
                <p className="text-sm text-muted-foreground">
                  {t("analysis.evidenceStrengthTooltipSecondary")}{" "}
                  <strong>{t("analysis.evidenceStrengthTooltipEmphasis")}</strong>
                </p>
              </SpicyTooltipBody>
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
                {t("analysis.evidenceStrength")}: {(strength * 100).toFixed(1)}%
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
                {t("analysis.literatureAgreementRange", {
                  low: (lower * 100).toFixed(1),
                  high: (upper * 100).toFixed(1),
                })}
                {product.paper_count && ` (${t("analysis.paperCountShort", { count: product.paper_count })})`}
              </span>
              <span>{t("analysis.evidenceScaleRange")}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default ProbabilityChart;
