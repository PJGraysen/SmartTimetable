import http from "./http";

export type NotificationItem = {
  id: number;
  kind: "INFO" | "APPROVAL" | "APPROVED" | "REJECTED" | "REQUEST" | "ALERT";
  title: string;
  body: string;
  url: string;
  is_read: boolean;
  created_at: string;
  read_at: string | null;
};

export type ApprovalItem = {
  id: number;
  kind: string;
  status: "PENDING" | "APPROVED" | "REJECTED" | "CANCELLED";
  title: string;
  body: string;
  requested_by: number;
  requested_by_name: string;
  assigned_to: number;
  assigned_to_name: string;
  created_at: string;
  decided_at: string | null;
  decision_note: string;
};

export async function listNotifications(): Promise<NotificationItem[]> {
  const { data } = await http.get("/notifications/");
  return Array.isArray(data) ? data : (data?.results || []);
}

export async function unreadCount(): Promise<number> {
  const { data } = await http.get("/notifications/unread-count/");
  return data?.unread ?? 0;
}

export async function markRead(id: number) {
  const { data } = await http.post(`/notifications/${id}/mark-read/`, {});
  return data;
}

export async function markAllRead() {
  const { data } = await http.post("/notifications/mark-all-read/", {});
  return data;
}

export async function listApprovals(): Promise<ApprovalItem[]> {
  const { data } = await http.get("/approvals/");
  return Array.isArray(data) ? data : (data?.results || []);
}

export async function pendingCount(): Promise<number> {
  const { data } = await http.get("/approvals/pending-count/");
  return data?.pending ?? 0;
}

export async function approveRequest(id: number, note = "") {
  const { data } = await http.post(`/approvals/${id}/approve/`, { note });
  return data;
}

export async function rejectRequest(id: number, note = "") {
  const { data } = await http.post(`/approvals/${id}/reject/`, { note });
  return data;
}
