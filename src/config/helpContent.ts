/**
 * Central help content configuration for all AEGIS pages.
 *
 * Each entry provides structured help that renders in the PageHelp modal.
 * Now supports i18n translations via the useHelpContent hook.
 */

import { useTranslation } from "react-i18next";

export interface RelatedPage {
  name: string;
  path: string;
}

export interface HelpLegendItem {
  label: string;
  meaning: string;
}

export interface HelpActionItem {
  action: string;
  effect: string;
}

export interface HelpContent {
  title: string;
  description: string;
  whatItDoes: string[];
  howToUse: string[];
  useCases: string[];
  tips?: string[];
  flagsAndStatuses?: HelpLegendItem[];
  actionsAndButtons?: HelpActionItem[];
  relatedPages?: RelatedPage[];
  apiEndpoint?: string;
}

// Hook to get translated help content
export const useHelpContent = () => {
  const { t } = useTranslation();

  const helpContent: Record<string, HelpContent> = {
    fateExplorer: {
      title: t('help.fateExplorer.title', 'Fate Explorer'),
      description: t('help.fateExplorer.description',
        'Explore PFAS degradation pathways from the peer-reviewed literature. Built on 732 pathways extracted from 353 papers with DOI-traceable evidence.'),
      whatItDoes: t('help.fateExplorer.whatItDoes', { returnObjects: true, defaultValue: [
        "Maps parent-to-product degradation pathways for PFAS compounds",
        "Shows observation counts, evidence scores, and temperature ranges from the literature",
        "Identifies hazard levels and regulatory status of degradation products",
        "Links every pathway to its source DOI for independent verification",
      ]}) as string[],
      howToUse: t('help.fateExplorer.howToUse', { returnObjects: true, defaultValue: [
        "Select or search for a parent compound from the dropdown",
        "Review the degradation products table — sorted by evidence score",
        "Click any row to see the full evidence chain with verbatim quotes",
        "Use the temperature and atmosphere filters to narrow results",
      ]}) as string[],
      useCases: t('help.fateExplorer.useCases', { returnObjects: true, defaultValue: [
        "Screen a fluoropolymer for known thermal degradation products",
        "Identify whether a compound degrades to regulated PFAS (e.g. PFOA, PFOS)",
        "Gather DOI citations for a regulatory submission or expert report",
      ]}) as string[],
      tips: t('help.fateExplorer.tips', { returnObjects: true, defaultValue: [
        "Higher evidence scores indicate more independent observations across papers",
        "Temperature ranges show the experimental conditions where degradation was observed",
        "Products flagged as 'regulated' appear in EPA, EU, or Stockholm Convention lists",
      ]}) as string[],
      relatedPages: [
        { name: t('nav.evidence', 'Evidence Chain'), path: "/evidence" },
        { name: t('nav.regulatory', 'Regulatory'), path: "/regulatory" },
        { name: t('nav.tier1', 'Tier 1'), path: "/tier1" },
      ],
      apiEndpoint: "/api/v1/pathways",
    },

    litigation: {
      title: t('help.litigation.title', 'SENTINEL — Litigation Risk'),
      description: t('help.litigation.description',
        'Publication dynamics analysis and litigation risk forecasting. Tracks scientific attention trajectories using physics-inspired metrics (velocity, acceleration, jerk) derived from PubMed publication data.'),
      whatItDoes: t('help.litigation.whatItDoes', { returnObjects: true, defaultValue: [
        "Tracks publication volume, velocity, acceleration, and jerk for PFAS compounds",
        "Provides a GenX case study backtest against 412 PubMed publications and 14 key events",
        "Forecasts litigation risk windows based on publication dynamics patterns",
        "Maps the relationship between scientific attention and regulatory/legal action",
      ]}) as string[],
      howToUse: t('help.litigation.howToUse', { returnObjects: true, defaultValue: [
        "Use the GenX Case Study tab to see the validated backtest against real events",
        "Switch to the Risk Forecast tab to view forward-looking projections",
        "Review the publication dynamics chart — rising acceleration signals emerging risk",
        "Check the timeline of key events to see how science preceded litigation",
      ]}) as string[],
      useCases: t('help.litigation.useCases', { returnObjects: true, defaultValue: [
        "Assess whether a compound is on a litigation trajectory similar to GenX or PFOA",
        "Identify the publication velocity inflection points that preceded past lawsuits",
        "Support early-warning monitoring for compounds in your portfolio",
      ]}) as string[],
      tips: t('help.litigation.tips', { returnObjects: true, defaultValue: [
        "Publication count is 'position' — velocity is papers/year, acceleration is how fast velocity changes",
        "Jerk (third derivative) spikes often precede regulatory action by 12–18 months",
        "The GenX analysis incorporates 412 peer-reviewed publications and regulatory filing data",
      ]}) as string[],
      relatedPages: [
        { name: t('nav.portfolio', 'Portfolio'), path: "/portfolio" },
        { name: t('nav.evidence', 'Evidence Chain'), path: "/evidence" },
      ],
      apiEndpoint: "/api/v1/litigation",
    },

    regulatory: {
      title: t('help.regulatory.title', 'Regulatory Compliance'),
      description: t('help.regulatory.description',
        'Check compounds against EPA, EU REACH, Stockholm Convention, APAC jurisdictions, and state-level regulatory frameworks. Covers MCLs, health advisories, and emerging standards.'),
      whatItDoes: t('help.regulatory.whatItDoes', { returnObjects: true, defaultValue: [
        "Screens compounds against multi-jurisdictional regulatory databases",
        "Shows MCL (Maximum Contaminant Level) values where established",
        "Identifies health advisories, action levels, and notification thresholds",
        "Flags compounds on the EPA PFAS Action Plan, Stockholm Convention annexes, and APAC frameworks (Japan CSCL, K-REACH, China MEE, Australia NHMRC, Singapore NEA, Taiwan MOENV, India FSSAI)",
      ]}) as string[],
      howToUse: t('help.regulatory.howToUse', { returnObjects: true, defaultValue: [
        "Enter a compound name or CAS number in the search field",
        "Review the regulatory status cards for each jurisdiction",
        "Check whether the compound has established limits or is under review",
        "Export results for inclusion in compliance reports",
      ]}) as string[],
      useCases: t('help.regulatory.useCases', { returnObjects: true, defaultValue: [
        "Verify whether a degradation product triggers regulatory obligations",
        "Compare regulatory status across EPA, EU, APAC, and state frameworks",
        "Build the regulatory section of an environmental impact assessment",
      ]}) as string[],
      tips: t('help.regulatory.tips', { returnObjects: true, defaultValue: [
        "APAC regulations are accelerating; monitor finalized-to-binding transitions by jurisdiction",
        "State-level limits (e.g., Michigan, New Jersey) are often stricter than federal MCLs",
        "Use alongside Fate Explorer to check if degradation products are regulated",
      ]}) as string[],
      flagsAndStatuses: t('help.regulatory.flagsAndStatuses', { returnObjects: true, defaultValue: [
        { label: "Regulatory nav badge (red number)", meaning: "Count of HITL items still pending review or approval." },
        { label: "PENDING_REVIEW", meaning: "First gate state. Analyst must confirm/escalate/dismiss before briefing approval." },
        { label: "PENDING_APPROVAL", meaning: "Second gate state. Item has been reviewed and awaits final approve/hold decision." },
        { label: "Human review required", meaning: "Set automatically for critical flags, class-only matches, or low-confidence pathways." },
        { label: "Critical flags: N", meaning: "Number of CRITICAL threat flags from resolver output for that item." },
        { label: "ENACTED / FINAL PENDING / PROPOSED / UNDER CONSIDERATION / MONITORING", meaning: "Regulatory maturity stages used in the Landscape forecast." },
        { label: "Signal severity badges (critical/high/medium/low)", meaning: "Signal priority from L3/L4 triage and impact scoring." },
      ]}) as HelpLegendItem[],
      actionsAndButtons: t('help.regulatory.actionsAndButtons', { returnObjects: true, defaultValue: [
        { action: "Landscape", effect: "Jurisdiction/regulation baseline from governed assertions." },
        { action: "Signals", effect: "Live monitor feed of detected regulatory changes and why they matter." },
        { action: "Resolver", effect: "Run compound/product exposure analysis, including inherited liability." },
        { action: "Review Queue", effect: "Process analyst HITL gate actions for pending resolver outputs." },
        { action: "Check Compliance", effect: "Runs regulatory screening for the selected material and refreshes forecast cards." },
        { action: "Include Degradation Products", effect: "When enabled, includes downstream products in compliance evaluation." },
        { action: "Seed Demo / Clear Seeds", effect: "Insert or remove demo monitor signals for non-empty workflows and demos." },
        { action: "Confirm", effect: "Advance a PENDING_REVIEW item to PENDING_APPROVAL." },
        { action: "Escalate", effect: "Mark item for legal/regulatory escalation while retaining it in queue." },
        { action: "Dismiss", effect: "Close item with required written justification (captured in audit trail)." },
        { action: "Approve", effect: "Finalize a PENDING_APPROVAL item and remove it from pending queue." },
        { action: "Hold", effect: "Keep item in pending approval state for follow-up evidence/review." },
      ]}) as HelpActionItem[],
      relatedPages: [
        { name: t('nav.fateExplorer', 'Fate Explorer'), path: "/" },
        { name: t('nav.portfolio', 'Portfolio'), path: "/portfolio" },
      ],
      apiEndpoint: "/api/v1/regulatory",
    },

    portfolio: {
      title: t('help.portfolio.title', 'Portfolio Assessment'),
      description: t('help.portfolio.description',
        'Batch screening of compound portfolios for aggregate PFAS risk. Evaluates materials against degradation, regulatory, and litigation risk dimensions.'),
      whatItDoes: t('help.portfolio.whatItDoes', { returnObjects: true, defaultValue: [
        "Screens multiple compounds simultaneously against all AEGIS risk dimensions",
        "Generates a composite risk score combining degradation, regulatory, and litigation factors",
        "Ranks compounds by overall risk for prioritization",
        "Identifies the highest-risk degradation products across a portfolio",
      ]}) as string[],
      howToUse: t('help.portfolio.howToUse', { returnObjects: true, defaultValue: [
        "Select compounds to include in the portfolio assessment",
        "Review the risk matrix showing each compound's scores across dimensions",
        "Sort by overall risk score to identify priority compounds",
        "Drill into individual compounds for detailed pathway and regulatory data",
      ]}) as string[],
      useCases: t('help.portfolio.useCases', { returnObjects: true, defaultValue: [
        "Prioritize which fluoropolymers in a product line need deeper evaluation",
        "Compare risk profiles across alternative chemistries",
        "Generate a portfolio-level risk summary for executive review",
      ]}) as string[],
      relatedPages: [
        { name: t('nav.reports', 'Reports'), path: "/reports" },
        { name: t('nav.fateExplorer', 'Fate Explorer'), path: "/" },
        { name: t('nav.regulatory', 'Regulatory'), path: "/regulatory" },
      ],
      apiEndpoint: "/api/v1/portfolio",
    },

    reports: {
      title: t('help.reports.title', 'Executive Reports'),
      description: t('help.reports.description',
        'Generate structured risk assessment reports for stakeholders. Combines data from all AEGIS modules into formatted deliverables.'),
      whatItDoes: t('help.reports.whatItDoes', { returnObjects: true, defaultValue: [
        "Compiles pathway, regulatory, and risk data into structured report formats",
        "Generates executive summaries with key findings and recommendations",
        "Includes DOI-traceable evidence citations for every claim",
        "Produces output suitable for regulatory submissions or board presentations",
      ]}) as string[],
      howToUse: t('help.reports.howToUse', { returnObjects: true, defaultValue: [
        "Select the report type and target compounds",
        "Choose which modules to include (pathways, regulatory, litigation)",
        "Review the generated report and edit as needed",
        "Export to PDF or share with stakeholders",
      ]}) as string[],
      useCases: t('help.reports.useCases', { returnObjects: true, defaultValue: [
        "Prepare a risk assessment deliverable for a client engagement",
        "Generate a regulatory submission appendix with literature evidence",
        "Create an executive briefing on PFAS exposure for leadership",
      ]}) as string[],
      relatedPages: [
        { name: t('nav.portfolio', 'Portfolio'), path: "/portfolio" },
        { name: t('nav.evidence', 'Evidence Chain'), path: "/evidence" },
      ],
      apiEndpoint: "/api/v1/reports",
    },

    evidence: {
      title: t('help.evidence.title', 'Evidence Chain'),
      description: t('help.evidence.description',
        'Trace every AEGIS claim back to its source DOI. Browse the full corpus of 353 peer-reviewed papers and 732 extracted degradation pathways.'),
      whatItDoes: t('help.evidence.whatItDoes', { returnObjects: true, defaultValue: [
        "Provides full traceability from any risk assessment claim to source literature",
        "Shows verbatim quotes from papers with page/section locations",
        "Links to DOIs for direct access to source publications",
        "Displays extraction confidence scores for each evidence item",
      ]}) as string[],
      howToUse: t('help.evidence.howToUse', { returnObjects: true, defaultValue: [
        "Search by compound name, DOI, or keyword",
        "Browse pathways grouped by their source publication",
        "Click any DOI link to open the source paper directly",
        "Review verbatim quotes to verify the extraction accuracy",
      ]}) as string[],
      useCases: t('help.evidence.useCases', { returnObjects: true, defaultValue: [
        "Verify a specific degradation pathway claim before citing it in testimony",
        "Find all papers that discuss a particular compound's thermal behavior",
        "Audit the evidence quality behind a high-risk signal",
      ]}) as string[],
      tips: t('help.evidence.tips', { returnObjects: true, defaultValue: [
        "Evidence with multiple independent DOIs is more defensible than single-source claims",
        "Verbatim quotes are extracted directly — always verify against the source paper",
        "Confidence scores reflect extraction certainty, not scientific certainty",
      ]}) as string[],
      relatedPages: [
        { name: t('nav.fateExplorer', 'Fate Explorer'), path: "/" },
        { name: t('nav.reports', 'Reports'), path: "/reports" },
      ],
    },

    analysis: {
      title: t('help.analysis.title', 'PFAS Analysis'),
      description: t('help.analysis.description',
        'Thermal degradation analysis for fluoropolymer compounds. Focused analysis of degradation behavior under specific temperature and atmosphere conditions.'),
      whatItDoes: t('help.analysis.whatItDoes', { returnObjects: true, defaultValue: [
        "Analyzes thermal degradation behavior for specific PFAS compounds",
        "Shows degradation products at different temperature ranges",
        "Maps degradation under different atmospheric conditions (air, nitrogen, vacuum)",
        "Provides yield estimates where reported in the literature",
      ]}) as string[],
      howToUse: t('help.analysis.howToUse', { returnObjects: true, defaultValue: [
        "Select a compound and specify the conditions of interest",
        "Review the degradation product distribution across temperature ranges",
        "Compare behavior under different atmospheric conditions",
        "Use the evidence links to trace findings to source papers",
      ]}) as string[],
      useCases: t('help.analysis.useCases', { returnObjects: true, defaultValue: [
        "Evaluate what a fluoropolymer produces during incineration (>800°C)",
        "Compare degradation under manufacturing conditions vs. end-of-life scenarios",
        "Assess whether low-temperature processing stays below degradation thresholds",
      ]}) as string[],
      relatedPages: [
        { name: t('nav.fateExplorer', 'Fate Explorer'), path: "/" },
        { name: t('nav.evidence', 'Evidence Chain'), path: "/evidence" },
      ],
      apiEndpoint: "/api/v1/analysis",
    },

    intelligence: {
      title: t('help.intelligence.title', 'Regulatory Intelligence'),
      description: t('help.intelligence.description',
        'Monitor live regulatory signals, run recursive exposure resolution, and manage human-in-the-loop approvals.'),
      whatItDoes: t('help.intelligence.whatItDoes', { returnObjects: true, defaultValue: [
        "Aggregates monitored regulatory signals with severity and classification",
        "Runs recursive compound-to-product exposure analysis through degradation pathways",
        "Queues resolver outputs for analyst review before approval and distribution",
        "Maintains a single operational view of monitoring + resolver + approvals",
      ]}) as string[],
      howToUse: t('help.intelligence.howToUse', { returnObjects: true, defaultValue: [
        "Use Signals to review latest detected changes and severity",
        "Run Resolver on a product, compound, CAS, or SMILES to generate exposure outputs",
        "Process pending items in the Review Queue using confirm/escalate/dismiss/approve actions",
        "Add justifications for dismissals and other analyst decisions",
      ]}) as string[],
      useCases: t('help.intelligence.useCases', { returnObjects: true, defaultValue: [
        "Triage a newly detected EPA/ECHA signal and assess Chemours exposure impact",
        "Run inherited-liability checks for fluoropolymer products",
        "Operationalize analyst sign-off before executive distribution",
      ]}) as string[],
      tips: t('help.intelligence.tips', { returnObjects: true, defaultValue: [
        "Critical flags should always be escalated for legal/regulatory review",
        "Class-level matches require analyst confirmation of product applicability",
        "Use resolver IDs to track decisions across gate states and audit logs",
      ]}) as string[],
      flagsAndStatuses: t('help.intelligence.flagsAndStatuses', { returnObjects: true, defaultValue: [
        { label: "critical/high/medium/low", meaning: "Signal severity from triage and Chemours impact scoring." },
        { label: "PENDING_REVIEW / PENDING_APPROVAL", meaning: "HITL gate states for resolver outputs." },
        { label: "Human review required", meaning: "Analyst intervention is mandatory before distribution." },
      ]}) as HelpLegendItem[],
      actionsAndButtons: t('help.intelligence.actionsAndButtons', { returnObjects: true, defaultValue: [
        { action: "Refresh", effect: "Reload live signals and pending queue data from API." },
        { action: "Run Resolver", effect: "Submit a resolver job and create a queue item with gate status." },
        { action: "Confirm / Escalate / Dismiss / Approve / Hold", effect: "Apply HITL actions with audit logging and state transitions." },
      ]}) as HelpActionItem[],
      relatedPages: [
        { name: t('nav.regulatory', 'Regulatory'), path: "/regulatory" },
        { name: t('nav.tier1', 'Tier 1'), path: "/tier1" },
        { name: t('nav.evidence', 'Evidence Chain'), path: "/evidence" },
      ],
      apiEndpoint: "/api/v1/resolver/resolve",
    },

    tier1: {
      title: t('help.tier1.title', 'Structural Intelligence (Tier 1 + Tier 2)'),
      description: t('help.tier1.description',
        'Structure-aware compound screening combining Tier 1 (Morgan fingerprint similarity against 10,974 EPA PFAS compounds) with Tier 2 (substructure pattern mining with Wilson score confidence intervals from 732 literature pathways). Not a prediction engine — reports what the published literature shows.'),
      whatItDoes: t('help.tier1.whatItDoes', { returnObjects: true, defaultValue: [
        "Tier 1: Computes Tanimoto similarity against the full EPA PFAS database and aggregates degradation endpoints",
        "Tier 2: Detects substructure patterns (SMARTS + algorithmic chain analysis) and correlates them with endpoint buckets",
        "Reports Wilson score confidence intervals — honest uncertainty, not fake precision",
        "Tracks precursor resolution coverage so you know how grounded the correlations are",
        "Returns DOI-cited evidence for every pathway found",
      ]}) as string[],
      howToUse: t('help.tier1.howToUse', { returnObjects: true, defaultValue: [
        "Enter a SMILES string directly, or use a quick-select badge (GenX, PFOA, PFOS, 6:2 FTOH)",
        "Review the risk signal banner — HIGH (red), MEDIUM (amber), LOW (green)",
        "Check the Substructure Fingerprint card for detected patterns and fluorine metrics",
        "Expand Pattern-Based Endpoint Correlations to see confidence intervals from the corpus",
        "Use the Corpus Rules Explorer to browse all mined rules and coverage statistics",
      ]}) as string[],
      useCases: t('help.tier1.useCases', { returnObjects: true, defaultValue: [
        "Screen a novel compound by finding what happens to structurally similar PFAS",
        "Identify substructure patterns (e.g., long perfluoro chain + carboxylic acid) that correlate with specific endpoints",
        "Assess how well-grounded the correlations are via the coverage report",
        "Gather literature evidence for compounds without direct study data",
      ]}) as string[],
      tips: t('help.tier1.tips', { returnObjects: true, defaultValue: [
        "The risk signal reflects endpoint classes: long-chain acids and sulfonates = HIGH",
        "Tier 2 pattern badges are color-coded: blue = SMARTS, green = algorithmic, purple = classification",
        "Confidence intervals show the plausible range — wide intervals mean few supporting precursors",
        "The coverage report shows resolution rate — low coverage means rules are based on fewer compounds",
        "All evidence is DOI-linked — click any citation to verify the source paper",
      ]}) as string[],
      relatedPages: [
        { name: t('nav.fateExplorer', 'Fate Explorer'), path: "/" },
        { name: t('nav.evidence', 'Evidence Chain'), path: "/evidence" },
        { name: t('nav.regulatory', 'Regulatory'), path: "/regulatory" },
      ],
      apiEndpoint: "/api/v1/tier1",
    },
  };

  return helpContent;
};

