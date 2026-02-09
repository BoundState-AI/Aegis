# AEGIS Frontend Client-Readiness Audit

**Date:** 2026-02-09
**Target:** aegis.boundstate.ai
**Context:** Chemours lawyers may explore this site this week
**Stack:** React 18 + Vite + TypeScript + Tailwind + shadcn/ui

---

## CRITICAL FINDINGS (Chemours lawyers would notice)

### C1. Footer disclaimer labels entire platform as "Demo" — visible on EVERY page

| | |
|---|---|
| **File** | `src/i18n/locales/en.json:71` |
| **Code** | `"disclaimer": "*AEGIS Demo — BoundState PFAS Intelligence Platform. For evaluation purposes."` |
| **Rendered in** | `src/App.tsx:38-46` — the `<Disclaimer>` component, rendered inside `<Navigation>` on every non-standalone route |
| **Also in** | `src/i18n/locales/ja.json:71` (Japanese translation) |
| **Fix** | Remove or replace with production-appropriate text. At minimum remove "Demo" and "For evaluation purposes." |

### C2. "Preview Model" disclaimer banner on Litigation Risk Forecast

| | |
|---|---|
| **File** | `src/pages/LitigationRisk.tsx:1117-1123` |
| **Code** | `<Alert>` banner rendering: `<strong>{t('common.previewModel')}:</strong> {t('litigation.modelDisclaimer')}` |
| **Text** | `"Preview Model: Litigation probabilities are calculated using a simplified model based on publication velocity, compound type, and historical case data. Production deployment requires actuarial review and jurisdiction-specific factors."` (en.json:162) |
| **Also** | `en.json:59-60` defines `"previewMode"` and `"previewModel"` strings |
| **Fix** | Remove or reword. The phrase "simplified model" and "Production deployment requires" directly tells lawyers this isn't production-ready. |

### C3. Portfolio Assessment disclaimer says "simplified models"

| | |
|---|---|
| **File** | `src/i18n/locales/en.json:244` |
| **Code** | `"demoDisclaimer": "Risk scores use simplified models. Production deployment requires site-specific risk factors and comprehensive material characterization."` |
| **Also in** | `ja.json:246` |
| **Fix** | Remove or reword. The key `demoDisclaimer` is self-evidently a demo artifact. |

### C4. BoundState logo and link displayed in navigation bar on EVERY page

| | |
|---|---|
| **File** | `src/App.tsx:82` |
| **Code** | `<BoundStateLogo variant="full" theme="light" size="sm" />` |
| **Renders** | Logo SVG + "BoundState" text in bottom nav, linked to `https://www.boundstate.ai/` (`src/components/layout/BoundStateLogo.tsx:96`) |
| **Fix** | Remove BoundStateLogo from nav, or replace with Chemours branding. The logo is a clickable link to an external vendor site. |

### C5. Ensurance page is entirely BoundState marketing collateral

| | |
|---|---|
| **File** | `src/pages/Ensurance.tsx` (entire file, ~410 lines) |
| **Route** | `/ensurance` — accessible via direct URL |
| **Issues** | Links to `https://boundstate.ai` (line 51), displays `boundstate.ai` branding (line 57), `mailto:joe@boundstate.ai` contact buttons (lines 61, 110, 358, 367), "© 2025 BoundState, Inc." copyright (en.json:481), BoundState tagline (en.json:477) |
| **Fix** | Remove route entirely or gate it. This page is a sales pitch for BoundState's Ensurance product, not AEGIS functionality. A lawyer clicking around could land on it. |

### C6. `<meta name="author" content="BoundState" />` in HTML head

| | |
|---|---|
| **File** | `index.html:9` |
| **Fix** | Remove or change to appropriate attribution. |

### C7. GenX case study uses Chemours' own litigation as validation data

