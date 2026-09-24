import http from "./http";

export type AuditEvent = {
  id: string;
  created_at: string;
  actor: number | null;
  actor_username: string | null;
  actor_display: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  entity_label: string;
  meta_json: Record<string, unknown>;
  ip_address: string | null;
  user_agent: string;
};

export type AuditPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: AuditEvent[];
};

export async function listAuditEvents(params?: {
  entity_type?: string;
  action?: string;
  q?: string;
  from?: string;
  to?: string;
  page?: number;
  page_size?: number;
}): Promise<AuditPage> {
  const qs = new URLSearchParams();
  if (params?.entity_type) qs.set("entity_type", params.entity_type);
  if (params?.action) qs.set("action", params.action);
  if (params?.q) qs.set("search", params.q);
  if (params?.from) qs.set("from", params.from);
  if (params?.to) qs.set("to", params.to);
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  const { data } = await http.get(`/academics/audit-events/${suffix}`);
  // tolerate array or paginated
  if (Array.isArray(data)) {
    return { count: data.length, next: null, previous: null, results: data };
  }
  return data;
}