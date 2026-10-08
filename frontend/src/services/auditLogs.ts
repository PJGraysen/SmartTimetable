import http from "./http";

export type AuditLog = {
  id: string;
  created_at: string;
  user: number | null;
  user_username: string | null;
  user_name: string | null;
  action: string;
  entity_type: string;
  entity_id: string;
  description: string;
  ip_address: string | null;
};

type Paged<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

type ListParams = {
  entity_type?: string;
  action?: string;
  q?: string;
  from?: string;
  to?: string;
  page_size?: number;
};

export async function listAuditLogs(params: ListParams = {}): Promise<Paged<AuditLog>> {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") qs.append(k, String(v));
  });
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  const { data } = await http.get<Paged<AuditLog> | AuditLog[]>(`/audit/logs/${suffix}`);

  // Backend may return either a paginated object {count, results} or a
  // plain array (when no pagination_class is configured). Normalise here.
  if (Array.isArray(data)) {
    return {
      count: data.length,
      next: null,
      previous: null,
      results: data,
    };
  }
  return {
    count: data.count ?? 0,
    next: data.next ?? null,
    previous: data.previous ?? null,
    results: Array.isArray(data.results) ? data.results : [],
  };
}
