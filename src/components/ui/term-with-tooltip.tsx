import * as React from "react";
import { useTranslation } from "react-i18next";
import { Info } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface TermWithTooltipProps {
  /** i18n key for the tooltip explanation (e.g., "tooltips.confidence") */
  explanationKey: string;
  /** The content to display as the trigger */
  children: React.ReactNode;
  /** Which side to show the tooltip */
  side?: "top" | "bottom" | "left" | "right";
  /** Whether to show the info icon next to the term */
  showIcon?: boolean;
  /** Additional className for the wrapper */
  className?: string;
}

export const TermWithTooltip = ({
  explanationKey,
  children,
  side = "top",
  showIcon = true,
  className = "",
}: TermWithTooltipProps) => {
  const { t } = useTranslation();

  // Get the explanation text from i18n
  const explanation = t(`${explanationKey}.explanation`);

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className={`inline-flex items-center gap-1 cursor-help ${className}`}>
          {children}
          {showIcon && <Info className="h-3.5 w-3.5 text-muted-foreground" />}
        </span>
      </TooltipTrigger>
      <TooltipContent side={side} className="max-w-xs p-3">
        <p className="text-sm">{explanation}</p>
      </TooltipContent>
    </Tooltip>
  );
};
