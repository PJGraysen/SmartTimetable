import { useEffect, useState } from "react";
import { Activity, Radio, Users } from "lucide-react";
import http from "../../services/http";
import { useLiveActivity } from "../../hooks/useLiveActivity";

type ActiveUser = {
  user: number;
  username: string;
  first_name: string;
  last_name: string;
  last_seen: string;
  last_path: string;
  user_agent: string;
  ip_address: string | null;
};

type AuditLog = {
  id: string;
  created_at: string;
  user_username: string | null;
  user_name: string | null;
  action: string;
  entity_type: string;
  entity_id: string;
  description: string;
  ip_address: string | null;
};

const ACTION_COLORS: Record<string, { bg: string; fg: string }> = {
  CREATE:  { bg: "#dcfce7", fg: "#166534" },
  UPDATE:  { bg: "#e0f2fe", fg: "#075985" },
  DELETE:  { bg: "#fee2e2", fg: "#991b1b" },
  PUBLISH: { bg: "#dcfce7", fg: "#166534" },
  ERROR:   { bg: "#fef3c7", fg: "#92400e" },
};

function relTime(iso: string): string {
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 5) return "just now";
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return new Date(iso).toLocaleDateString();
}

export default function LiveActivityPage() {
  const [users, setUsers] = useState<ActiveUser[]>([]);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  const { status: wsStatus, last: wsEvent } = useLiveActivity(true);

  // Apply incoming WebSocket events to local state without a refetch
  useEffect(() => {
    if (!wsEvent) return;
    if (wsEvent.type === "heartbeat") {
      const incoming: ActiveUser = {
        user: wsEvent.user_id,
        username: wsEvent.username,
        first_name: wsEvent.first_name,
        last_name: wsEvent.last_name,
        last_seen: wsEvent.last_seen,
        last_path: wsEvent.last_path,
        user_agent: "",
        ip_address: wsEvent.ip_address,
      };
      setUsers((prev) => {
        const next = prev.filter((u) => u.user !== incoming.user);
        next.unshift(incoming);
        return next;
      });
    } else if (wsEvent.type === "audit") {
      const incoming: AuditLog = {
        id: wsEvent.id,
        created_at: wsEvent.created_at,
        user_username: wsEvent.user_username,
        user_name: wsEvent.user_name,
        action: wsEvent.action,
        entity_type: wsEvent.entity_type,
        entity_id: wsEvent.entity_id,
        description: wsEvent.description,
        ip_address: wsEvent.ip_address,
      };
      setLogs((prev) => {
        if (prev.some((r) => r.id === incoming.id)) return prev;
        return [incoming, ...prev].slice(0, 100);
      });
    }
  }, [wsEvent]);

  async function load() {
    try {
      const [a, b] = await Promise.all([
        http.get("/audit/active-users/", { params: { window: 120 } }),
        http.get("/audit/logs/", { params: { page_size: 50 } }),
      ]);
      setUsers(a.data.users || []);
      // /audit/logs/ may be array or paginated ? normalise
      const raw = b.data;
      setLogs(Array.isArray(raw) ? raw : (raw.results || []));
      setErr("");
    } catch (e: any) {
      setErr(e?.response?.data?.detail || "Failed to load live data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // WebSocket delivers new activity instantly. This slower poll only
    // ensures active-users list eventually drops idle users.
    const id = window.setInterval(load, 30000);
    return () => window.clearInterval(id);
  }, []);

  return (
    <div style={{ padding: "2rem", maxWidth: "1400px", margin: "0 auto" }}>
      <header style={{ marginBottom: "1.5rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{
            width: 52, height: 52, borderRadius: 14,
            background: "linear-gradient(135deg, #22b4f0, #0b5d8c)",
            display: "grid", placeItems: "center", color: "#fff",
          }}>
            <Radio size={26} />
          </div>
          <div>
            <h1 style={{ margin: 0, fontSize: "1.7rem", color: "#1e2e40", fontWeight: 800 }}>
              Live Activity
            </h1>
            <div style={{ fontSize: "0.85rem", color: "#64748b", display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{
                width: 8, height: 8, borderRadius: "50%",
                background:
                  wsStatus === "open" ? "#22c55e"
                  : wsStatus === "connecting" ? "#f59e0b" : "#ef4444",
                display: "inline-block",
              }} />
              {wsStatus === "open" ? "Live (real-time)"
                : wsStatus === "connecting" ? "Connecting?"
                : "Reconnecting?"}
            </div>
          </div>
        </div>
      </header>

      {loading && <div style={{ color: "#64748b" }}>Loading?</div>}
      {err && <div style={{ color: "#991b1b" }}>{err}</div>}

      {/* Active users */}
      <section style={{
        background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12,
        padding: "1rem 1.25rem", marginBottom: "1.25rem",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
          <Users size={16} color="#0ea5e9" />
          <h2 style={{ margin: 0, fontSize: "0.95rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "#334155", fontWeight: 800 }}>
            Active now ({users.length})
          </h2>
        </div>
        {users.length === 0 ? (
          <div style={{ padding: "1.5rem", color: "#94a3b8", textAlign: "center", fontSize: "0.85rem" }}>
            No users active in the last 2 minutes.
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 10 }}>
            {users.map((u) => (
              <div key={u.user} style={{
                border: "1px solid #e2e8f0", borderRadius: 10, padding: "10px 12px",
                background: "#f8fafc",
              }}>
                <div style={{ fontWeight: 800, color: "#0f172a" }}>
                  {u.first_name || u.last_name
                    ? `${u.first_name} ${u.last_name}`.trim()
                    : u.username}
                </div>
                <div style={{ fontSize: "0.75rem", color: "#64748b", marginTop: 2 }}>
                  @{u.username} ? {u.ip_address || "?"}
                </div>
                <div style={{ fontSize: "0.72rem", color: "#94a3b8", marginTop: 4, fontFamily: "monospace", wordBreak: "break-all" }}>
                  {u.last_path || "/"}
                </div>
                <div style={{ fontSize: "0.7rem", color: "#16a34a", marginTop: 6, fontWeight: 700 }}>
                  ? {relTime(u.last_seen)}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Live log */}
      <section style={{
        background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12,
        padding: "1rem 1.25rem",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
          <Activity size={16} color="#0ea5e9" />
          <h2 style={{ margin: 0, fontSize: "0.95rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "#334155", fontWeight: 800 }}>
            Activity stream
          </h2>
        </div>
        {logs.length === 0 ? (
          <div style={{ padding: "1.5rem", color: "#94a3b8", textAlign: "center", fontSize: "0.85rem" }}>
            No activity yet.
          </div>
        ) : (
          <div style={{ display: "grid", gap: 6 }}>
            {logs.map((r) => {
              const c = ACTION_COLORS[r.action] || { bg: "#f1f5f9", fg: "#334155" };
              return (
                <div key={r.id} style={{
                  display: "grid", gridTemplateColumns: "70px 1fr auto",
                  gap: 10, alignItems: "center", padding: "8px 4px",
                  borderTop: "1px solid #f1f5f9", fontSize: "0.85rem",
                }}>
                  <span style={{
                    background: c.bg, color: c.fg,
                    padding: "2px 8px", borderRadius: 999,
                    fontSize: "0.68rem", fontWeight: 800, textAlign: "center",
                  }}>{r.action}</span>
                  <div>
                    <div style={{ color: "#0f172a" }}>
                      <b>{r.user_name || r.user_username || "?"}</b>{" "}
                      <span style={{ color: "#64748b" }}>{r.description}</span>
                    </div>
                    <div style={{ fontSize: "0.72rem", color: "#94a3b8" }}>
                      {r.entity_type} ? {r.entity_id} ? {r.ip_address || "?"}
                    </div>
                  </div>
                  <span style={{ fontSize: "0.72rem", color: "#64748b", whiteSpace: "nowrap" }}>
                    {relTime(r.created_at)}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
