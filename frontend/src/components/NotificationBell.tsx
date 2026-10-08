import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Bell, Check, CheckCheck, Inbox, X } from "lucide-react";
import {
  type NotificationItem,
  type ApprovalItem,
  listNotifications,
  listApprovals,
  unreadCount,
  pendingCount,
  markRead,
  markAllRead,
  approveRequest,
  rejectRequest,
} from "../services/notifications";

const POLL_MS = 20000; // 20 seconds

type Tab = "notifications" | "approvals";

export default function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<Tab>("notifications");
  const [unread, setUnread] = useState(0);
  const [pending, setPending] = useState(0);
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [approvals, setApprovals] = useState<ApprovalItem[]>([]);
  const [loading, setLoading] = useState(false);
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const navigate = useNavigate();

  // Poll for counts
  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const [u, p] = await Promise.all([unreadCount(), pendingCount()]);
        if (alive) { setUnread(u); setPending(p); }
      } catch { /* silent */ }
    };
    void tick();
    const id = window.setInterval(tick, POLL_MS);
    return () => { alive = false; window.clearInterval(id); };
  }, []);

  // When opened, load data
  useEffect(() => {
    if (!open) return;
    setLoading(true);
    Promise.all([listNotifications(), listApprovals()])
      .then(([n, a]) => { setItems(n); setApprovals(a); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [open]);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const handleItemClick = useCallback(async (n: NotificationItem) => {
    if (!n.is_read) {
      try { await markRead(n.id); } catch { /* silent */ }
      setItems((prev) => prev.map((x) => x.id === n.id ? { ...x, is_read: true } : x));
      setUnread((c) => Math.max(0, c - 1));
    }
    if (n.url) {
      setOpen(false);
      navigate(n.url);
    }
  }, [navigate]);

  const handleMarkAll = useCallback(async () => {
    try {
      await markAllRead();
      setItems((prev) => prev.map((x) => ({ ...x, is_read: true })));
      setUnread(0);
    } catch { /* silent */ }
  }, []);

  const handleApprove = useCallback(async (a: ApprovalItem, ok: boolean) => {
    try {
      if (ok) await approveRequest(a.id);
      else await rejectRequest(a.id);
      setApprovals((prev) => prev.map((x) =>
        x.id === a.id ? { ...x, status: ok ? "APPROVED" : "REJECTED" } : x
      ));
      setPending((c) => Math.max(0, c - 1));
    } catch { /* silent */ }
  }, []);

  const totalBadge = unread + pending;

  return (
    <div className="notif-bell" ref={wrapRef}>
      <button
        type="button"
        className="notif-bell-btn"
        onClick={() => setOpen((v) => !v)}
        title="Notifications"
        aria-label="Notifications"
      >
        <Bell size={18} />
        {totalBadge > 0 && (
          <span className="notif-badge">{totalBadge > 99 ? "99+" : totalBadge}</span>
        )}
      </button>

      {open && (
        <div className="notif-panel" role="dialog" aria-label="Notifications panel">
          <div className="notif-head">
            <div className="notif-tabs">
              <button
                className={"notif-tab" + (tab === "notifications" ? " active" : "")}
                onClick={() => setTab("notifications")}
              >
                <Inbox size={14} /> Inbox
                {unread > 0 && <span className="notif-pill">{unread}</span>}
              </button>
              <button
                className={"notif-tab" + (tab === "approvals" ? " active" : "")}
                onClick={() => setTab("approvals")}
              >
                <Check size={14} /> Approvals
                {pending > 0 && <span className="notif-pill warn">{pending}</span>}
              </button>
            </div>
            <button
              className="notif-close"
              onClick={() => setOpen(false)}
              title="Close"
              aria-label="Close"
            >
              <X size={16} />
            </button>
          </div>

          <div className="notif-body">
            {loading && <div className="notif-empty">Loading…</div>}

            {!loading && tab === "notifications" && (
              <>
                {items.length === 0 ? (
                  <div className="notif-empty">No notifications yet.</div>
                ) : (
                  <>
                    <div className="notif-actions">
                      <button className="notif-link" onClick={handleMarkAll}>
                        <CheckCheck size={14} /> Mark all read
                      </button>
                    </div>
                    <ul className="notif-list">
                      {items.map((n) => (
                        <li
                          key={n.id}
                          className={"notif-item" + (n.is_read ? "" : " unread")}
                          onClick={() => handleItemClick(n)}
                        >
                          <div className="notif-kind">{n.kind}</div>
                          <div className="notif-title">{n.title}</div>
                          {n.body && <div className="notif-text">{n.body}</div>}
                          <div className="notif-time">
                            {new Date(n.created_at).toLocaleString()}
                          </div>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </>
            )}

            {!loading && tab === "approvals" && (
              <>
                {approvals.length === 0 ? (
                  <div className="notif-empty">No approvals.</div>
                ) : (
                  <ul className="notif-list">
                    {approvals.map((a) => (
                      <li key={a.id} className="notif-item">
                        <div className={"notif-status " + a.status.toLowerCase()}>
                          {a.status}
                        </div>
                        <div className="notif-title">{a.title}</div>
                        {a.body && <div className="notif-text">{a.body}</div>}
                        <div className="notif-meta">
                          From <b>{a.requested_by_name}</b> · {new Date(a.created_at).toLocaleString()}
                        </div>
                        {a.status === "PENDING" && (
                          <div className="notif-ap-buttons">
                            <button
                              className="notif-btn-approve"
                              onClick={() => handleApprove(a, true)}
                            >
                              <Check size={13} /> Approve
                            </button>
                            <button
                              className="notif-btn-reject"
                              onClick={() => handleApprove(a, false)}
                            >
                              <X size={13} /> Reject
                            </button>
                          </div>
                        )}
                        {a.decision_note && (
                          <div className="notif-note">Note: {a.decision_note}</div>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
