// API configuration
// - Production (Vercel): default empty string routes through vercel.json /api proxy.
// - Optional explicit base: VITE_API_BASE or VITE_RAILWAY_API_BASE.
const RAW_API_BASE = import.meta.env.VITE_API_BASE || import.meta.env.VITE_RAILWAY_API_BASE || "";
export const API_BASE = String(RAW_API_BASE).replace(/\/+$/, "");
