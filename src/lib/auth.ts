const AUTH_FLAG_KEY = "aegis.authenticated";

const ENV_API_KEY =
  import.meta.env.VITE_AEGIS_API_KEY ||
  import.meta.env.VITE_AEGIS_MONITOR_API_KEY ||
  "";

function hasWindow(): boolean {
  return typeof window !== "undefined";
}

function readStorageValue(key: string): string {
  if (!hasWindow()) return "";
  return sessionStorage.getItem(key) || localStorage.getItem(key) || "";
}

function writeStorageValue(key: string, value: string, remember: boolean): void {
  if (!hasWindow()) return;
  const target = remember ? localStorage : sessionStorage;
  const other = remember ? sessionStorage : localStorage;
  target.setItem(key, value);
  other.removeItem(key);
}

function clearStorageValue(key: string): void {
  if (!hasWindow()) return;
  sessionStorage.removeItem(key);
  localStorage.removeItem(key);
}

export function getActiveApiKey(): string {
  return ENV_API_KEY;
}

export function isAuthenticated(): boolean {
  return readStorageValue(AUTH_FLAG_KEY) === "true";
}

export function loginWithSession(remember: boolean): void {
  writeStorageValue(AUTH_FLAG_KEY, "true", remember);
}

export function clearAuthSession(): void {
  clearStorageValue(AUTH_FLAG_KEY);
}
