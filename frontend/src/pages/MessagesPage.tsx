import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Bell, Trash2, Check, CheckCheck, Send, Inbox, Search, Mail, Reply,
  Archive, ArchiveRestore, Star, Paperclip, X, ChevronDown, ChevronUp,
} from "lucide-react";
import {
  listNotifications, markRead, markAllRead, deleteNotification,
  listRecipients, sendMessageWithAttachment,
  archiveNotification, unarchiveNotification, starNotification, unstarNotification,
  type Recipient, type ProNotificationItem,
} from "../services/notifications";

type Tab = "inbox" | "archived" | "compose";
type InboxFilter = "all" | "unread" | "starred";

const KIND_COLORS: Record<string, string> = {
  INFO: "#0284c7", APPROVAL: "#d97706", APPROVED: "#16a34a",
  REJECTED: "#dc2626", REQUEST: "#7c3aed", ALERT: "#ea580c",
};
const KIND_LABELS: Record<string, string> = {
  INFO: "Info", APPROVAL: "Approval", APPROVED: "Approved",
  REJECTED: "Rejected", REQUEST: "Request", ALERT: "Alert",
};

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

export default function MessagesPage() {
  const [tab, setTab] = useState<Tab>("inbox");
  const [filter, setFilter] = useState<InboxFilter>("all");
  const [search, setSearch] = useState("");
  const [items, setItems] = useState<ProNotificationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [acting, setActing] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);
  const navigate = useNavigate();

  // Compose state
  const [recipients, setRecipients] = useState<Recipient[]>([]);
  const [recipientId, setRecipientId] = useState<number | "">("");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [kind, setKind] = useState<string>("INFO");
  const [attachment, setAttachment] = useState<File | null>(null);
  const [parentId, setParentId] = useState<number | null>(null);
  const [parentPreview, setParentPreview] = useState<ProNotificationItem | null>(null);
  const [sending, setSending] = useState(false);
  const [sentOk, setSentOk] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadInbox = async () => {
    setLoading(true);
    try { setItems((await listNotifications()) as ProNotificationItem[]); }
    catch { setItems([]); }
    finally { setLoading(false); }
  };

  useEffect(() => {
    loadInbox();
    listRecipients().then(setRecipients).catch(() => setRecipients([]));
  }, []);

  const inboxItems = useMemo(() => items.filter(i => !i.is_archived), [items]);
  const archivedItems = useMemo(() => items.filter(i => i.is_archived), [items]);

  const filtered = useMemo(() => {
    let list = tab === "archived" ? archivedItems : inboxItems;
    if (filter === "unread") list = list.filter(n => !n.is_read);
    if (filter === "starred") list = list.filter(n => n.is_starred);
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      list = list.filter(n =>
        n.title.toLowerCase().includes(q) ||
        n.body.toLowerCase().includes(q) ||
        (n.sender_name || "").toLowerCase().includes(q)
      );
    }
    return list;
  }, [inboxItems, archivedItems, tab, filter, search]);

  const unreadTotal = inboxItems.filter(n => !n.is_read).length;

  const handleMarkRead = async (id: number) => {
    setActing("mark-" + id);
    try { await markRead(id); setItems(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n)); }
    finally { setActing(null); }
  };

  const handleMarkAll = async () => {
    setActing("mark-all");
    try { await markAllRead(); setItems(prev => prev.map(n => ({ ...n, is_read: true }))); }
    finally { setActing(null); }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this message?")) return;
    setActing("del-" + id);
    try { await deleteNotification(id); setItems(prev => prev.filter(n => n.id !== id)); }
    finally { setActing(null); }
  };

  const handleArchive = async (n: ProNotificationItem) => {
    setActing("arc-" + n.id);
    try {
      const updated = n.is_archived
        ? await unarchiveNotification(n.id)
        : await archiveNotification(n.id);
      setItems(prev => prev.map(x => x.id === n.id ? { ...x, ...updated } : x));
    } finally { setActing(null); }
  };

  const handleStar = async (n: ProNotificationItem) => {
    setActing("star-" + n.id);
    try {
      const updated = n.is_starred
        ? await unstarNotification(n.id)
        : await starNotification(n.id);
      setItems(prev => prev.map(x => x.id === n.id ? { ...x, ...updated } : x));
    } finally { setActing(null); }
  };

  const handleOpen = async (n: ProNotificationItem) => {
    if (!n.is_read) {
      try { await markRead(n.id); } catch {}
      setItems(prev => prev.map(x => x.id === n.id ? { ...x, is_read: true } : x));
    }
    if (n.url) navigate(n.url);
  };

  const handleReply = (n: ProNotificationItem) => {
    // find sender's user id
    const replyToId = n.sender;
    if (!replyToId) {
      alert("Cannot reply — sender is the system.");
      return;
    }
    setRecipientId(replyToId);
    setTitle(n.title.startsWith("Re:") ? n.title : "Re: " + n.title);
    setBody("");
    setParentId(n.id);
    setParentPreview(n);
    setKind("INFO");
    setAttachment(null);
    setTab("compose");
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!recipientId || !title.trim() || !body.trim()) return;
    setSending(true);
    setSentOk(false);
    try {
      await sendMessageWithAttachment({
        recipient_id: Number(recipientId),
        title: title.trim(),
        body: body.trim(),
        kind,
        parent_id: parentId,
        attachment,
      });
      setSentOk(true);
      setTitle(""); setBody(""); setKind("INFO"); setRecipientId("");
      setAttachment(null); setParentId(null); setParentPreview(null);
      setTimeout(() => setSentOk(false), 3000);
      loadInbox();
    } catch (e: any) {
      alert("Failed to send: " + (e?.response?.data?.detail || e.message || "unknown error"));
    } finally { setSending(false); }
  };

  return (
    <div style={{ padding: "2rem", maxWidth: "1200px", margin: "0 auto", fontFamily: "system-ui, sans-serif", minHeight: "100vh", background: "#f8fafc" }}>
      <div style={{ marginBottom: "1.5rem" }}>
        <h1 style={{ fontSize: "1.8rem", fontWeight: 900, color: "#0f172a", margin: 0 }}>Messages & Notifications</h1>
        <p style={{ color: "#64748b", margin: "6px 0 0 0", fontSize: "0.95rem" }}>Manage your inbox, reply, archive, and message colleagues.</p>
      </div>

      <div style={{ display: "flex", gap: "4px", marginBottom: "1.5rem", borderBottom: "2px solid #e2e8f0", flexWrap: "wrap" }}>
        {([
          { key: "inbox", label: "Inbox", icon: Inbox, badge: unreadTotal },
          { key: "archived", label: "Archived", icon: Archive, badge: archivedItems.length },
          { key: "compose", label: "Compose", icon: Send, badge: 0 },
        ] as const).map(t => (
          <button key={t.key} onClick={() => setTab(t.key as Tab)} style={{ padding: "12px 20px", background: "transparent", border: "none", borderBottom: tab === t.key ? "3px solid #0284c7" : "3px solid transparent", color: tab === t.key ? "#0284c7" : "#64748b", fontWeight: 800, fontSize: "0.95rem", cursor: "pointer", display: "flex", alignItems: "center", gap: "8px" }}>
            <t.icon size={18} /> {t.label}
            {t.badge > 0 && <span style={{ background: t.key === "archived" ? "#64748b" : "#dc2626", color: "#fff", fontSize: "0.7rem", fontWeight: 900, padding: "2px 8px", borderRadius: "999px" }}>{t.badge}</span>}
          </button>
        ))}
      </div>

      {(tab === "inbox" || tab === "archived") && (
        <>
          <div style={{ display: "flex", gap: "12px", marginBottom: "1.5rem", flexWrap: "wrap", alignItems: "center" }}>
            <div style={{ flex: 1, minWidth: "240px", display: "flex", alignItems: "center", gap: "8px", background: "#fff", border: "2px solid #e2e8f0", borderRadius: "10px", padding: "10px 14px" }}>
              <Search size={16} color="#64748b" />
              <input type="text" value={search} onChange={e => setSearch(e.target.value)} placeholder="Search messages..." style={{ flex: 1, border: "none", outline: "none", fontSize: "0.9rem", background: "transparent" }} />
            </div>
            <div style={{ display: "flex", gap: "4px", background: "#f1f5f9", padding: "4px", borderRadius: "10px" }}>
              {(["all", "unread", "starred"] as InboxFilter[]).map(f => (
                <button key={f} onClick={() => setFilter(f)} style={{ padding: "8px 16px", background: filter === f ? "#fff" : "transparent", border: "none", borderRadius: "8px", fontWeight: 800, fontSize: "0.8rem", color: filter === f ? "#0284c7" : "#64748b", cursor: "pointer", boxShadow: filter === f ? "0 2px 4px rgba(0,0,0,0.06)" : "none", textTransform: "capitalize" }}>{f}</button>
              ))}
            </div>
            {tab === "inbox" && (
              <button onClick={handleMarkAll} disabled={unreadTotal === 0 || acting === "mark-all"} style={{ display: "flex", alignItems: "center", gap: "6px", padding: "10px 16px", background: unreadTotal > 0 ? "#0284c7" : "#e2e8f0", color: unreadTotal > 0 ? "#fff" : "#94a3b8", border: "none", borderRadius: "10px", fontWeight: 800, fontSize: "0.8rem", cursor: unreadTotal > 0 ? "pointer" : "not-allowed" }}>
                <CheckCheck size={16} /> Mark all read
              </button>
            )}
          </div>

          {loading && <div style={{ textAlign: "center", padding: "3rem", color: "#64748b" }}>Loading messages...</div>}

          {!loading && filtered.length === 0 && (
            <div style={{ textAlign: "center", padding: "4rem 2rem", background: "#fff", border: "2px dashed #cbd5e1", borderRadius: "14px", color: "#64748b" }}>
              <Mail size={40} style={{ marginBottom: "12px", color: "#94a3b8" }} />
              <div style={{ fontSize: "1rem", fontWeight: 700 }}>
                {search ? "No messages match your search" : filter === "unread" ? "No unread messages" : filter === "starred" ? "No starred messages" : tab === "archived" ? "No archived messages" : "Your inbox is empty"}
              </div>
            </div>
          )}

          {!loading && filtered.length > 0 && (
            <div style={{ display: "grid", gap: "10px" }}>
              {filtered.map(n => {
                const color = KIND_COLORS[n.kind] || "#64748b";
                const isExpanded = expanded === n.id;
                return (
                  <div key={n.id} className="msg-row" style={{ background: n.is_read ? "#fff" : "#f0f9ff", border: n.is_read ? "1px solid #e2e8f0" : "2px solid #38bdf8", borderLeft: "5px solid " + color, borderRadius: "10px", padding: "14px 16px", display: "flex", gap: "12px", alignItems: "flex-start", transition: "all 0.2s ease" }}>
                    <div style={{ paddingTop: "2px" }}><Bell size={18} color={color} /></div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px", flexWrap: "wrap" }}>
                        {n.is_starred && <Star size={14} fill="#f59e0b" color="#f59e0b" />}
                        <span style={{ fontWeight: 800, fontSize: "0.92rem", color: "#0f172a" }}>{n.title}</span>
                        <span style={{ fontSize: "0.65rem", fontWeight: 800, textTransform: "uppercase", padding: "2px 6px", borderRadius: "4px", background: color + "22", color }}>{KIND_LABELS[n.kind] || n.kind}</span>
                        {!n.is_read && <span style={{ fontSize: "0.65rem", fontWeight: 800, padding: "2px 6px", borderRadius: "4px", background: "#dc2626", color: "#fff" }}>NEW</span>}
                        {n.attachment && <span title={n.attachment_name} style={{ fontSize: "0.7rem", display: "flex", alignItems: "center", gap: "4px", padding: "2px 6px", background: "#f1f5f9", borderRadius: "4px", color: "#475569" }}><Paperclip size={11} /> {n.attachment_name}</span>}
                        {n.replies_count > 0 && <span style={{ fontSize: "0.7rem", color: "#7c3aed", fontWeight: 700 }}>{n.replies_count} {n.replies_count === 1 ? "reply" : "replies"}</span>}
                      </div>
                      <div style={{ fontSize: "0.85rem", color: "#475569", marginBottom: "4px" }}>
                        <strong>From:</strong> {n.sender_name || "System"}
                        {n.sender_username && <span style={{ color: "#94a3b8" }}> ({n.sender_username})</span>}
                      </div>
                      <div style={{ fontSize: "0.85rem", color: "#334155", marginBottom: "4px", overflow: "hidden", textOverflow: "ellipsis", display: "-webkit-box", WebkitLineClamp: isExpanded ? 9999 : 2, WebkitBoxOrient: "vertical", whiteSpace: "pre-wrap" }}>{n.body}</div>
                      {n.body.length > 160 && (
                        <button onClick={() => setExpanded(isExpanded ? null : n.id)} style={{ background: "transparent", border: "none", padding: 0, color: "#0284c7", fontSize: "0.75rem", fontWeight: 800, cursor: "pointer", display: "inline-flex", alignItems: "center", gap: "2px" }}>
                          {isExpanded ? <><ChevronUp size={12} /> Show less</> : <><ChevronDown size={12} /> Show more</>}
                        </button>
                      )}
                      {n.attachment_url && (
                        <div style={{ marginTop: "6px" }}>
                          <a href={n.attachment_url} download={n.attachment_name} style={{ display: "inline-flex", alignItems: "center", gap: "6px", padding: "6px 10px", background: "#f1f5f9", border: "1px solid #e2e8f0", borderRadius: "6px", color: "#0284c7", fontSize: "0.75rem", fontWeight: 700, textDecoration: "none" }}>
                            <Paperclip size={12} /> {n.attachment_name || "Download attachment"}
                          </a>
                        </div>
                      )}
                      <div style={{ fontSize: "0.72rem", color: "#94a3b8", marginTop: "4px" }}>{new Date(n.created_at).toLocaleString()}</div>
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", gap: "6px", flexShrink: 0 }}>
                      <button onClick={() => handleStar(n)} disabled={acting === "star-" + n.id} title={n.is_starred ? "Unstar" : "Star"} style={{ padding: "6px", background: n.is_starred ? "#fef3c7" : "#fff", color: n.is_starred ? "#d97706" : "#64748b", border: "1px solid " + (n.is_starred ? "#fcd34d" : "#e2e8f0"), borderRadius: "6px", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>
                        <Star size={13} fill={n.is_starred ? "#d97706" : "none"} />
                      </button>
                      {n.url && <button onClick={() => handleOpen(n)} style={{ padding: "6px 10px", background: "#0284c7", color: "#fff", border: "none", borderRadius: "6px", fontWeight: 800, fontSize: "0.72rem", cursor: "pointer" }}>Open</button>}
                      {n.sender && <button onClick={() => handleReply(n)} title="Reply" style={{ padding: "6px 10px", background: "#fff", color: "#7c3aed", border: "1px solid #ddd6fe", borderRadius: "6px", fontWeight: 800, fontSize: "0.72rem", cursor: "pointer", display: "flex", alignItems: "center", gap: "4px" }}><Reply size={13} /> Reply</button>}
                      {!n.is_read && <button onClick={() => handleMarkRead(n.id)} disabled={acting === "mark-" + n.id} style={{ padding: "6px 10px", background: "#fff", color: "#0284c7", border: "1px solid #0284c7", borderRadius: "6px", fontWeight: 800, fontSize: "0.72rem", cursor: "pointer", display: "flex", alignItems: "center", gap: "4px" }}><Check size={13} /> Read</button>}
                      <button onClick={() => handleArchive(n)} disabled={acting === "arc-" + n.id} title={n.is_archived ? "Unarchive" : "Archive"} style={{ padding: "6px 10px", background: "#fff", color: "#64748b", border: "1px solid #e2e8f0", borderRadius: "6px", fontWeight: 800, fontSize: "0.72rem", cursor: "pointer", display: "flex", alignItems: "center", gap: "4px" }}>
                        {n.is_archived ? <><ArchiveRestore size={13} /> Unarchive</> : <><Archive size={13} /> Archive</>}
                      </button>
                      <button onClick={() => handleDelete(n.id)} disabled={acting === "del-" + n.id} title="Delete" style={{ padding: "6px 10px", background: "#fff", color: "#dc2626", border: "1px solid #fecaca", borderRadius: "6px", fontWeight: 800, fontSize: "0.72rem", cursor: "pointer", display: "flex", alignItems: "center", gap: "4px" }}><Trash2 size={13} /></button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}

      {tab === "compose" && (
        <form onSubmit={handleSend} style={{ background: "#fff", border: "2px solid #e2e8f0", borderRadius: "14px", padding: "2rem", maxWidth: "800px" }}>
          <h2 style={{ margin: "0 0 1.5rem 0", fontSize: "1.2rem", fontWeight: 900, color: "#0f172a", display: "flex", alignItems: "center", gap: "8px" }}>
            <Send size={20} color="#0284c7" /> {parentPreview ? "Reply to message" : "New Message"}
          </h2>

          {parentPreview && (
            <div style={{ marginBottom: "1rem", padding: "12px 14px", background: "#f8fafc", borderLeft: "4px solid #7c3aed", borderRadius: "6px", fontSize: "0.8rem", color: "#475569" }}>
              <div style={{ fontWeight: 800, marginBottom: "4px" }}>Replying to: {parentPreview.title}</div>
              <div style={{ fontStyle: "italic" }}>{parentPreview.body.slice(0, 200)}{parentPreview.body.length > 200 ? "…" : ""}</div>
              <button type="button" onClick={() => { setParentId(null); setParentPreview(null); setTitle(title.replace(/^Re:\s*/, "")); }} style={{ marginTop: "8px", padding: "4px 10px", background: "#fff", border: "1px solid #cbd5e1", borderRadius: "4px", fontSize: "0.72rem", fontWeight: 700, cursor: "pointer", color: "#64748b" }}>
                <X size={11} style={{ marginRight: "4px" }} /> Cancel reply
              </button>
            </div>
          )}

          <div style={{ display: "grid", gap: "16px" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 800, color: "#475569", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "6px" }}>To</label>
              <select value={recipientId} onChange={e => setRecipientId(e.target.value ? Number(e.target.value) : "")} required style={{ width: "100%", padding: "12px 14px", border: "2px solid #e2e8f0", borderRadius: "10px", fontSize: "0.9rem", outline: "none", background: "#fff", fontWeight: 600 }}>
                <option value="">— Select a recipient —</option>
                {recipients.map(r => <option key={r.id} value={r.id}>{r.name} ({r.username})</option>)}
              </select>
            </div>
            <div>
              <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 800, color: "#475569", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "6px" }}>Category</label>
              <select value={kind} onChange={e => setKind(e.target.value)} style={{ width: "100%", padding: "12px 14px", border: "2px solid #e2e8f0", borderRadius: "10px", fontSize: "0.9rem", outline: "none", background: "#fff", fontWeight: 600 }}>
                <option value="INFO">Info</option><option value="ALERT">Alert</option><option value="REQUEST">Request</option>
              </select>
            </div>
            <div>
              <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 800, color: "#475569", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "6px" }}>Subject</label>
              <input type="text" value={title} onChange={e => setTitle(e.target.value)} required maxLength={200} placeholder="Brief summary of your message" style={{ width: "100%", padding: "12px 14px", border: "2px solid #e2e8f0", borderRadius: "10px", fontSize: "0.9rem", outline: "none", boxSizing: "border-box" }} />
            </div>
            <div>
              <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 800, color: "#475569", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "6px" }}>Message</label>
              <textarea value={body} onChange={e => setBody(e.target.value)} required rows={6} placeholder="Type your message here..." style={{ width: "100%", padding: "12px 14px", border: "2px solid #e2e8f0", borderRadius: "10px", fontSize: "0.9rem", outline: "none", boxSizing: "border-box", resize: "vertical", fontFamily: "inherit" }} />
            </div>
            <div>
              <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 800, color: "#475569", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "6px" }}>Attachment (max 10 MB)</label>
              <input ref={fileInputRef} type="file" onChange={e => setAttachment(e.target.files?.[0] || null)} style={{ display: "none" }} />
              {!attachment ? (
                <button type="button" onClick={() => fileInputRef.current?.click()} style={{ display: "flex", alignItems: "center", gap: "8px", padding: "10px 16px", background: "#f8fafc", border: "2px dashed #cbd5e1", borderRadius: "10px", fontSize: "0.85rem", fontWeight: 700, color: "#64748b", cursor: "pointer" }}>
                  <Paperclip size={16} /> Click to attach a file
                </button>
              ) : (
                <div style={{ display: "flex", alignItems: "center", gap: "10px", padding: "10px 14px", background: "#f0f9ff", border: "2px solid #bae6fd", borderRadius: "10px" }}>
                  <Paperclip size={16} color="#0284c7" />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: "0.85rem", fontWeight: 800, color: "#0f172a" }}>{attachment.name}</div>
                    <div style={{ fontSize: "0.75rem", color: "#64748b" }}>{formatSize(attachment.size)}</div>
                  </div>
                  <button type="button" onClick={() => setAttachment(null)} style={{ padding: "4px", background: "transparent", border: "none", cursor: "pointer", color: "#dc2626" }}><X size={16} /></button>
                </div>
              )}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "12px", marginTop: "8px" }}>
              <button type="submit" disabled={sending || !recipientId || !title.trim() || !body.trim()} style={{ display: "flex", alignItems: "center", gap: "8px", padding: "12px 24px", background: sending ? "#94a3b8" : "linear-gradient(135deg, #0284c7, #0369a1)", color: "#fff", border: "none", borderRadius: "10px", fontWeight: 900, fontSize: "0.95rem", cursor: sending ? "not-allowed" : "pointer", boxShadow: "0 8px 20px rgba(2,132,199,0.3)" }}>
                <Send size={18} /> {sending ? "Sending..." : parentId ? "Send Reply" : "Send Message"}
              </button>
              {sentOk && <span style={{ color: "#16a34a", fontWeight: 800, fontSize: "0.85rem", display: "flex", alignItems: "center", gap: "6px" }}><Check size={16} /> Sent successfully</span>}
            </div>
          </div>
        </form>
      )}

      <style>{`.msg-row:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(0,0,0,0.08); }`}</style>
    </div>
  );
}