// Default export for backwards compatibility (English fallback)
const helpContent: Record<string, HelpContent> = {
  fateExplorer: {
    title: "Fate Explorer",
    description:
      "Explore PFAS degradation pathways from the peer-reviewed literature. " +
      "Built on 732 pathways extracted from 353 papers with DOI-traceable evidence.",
    whatItDoes: [
      "Maps parent-to-product degradation pathways for PFAS compounds",
      "Shows observation counts, evidence scores, and temperature ranges from the literature",
      "Identifies hazard levels and regulatory status of degradation products",
      "Links every pathway to its source DOI for independent verification",
    ],
    howToUse: [
      "Select or search for a parent compound from the dropdown",
      "Review the degradation products table — sorted by evidence score",
      "Click any row to see the full evidence chain with verbatim quotes",
      "Use the temperature and atmosphere filters to narrow results",
    ],
    useCases: [
      "Screen a fluoropolymer for known thermal degradation products",
      "Identify whether a compound degrades to regulated PFAS (e.g. PFOA, PFOS)",
      "Gather DOI citations for a regulatory submission or expert report",
    ],
    tips: [
      "Higher evidence scores indicate more independent observations across papers",
      "Temperature ranges show the experimental conditions where degradation was observed",
      "Products flagged as 'regulated' appear in EPA, EU, or Stockholm Convention lists",
    ],
    relatedPages: [
      { name: "Evidence Chain", path: "/evidence" },
      { name: "Regulatory", path: "/regulatory" },
      { name: "Tier 1", path: "/tier1" },
    ],
    apiEndpoint: "/api/v1/pathways",
  },

  litigation: {
    title: "SENTINEL — Litigation Risk",
    description:
      "Publication dynamics analysis and litigation risk forecasting. " +
      "Tracks scientific attention trajectories using physics-inspired metrics " +
      "(velocity, acceleration, jerk) derived from PubMed publication data.",
    whatItDoes: [
      "Tracks publication volume, velocity, acceleration, and jerk for PFAS compounds",
      "Provides a GenX case study backtest against 412 PubMed publications and 14 key events",
      "Forecasts litigation risk windows based on publication dynamics patterns",
      "Maps the relationship between scientific attention and regulatory/legal action",
    ],
    howToUse: [
      "Use the GenX Case Study tab to see the validated backtest against real events",
      "Switch to the Risk Forecast tab to view forward-looking projections",
      "Review the publication dynamics chart — rising acceleration signals emerging risk",
      "Check the timeline of key events to see how science preceded litigation",
    ],
    useCases: [
      "Assess whether a compound is on a litigation trajectory similar to GenX or PFOA",
      "Identify the publication velocity inflection points that preceded past lawsuits",
      "Support early-warning monitoring for compounds in your portfolio",
    ],
    tips: [
      "Publication count is 'position' — velocity is papers/year, acceleration is how fast velocity changes",
      "Jerk (third derivative) spikes often precede regulatory action by 12–18 months",
      "The GenX analysis incorporates 412 peer-reviewed publications and regulatory filing data",
    ],
    relatedPages: [
      { name: "Portfolio", path: "/portfolio" },
      { name: "Evidence Chain", path: "/evidence" },
    ],
    apiEndpoint: "/api/v1/litigation",
  },

  regulatory: {
    title: "Regulatory Compliance",
    description:
      "Check compounds against EPA, EU REACH, Stockholm Convention, and state-level " +
      "regulatory frameworks. Covers MCLs, health advisories, and emerging standards.",
    whatItDoes: [
      "Screens compounds against multi-jurisdictional regulatory databases",
      "Shows MCL (Maximum Contaminant Level) values where established",
      "Identifies health advisories, action levels, and notification thresholds",
      "Flags compounds on the EPA PFAS Action Plan, Stockholm Convention annexes, and APAC frameworks (Japan CSCL, K-REACH, China MEE, Australia NHMRC, Singapore NEA, Taiwan MOENV, India FSSAI)",
    ],
    howToUse: [
      "Enter a compound name or CAS number in the search field",
      "Review the regulatory status cards for each jurisdiction",
      "Check whether the compound has established limits or is under review",
      "Export results for inclusion in compliance reports",
    ],
    useCases: [
      "Verify whether a degradation product triggers regulatory obligations",
      "Compare regulatory status across EPA, EU, APAC, and state frameworks",
      "Build the regulatory section of an environmental impact assessment",
    ],
    tips: [
      "APAC regulations are accelerating; monitor finalized-to-binding transitions by jurisdiction",
      "State-level limits (e.g., Michigan, New Jersey) are often stricter than federal MCLs",
      "Use alongside Fate Explorer to check if degradation products are regulated",
    ],
    flagsAndStatuses: [
      { label: "Regulatory nav badge (red number)", meaning: "Count of HITL items still pending review or approval." },
      { label: "PENDING_REVIEW", meaning: "First gate state. Analyst must confirm/escalate/dismiss before briefing approval." },
      { label: "PENDING_APPROVAL", meaning: "Second gate state. Item has been reviewed and awaits final approve/hold decision." },
      { label: "Human review required", meaning: "Set automatically for critical flags, class-only matches, or low-confidence pathways." },
      { label: "Critical flags: N", meaning: "Number of CRITICAL threat flags from resolver output for that item." },
      { label: "ENACTED / FINAL PENDING / PROPOSED / UNDER CONSIDERATION / MONITORING", meaning: "Regulatory maturity stages used in the Landscape forecast." },
      { label: "Signal severity badges (critical/high/medium/low)", meaning: "Signal priority from L3/L4 triage and impact scoring." },
    ],
    actionsAndButtons: [
      { action: "Landscape", effect: "Jurisdiction/regulation baseline from governed assertions." },
      { action: "Signals", effect: "Live monitor feed of detected regulatory changes and why they matter." },
      { action: "Resolver", effect: "Run compound/product exposure analysis, including inherited liability." },
      { action: "Review Queue", effect: "Process analyst HITL gate actions for pending resolver outputs." },
      { action: "Check Compliance", effect: "Runs regulatory screening for the selected material and refreshes forecast cards." },
      { action: "Include Degradation Products", effect: "When enabled, includes downstream products in compliance evaluation." },
      { action: "Seed Demo / Clear Seeds", effect: "Insert or remove demo monitor signals for non-empty workflows and demos." },
      { action: "Confirm", effect: "Advance a PENDING_REVIEW item to PENDING_APPROVAL." },
      { action: "Escalate", effect: "Mark item for legal/regulatory escalation while retaining it in queue." },
      { action: "Dismiss", effect: "Close item with required written justification (captured in audit trail)." },
      { action: "Approve", effect: "Finalize a PENDING_APPROVAL item and remove it from pending queue." },
      { action: "Hold", effect: "Keep item in pending approval state for follow-up evidence/review." },
    ],
    relatedPages: [
      { name: "Fate Explorer", path: "/" },
      { name: "Portfolio", path: "/portfolio" },
    ],
    apiEndpoint: "/api/v1/regulatory",
  },

  portfolio: {
    title: "Portfolio Assessment",
    description:
      "Batch screening of compound portfolios for aggregate PFAS risk. " +
      "Evaluates materials against degradation, regulatory, and litigation risk dimensions.",
    whatItDoes: [
      "Screens multiple compounds simultaneously against all AEGIS risk dimensions",
      "Generates a composite risk score combining degradation, regulatory, and litigation factors",
      "Ranks compounds by overall risk for prioritization",
      "Identifies the highest-risk degradation products across a portfolio",
    ],
    howToUse: [
      "Select compounds to include in the portfolio assessment",
      "Review the risk matrix showing each compound's scores across dimensions",
      "Sort by overall risk score to identify priority compounds",
      "Drill into individual compounds for detailed pathway and regulatory data",
    ],
    useCases: [
      "Prioritize which fluoropolymers in a product line need deeper evaluation",
      "Compare risk profiles across alternative chemistries",
      "Generate a portfolio-level risk summary for executive review",
    ],
    relatedPages: [
      { name: "Reports", path: "/reports" },
      { name: "Fate Explorer", path: "/" },
      { name: "Regulatory", path: "/regulatory" },
    ],
    apiEndpoint: "/api/v1/portfolio",
  },

  reports: {
    title: "Executive Reports",
    description:
      "Generate structured risk assessment reports for stakeholders. " +
      "Combines data from all AEGIS modules into formatted deliverables.",
    whatItDoes: [
      "Compiles pathway, regulatory, and risk data into structured report formats",
      "Generates executive summaries with key findings and recommendations",
      "Includes DOI-traceable evidence citations for every claim",
      "Produces output suitable for regulatory submissions or board presentations",
    ],
    howToUse: [
      "Select the report type and target compounds",
      "Choose which modules to include (pathways, regulatory, litigation)",
      "Review the generated report and edit as needed",
      "Export to PDF or share with stakeholders",
    ],
    useCases: [
      "Prepare a risk assessment deliverable for a client engagement",
      "Generate a regulatory submission appendix with literature evidence",
      "Create an executive briefing on PFAS exposure for leadership",
    ],
    relatedPages: [
      { name: "Portfolio", path: "/portfolio" },
      { name: "Evidence Chain", path: "/evidence" },
    ],
    apiEndpoint: "/api/v1/reports",
  },

  evidence: {
    title: "Evidence Chain",
    description:
      "Trace every AEGIS claim back to its source DOI. Browse the full corpus of " +
      "353 peer-reviewed papers and 732 extracted degradation pathways.",
    whatItDoes: [
      "Provides full traceability from any risk assessment claim to source literature",
      "Shows verbatim quotes from papers with page/section locations",
      "Links to DOIs for direct access to source publications",
      "Displays extraction confidence scores for each evidence item",
    ],
    howToUse: [
      "Search by compound name, DOI, or keyword",
      "Browse pathways grouped by their source publication",
      "Click any DOI link to open the source paper directly",
      "Review verbatim quotes to verify the extraction accuracy",
    ],
    useCases: [
      "Verify a specific degradation pathway claim before citing it in testimony",
      "Find all papers that discuss a particular compound's thermal behavior",
      "Audit the evidence quality behind a high-risk signal",
    ],
    tips: [
      "Evidence with multiple independent DOIs is more defensible than single-source claims",
      "Verbatim quotes are extracted directly — always verify against the source paper",
      "Confidence scores reflect extraction certainty, not scientific certainty",
    ],
    relatedPages: [
      { name: "Fate Explorer", path: "/" },
      { name: "Reports", path: "/reports" },
    ],
  },

  analysis: {
    title: "PFAS Analysis",
    description:
      "Thermal degradation analysis for fluoropolymer compounds. " +
      "Focused analysis of degradation behavior under specific temperature and atmosphere conditions.",
    whatItDoes: [
      "Analyzes thermal degradation behavior for specific PFAS compounds",
      "Shows degradation products at different temperature ranges",
      "Maps degradation under different atmospheric conditions (air, nitrogen, vacuum)",
      "Provides yield estimates where reported in the literature",
    ],
    howToUse: [
      "Select a compound and specify the conditions of interest",
      "Review the degradation product distribution across temperature ranges",
      "Compare behavior under different atmospheric conditions",
      "Use the evidence links to trace findings to source papers",
    ],
    useCases: [
      "Evaluate what a fluoropolymer produces during incineration (>800°C)",
      "Compare degradation under manufacturing conditions vs. end-of-life scenarios",
      "Assess whether low-temperature processing stays below degradation thresholds",
    ],
    relatedPages: [
      { name: "Fate Explorer", path: "/" },
      { name: "Evidence Chain", path: "/evidence" },
    ],
    apiEndpoint: "/api/v1/analysis",
  },

  intelligence: {
    title: "Regulatory Intelligence",
    description:
      "Monitor live regulatory signals, run recursive exposure resolution, and manage human-in-the-loop approvals.",
    whatItDoes: [
      "Aggregates monitored regulatory signals with severity and classification",
      "Runs recursive compound-to-product exposure analysis through degradation pathways",
      "Queues resolver outputs for analyst review before approval and distribution",
      "Maintains a single operational view of monitoring + resolver + approvals",
    ],
    howToUse: [
      "Use Signals to review latest detected changes and severity",
      "Run Resolver on a product, compound, CAS, or SMILES to generate exposure outputs",
      "Process pending items in the Review Queue using confirm/escalate/dismiss/approve actions",
      "Add justifications for dismissals and other analyst decisions",
    ],
    useCases: [
      "Triage a newly detected EPA/ECHA signal and assess Chemours exposure impact",
      "Run inherited-liability checks for fluoropolymer products",
      "Operationalize analyst sign-off before executive distribution",
    ],
    tips: [
      "Critical flags should always be escalated for legal/regulatory review",
      "Class-level matches require analyst confirmation of product applicability",
      "Use resolver IDs to track decisions across gate states and audit logs",
    ],
    flagsAndStatuses: [
      { label: "critical/high/medium/low", meaning: "Signal severity from triage and Chemours impact scoring." },
      { label: "PENDING_REVIEW / PENDING_APPROVAL", meaning: "HITL gate states for resolver outputs." },
      { label: "Human review required", meaning: "Analyst intervention is mandatory before distribution." },
    ],
    actionsAndButtons: [
      { action: "Refresh", effect: "Reload live signals and pending queue data from API." },
      { action: "Run Resolver", effect: "Submit a resolver job and create a queue item with gate status." },
      { action: "Confirm / Escalate / Dismiss / Approve / Hold", effect: "Apply HITL actions with audit logging and state transitions." },
    ],
    relatedPages: [
      { name: "Regulatory", path: "/regulatory" },
      { name: "Tier 1", path: "/tier1" },
      { name: "Evidence Chain", path: "/evidence" },
    ],
    apiEndpoint: "/api/v1/resolver/resolve",
  },

  tier1: {
    title: "Structural Intelligence (Tier 1 + Tier 2)",
    description:
      "Structure-aware compound screening combining Tier 1 (Morgan fingerprint similarity " +
      "against 10,974 EPA PFAS compounds) with Tier 2 (substructure pattern mining with " +
      "Wilson score confidence intervals from 732 literature pathways). " +
      "Not a prediction engine — reports what the published literature shows.",
    whatItDoes: [
      "Tier 1: Computes Tanimoto similarity against the full EPA PFAS database and aggregates degradation endpoints",
      "Tier 2: Detects substructure patterns (SMARTS + algorithmic chain analysis) and correlates them with endpoint buckets",
      "Reports Wilson score confidence intervals — honest uncertainty, not fake precision",
      "Tracks precursor resolution coverage so you know how grounded the correlations are",
      "Returns DOI-cited evidence for every pathway found",
    ],
    howToUse: [
      "Enter a SMILES string directly, or use a quick-select badge (GenX, PFOA, PFOS, 6:2 FTOH)",
      "Review the risk signal banner — HIGH (red), MEDIUM (amber), LOW (green)",
      "Check the Substructure Fingerprint card for detected patterns and fluorine metrics",
      "Expand Pattern-Based Endpoint Correlations to see confidence intervals from the corpus",
      "Use the Corpus Rules Explorer to browse all mined rules and coverage statistics",
    ],
    useCases: [
      "Screen a novel compound by finding what happens to structurally similar PFAS",
      "Identify substructure patterns (e.g., long perfluoro chain + carboxylic acid) that correlate with specific endpoints",
      "Assess how well-grounded the correlations are via the coverage report",
      "Gather literature evidence for compounds without direct study data",
    ],
    tips: [
      "The risk signal reflects endpoint classes: long-chain acids and sulfonates = HIGH",
      "Tier 2 pattern badges are color-coded: blue = SMARTS, green = algorithmic, purple = classification",
      "Confidence intervals show the plausible range — wide intervals mean few supporting precursors",
      "The coverage report shows resolution rate — low coverage means rules are based on fewer compounds",
      "All evidence is DOI-linked — click any citation to verify the source paper",
    ],
    relatedPages: [
      { name: "Fate Explorer", path: "/" },
      { name: "Evidence Chain", path: "/evidence" },
      { name: "Regulatory", path: "/regulatory" },
    ],
    apiEndpoint: "/api/v1/tier1",
  },
};

export default helpContent;
