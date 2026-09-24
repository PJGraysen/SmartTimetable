import http from "./http";

export type ReportableError = {
  source: string;
  severity?: "ERROR" | "WARNING" | "INFO";
  code?: string;
  message: string;
  context?: Record<string, unknown>;
  url?: string;
  scheduling_run?: string;
};

export async function reportError(payload: ReportableError): Promise<void> {
  try {
    await http.post("/scheduling/errors/report/", {
      ...payload,
      url: payload.url ?? (typeof window !== "undefined" ? window.location.pathname : ""),
    });
  } catch {
    // best-effort logging; never break UX because of it
  }
}

export type ErrorLog = {
  id: string;
  created_at: string;
  source: string;
  severity: "ERROR" | "WARNING" | "INFO";
  code: string;
  message: string;
  context: Record<string, unknown>;
  user: string | null;
  url: string;
};

export async function listErrorLogs(params?: {
  severity?: string; source?: string;
}): Promise<{ count: number; results: ErrorLog[] }> {
  const qs = new URLSearchParams();
  if (params?.severity) qs.set("severity", params.severity);
  if (params?.source) qs.set("source", params.source);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  const { data } = await http.get(`/scheduling/errors/${suffix}`);
  return data;
}