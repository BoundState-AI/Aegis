import { useEffect, useMemo, useState } from "react";
import { Activity, CheckCircle2, Clock3, Eye, Loader2, ShieldAlert, Sparkles } from "lucide-react";
import { useTranslation } from "react-i18next";

import ChemoursHeader from "@/components/layout/ChemoursHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import { API_BASE } from "@/config/api";
import { useHelpContent } from "@/config/helpContent";

type SignalRow = {
  signal_id: string;
  detected_at?: string;
  source_label?: string;
  country?: string;
  classification?: string;
  severity?: string;
  summary?: string;
};

type PendingItem = {
  resolution_id: string;
  gate_status: "PENDING_REVIEW" | "PENDING_APPROVAL" | "APPROVED" | "DISMISSED";
  human_review_required?: boolean;
  warnings?: string[];
  summary?: {
    compound?: string;
    critical_flags?: number;
  };
};

type ResolveResponse = {
  resolution_id: string;
  gate_status: string;
  warnings?: string[];
  result: {
    query_compound?: { preferred_name?: string; cas?: string };
    total_exposure?: { assertions_triggered?: number; trajectory?: string };
    threat_flags?: Array<{ flag_type?: string; severity?: string }>;
  };
};

export type IntelligenceTabKey = "signals" | "resolver" | "queue";

interface IntelligenceProps {
  embedded?: boolean;
  initialTab?: IntelligenceTabKey;
  singleTab?: IntelligenceTabKey;
  hideSummaryCards?: boolean;
}

const API_KEY = import.meta.env.VITE_AEGIS_API_KEY || import.meta.env.VITE_AEGIS_MONITOR_API_KEY || "";

