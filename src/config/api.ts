// API configuration - uses environment variable in production, localhost in development
export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8002";
