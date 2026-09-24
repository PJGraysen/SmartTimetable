import http from "./http";

export type AdminUser = {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  is_staff: boolean;
  is_superuser: boolean;
  groups: string[];
  last_login: string | null;
  date_joined: string | null;
};

export type AdminGroup = {
  id: number;
  name: string;
  user_count: number;
  permission_count: number;
};

export type AdminHealth = {
  db_ok: boolean;
  disk: { total_gb: number; used_gb: number; free_gb: number; used_pct: number };
  counts: Record<string, number>;
  recent_audit: Array<{
    created_at: string;
    action: string;
    entity_type: string;
    entity_label: string;
  }>;
  server_time: string;
};

export type AdminWarning = {
  severity: "info" | "warning" | "danger";
  title: string;
  detail: string;
};

export async function listUsers(q?: string): Promise<{ count: number; results: AdminUser[] }> {
  const suffix = q ? `?q=${encodeURIComponent(q)}` : "";
  const { data } = await http.get(`/platform/admin/users/${suffix}`);
  return data;
}

export async function createUser(payload: Partial<AdminUser> & { username: string; password?: string }): Promise<AdminUser> {
  const { data } = await http.post<AdminUser>("/platform/admin/users/", payload);
  return data;
}

export async function updateUser(id: number, patch: Partial<AdminUser>): Promise<AdminUser> {
  const { data } = await http.patch<AdminUser>(`/platform/admin/users/${id}/`, patch);
  return data;
}

export async function deleteUser(id: number): Promise<void> {
  await http.delete(`/platform/admin/users/${id}/`);
}

export async function resetPassword(id: number, password: string): Promise<{ ok: boolean; username: string }> {
  const { data } = await http.post(`/platform/admin/users/${id}/reset-password/`, { password });
  return data;
}

export async function listGroups(): Promise<AdminGroup[]> {
  const { data } = await http.get<AdminGroup[]>("/platform/admin/groups/");
  return data;
}

export async function createGroup(name: string): Promise<AdminGroup> {
  const { data } = await http.post<AdminGroup>("/platform/admin/groups/", { name });
  return data;
}

export async function deleteGroup(id: number): Promise<void> {
  await http.delete(`/platform/admin/groups/${id}/`);
}

export async function fetchHealth(): Promise<AdminHealth> {
  const { data } = await http.get<AdminHealth>("/platform/admin/health/");
  return data;
}

export async function fetchWarnings(): Promise<{ count: number; warnings: AdminWarning[] }> {
  const { data } = await http.get("/platform/admin/warnings/");
  return data;
}