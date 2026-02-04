import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import NotFound from "./pages/NotFound";
import PFASAnalysis from "./pages/PFASAnalysis";
import FateExplorer from "./pages/FateExplorer";
import LitigationRisk from "./pages/LitigationRisk";
import RegulatoryCompliance from "./pages/RegulatoryCompliance";
import PortfolioAssessment from "./pages/PortfolioAssessment";
import ExecutiveReports from "./pages/ExecutiveReports";
import EvidenceChain from "./pages/EvidenceChain";
import StructuralSimilarity from "./pages/StructuralSimilarity";
import Ensurance from "./pages/Ensurance";
import { Scale, Globe, Package, FileText, BookOpen, FlaskConical, Network, Fingerprint } from "lucide-react";
import { BoundStateLogo } from "./components/layout/BoundStateLogo";
import { LanguageToggle } from "./components/ui/language-toggle";
import { useBackendWarmup } from "./hooks/use-backend-warmup";

const queryClient = new QueryClient();

const navItems = [
  { path: "/", labelKey: "nav.fateExplorer", icon: Network },
  { path: "/litigation", labelKey: "nav.sentinel", icon: Scale },
  { path: "/regulatory", labelKey: "nav.regulatory", icon: Globe },
  { path: "/portfolio", labelKey: "nav.portfolio", icon: Package },
  { path: "/reports", labelKey: "nav.reports", icon: FileText },
  { path: "/evidence", labelKey: "nav.evidence", icon: BookOpen },
  { path: "/analysis", labelKey: "nav.analysis", icon: FlaskConical },
  { path: "/tier1", labelKey: "nav.tier1", icon: Fingerprint },
];

// Routes that should NOT show the platform navigation
const standaloneRoutes = ['/ensurance'];

const Disclaimer = () => {
  const { t } = useTranslation();
  return (
    <div className="container mx-auto px-4 py-2 text-left">
      <p className="text-xs text-gray-400 italic">
        {t('nav.disclaimer')}
      </p>
    </div>
  );
};

const Navigation = () => {
  const location = useLocation();
  const { t } = useTranslation();

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-50 shadow-lg">
      <Disclaimer />
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between py-2">
          <div className="w-24 flex items-center">
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
                  className={`flex flex-col items-center px-3 py-2 rounded-lg transition-colors ${
                    isActive
                      ? "bg-gradient-to-r from-chemours-red/10 to-chemours-orange/10 text-chemours-red"
                      : "text-gray-500 hover:text-chemours-red hover:bg-gray-100"
                  }`}
                >
                  <Icon className="h-5 w-5" />
                  <span className="text-xs mt-1">{t(item.labelKey)}</span>
                </Link>
              );
            })}
          </div>
          <div className="flex-shrink-0 flex justify-end">
            <BoundStateLogo variant="full" theme="light" size="sm" />
          </div>
        </div>
      </div>
    </nav>
  );
};

const AppContent = () => {
  const location = useLocation();
  const isStandalone = standaloneRoutes.includes(location.pathname);

  // Keep Railway backend warm to prevent cold start delays
  useBackendWarmup();

  return (
    <div className={isStandalone ? '' : 'pb-20'}>
      <Routes>
        <Route path="/" element={<FateExplorer />} />
        <Route path="/litigation" element={<LitigationRisk />} />
        <Route path="/regulatory" element={<RegulatoryCompliance />} />
        <Route path="/portfolio" element={<PortfolioAssessment />} />
        <Route path="/reports" element={<ExecutiveReports />} />
        <Route path="/evidence" element={<EvidenceChain />} />
        <Route path="/analysis" element={<PFASAnalysis />} />
        <Route path="/tier1" element={<StructuralSimilarity />} />
        <Route path="/ensurance" element={<Ensurance />} />
        {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
        <Route path="*" element={<NotFound />} />
      </Routes>
      {!isStandalone && <Navigation />}
    </div>
  );
};

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <AppContent />
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
