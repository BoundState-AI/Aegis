import * as React from "react";
import { useTranslation } from "react-i18next";
import { Info } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { SpicyTooltipBody } from "@/components/ui/spicy-tooltip-body";

interface ProductLabelProps {
  /** The product value, e.g., "P1 (M/Z=384.9)" or "PFOA" */
  value: string;
}

// Regex to match intermediate product patterns like "P1 (M/Z=384.9)"
const INTERMEDIATE_PATTERN = /^(P\d+)\s*\(M\/Z=(\d+\.?\d*)\)$/i;

// Regex to match just P1, P2 style names (without M/Z)
const SIMPLE_INTERMEDIATE_PATTERN = /^P\d+$/i;

// Regex to match M/Z anywhere in the string
const MZ_PATTERN = /M\/Z[=:]?\s*(\d+\.?\d*)/i;

export const ProductLabel = ({ value }: ProductLabelProps) => {
  const { t } = useTranslation();

  // Check for full intermediate pattern: "P1 (M/Z=384.9)"
  const fullMatch = value.match(INTERMEDIATE_PATTERN);
  if (fullMatch) {
    const [, productId, mzValue] = fullMatch;
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="inline-flex items-center gap-1 cursor-help">
            <span className="font-semibold text-daikin-blue">{productId}</span>
            <span className="text-gray-500">(M/Z={mzValue})</span>
            <Info className="h-3.5 w-3.5 text-muted-foreground" />
          </span>
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-sm p-3">
          <SpicyTooltipBody>
            <p className="text-sm">
              <strong>{productId}</strong>: {t('tooltips.productIntermediate.explanation')}
            </p>
            <p className="text-sm text-muted-foreground">
              <strong>M/Z={mzValue}</strong>: {t('tooltips.massToCharge.explanation')}
            </p>
          </SpicyTooltipBody>
        </TooltipContent>
      </Tooltip>
    );
  }

  // Check for simple intermediate: "P1", "P2", etc.
  if (SIMPLE_INTERMEDIATE_PATTERN.test(value)) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="inline-flex items-center gap-1 cursor-help">
            <span className="font-semibold text-daikin-blue">{value}</span>
            <Info className="h-3.5 w-3.5 text-muted-foreground" />
          </span>
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-xs p-3">
          <SpicyTooltipBody>
            <p className="text-sm">
              <strong>{value}</strong>: {t('tooltips.productIntermediate.explanation')}
            </p>
          </SpicyTooltipBody>
        </TooltipContent>
      </Tooltip>
    );
  }

  // Check for M/Z anywhere in the string (partial match)
  const mzMatch = value.match(MZ_PATTERN);
  if (mzMatch) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="inline-flex items-center gap-1 cursor-help">
            {value}
            <Info className="h-3.5 w-3.5 text-muted-foreground" />
          </span>
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-xs p-3">
          <SpicyTooltipBody>
            <p className="text-sm">
              <strong>M/Z</strong>: {t('tooltips.massToCharge.explanation')}
            </p>
          </SpicyTooltipBody>
        </TooltipContent>
      </Tooltip>
    );
  }

  // Simple product name - no tooltip needed
  return <span>{value}</span>;
};
