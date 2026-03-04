const AUTH_FLAG_KEY = "aegis.authenticated";
const API_KEY_STORAGE_KEY = "aegis.apiKey";
const EMAIL_STORAGE_KEY = "aegis.email";

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

export function hasManagedSessionAuth(): boolean {
  return true;
}

export function getActiveApiKey(): string {
  const stored = readStorageValue(API_KEY_STORAGE_KEY);
  return stored || ENV_API_KEY;
}

export function getStoredEmail(): string {
  return readStorageValue(EMAIL_STORAGE_KEY);
}

export function isAuthenticated(): boolean {
  const authed = readStorageValue(AUTH_FLAG_KEY) === "true";
  return authed && Boolean(getActiveApiKey());
}

export function loginWithApiKey(apiKey: string, email: string, remember: boolean): void {
  writeStorageValue(AUTH_FLAG_KEY, "true", remember);
  writeStorageValue(API_KEY_STORAGE_KEY, apiKey, remember);
  writeStorageValue(EMAIL_STORAGE_KEY, email, remember);
}

export function clearAuthSession(): void {
  clearStorageValue(AUTH_FLAG_KEY);
  clearStorageValue(API_KEY_STORAGE_KEY);
  clearStorageValue(EMAIL_STORAGE_KEY);
}
