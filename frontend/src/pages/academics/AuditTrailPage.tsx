import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Filter, RefreshCw, ScrollText, X } from "lucide-react";
import { listAuditLogs, type AuditLog as AuditEvent } from "../../services/auditLogs";

const BROWN = "#2b1a0f", BROWN2 = "#5a3a1e", SKY = "#22b4f0", CREAM = "#f5eee2";

const ACTION_COLOR: Record<string, { bg: string; fg: string }> = {
  CREATE:      { bg: "#dcfce7", fg: "#166534" },
  UPDATE:      { bg: "#e0f2fe", fg: "#075985" },
  DELETE:      { bg: "#fee2e2", fg: "#991b1b" },
  PUBLISH:     { bg: "#dcfce7", fg: "#166534" },
  UNPUBLISH:   { bg: "#fef3c7", fg: "#92400e" },
  ARCHIVE:     { bg: "#e0e7ff", fg: "#3730a3" },
  BULK_UPDATE: { bg: "#f0f9ff", fg: "#0c4a6e" },
  STATUS_CHANGE: { bg: "#f3e8ff", fg: "#6b21a8" },
};

function relTime(iso: string): string {
  const d = new Date(iso);
  const diff = Date.now() - d.getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const days = Math.floor(h / 24);
  if (days < 30) return `${days}d ago`;
  return d.toLocaleDateString();
}

