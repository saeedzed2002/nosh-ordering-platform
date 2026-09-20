const defaultApiBaseUrl = "http://localhost:8000";

export function resolveApiBaseUrl(value?: string): string {
  const candidate = value?.trim() || defaultApiBaseUrl;
  return candidate.replace(/\/+$/, "");
}

export const apiBaseUrl = resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL);
