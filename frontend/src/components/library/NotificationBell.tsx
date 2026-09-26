import { useEffect, useState } from "react";
import { Bell, X, CheckCircle2 } from "lucide-react";
import * as lib from "../../services/library";

export default function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<{ unread: number; notifications: lib.NotificationRow[] } | null>(null);

  async function load() {
    try { setData(await lib.notificationsMe()); } catch { setData({ unread: 0, notifications: [] }); }
  }
  useEffect(() => {
    void load();
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, []);

  async function markRead(id: string) {
    try { await lib.markNotificationRead(id); await load(); } catch {}
  }

  return (
    <div style={{ position: "relative", display: "inline-block" }}>
      <button type="button" onClick={() => setOpen((v) => !v)}
              style={{ background: "rgba(255,255,255,0.95)", border: "1px solid #e5e7eb",
                       borderRadius: 8, padding: "0.4rem 0.6rem", cursor: "pointer",
                       display: "inline-flex", alignItems: "center", gap: "0.35rem",
                       fontWeight: 700, color: "#1e3a8a" }}>
        <Bell size={16} />
        <span style={{ fontSize: "0.75rem" }}>Inbox</span>
        {data && data.unread > 0 ? (
          <span style={{ background: "#b91c1c", color: "#fff", borderRadius: 10,
                         fontSize: "0.65rem", padding: "0 0.35rem", fontWeight: 800 }}>
            {data.unread}
          </span>
        ) : null}
      </button>
      {open ? (
        <div style={{ position: "absolute", right: 0, top: "calc(100% + 6px)",
                      background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10,
                      boxShadow: "0 8px 24px rgba(15,23,42,0.15)", zIndex: 9999,
                      minWidth: 360, maxHeight: 480, overflowY: "auto" }}>
          <div style={{ padding: "0.6rem 0.85rem", borderBottom: "1px solid #f1f5f9",
                        display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <strong style={{ fontSize: "0.85rem" }}>Notifications</strong>
            <button type="button" onClick={() => setOpen(false)}
                    style={{ background: "transparent", border: "none", cursor: "pointer", color: "#64748b" }}>
              <X size={14} />
            </button>
          </div>
          {!data || data.notifications.length === 0 ? (
            <div style={{ padding: "1rem", fontSize: "0.82rem", color: "#64748b", textAlign: "center" }}>
              No notifications.
            </div>
          ) : (
            data.notifications.map((n) => (
              <div key={n.id} style={{ padding: "0.6rem 0.85rem", borderBottom: "1px solid #f1f5f9",
                                        fontSize: "0.82rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: "0.5rem" }}>
                  <strong style={{ color: n.status === "READ" ? "#64748b" : "#111827" }}>{n.subject}</strong>
                  {n.status !== "READ" ? (
                    <button type="button" onClick={() => markRead(n.id)}
                            title="Mark read"
                            style={{ background: "transparent", border: "none",
                                     cursor: "pointer", color: "#166534" }}>
                      <CheckCircle2 size={13} />
                    </button>
                  ) : null}
                </div>
                <div style={{ color: "#64748b", marginTop: "0.25rem", whiteSpace: "pre-wrap" }}>{n.body}</div>
                <div style={{ color: "#94a3b8", fontSize: "0.7rem", marginTop: "0.3rem" }}>
                  {new Date(n.created_at).toLocaleString()}
                </div>
              </div>
            ))
          )}
        </div>
      ) : null}
    </div>
  );
}