export default function AuditTrailPage() {
  const navigate = useNavigate();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [entityType, setEntityType] = useState("");
  const [actionFilter, setActionFilter] = useState("");
  const [q, setQ] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");

  async function load() {
    setLoading(true); setError(null);
    try {
      const data = await listAuditLogs({
        entity_type: entityType || undefined,
        action: actionFilter || undefined,
        q: q || undefined,
        from: fromDate || undefined,
        to: toDate || undefined,
        page_size: 500,
      });
      setEvents(Array.isArray(data.results) ? data.results : []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load audit trail");
    } finally { setLoading(false); }
  }

  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const entityTypes = useMemo(() => {
    const s = new Set(events.map((e) => e.entity_type));
    return Array.from(s).sort();
  }, [events]);

  const actions = useMemo(() => {
    const s = new Set(events.map((e) => e.action));
    return Array.from(s).sort();
  }, [events]);

  return (
    <div style={{ padding: "2rem", maxWidth: "1400px", margin: "0 auto" }}>
      <button type="button" onClick={() => navigate(-1)} style={{
        display: "inline-flex", alignItems: "center", gap: "6px",
        background: "transparent", border: "none", color: BROWN2,
        fontWeight: 600, cursor: "pointer", marginBottom: "1rem",
      }}><ArrowLeft size={16} /> Back</button>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "1rem", marginBottom: "1.5rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <div style={{
            width: "52px", height: "52px", borderRadius: "14px",
            background: `linear-gradient(135deg, ${SKY}, #0b5d8c)`,
            color: "#fff", display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 6px 18px rgba(34,180,240,0.35)",
          }}><ScrollText size={26} /></div>
          <div>
            <h1 style={{ margin: 0, fontSize: "1.7rem", color: "#1e2e40", fontWeight: 800 }}>
              Audit Trail
            </h1>
            <p style={{ margin: "2px 0 0", color: "#748095", fontSize: "0.9rem" }}>
              Every significant academic-data change — who, when, what.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={load}
          disabled={loading}
          style={{
            display: "inline-flex", alignItems: "center", gap: "6px",
            background: SKY, color: "#fff", border: "none",
            padding: "0.55rem 1rem", borderRadius: "10px",
            cursor: loading ? "not-allowed" : "pointer",
            fontWeight: 700, fontSize: "0.85rem",
          }}
        >
          <RefreshCw size={15} /> Refresh
        </button>
      </div>

      {/* Filters */}
      <div style={{
        background: "#fff", border: "1px solid #e5e7eb", borderRadius: "14px",
        padding: "1rem 1.25rem", marginBottom: "1.25rem",
        boxShadow: "0 4px 14px rgba(10,18,29,0.05)",
        display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr 1fr auto", gap: "10px", alignItems: "end",
      }}>
        <div>
          <label style={{ fontSize: "0.72rem", fontWeight: 700, color: "#748095", letterSpacing: "0.06em" }}>ENTITY</label>
          <select value={entityType} onChange={(e) => setEntityType(e.target.value)}
            style={{ width: "100%", padding: "5px 8px", border: "1px solid #cbd5e1", borderRadius: "6px", background: "#fff" }}>
            <option value="">All</option>
            {entityTypes.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
        <div>
          <label style={{ fontSize: "0.72rem", fontWeight: 700, color: "#748095", letterSpacing: "0.06em" }}>ACTION</label>
          <select value={actionFilter} onChange={(e) => setActionFilter(e.target.value)}
            style={{ width: "100%", padding: "5px 8px", border: "1px solid #cbd5e1", borderRadius: "6px", background: "#fff" }}>
            <option value="">All</option>
            {actions.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
        <div>
          <label style={{ fontSize: "0.72rem", fontWeight: 700, color: "#748095", letterSpacing: "0.06em" }}>FROM</label>
          <input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)}
            style={{ width: "100%", padding: "5px 8px", border: "1px solid #cbd5e1", borderRadius: "6px" }} />
        </div>
        <div>
          <label style={{ fontSize: "0.72rem", fontWeight: 700, color: "#748095", letterSpacing: "0.06em" }}>TO</label>
          <input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)}
            style={{ width: "100%", padding: "5px 8px", border: "1px solid #cbd5e1", borderRadius: "6px" }} />
        </div>
        <div>
          <label style={{ fontSize: "0.72rem", fontWeight: 700, color: "#748095", letterSpacing: "0.06em" }}>SEARCH</label>
          <input value={q} onChange={(e) => setQ(e.target.value)}
            placeholder="label substring"
            style={{ width: "100%", padding: "5px 8px", border: "1px solid #cbd5e1", borderRadius: "6px" }} />
        </div>
        <button type="button" onClick={load}
          style={{
            display: "inline-flex", alignItems: "center", gap: "5px",
            background: BROWN2, color: "#fff", border: "none",
            padding: "7px 14px", borderRadius: "8px", cursor: "pointer",
            fontWeight: 700, fontSize: "0.82rem",
          }}
        ><Filter size={14} /> Apply</button>
      </div>

      {error && (
        <div style={{ padding: "0.8rem 1rem", borderRadius: "10px", background: "#fee2e2", color: "#991b1b", marginBottom: "1rem" }}>
          {error}
        </div>
      )}

      <div style={{
        background: "#fff", borderRadius: "12px", overflow: "hidden",
        border: "1px solid #e5e7eb", boxShadow: "0 4px 14px rgba(10,18,29,0.06)",
      }}>
        {loading ? (
          <div style={{ padding: "3rem", textAlign: "center", color: "#94a3b8" }}>Loading…</div>
        ) : events.length === 0 ? (
          <div style={{ padding: "3rem", textAlign: "center", color: "#94a3b8" }}>
            No audit events yet. Enter or change marks to generate some.
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.86rem" }}>
              <thead>
                <tr style={{ background: `linear-gradient(135deg, ${BROWN}, ${BROWN2})`, color: CREAM }}>
                  <th style={{ textAlign: "left", padding: "0.7rem 1rem", width: "130px" }}>When</th>
                  <th style={{ textAlign: "left", padding: "0.7rem 1rem", width: "130px" }}>Action</th>
                  <th style={{ textAlign: "left", padding: "0.7rem 1rem", width: "110px" }}>Entity</th>
                  <th style={{ textAlign: "left", padding: "0.7rem 1rem" }}>Label</th>
                  <th style={{ textAlign: "left", padding: "0.7rem 1rem", width: "140px" }}>Actor</th>
                  <th style={{ textAlign: "left", padding: "0.7rem 1rem", width: "130px" }}>IP</th>
                </tr>
              </thead>
              <tbody>
                {events.map((ev) => {
                  const c = ACTION_COLOR[ev.action] ?? { bg: "#f1f5f9", fg: "#64748b" };
                  return (
                    <tr key={ev.id} style={{ borderTop: "1px solid #f1f5f9" }}>
                      <td style={{ padding: "0.6rem 1rem", color: "#748095", fontSize: "0.8rem" }}
                          title={new Date(ev.created_at).toLocaleString()}>
                        {relTime(ev.created_at)}
                      </td>
                      <td style={{ padding: "0.6rem 1rem" }}>
                        <span style={{
                          padding: "2px 8px", borderRadius: "999px",
                          fontSize: "0.72rem", fontWeight: 700,
                          background: c.bg, color: c.fg,
                        }}>{ev.action}</span>
                      </td>
                      <td style={{ padding: "0.6rem 1rem", color: BROWN2, fontWeight: 600 }}>{ev.entity_type}</td>
                      <td style={{ padding: "0.6rem 1rem" }}>
                        <div>{ev.entity_label}</div>
                        {ev.meta_json && Object.keys(ev.meta_json).length > 0 && (
                          <div style={{ fontSize: "0.72rem", color: "#94a3b8", marginTop: "2px" }}>
                            {Object.entries(ev.meta_json).map(([k, v]) => `${k}: ${v}`).join(" · ")}
                          </div>
                        )}
                      </td>
                      <td style={{ padding: "0.6rem 1rem", color: "#475569" }}>
                        {ev.actor_display ?? ev.actor_username ?? <span style={{ color: "#cbd5e1" }}>system</span>}
                      </td>
                      <td style={{ padding: "0.6rem 1rem", color: "#94a3b8", fontFamily: "monospace", fontSize: "0.78rem" }}>
                        {ev.ip_address ?? "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}