import { FormEvent, useMemo, useState } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { KeyRound, ShieldCheck } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { isAuthenticated, isValidLoginPassword, loginWithSession } from "@/lib/auth";

const DEFAULT_REDIRECT = "/fate-explorer";

function getSafeNextPath(next: string | null): string {
  if (!next) return DEFAULT_REDIRECT;
  if (!next.startsWith("/") || next.startsWith("//")) return DEFAULT_REDIRECT;
  return next;
}

export default function Login() {
  const [params] = useSearchParams();
  const navigate = useNavigate();

  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [error, setError] = useState("");

  const nextPath = useMemo(() => getSafeNextPath(params.get("next")), [params]);
  const authed = isAuthenticated();

  if (authed) {
    return <Navigate to={nextPath} replace />;
  }

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!isValidLoginPassword(password.trim())) {
      setError("Incorrect password.");
      return;
    }

    loginWithSession(remember);
    navigate(nextPath, { replace: true });
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-100 via-white to-slate-50 px-4 py-10">
      <div className="mx-auto flex min-h-[80vh] w-full max-w-5xl items-center justify-center">
        <Card className="w-full max-w-md border-slate-200 shadow-xl shadow-slate-300/40">
          <CardHeader className="space-y-3">
            <div className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-daikin-blue/10 text-daikin-blue">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <CardTitle className="text-2xl text-slate-900">AEGIS Login</CardTitle>
            <CardDescription>
              Enter the platform password to access AEGIS.
            </CardDescription>
          </CardHeader>

          <CardContent>
            <form className="space-y-4" onSubmit={onSubmit}>
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <div className="relative">
                  <KeyRound className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <Input
                    id="password"
                    type="password"
                    autoComplete="current-password"
                    className="pl-9"
                    placeholder="Enter password"
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value);
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
                  className="h-4 w-4 rounded border-slate-300 text-daikin-blue focus:ring-daikin-blue"
                />
                Remember this device
              </label>

              {error && (
                <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>
              )}

              <Button type="submit" className="w-full bg-daikin-blue hover:bg-daikin-blue/90">
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
