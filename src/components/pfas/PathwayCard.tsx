import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, AlertTriangle, ExternalLink, ChevronDown, ChevronUp, Info } from "lucide-react";
import { PathwayResult } from "@/types/pfas";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { SpicyTooltipBody } from "@/components/ui/spicy-tooltip-body";

interface PathwayCardProps {
  pathway: PathwayResult;
}

const PathwayCard = ({ pathway }: PathwayCardProps) => {
  const { t } = useTranslation();
  const [showRegulatory, setShowRegulatory] = useState(false);
  const [showEvidence, setShowEvidence] = useState(false);

  // Extract unique DOIs from evidence array
  const getUniqueDois = (evidence: typeof pathway.evidence): string[] => {
    const dois = evidence.map(ev => ev.doi).filter((doi): doi is string => !!doi);
    return [...new Set(dois)];
  };

  // Support both new and legacy field names
  const evidenceStrength = pathway.evidence_strength ?? pathway.probability_mean;
  const agreementLow = pathway.literature_agreement?.low ?? pathway.probability_ci_90.low;
  const agreementHigh = pathway.literature_agreement?.high ?? pathway.probability_ci_90.high;

  const strengthPercent = (evidenceStrength * 100).toFixed(1);
  const rangeLow = (agreementLow * 100).toFixed(1);
  const rangeHigh = (agreementHigh * 100).toFixed(1);

  return (
    <Card className="p-6 space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <h3 className="text-2xl font-bold text-foreground">{pathway.product}</h3>
            {pathway.plausible ? (
              <CheckCircle2 className="h-6 w-6 text-risk-low flex-shrink-0" />
            ) : (
              <AlertTriangle className="h-6 w-6 text-risk-high flex-shrink-0" />
            )}
          </div>
          <Badge variant="secondary" className="mb-3">
            {pathway.mechanism}
          </Badge>
          {!pathway.plausible && (
            <p className="text-sm text-muted-foreground italic mt-2">
              {pathway.plausibility_notes}
            </p>
          )}
        </div>
      </div>

      {/* Pathway Chain */}
      <div className="flex items-center gap-2 flex-wrap text-sm">
        {pathway.pathway.map((step, idx) => (
          <div key={idx} className="flex items-center gap-2">
            <span className={idx === 0 ? "font-semibold text-primary" : idx === pathway.pathway.length - 1 ? "font-semibold text-destructive" : "text-muted-foreground"}>
              {step}
            </span>
            {idx < pathway.pathway.length - 1 && (
              <span className="text-muted-foreground">→</span>
            )}
          </div>
        ))}
      </div>

      {/* Evidence Strength Visualization */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2">
            <span className="font-medium">{t("common.confidence")}</span>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Info className="h-4 w-4 text-muted-foreground cursor-help" />
                </TooltipTrigger>
                <TooltipContent side="top" className="max-w-xs p-3">
                  <SpicyTooltipBody>
                    <p className="text-sm">{t("tooltips.confidence.explanation")}</p>
                  </SpicyTooltipBody>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
          <span className="font-bold text-lg">{strengthPercent}%</span>
        </div>

        <div className="relative h-10 bg-muted rounded-lg overflow-hidden">
          <div
            className="absolute h-full bg-primary/30"
            style={{
              left: `${agreementLow * 100}%`,
              width: `${(agreementHigh - agreementLow) * 100}%`
            }}
          />
          <div
            className="absolute h-full w-1 bg-primary"
            style={{ left: `${evidenceStrength * 100}%` }}
          />
        </div>

        <p className="text-xs text-muted-foreground">
          {t("analysis.literatureAgreementRange", { low: rangeLow, high: rangeHigh })}
          {pathway.paper_count ? ` • ${t("analysis.paperCountShort", { count: pathway.paper_count })}` : ""}
          {pathway.observation_count ? ` • ${t("analysis.observationCountShort", { count: pathway.observation_count })}` : ""}
        </p>

        {/* Source DOI Links */}
        {pathway.evidence.length > 0 && getUniqueDois(pathway.evidence).length > 0 && (
          <div className="flex items-center gap-2 flex-wrap text-sm pt-2">
            <span className="text-muted-foreground font-medium">{t("common.sources")}:</span>
            {getUniqueDois(pathway.evidence).slice(0, 3).map((doi, idx) => (
              <a
                key={idx}
                href={`https://doi.org/${doi}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
              >
                <ExternalLink className="h-3 w-3" />
                <span className="font-mono text-xs">{doi}</span>
              </a>
            ))}
            {getUniqueDois(pathway.evidence).length > 3 && (
              <button
                onClick={() => setShowEvidence(true)}
                className="text-xs text-muted-foreground hover:text-primary transition-colors"
              >
                {t("analysis.moreSources", { count: getUniqueDois(pathway.evidence).length - 3 })}
              </button>
            )}
          </div>
        )}
      </div>

      {/* Regulatory Status Toggle */}
      <div className="border-t pt-4">
        <Button
          variant="ghost"
          onClick={() => setShowRegulatory(!showRegulatory)}
          className="w-full justify-between"
        >
          <span className="font-semibold">{t("analysis.regulatoryStatus")}</span>
          {showRegulatory ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </Button>
        
        {showRegulatory && (
          <div className="mt-4 space-y-3">
            {pathway.regulatory_status.is_regulated ? (
              <>
                <div className="flex flex-wrap gap-2">
                  {pathway.regulatory_status.jurisdictions.map((j, idx) => (
                    <Badge key={idx} variant="destructive">
                      {j.name}: {j.status}
                    </Badge>
                  ))}
                </div>
                {pathway.regulatory_status.litigation.length > 0 && (
                  <div className="bg-risk-high/10 border border-risk-high/20 rounded-lg p-3">
                    <p className="font-semibold text-sm mb-2 flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4" />
                      {t("analysis.litigationWarnings")}
                    </p>
                    {pathway.regulatory_status.litigation.map((lit, idx) => (
                      <div key={idx} className="text-sm mb-2 last:mb-0">
                        <span className="font-medium">{lit.case}:</span> {lit.context}
                      </div>
                    ))}
                  </div>
                )}
                {pathway.regulatory_status.effective_date && (
                  <p className="text-sm text-muted-foreground">
                    {t("regulatory.effective")}: {pathway.regulatory_status.effective_date}
                  </p>
                )}
              </>
            ) : (
              <p className="text-sm text-muted-foreground">{t("analysis.noCurrentRegulatoryRestrictions")}</p>
            )}
          </div>
        )}
      </div>

      {/* Evidence Toggle */}
      <div className="border-t pt-4">
        <Button
          variant="ghost"
          onClick={() => setShowEvidence(!showEvidence)}
          className="w-full justify-between"
        >
          <span className="font-semibold">{t("analysis.scientificEvidence")} ({pathway.evidence.length})</span>
          {showEvidence ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </Button>
        
        {showEvidence && (
          <div className="mt-4 space-y-3">
            {pathway.evidence.map((ev, idx) => (
              <div key={idx} className="bg-muted/50 rounded-lg p-3 text-sm">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <span className="font-semibold">{ev.source}</span>
                  {ev.doi && (
                    <a 
                      href={`https://doi.org/${ev.doi}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary hover:text-primary/80"
                    >
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  )}
                </div>
                <p className="text-muted-foreground italic border-l-2 border-primary pl-3">
                  "{ev.fragment}"
                </p>
                {ev.page && (
                  <p className="text-xs text-muted-foreground mt-1">{t("analysis.pageNumber", { page: ev.page })}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
};

export default PathwayCard;
