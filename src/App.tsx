import { useMemo } from "react";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import NotFound from "./pages/NotFound";
import PFASAnalysis from "./pages/PFASAnalysis";
import FateExplorer from "./pages/FateExplorer";
import AegisLanding from "./pages/AegisLanding";
import LitigationRisk from "./pages/LitigationRisk";
import RegulatoryCompliance from "./pages/RegulatoryCompliance";
import PortfolioAssessment from "./pages/PortfolioAssessment";
import ExecutiveReports from "./pages/ExecutiveReports";
import EvidenceChain from "./pages/EvidenceChain";
import StructuralSimilarity from "./pages/StructuralSimilarity";
import Login from "./pages/Login";
// import Ensurance from "./pages/Ensurance";
import { Scale, Globe, Package, FileText, BookOpen, FlaskConical, Network, Fingerprint, LogOut } from "lucide-react";
import ErrorBoundary from "./components/ErrorBoundary";
import { LanguageToggle } from "./components/ui/language-toggle";
import { useBackendWarmup } from "./hooks/use-backend-warmup";
import { Analytics } from "@vercel/analytics/react";
import { apiGet } from "./lib/apiClient";
import { pendingListSchema } from "./lib/apiSchemas";
import { clearAuthSession, isAuthenticated } from "./lib/auth";

const queryClient = new QueryClient();
const navItems = [
  { path: "/fate-explorer", labelKey: "nav.fateExplorer", icon: Network },
  { path: "/litigation", labelKey: "nav.sentinel", icon: Scale },
  { path: "/regulatory", labelKey: "nav.regulatory", icon: Globe },
  { path: "/portfolio", labelKey: "nav.portfolio", icon: Package },
  { path: "/reports", labelKey: "nav.reports", icon: FileText },
  { path: "/evidence", labelKey: "nav.evidence", icon: BookOpen },
  { path: "/analysis", labelKey: "nav.analysis", icon: FlaskConical },
  { path: "/tier1", labelKey: "nav.tier1", icon: Fingerprint },
];

const standaloneRoutes = new Set(["/", "/login"]);
const publicRoutes = new Set(["/login"]);

const Disclaimer = () => {
  const { t } = useTranslation();
  return (
    <div className="container mx-auto px-4 py-2 text-left">
      <p className="text-xs text-gray-400 italic">{t("nav.disclaimer")}</p>
    </div>
  );
};

const Navigation = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const pendingQuery = useQuery({
    queryKey: ["resolverPendingNav"],
    queryFn: () => apiGet("/api/v1/resolver/pending?limit=100", pendingListSchema),
    staleTime: 30_000,
    refetchInterval: 60_000,
    retry: 1,
  });

  const pendingReviewCount = useMemo(() => {
    const items = pendingQuery.data?.items || [];
    return items.filter(
      (row) => row.gate_status === "PENDING_REVIEW" || row.gate_status === "PENDING_APPROVAL",
    ).length;
  }, [pendingQuery.data]);

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 border-t border-gray-200 bg-white shadow-lg">
      <Disclaimer />
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between py-2">
          <div className="flex w-24 items-center">
            <LanguageToggle />
          </div>
          <div className="flex items-center gap-1 overflow-x-auto">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`relative flex flex-col items-center rounded-lg px-3 py-2 transition-colors ${
                    isActive
                      ? "bg-gradient-to-r from-chemours-red/10 to-chemours-orange/10 text-chemours-red"
                      : "text-gray-500 hover:bg-gray-100 hover:text-chemours-red"
                  }`}
                >
                  {item.path === "/regulatory" && pendingReviewCount > 0 && (
                    <span className="absolute -right-1 -top-1 min-h-[18px] min-w-[18px] rounded-full bg-red-600 px-1 text-center text-[10px] font-semibold leading-[18px] text-white">
                      {pendingReviewCount > 99 ? "99+" : pendingReviewCount}
                    </span>
                  )}
                  <Icon className="h-5 w-5" />
                  <span className="mt-1 text-xs">{t(item.labelKey)}</span>
                </Link>
              );
            })}
          </div>
          <div className="flex w-24 flex-shrink-0 justify-end">
            <button
              type="button"
              onClick={() => {
                clearAuthSession();
                queryClient.clear();
                navigate("/login", { replace: true });
              }}
              className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-gray-500 transition-colors hover:bg-gray-100 hover:text-chemours-red"
            >
              <LogOut className="h-4 w-4" />
              Sign out
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
};

const AppContent = () => {
  const location = useLocation();

  // Keep Railway backend warm to prevent cold start delays
  useBackendWarmup();

  const isStandalone = standaloneRoutes.has(location.pathname);
  const isPublicRoute = publicRoutes.has(location.pathname);
  const authed = isAuthenticated();

  if (location.pathname === "/login" && authed) {
    return <Navigate to="/fate-explorer" replace />;
  }

  if (!isPublicRoute && !authed) {
    const next = `${location.pathname}${location.search}${location.hash}`;
    return <Navigate to={`/login?next=${encodeURIComponent(next)}`} replace />;
  }

  return (
    <div className={isStandalone ? "" : "pb-20"}>
      <Routes>
        <Route path="/" element={<AegisLanding />} />
        <Route path="/login" element={<Login />} />
        <Route path="/fate-explorer" element={<FateExplorer />} />
        <Route path="/litigation" element={<LitigationRisk />} />
        <Route path="/intelligence" element={<Navigate to="/regulatory?view=signals" replace />} />
        <Route path="/regulatory" element={<RegulatoryCompliance />} />
        <Route path="/portfolio" element={<PortfolioAssessment />} />
        <Route path="/reports" element={<ExecutiveReports />} />
        <Route path="/evidence" element={<EvidenceChain />} />
        <Route path="/analysis" element={<PFASAnalysis />} />
        <Route path="/tier1" element={<StructuralSimilarity />} />
        {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
        <Route path="*" element={<NotFound />} />
      </Routes>
      {!isStandalone && <Navigation />}
    </div>
  );
};

const App = () => (
  <ErrorBoundary>
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <BrowserRouter>
          <AppContent />
        </BrowserRouter>
        <Analytics />
      </TooltipProvider>
    </QueryClientProvider>
  </ErrorBoundary>
);

export default App;