const Intelligence = ({
  embedded = false,
  initialTab = "signals",
  singleTab,
  hideSummaryCards = false,
}: IntelligenceProps) => {
  const { t } = useTranslation();
  const { toast } = useToast();
  const helpContent = useHelpContent();
  const [activeTab, setActiveTab] = useState<IntelligenceTabKey>(singleTab || initialTab);

  const [signals, setSignals] = useState<SignalRow[]>([]);
  const [pending, setPending] = useState<PendingItem[]>([]);
  const [loadingSignals, setLoadingSignals] = useState(false);
  const [loadingPending, setLoadingPending] = useState(false);
  const [resolving, setResolving] = useState(false);
  const [seedAction, setSeedAction] = useState<"seed" | "clear" | null>(null);
  const [compound, setCompound] = useState("Opteon 1234yf");
  const [resolverResult, setResolverResult] = useState<ResolveResponse | null>(null);
  const [justificationById, setJustificationById] = useState<Record<string, string>>({});
  const [actingId, setActingId] = useState<string | null>(null);

  const headers = useMemo(
    () => ({
      ...(API_KEY ? { "X-AEGIS-API-Key": API_KEY, Authorization: `Bearer ${API_KEY}` } : {}),
      "Content-Type": "application/json",
    }),
    [],
  );

  const loadSignals = async () => {
    setLoadingSignals(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/monitor/signals?limit=25`, { headers });
      if (!res.ok) throw new Error(`signals ${res.status}`);
      const data = await res.json();
      setSignals((data?.signals || []) as SignalRow[]);
    } catch {
      toast({
        title: t("intelligence.toasts.signalsUnavailableTitle"),
        description: t("intelligence.toasts.signalsUnavailableDescription"),
        variant: "destructive",
      });
    } finally {
      setLoadingSignals(false);
    }
  };

  const loadPending = async () => {
    setLoadingPending(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/resolver/pending?limit=100`, { headers });
      if (!res.ok) throw new Error(`pending ${res.status}`);
      const data = await res.json();
      setPending((data?.items || []) as PendingItem[]);
    } catch {
      toast({
        title: t("intelligence.toasts.queueUnavailableTitle"),
        description: t("intelligence.toasts.queueUnavailableDescription"),
        variant: "destructive",
      });
    } finally {
      setLoadingPending(false);
    }
  };

  useEffect(() => {
    void loadSignals();
    void loadPending();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (singleTab) {
      setActiveTab(singleTab);
    }
  }, [singleTab]);

  const runResolve = async () => {
    if (!compound.trim()) return;
    setResolving(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/resolver/resolve`, {
        method: "POST",
        headers,
        body: JSON.stringify({ compound: compound.trim() }),
      });
      if (!res.ok) throw new Error(`resolve ${res.status}`);
      const data = (await res.json()) as ResolveResponse;
      setResolverResult(data);
      toast({
        title: t("intelligence.toasts.resolverQueuedTitle"),
        description: t("intelligence.toasts.resolverQueuedDescription", {
          id: data.resolution_id,
          status: data.gate_status,
        }),
      });
      void loadPending();
    } catch {
      toast({
        title: t("intelligence.toasts.resolverFailedTitle"),
        description: t("intelligence.toasts.resolverFailedDescription"),
        variant: "destructive",
      });
    } finally {
      setResolving(false);
    }
  };

  const runSeedDemoSignals = async () => {
    setSeedAction("seed");
    try {
      const res = await fetch(`${API_BASE}/api/v1/monitor/seed-demo`, {
        method: "POST",
        headers,
      });
      if (!res.ok) throw new Error(`seed ${res.status}`);
      const data = await res.json();
      toast({
        title: t("intelligence.toasts.seedDemoSuccessTitle"),
        description: t("intelligence.toasts.seedDemoSuccessDescription", {
          inserted: data?.inserted ?? 0,
          skipped: data?.skipped ?? 0,
        }),
      });
      void loadSignals();
    } catch {
      toast({
        title: t("intelligence.toasts.seedDemoFailedTitle"),
        description: t("intelligence.toasts.seedDemoFailedDescription"),
        variant: "destructive",
      });
    } finally {
      setSeedAction(null);
    }
  };

  const runClearDemoSignals = async () => {
    setSeedAction("clear");
    try {
      const res = await fetch(`${API_BASE}/api/v1/monitor/seed-demo/clear`, {
        method: "POST",
        headers,
      });
      if (!res.ok) throw new Error(`clear ${res.status}`);
      const data = await res.json();
      toast({
        title: t("intelligence.toasts.clearDemoSuccessTitle"),
        description: t("intelligence.toasts.clearDemoSuccessDescription", {
          deleted: data?.deleted ?? 0,
        }),
      });
      void loadSignals();
    } catch {
      toast({
        title: t("intelligence.toasts.clearDemoFailedTitle"),
        description: t("intelligence.toasts.clearDemoFailedDescription"),
        variant: "destructive",
      });
    } finally {
      setSeedAction(null);
    }
  };

  const actOnResolution = async (
    item: PendingItem,
    action: "confirm" | "dismiss" | "escalate" | "approve" | "hold",
  ) => {
    const justification = (justificationById[item.resolution_id] || "").trim();
    const isReview = item.gate_status === "PENDING_REVIEW";
    const needsJustification = action === "dismiss";
    if (needsJustification && !justification) {
      toast({
        title: t("intelligence.toasts.justificationRequiredTitle"),
        description: t("intelligence.toasts.justificationRequiredDescription"),
        variant: "destructive",
      });
      return;
    }

    setActingId(item.resolution_id);
    try {
      const endpoint = isReview ? "/api/v1/resolver/review" : "/api/v1/resolver/approve";
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          resolution_id: item.resolution_id,
          action,
          justification,
        }),
      });
      if (!res.ok) throw new Error(`gate ${res.status}`);
      toast({
        title: t("intelligence.toasts.queueUpdatedTitle"),
        description: t("intelligence.toasts.queueUpdatedDescription", {
          id: item.resolution_id,
          action,
        }),
      });
      void loadPending();
    } catch {
      toast({
        title: t("intelligence.toasts.gateActionFailedTitle"),
        description: t("intelligence.toasts.gateActionFailedDescription", {
          id: item.resolution_id,
          action,
        }),
        variant: "destructive",
      });
    } finally {
      setActingId(null);
    }
  };

  const content = (
    <div className="space-y-6">
      {!hideSummaryCards && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>{t("intelligence.cards.recentSignals")}</CardDescription>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5 text-chemours-red" />
                {signals.length}
              </CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>{t("intelligence.cards.pendingReview")}</CardDescription>
              <CardTitle className="flex items-center gap-2">
                <Clock3 className="h-5 w-5 text-amber-500" />
                {pending.filter((x) => x.gate_status === "PENDING_REVIEW").length}
              </CardTitle>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>{t("intelligence.cards.pendingApproval")}</CardDescription>
              <CardTitle className="flex items-center gap-2">
                <Eye className="h-5 w-5 text-blue-500" />
                {pending.filter((x) => x.gate_status === "PENDING_APPROVAL").length}
              </CardTitle>
            </CardHeader>
          </Card>
        </div>
      )}

      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as IntelligenceTabKey)} className="space-y-4">
        {!singleTab && (
          <TabsList>
            <TabsTrigger value="signals">{t("intelligence.tabs.signals")}</TabsTrigger>
            <TabsTrigger value="resolver">{t("intelligence.tabs.resolver")}</TabsTrigger>
            <TabsTrigger value="queue">{t("intelligence.tabs.reviewQueue")}</TabsTrigger>
          </TabsList>
        )}

          <TabsContent value="signals">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>{t("intelligence.signals.title")}</CardTitle>
                    <CardDescription>{t("intelligence.signals.description")}</CardDescription>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" onClick={() => void runSeedDemoSignals()} disabled={seedAction !== null}>
                      {seedAction === "seed" ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : null}
                      {t("intelligence.signals.actions.seedDemo")}
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => void runClearDemoSignals()} disabled={seedAction !== null}>
                      {seedAction === "clear" ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : null}
                      {t("intelligence.signals.actions.clearDemo")}
                    </Button>
                    <Button variant="outline" onClick={() => void loadSignals()} disabled={loadingSignals}>
                      {loadingSignals ? <Loader2 className="h-4 w-4 animate-spin" /> : t("intelligence.refresh")}
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {signals.map((s) => (
                  <div key={s.signal_id} className="border rounded-md p-3 bg-white">
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <Badge variant="outline">{s.severity || t("common.unknown")}</Badge>
                      <Badge variant="secondary">{s.classification || t("intelligence.signals.unclassified")}</Badge>
                      <span className="text-xs text-gray-500">{s.country || t("common.notAvailable")}</span>
                    </div>
                    <div className="text-sm font-medium text-chemours-dark">
                      {s.source_label || t("intelligence.signals.unknownSource")}
                    </div>
                    <div className="text-sm text-gray-600">{s.summary || t("intelligence.signals.noSummary")}</div>
                    <div className="text-xs text-gray-500 mt-1">{s.detected_at || ""}</div>
                  </div>
                ))}
                {!loadingSignals && signals.length === 0 && (
                  <div className="text-sm text-gray-500">{t("intelligence.signals.empty")}</div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="resolver">
            <Card>
              <CardHeader>
                <CardTitle>{t("intelligence.resolver.title")}</CardTitle>
                <CardDescription>{t("intelligence.resolver.description")}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex gap-3">
                  <Input
                    value={compound}
                    onChange={(e) => setCompound(e.target.value)}
                    placeholder={t("intelligence.resolver.inputPlaceholder")}
                  />
                  <Button onClick={runResolve} disabled={resolving}>
                    {resolving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Sparkles className="h-4 w-4 mr-2" />}
                    {t("intelligence.resolver.run")}
                  </Button>
                </div>

                {resolverResult && (
                  <div className="border rounded-md p-4 bg-white space-y-2">
                    <div className="flex items-center gap-2">
                      <Badge>{resolverResult.gate_status}</Badge>
                      <span className="text-xs text-gray-500">{resolverResult.resolution_id}</span>
                    </div>
                    <div className="text-sm">
                      <span className="font-medium">{t("intelligence.resolver.compound")}:</span>{" "}
                      {resolverResult.result?.query_compound?.preferred_name || t("common.notAvailable")} ({resolverResult.result?.query_compound?.cas || t("intelligence.resolver.noCas")})
                    </div>
                    <div className="text-sm">
                      <span className="font-medium">{t("intelligence.resolver.assertions")}:</span>{" "}
                      {resolverResult.result?.total_exposure?.assertions_triggered ?? 0}
                      {" · "}
                      <span className="font-medium">{t("intelligence.resolver.trajectory")}:</span>{" "}
                      {resolverResult.result?.total_exposure?.trajectory || t("common.notAvailable")}
                    </div>
                    <div className="flex gap-2 flex-wrap">
                      {(resolverResult.result?.threat_flags || []).map((f, i) => (
                        <Badge key={`${f.flag_type || "flag"}-${i}`} variant="outline">
                          {f.flag_type || t("intelligence.resolver.flag")}:{f.severity || t("common.unknown")}
                        </Badge>
                      ))}
                    </div>
                    {(resolverResult.warnings || []).length > 0 && (
                      <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-2">
                        {(resolverResult.warnings || []).join(" | ")}
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="queue">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>{t("intelligence.queue.title")}</CardTitle>
                    <CardDescription>{t("intelligence.queue.description")}</CardDescription>
                  </div>
                  <Button variant="outline" onClick={() => void loadPending()} disabled={loadingPending}>
                    {loadingPending ? <Loader2 className="h-4 w-4 animate-spin" /> : t("intelligence.refresh")}
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {pending.map((item) => {
                  const isReview = item.gate_status === "PENDING_REVIEW";
                  const busy = actingId === item.resolution_id;
                  return (
                    <div key={item.resolution_id} className="border rounded-md p-3 bg-white space-y-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge>{item.gate_status}</Badge>
                        {item.human_review_required && (
                          <Badge variant="destructive" className="flex items-center gap-1">
                            <ShieldAlert className="h-3 w-3" /> {t("intelligence.queue.reviewRequired")}
                          </Badge>
                        )}
                        <span className="text-xs text-gray-500">{item.resolution_id}</span>
                      </div>
                      <div className="text-sm text-gray-700">
                        {(item.summary?.compound || t("intelligence.queue.unknownCompound"))} · {t("intelligence.queue.criticalFlags")}:{" "}
                        {item.summary?.critical_flags ?? 0}
                      </div>
                      {(item.warnings || []).length > 0 && (
                        <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-2">
                          {(item.warnings || []).join(" | ")}
                        </div>
                      )}
                      <Input
                        value={justificationById[item.resolution_id] || ""}
                        onChange={(e) =>
                          setJustificationById((prev) => ({
                            ...prev,
                            [item.resolution_id]: e.target.value,
                          }))
                        }
                        placeholder={t("intelligence.queue.justificationPlaceholder")}
                      />
                      <div className="flex gap-2 flex-wrap">
                        {isReview ? (
                          <>
                            <Button size="sm" onClick={() => void actOnResolution(item, "confirm")} disabled={busy}>
                              <CheckCircle2 className="h-4 w-4 mr-1" /> {t("intelligence.queue.actions.confirm")}
                            </Button>
                            <Button size="sm" variant="outline" onClick={() => void actOnResolution(item, "escalate")} disabled={busy}>
                              {t("intelligence.queue.actions.escalate")}
                            </Button>
                            <Button size="sm" variant="destructive" onClick={() => void actOnResolution(item, "dismiss")} disabled={busy}>
                              {t("intelligence.queue.actions.dismiss")}
                            </Button>
                          </>
                        ) : (
                          <>
                            <Button size="sm" onClick={() => void actOnResolution(item, "approve")} disabled={busy}>
                              <CheckCircle2 className="h-4 w-4 mr-1" /> {t("intelligence.queue.actions.approve")}
                            </Button>
                            <Button size="sm" variant="outline" onClick={() => void actOnResolution(item, "hold")} disabled={busy}>
                              {t("intelligence.queue.actions.hold")}
                            </Button>
                          </>
                        )}
                      </div>
                    </div>
                  );
                })}
                {!loadingPending && pending.length === 0 && (
                  <div className="text-sm text-gray-500">{t("intelligence.queue.empty")}</div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
      </Tabs>
    </div>
  );

  if (embedded) {
    return content;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <ChemoursHeader
        title={t("intelligence.title")}
        subtitle={t("intelligence.subtitle")}
        helpContent={helpContent.intelligence}
      />
      <main className="container mx-auto px-4 py-8">{content}</main>
    </div>
  );
};

export default Intelligence;