| | |
|---|---|
| **Files** | `src/pages/LitigationRisk.tsx:489-502` (tab: "Validation Case Studies"), `public/data/backtest_genx.json` (15KB of Chemours litigation history) |
| **Content** | "The Claims vs. The Reality" section (LitigationRisk.tsx:931-969) juxtaposes DuPont marketing claims against documented outcomes. Sentiment annotation (en.json:142) calls out "manufacturer-controlled (DuPont brochure, 2008-2010)". Industry claims array includes "DuPont PMN Submission to EPA" and "$2.2B Chemours Settlement". |
| **Help text** | `src/config/helpContent.ts:89` — `"The GenX backtest is validated against real Chemours litigation timeline with 412 PubMed papers"` |
| **Severity** | This is the default tab. Chemours lawyers open the Litigation page and immediately see their own company's litigation dissected as a case study with "Claims vs. Reality" framing. |
| **Fix** | This is a product decision — but at minimum, don't make it the default tab. Consider whether showing a client their own litigation losses ($14.5B) as "validation" is appropriate for a client demo. |

### C8. Error message leaks dev environment details to users

| | |
|---|---|
| **File** | `src/i18n/locales/en.json:54` |
| **Code** | `"couldNotConnect": "Could not connect to AEGIS API. Make sure the backend is running on port 8002."` |
| **Rendered in** | `src/pages/FateExplorer.tsx:132`, `src/pages/LitigationRisk.tsx:444` |
| **Fix** | Remove "Make sure the backend is running on port 8002" — this is a developer instruction visible to end users when the API is down. Replace with something like "Service temporarily unavailable. Please try again." |

### C9. Raw `error.message` rendered to user in toast

| | |
|---|---|
| **File** | `src/pages/StructuralSimilarity.tsx:291-296` |
| **Code** | `description: error.message \|\| t('tier1.couldNotConnect')` |
| **Fix** | Remove `error.message` — could expose stack traces, internal paths, or server error details. Use only the i18n fallback string. |

### C10. No React Error Boundary — crashes show white screen or React stack trace

| | |
|---|---|
| **File** | `src/App.tsx:117-127` |
| **Issue** | No `<ErrorBoundary>` wrapping the app. An unhandled error in any component will show a blank white screen in production or React's error overlay with full component tree in development. |
| **Fix** | Add an ErrorBoundary component that shows a user-friendly error page. |

---

## MINOR FINDINGS (cleanup, not embarrassing)

### M1. Build timestamp comment in API config

| | |
|---|---|
| **File** | `src/config/api.ts:4` |
| **Code** | `// Build timestamp: 2026-01-31T19:30:00Z - Force clean build` |
| **Fix** | Remove — no functional purpose, reveals build timeline. |

### M2. "Demo compound" in user-facing help text

| | |
|---|---|
| **Files** | `en.json:57` — `"Enter a SMILES string or select a demo compound."`, `en.json:316` — same |
| **Fix** | Change "demo compound" to "reference compound" or "example compound." |

### M3. Hardcoded `DEMO_COMPOUNDS` array with GenX as default

| | |
|---|---|
| **File** | `src/pages/StructuralSimilarity.tsx:135-140` |
| **Code** | `const DEMO_COMPOUNDS = [{ name: "GenX", ... }, { name: "PFOA", ... }, ...]` |
| **Default** | Line 173: `useState(DEMO_COMPOUNDS[0].smiles)` — GenX loads on page open |
| **Comment** | Line 192: `// Auto-query GenX on mount` |
| **Fix** | Rename variable to `REFERENCE_COMPOUNDS`. The word "DEMO" in source is fine but the variable name propagates to UI via "Quick Select" badges. |

### M4. LitigationRisk defaults to PFOA with revealing comment

| | |
|---|---|
| **File** | `src/pages/LitigationRisk.tsx:319, 349` |
| **Code** | `useState<string>("pfoa")` and comment `// Default to PFOA if available (stronger validation case)` |
| **Fix** | Remove the comment. The default behavior itself is fine for the product. |

### M5. All pages auto-load with pre-filled data on mount

| | |
|---|---|
| **Pages** | FateExplorer (PTFE, line 79), EvidenceChain (PTFE, line 54), PFASAnalysis (PTFE, line 42), RegulatoryCompliance (PTFE, line 63), ExecutiveReports (PTFE, line 42), PortfolioAssessment (PTFE+FEP, line 80), StructuralSimilarity (GenX, line 192) |
| **Fix** | This is a design choice — auto-loading data shows the platform works immediately. Not a bug, but be aware every page fires API calls immediately. |

