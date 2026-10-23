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


// ─── Messages (send/delete/recipients) ──────────────────────
export type Recipient = {
  id: number;
  name: string;
  username: string;
};

export async function listRecipients(): Promise<Recipient[]> {
  const { data } = await http.get("/notifications/recipients/");
  return Array.isArray(data) ? data : (data?.results || []);
}

export async function sendMessage(payload: {
  recipient_id: number;
  title: string;
  body: string;
  kind?: string;
  url?: string;
}): Promise<NotificationItem> {
  const { data } = await http.post<NotificationItem>("/notifications/", {
    recipient_id: payload.recipient_id,
    title: payload.title,
    body: payload.body,
    kind: payload.kind || "INFO",
    url: payload.url || "",
  });
  return data;
}

export async function deleteNotification(id: number): Promise<void> {
  await http.delete(`/notifications/${id}/`);
}


// ─── Phase 3: Attachments, reply, archive, star ────────────────
export type ProNotificationItem = NotificationItem & {
  is_archived: boolean;
  is_starred: boolean;
  sender: number | null;
  sender_name: string | null;
  sender_username: string | null;
  parent: number | null;
  attachment: string | null;
  attachment_name: string;
  attachment_url: string | null;
  replies_count: number;
};

export async function sendMessageWithAttachment(payload: {
  recipient_id: number;
  title: string;
  body: string;
  kind?: string;
  url?: string;
  parent_id?: number | null;
  attachment?: File | null;
}): Promise<ProNotificationItem> {
  const form = new FormData();
  form.append("recipient_id", String(payload.recipient_id));
  form.append("title", payload.title);
  form.append("body", payload.body);
  form.append("kind", payload.kind || "INFO");
  if (payload.url) form.append("url", payload.url);
  if (payload.parent_id) form.append("parent_id", String(payload.parent_id));
  if (payload.attachment) {
    form.append("attachment", payload.attachment);
    form.append("attachment_name", payload.attachment.name);
  }
  const { data } = await http.post<ProNotificationItem>("/notifications/", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function archiveNotification(id: number): Promise<ProNotificationItem> {
  const { data } = await http.post<ProNotificationItem>(`/notifications/${id}/archive/`, {});
  return data;
}

export async function unarchiveNotification(id: number): Promise<ProNotificationItem> {
  const { data } = await http.post<ProNotificationItem>(`/notifications/${id}/unarchive/`, {});
  return data;
}

export async function starNotification(id: number): Promise<ProNotificationItem> {
  const { data } = await http.post<ProNotificationItem>(`/notifications/${id}/star/`, {});
  return data;
}

export async function unstarNotification(id: number): Promise<ProNotificationItem> {
  const { data } = await http.post<ProNotificationItem>(`/notifications/${id}/unstar/`, {});
  return data;
}
