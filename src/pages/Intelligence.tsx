import { useEffect, useState } from "react";
import { Activity, CheckCircle2, Clock3, Eye, Loader2, ShieldAlert, Sparkles } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import ChemoursHeader from "@/components/layout/ChemoursHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import { useHelpContent } from "@/config/helpContent";
import { apiGet, apiPost } from "@/lib/apiClient";
import {
  clearDemoSchema,
  gateActionSchema,
  pendingListSchema,
  resolveResponseSchema,
  seedDemoSchema,
  signalListSchema,
  type PendingItem,
  type ResolveResponse,
  type SignalRow,
} from "@/lib/apiSchemas";

export type IntelligenceTabKey = "signals" | "resolver" | "queue";

interface IntelligenceProps {
  embedded?: boolean;
  initialTab?: IntelligenceTabKey;
  singleTab?: IntelligenceTabKey;
  hideSummaryCards?: boolean;
}

const QUERY_KEY_SIGNALS = ["monitorSignals"] as const;
const QUERY_KEY_PENDING = ["resolverPending"] as const;

const Intelligence = ({
  embedded = false,
  initialTab = "signals",
  singleTab,
  hideSummaryCards = false,
}: IntelligenceProps) => {
  const { t } = useTranslation();
  const { toast } = useToast();
  const helpContent = useHelpContent();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<IntelligenceTabKey>(singleTab || initialTab);

  const [compound, setCompound] = useState("Opteon 1234yf");
  const [resolverResult, setResolverResult] = useState<ResolveResponse | null>(null);
  const [justificationById, setJustificationById] = useState<Record<string, string>>({});
  const [actingId, setActingId] = useState<string | null>(null);
  const [seedAction, setSeedAction] = useState<"seed" | "clear" | null>(null);

  const signalsQuery = useQuery({
    queryKey: QUERY_KEY_SIGNALS,
    queryFn: async () => {
      const data = await apiGet("/api/v1/monitor/signals?limit=25", signalListSchema);
      return data.signals;
    },
    staleTime: 30_000,
    retry: 1,
  });

  const pendingQuery = useQuery({
    queryKey: QUERY_KEY_PENDING,
    queryFn: async () => {
      const data = await apiGet("/api/v1/resolver/pending?limit=100", pendingListSchema);
      return data.items;
    },
    staleTime: 15_000,
    retry: 1,
  });

  const resolveMutation = useMutation({
    mutationFn: async (rawCompound: string) =>
      apiPost("/api/v1/resolver/resolve", resolveResponseSchema, { compound: rawCompound }),
    onSuccess: (data) => {
      setResolverResult(data);
      toast({
        title: t("intelligence.toasts.resolverQueuedTitle"),
        description: t("intelligence.toasts.resolverQueuedDescription", {
          id: data.resolution_id,
          status: data.gate_status,
        }),
      });
      void queryClient.invalidateQueries({ queryKey: QUERY_KEY_PENDING });
    },
    onError: () => {
      toast({
        title: t("intelligence.toasts.resolverFailedTitle"),
        description: t("intelligence.toasts.resolverFailedDescription"),
        variant: "destructive",
      });
    },
  });

  const seedDemoMutation = useMutation({
    mutationFn: () => apiPost("/api/v1/monitor/seed-demo", seedDemoSchema, {}),
    onSuccess: (data) => {
      toast({
        title: t("intelligence.toasts.seedDemoSuccessTitle"),
        description: t("intelligence.toasts.seedDemoSuccessDescription", {
          inserted: data.inserted,
          skipped: data.skipped,
        }),
      });
      void queryClient.invalidateQueries({ queryKey: QUERY_KEY_SIGNALS });
    },
    onError: () => {
      toast({
        title: t("intelligence.toasts.seedDemoFailedTitle"),
        description: t("intelligence.toasts.seedDemoFailedDescription"),
        variant: "destructive",
      });
    },
    onSettled: () => {
      setSeedAction(null);
    },
  });

  const clearDemoMutation = useMutation({
    mutationFn: () => apiPost("/api/v1/monitor/seed-demo/clear", clearDemoSchema, {}),
    onSuccess: (data) => {
      toast({
        title: t("intelligence.toasts.clearDemoSuccessTitle"),
        description: t("intelligence.toasts.clearDemoSuccessDescription", {
          deleted: data.deleted,
        }),
      });
      void queryClient.invalidateQueries({ queryKey: QUERY_KEY_SIGNALS });
    },
    onError: () => {
      toast({
        title: t("intelligence.toasts.clearDemoFailedTitle"),
        description: t("intelligence.toasts.clearDemoFailedDescription"),
        variant: "destructive",
      });
    },
    onSettled: () => {
      setSeedAction(null);
    },
  });

  const gateActionMutation = useMutation({
    mutationFn: async ({
      endpoint,
      resolutionId,
      action,
      justification,
    }: {
      endpoint: "/api/v1/resolver/review" | "/api/v1/resolver/approve";
      resolutionId: string;
      action: "confirm" | "dismiss" | "escalate" | "approve" | "hold";
      justification: string;
    }) =>
      apiPost(endpoint, gateActionSchema, {
        resolution_id: resolutionId,
        action,
        justification,
      }),
    onSuccess: (_data, vars) => {
      toast({
        title: t("intelligence.toasts.queueUpdatedTitle"),
        description: t("intelligence.toasts.queueUpdatedDescription", {
          id: vars.resolutionId,
          action: vars.action,
        }),
      });
      void queryClient.invalidateQueries({ queryKey: QUERY_KEY_PENDING });
    },
    onError: (_error, vars) => {
      toast({
        title: t("intelligence.toasts.gateActionFailedTitle"),
        description: t("intelligence.toasts.gateActionFailedDescription", {
          id: vars.resolutionId,
          action: vars.action,
        }),
        variant: "destructive",
      });
    },
    onSettled: () => {
      setActingId(null);
    },
  });

  useEffect(() => {
    if (signalsQuery.isError) {
      toast({
        title: t("intelligence.toasts.signalsUnavailableTitle"),
        description: t("intelligence.toasts.signalsUnavailableDescription"),
        variant: "destructive",
      });
    }
    // Intentionally driven by React Query state transition.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signalsQuery.errorUpdatedAt, signalsQuery.isError]);

  useEffect(() => {
    if (pendingQuery.isError) {
      toast({
        title: t("intelligence.toasts.queueUnavailableTitle"),
        description: t("intelligence.toasts.queueUnavailableDescription"),
        variant: "destructive",
      });
    }
    // Intentionally driven by React Query state transition.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingQuery.errorUpdatedAt, pendingQuery.isError]);

  useEffect(() => {
    if (singleTab) {
      setActiveTab(singleTab);
    }
  }, [singleTab]);

  const signals: SignalRow[] = signalsQuery.data ?? [];
  const pending: PendingItem[] = pendingQuery.data ?? [];
  const loadingSignals = signalsQuery.isFetching;
  const loadingPending = pendingQuery.isFetching;

  const runResolve = async () => {
    const normalized = compound.trim();
    if (!normalized) return;
    await resolveMutation.mutateAsync(normalized);
  };

  const runSeedDemoSignals = async () => {
    setSeedAction("seed");
    await seedDemoMutation.mutateAsync();
  };

  const runClearDemoSignals = async () => {
    setSeedAction("clear");
    await clearDemoMutation.mutateAsync();
  };

  const actOnResolution = async (
    item: PendingItem,
    action: "confirm" | "dismiss" | "escalate" | "approve" | "hold",
  ) => {
    const justification = (justificationById[item.resolution_id] || "").trim();
    const isReview = item.gate_status === "PENDING_REVIEW";
    if (action === "dismiss" && !justification) {
      toast({
        title: t("intelligence.toasts.justificationRequiredTitle"),
        description: t("intelligence.toasts.justificationRequiredDescription"),
        variant: "destructive",
      });
      return;
    }

    setActingId(item.resolution_id);
    await gateActionMutation.mutateAsync({
      endpoint: isReview ? "/api/v1/resolver/review" : "/api/v1/resolver/approve",
      resolutionId: item.resolution_id,
      action,
      justification,
    });
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
                  <Button variant="outline" onClick={() => void signalsQuery.refetch()} disabled={loadingSignals}>
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
                <Button onClick={() => void runResolve()} disabled={resolveMutation.isPending}>
                  {resolveMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Sparkles className="h-4 w-4 mr-2" />}
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
                <Button variant="outline" onClick={() => void pendingQuery.refetch()} disabled={loadingPending}>
                  {loadingPending ? <Loader2 className="h-4 w-4 animate-spin" /> : t("intelligence.refresh")}
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {pending.map((item) => {
                const isReview = item.gate_status === "PENDING_REVIEW";
                const busy = actingId === item.resolution_id || gateActionMutation.isPending;
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
