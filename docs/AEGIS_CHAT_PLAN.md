# AEGIS Chat Plan: Page-Aware Intelligence Assistant

> **Date:** 2026-03-26
> **Status:** Proposed
> **Author:** Claude / Dr. Joseph Wilde

---

## Vision

Each AEGIS page gets an embedded AI chat that is an **expert on that specific page** — it knows what the page does, what controls exist, what data is currently showing, and what actions the user can take. Not a generic chatbot — a contextual assistant that can see what you see.

---

## Architecture Overview

```
┌─ Per-Page Chat Context ─────────────────────────────┐
│                                                      │
│  Each page exports a chatContext object:              │
│                                                      │
│  {                                                   │
│    pageId: "fate-explorer",                          │
│    systemPrompt: "You are the Fate Explorer...",     │
│    currentState: {        ← live, reactive           │
│      selectedCompound: "PTFE",                       │
│      tempRange: [200, 800],                          │
│      results: [...],      ← actual data on screen    │
│      resultCount: 14,                                │
│    },                                                │
│    capabilities: [        ← what the page can DO     │
│      "search pathways for a parent compound",        │
│      "filter by temperature range",                  │
│      "filter by atmosphere type",                    │
│      ...                                             │
│    ]                                                 │
│  }                                                   │
│                                                      │
└──────────────────┬───────────────────────────────────┘
                   │
                   ▼
┌─ ChatProvider (React Context) ───────────────────────┐
│                                                      │
│  Wraps each page. Receives chatContext.               │
│  Renders the ChatDrawer overlay.                     │
│  Passes currentState + systemPrompt to backend.      │
│                                                      │
└──────────────────┬───────────────────────────────────┘
                   │ POST /api/v1/chat/stream
                   ▼
┌─ Backend chat_route.py ─────────────────────────────┐
│                                                      │
│  Receives: { message, pageId, systemPrompt,          │
│              pageState, sessionId }                   │
│                                                      │
│  Builds Anthropic messages call:                     │
│    system = pageSystemPrompt + pageState summary     │
│    messages = conversation history + user message    │
│                                                      │
│  Streams response back via SSE                       │
└─────────────────────────────────────────────────────┘
```

---

## What Each Page's Chat Knows

### 1. Fate Explorer

**System prompt context:** "You are the Fate Explorer assistant. The user is exploring PFAS degradation pathways."

**Live state injected:**
- Currently selected parent compound
- Temperature range filter (min/max)
- Atmosphere filter
- Min observations filter
- Current results: list of products with confidence, hazard level, mechanism, sources
- Database stats: total compounds, transformations, papers

**Example conversations:**
- *"Why is TFA showing as CRITICAL hazard?"* → Chat knows TFA is in the results and its hazard level
- *"What if I lower the temperature to 200?"* → Chat explains what pathways disappear/appear at lower temps
- *"What does the confidence percentage mean?"* → Chat explains it's based on number of independent papers confirming the pathway
- *"Which of these products are regulated?"* → Chat scans the visible results and lists the regulated ones

---

### 2. Litigation Risk (SENTINEL)

**Live state injected:**
- Selected compound (PFOA, GenX, etc.)
- Active tab (Case Study vs Risk Forecast)
- Active chart view (Publications, Sentinel Signal, Sentiment)
- Timeline data: years, velocities, alert levels, events
- Sentiment data: category breakdowns by year
- Headline stats: total publications, first signal year, settlements
- Forecast results (if run): probabilities, risk level, key drivers

**Example conversations:**
- *"When did PFOA enter the ELEVATED phase?"* → Chat reads the timeline data
- *"What caused the spike in 2015?"* → Chat correlates velocity spike with key events
- *"What's the difference between velocity and acceleration?"* → Chat explains SENTINEL signal math
- *"How does GenX compare to PFOA's trajectory?"* → Chat compares if both backtests are loaded
- *"What does reckoning sentiment mean?"* → Chat explains the 6 sentiment categories

---

### 3. Regulatory Compliance

**Live state injected:**
- Material being checked
- Include degradation products toggle state
- Forecast year
- Active sub-view (Landscape, Signals, Resolver, Review Queue)
- Non-compliant/warning/compliant counts and details
- APAC assertion details with confidence scores
- Cascade predictions

