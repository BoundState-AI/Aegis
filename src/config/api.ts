// API configuration
// - Production (Vercel): uses empty string to route through Vercel's /api proxy
// - Development: set VITE_API_BASE=http://localhost:8002
export const API_BASE = import.meta.env.VITE_API_BASE || "";
