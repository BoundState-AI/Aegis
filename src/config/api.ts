// API configuration
// - Production (Vercel): uses empty string to route through Vercel's /api proxy
// - Development: set VITE_API_BASE=http://localhost:8002
// Build timestamp: 2026-01-31T19:30:00Z - Force clean build
export const API_BASE = import.meta.env.VITE_API_BASE || "";