**Example conversations:**
- *"Why is PTFE non-compliant with EU PFAS restriction?"* → Chat reads the specific framework finding
- *"What happens if I include degradation products?"* → Chat explains how downstream products add regulatory risk
- *"Which APAC countries have the strictest rules?"* → Chat scans APAC assertions and ranks by status
- *"What's predicted for 2028?"* → Chat reads cascade predictions for that year

---

### 4. Portfolio Assessment

**Live state injected:**
- Current portfolio items (materials + volumes)
- Assessment results: risk categories, PFAS product counts, regulatory flags, litigation probabilities
- Executive summary text
- High risk count

**Example conversations:**
- *"Which material is the riskiest?"* → Chat ranks by litigation probability
- *"What if I remove FEP?"* → Chat explains the impact on portfolio risk
- *"Why does PTFE have 12 regulatory flags?"* → Chat explains based on results data
- *"Summarize the portfolio risk for my boss"* → Chat reformulates the executive summary

---

### 5. Executive Reports

**Live state injected:**
- Material being reported on
- Include litigation/regulatory toggles
- Generated report sections and content
- Classification level

**Example conversations:**
- *"Simplify section 3 for a non-technical audience"* → Chat rewrites the section
- *"What are the key takeaways?"* → Chat summarizes across all sections
- *"Is there any litigation risk mentioned?"* → Chat scans sections for litigation content

---

### 6. Evidence Chain

**Live state injected:**
- Material searched
- Citations returned (source, year, compound, finding, confidence, DOI)
- Overall confidence score
- Source coverage stats

**Example conversations:**
- *"Which paper has the strongest evidence?"* → Chat ranks by confidence
- *"Are there any citations from before 2010?"* → Chat filters by year
- *"What's the overall confidence based on?"* → Chat explains the aggregation method
- *"How many unique sources cover PFOA specifically?"* → Chat counts from citation data

---

### 7. PFAS Analysis

**Live state injected:**
- Selected material, temperature, atmosphere, exposure time
- Analysis results: compound evaluated, PFAS findings with pathways
- Per-finding: product, confidence, pathway chain, regulatory flags, litigation flag, DOIs

**Example conversations:**
- *"At what temperature does PFOA start forming?"* → Chat reads pathway conditions
- *"Which products have litigation risk?"* → Chat filters findings by litigation flag
- *"What's the pathway from PTFE to TFA?"* → Chat traces the arrow chain
- *"What would happen if I switched to inert atmosphere?"* → Chat explains expected differences

---

### 8. Structural Similarity

**Live state injected:**
- Query SMILES and compound name
- Tier 1 results: risk signal, similar EPA compounds, degradation endpoints, mechanisms
- Tier 2 results: substructure patterns, fluorine metrics, endpoint correlations with CIs
- Rules table data
- Coverage stats

**Example conversations:**
- *"What does the 0.87 similarity score mean?"* → Chat explains Tanimoto fingerprint similarity
- *"Why is GenX flagged HIGH risk?"* → Chat reads the risk signal breakdown
- *"What SMARTS patterns were detected?"* → Chat lists matched patterns
- *"How reliable is the TFA endpoint prediction?"* → Chat reads CI range and supporting pattern count
- *"What's the F/C ratio telling me?"* → Chat explains fluorine saturation metrics

---

## Implementation: Files to Create/Edit

### Backend (3 new files, 1 edit)

| File | Purpose |
|------|---------|
| `boundstate_aegis/models/chat_models.py` | `ChatRequest(message, page_id, system_prompt, page_state, session_id)`, `ChatStreamChunk(delta, done)` |
| `boundstate_aegis/engines/chat_engine.py` | Builds Anthropic API call with system prompt + page state + conversation history. Streams response. In-memory session store. |
| `boundstate_aegis/api/routes/chat_route.py` | `POST /api/v1/chat/stream` SSE StreamingResponse |
| `boundstate_aegis/api/aegis_api.py` | Register chat router |

### Frontend (6 new files, 9 edits)

