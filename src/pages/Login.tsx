import { FormEvent, useMemo, useState } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { KeyRound, ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  getActiveApiKey,
  getStoredEmail,
  isAuthenticated,
  loginWithApiKey,
} from "@/lib/auth";

const DEFAULT_REDIRECT = "/fate-explorer";

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
  const [email, setEmail] = useState(getStoredEmail());
  const [apiKey, setApiKey] = useState("");
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState("");

  const nextPath = useMemo(() => getSafeNextPath(params.get("next")), [params]);

  if (isAuthenticated()) {
    return <Navigate to={nextPath} replace />;
  }

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const trimmedEmail = email.trim();
    const trimmedApiKey = apiKey.trim();

    if (!isValidEmail(trimmedEmail)) {
      setError("Enter a valid work email.");
      return;
    }

    const effectiveApiKey = trimmedApiKey || getActiveApiKey();

    if (effectiveApiKey.length < 8) {
      setError("Enter a valid AEGIS API key.");
      return;
    }

    loginWithApiKey(effectiveApiKey, trimmedEmail, remember);
    navigate(nextPath, { replace: true });
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-100 via-white to-slate-50 px-4 py-10">
      <div className="mx-auto flex min-h-[80vh] w-full max-w-5xl items-center justify-center">
        <Card className="w-full max-w-md border-slate-200 shadow-xl shadow-slate-300/40">
          <CardHeader className="space-y-3">
            <div className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-chemours-red/10 text-chemours-red">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <CardTitle className="text-2xl text-slate-900">AEGIS Login</CardTitle>
            <CardDescription>
              Use your work email and API key to access the AEGIS platform.
            </CardDescription>
          </CardHeader>

          <CardContent>
            <form className="space-y-4" onSubmit={onSubmit}>
              <div className="space-y-2">
                <Label htmlFor="email">Work Email</Label>
                <Input
                  id="email"
                  autoComplete="email"
                  placeholder="you@company.com"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    if (error) setError("");
                  }}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="api-key">API Key</Label>
                <div className="relative">
                  <KeyRound className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <Input
                    id="api-key"
                    type="password"
                    autoComplete="current-password"
                    className="pl-9"
                    placeholder="Paste your AEGIS key"
                    value={apiKey}
                    onChange={(e) => {
                      setApiKey(e.target.value);
                      if (error) setError("");
                    }}
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
                />
                Remember this device
              </label>

              {error && (
                <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
              )}

              <Button type="submit" className="w-full bg-chemours-red hover:bg-chemours-red/90">
                Sign In
              </Button>
            </form>

            <p className="mt-5 text-center text-xs text-slate-500">
              Need platform access? Contact your AEGIS administrator.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