### M6. `placeholder.svg` and `boundstate-logo.png` (431KB) in public/

| | |
|---|---|
| **Files** | `public/placeholder.svg` (3.2KB), `public/boundstate-logo.png` (431KB) |
| **Fix** | `boundstate-logo.png` is 431KB and only used by the BoundStateLogo component and Ensurance page. If those are removed, delete this file. The placeholder.svg appears unused. |

### M7. Package name is a template placeholder

| | |
|---|---|
| **File** | `package.json:2` |
| **Code** | `"name": "vite_react_shadcn_ts"` |
| **Fix** | Rename to `aegis-frontend` or similar. |

### M8. Copyright year is 2025 on Ensurance page

| | |
|---|---|
| **File** | `en.json:481` |
| **Code** | `"copyright": "© 2025 BoundState, Inc. All rights reserved."` |
| **Fix** | If Ensurance page is kept, update year to 2026. |

### M9. Backend warmup pings every 4 minutes

| | |
|---|---|
| **File** | `src/hooks/use-backend-warmup.ts:5, 27` |
| **Code** | `const WARMUP_INTERVAL_MS = 4 * 60 * 1000;` — pings `/health` every 4 min |
| **Fix** | This is intentional to prevent Railway cold starts. Not a problem per se, but increases server load. Acceptable for now. |

### M10. No route-level code splitting

| | |
|---|---|
| **File** | `src/App.tsx:7-16` |
| **Issue** | All 10 page components imported synchronously. Entire app downloads on first load. |
| **Fix** | Use `React.lazy()` for route components. Low priority but would improve first-load performance. |

### M11. `.gitignore` missing explicit `.env` entry

| | |
|---|---|
| **File** | `.gitignore` |
| **Issue** | Has `*.local` but not explicit `.env`. No `.env` files are committed (verified), but this is a best-practice gap. |
| **Fix** | Add `.env` and `.env.*` patterns. |

### M12. CORS includes localhost origins in default config

| | |
|---|---|
| **File** | `boundstate_aegis/api/aegis_api.py:85-94` |
| **Code** | Default CORS list includes `localhost:3000/5173/8080/8081` and `127.0.0.1` variants |
| **Fix** | Not a security issue — these are defaults overridable at runtime, and production CORS is properly restricted to HTTPS boundstate.ai domains. Minor hygiene. |

---

## WHAT'S CLEAN (No Issues Found)

| Category | Status |
|---|---|
| **console.log/debug/warn/error** | None in frontend source |
| **TODO/FIXME/HACK/XXX comments** | None |
| **debugger statements** | None |
| **React DevTools references** | None |
| **Hardcoded API keys/tokens/secrets** | None anywhere in repo |
| **.env files committed** | None |
| **CORS wildcard (*)** | Not used — origin list is explicit |
| **Admin/debug routes** | None exposed |
| **Source maps in production** | Disabled (Vite default) |
| **404 page** | Exists (`src/pages/NotFound.tsx`), user-friendly with i18n |
| **Loading states** | All pages have Loader2 spinners |
| **Empty states** | All pages handle zero-results gracefully |
| **Mobile responsiveness** | Tailwind responsive grid throughout |
| **Chemours branding on pages** | ChemoursHeader with logo on all main pages (proper) |
| **Tailwind theme** | Chemours brand colors correctly defined |

---

## PRIORITY ACTION PLAN

### Before lawyer visit (same day):
1. **C1** — Remove "Demo" and "For evaluation purposes" from footer disclaimer
2. **C2** — Remove "Preview Model" banner or reword without "simplified" / "production deployment"
3. **C3** — Remove or reword `demoDisclaimer` in Portfolio
4. **C4** — Remove BoundStateLogo from navigation bar
5. **C8** — Fix the "port 8002" error message
6. **C9** — Remove `error.message` from StructuralSimilarity toast

### Before any serious client engagement:
7. **C5** — Remove/gate `/ensurance` route
8. **C6** — Remove BoundState meta author tag
9. **C7** — Decide on GenX case study framing (product decision)
10. **C10** — Add ErrorBoundary component

### Cleanup (scheduled):
11. All MINOR findings (M1-M12)
