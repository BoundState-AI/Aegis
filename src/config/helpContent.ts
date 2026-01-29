/**
 * Central help content configuration for all AEGIS pages.
 *
 * Each entry provides structured help that renders in the PageHelp modal.
 */

export interface RelatedPage {
  name: string;
  path: string;
}

export interface HelpContent {
  title: string;
  description: string;
  whatItDoes: string[];
  howToUse: string[];
  useCases: string[];
  tips?: string[];
  relatedPages?: RelatedPage[];
  apiEndpoint?: string;
}

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
      "Uses the GPTL (Generalized Position-Time Litigation) model to track " +
      "scientific attention trajectories for PFAS compounds.",
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
      "The GPTL model treats publication count as 'position' — velocity is the rate of new papers",
      "Jerk (third derivative) spikes often precede regulatory action by 12–18 months",
      "The GenX backtest is validated against real Chemours litigation timeline",
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
      "Flags compounds on the EPA PFAS Action Plan or Stockholm Convention annexes",
    ],
    howToUse: [
      "Enter a compound name or CAS number in the search field",
      "Review the regulatory status cards for each jurisdiction",
      "Check whether the compound has established limits or is under review",
      "Export results for inclusion in compliance reports",
    ],
    useCases: [
      "Verify whether a degradation product triggers regulatory obligations",
      "Compare regulatory status across EPA, EU, and state frameworks",
      "Build the regulatory section of an environmental impact assessment",
    ],
    tips: [
      "Compounds 'under review' may have limits proposed — check the EPA PFAS Roadmap",
      "State-level limits (e.g., Michigan, New Jersey) are often stricter than federal MCLs",
      "Use alongside Fate Explorer to check if degradation products are regulated",
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
      "Evaluate what a fluoropolymer produces during incineration (>800\u00B0C)",
      "Compare degradation under manufacturing conditions vs. end-of-life scenarios",
      "Assess whether low-temperature processing stays below degradation thresholds",
    ],
    relatedPages: [
      { name: "Fate Explorer", path: "/" },
      { name: "Evidence Chain", path: "/evidence" },
    ],
    apiEndpoint: "/api/v1/analysis",
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