| File | Purpose |
|------|---------|
| **New:** `src/hooks/use-chat.ts` | Chat state management, SSE streaming, session tracking |
| **New:** `src/components/chat/ChatDrawer.tsx` | Slide-over drawer (Radix Sheet) |
| **New:** `src/components/chat/ChatMessageList.tsx` | Message bubbles, markdown rendering, streaming indicator |
| **New:** `src/components/chat/ChatInput.tsx` | Textarea + send button + suggested questions |
| **New:** `src/components/chat/ChatFAB.tsx` | Floating "Ask AEGIS" button |
| **New:** `src/components/chat/PageChatProvider.tsx` | React context that receives page state and wires to drawer |
| **Edit:** `src/lib/apiClient.ts` | Add `apiStream()` SSE helper |
| **Edit:** `src/pages/FateExplorer.tsx` | Export `chatContext` with live state |
| **Edit:** `src/pages/LitigationRisk.tsx` | Export `chatContext` with live state |
| **Edit:** `src/pages/RegulatoryCompliance.tsx` | Export `chatContext` with live state |
| **Edit:** `src/pages/PortfolioAssessment.tsx` | Export `chatContext` with live state |
| **Edit:** `src/pages/ExecutiveReports.tsx` | Export `chatContext` with live state |
| **Edit:** `src/pages/EvidenceChain.tsx` | Export `chatContext` with live state |
| **Edit:** `src/pages/PFASAnalysis.tsx` | Export `chatContext` with live state |
| **Edit:** `src/pages/StructuralSimilarity.tsx` | Export `chatContext` with live state |

### Dependencies to Add

| Package | Where | Purpose |
|---------|-------|---------|
| `react-markdown` | Frontend (npm) | Render markdown in chat responses |
| `remark-gfm` | Frontend (npm) | GitHub-flavored markdown (tables) |
| `anthropic` | Backend (pip) | Anthropic SDK for streaming |

---

## Key Design Decision: Page State as System Prompt

The core insight is that each page's **live state** gets serialized into the system prompt on every message. The LLM doesn't need RAG — it gets the actual data the user is looking at, injected as context:

```
System: You are the AEGIS Fate Explorer assistant.

The user is currently viewing degradation pathways for PTFE
with temperature range 200-800C, oxidative atmosphere.

Current results (14 pathways found):
- TFA: 92% confidence, CRITICAL hazard, 8 sources
- PFOA: 78% confidence, HIGH hazard, 5 sources
- HF: 95% confidence, MEDIUM hazard, 12 sources
...

Available controls: parent compound selector, temperature
range filter, atmosphere filter, min observations filter.

Help the user understand what they're seeing and what
actions they can take.
```

This is simpler than RAG, more accurate (it's the *exact* data on screen), and leverages what AEGIS already has.

---

## UI Design

### Chat Drawer
- **Slide-over from the right** (not a full page — user stays on their current page)
- Uses Radix `Sheet` component (already available via shadcn/ui)
- Width: ~420px on desktop, full-screen on mobile
- Header: "AEGIS Analyst" + page name badge + close button

### Floating Action Button (FAB)
- Persistent "Ask AEGIS" button, bottom-right corner (above nav bar)
- Icon: `MessageCircle` from Lucide
- Opens ChatDrawer on click

### Message Styles
- **User**: right-aligned, blue bubble, compact
- **Assistant**: left-aligned, white card with subtle border, full-width, markdown rendered
- **Streaming**: animated dots while response generates, characters appear progressively

### Suggested Questions
Each page shows 2-3 contextual starter questions in the empty chat state:
- Fate Explorer: "What degradation products form from PTFE?", "Which products are regulated?"
- Litigation: "When did this compound first appear in litigation?", "What's the settlement history?"
- etc.

---

## Backend: SSE Streaming Protocol

```
POST /api/v1/chat/stream
Content-Type: application/json

{
  "message": "Why is TFA critical?",
  "page_id": "fate-explorer",
  "system_prompt": "You are the Fate Explorer assistant...",
  "page_state": { ... serialized live state ... },
  "session_id": "abc123"
}

Response: text/event-stream

data: {"delta": "TFA (trifluoro", "done": false}
data: {"delta": "acetic acid) is classified", "done": false}
data: {"delta": " as CRITICAL because...", "done": false}
data: {"delta": "", "done": true}
```

### Session Management
- In-memory dict: `session_id -> list[ChatMessage]`
- Thread-safe with double-check locking (matches existing AEGIS cache pattern)
- Sessions expire after 30 minutes of inactivity
- No database required

---

## Phase Sequence

| Phase | Scope | Effort |
|-------|-------|--------|
| **Phase 1** | Backend: chat models, engine, route, SSE streaming | Backend |
| **Phase 2** | Frontend: ChatDrawer, MessageList, Input, FAB, use-chat hook, apiStream | Frontend |
| **Phase 3** | Wire up all 8 pages with chatContext (live state export) | Integration |
| **Phase 4** | Polish: suggested questions, markdown rendering, error states, i18n | UX |
