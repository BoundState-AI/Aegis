import { FormEvent, useEffect, useMemo, useState } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { Mail, ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, apiGet, apiPost } from "@/lib/apiClient";
import { accessRequestCreateSchema, accessRequestStatusSchema } from "@/lib/apiSchemas";
import { isAuthenticated, loginWithSession } from "@/lib/auth";

const DEFAULT_REDIRECT = "/fate-explorer";
const POLL_INTERVAL_MS = 5000;

function getSafeNextPath(next: string | null): string {
  if (!next) return DEFAULT_REDIRECT;
  if (!next.startsWith("/") || next.startsWith("//")) return DEFAULT_REDIRECT;
  return next;
}

function isValidEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

export default function Login() {
  const [params] = useSearchParams();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [remember, setRemember] = useState(true);
  const [rememberForApproval, setRememberForApproval] = useState(true);
  const [requestId, setRequestId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");

  const nextPath = useMemo(() => getSafeNextPath(params.get("next")), [params]);
  const authed = isAuthenticated();

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const trimmedEmail = email.trim().toLowerCase();
    if (!isValidEmail(trimmedEmail)) {
      setError("Enter a valid email address.");
      return;
    }

    setIsSubmitting(true);
    setError("");
    setInfo("");

    try {
      const response = await apiPost(
        "/api/v1/auth/access-request",
        accessRequestCreateSchema,
        { email: trimmedEmail },
      );

      if (response.status === "approved") {
        loginWithSession(remember);
        navigate(nextPath, { replace: true });
        return;
      }

      setRequestId(response.request_id);
      setRememberForApproval(remember);
      setInfo(
        response.email_sent
          ? "Request sent. Check with your admin for approval."
          : "Request recorded. Admin notification email is not configured yet.",
      );
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message || "Could not submit access request.");
      } else {
        setError("Could not submit access request.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  useEffect(() => {
    if (!requestId) return;

    let active = true;
    const poll = async () => {
      try {
        const status = await apiGet(
          `/api/v1/auth/access-request/${encodeURIComponent(requestId)}`,
          accessRequestStatusSchema,
        );

        if (!active) return;

        if (status.status === "approved") {
          loginWithSession(rememberForApproval);
          navigate(nextPath, { replace: true });
          return;
        }

        if (status.status === "rejected") {
          setError("Your access request was rejected. Contact your administrator.");
          setInfo("");
          setRequestId(null);
        }
      } catch {
        if (!active) return;
        setError("Could not refresh access request status.");
      }
    };

    void poll();
    const timer = window.setInterval(() => {
      void poll();
    }, POLL_INTERVAL_MS);

    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [navigate, nextPath, rememberForApproval, requestId]);

  if (authed) {
    return <Navigate to={nextPath} replace />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-100 via-white to-slate-50 px-4 py-10">
      <div className="mx-auto flex min-h-[80vh] w-full max-w-5xl items-center justify-center">
        <Card className="w-full max-w-md border-slate-200 shadow-xl shadow-slate-300/40">
          <CardHeader className="space-y-3">
            <div className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-chemours-red/10 text-chemours-red">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <CardTitle className="text-2xl text-slate-900">AEGIS Access</CardTitle>
            <CardDescription>
              Enter your email to request access. You will be signed in once approved.
            </CardDescription>
          </CardHeader>

          <CardContent>
            <form className="space-y-4" onSubmit={onSubmit}>
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <div className="relative">
                  <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <Input
                    id="email"
                    type="email"
                    autoComplete="email"
                    className="pl-9"
                    placeholder="you@company.com"
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value);
                      if (error) setError("");
                    }}
                    disabled={isSubmitting || Boolean(requestId)}
                  />
                </div>
              </div>

              <label className="flex items-center gap-2 text-sm text-slate-600" htmlFor="remember-device">
                <input
                  id="remember-device"
                  type="checkbox"
                  checked={remember}
                  onChange={(e) => setRemember(e.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 text-chemours-red focus:ring-chemours-red"
                  disabled={isSubmitting || Boolean(requestId)}
                />
                Remember this device
              </label>

              {info && (
                <p className="rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-700">{info}</p>
              )}

              {requestId && (
                <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                  Waiting for approval. Request ID: <span className="font-semibold">{requestId}</span>
                </p>
              )}

              {error && (
                <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
              )}

              <Button
                type="submit"
                className="w-full bg-chemours-red hover:bg-chemours-red/90"
                disabled={isSubmitting || Boolean(requestId)}
              >
                {isSubmitting ? "Submitting..." : "Request Access"}
              </Button>
            </form>

            <p className="mt-5 text-center text-xs text-slate-500">
              You will get access after an administrator approves your request.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
