import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertCircle, AlertTriangle, ArrowLeft, Info, RefreshCw, Shield } from "lucide-react";
import { listErrorLogs, type ErrorLog } from "../../services/errors";

const BROWN = "#2b1a0f", BROWN2 = "#5a3a1e", SKY = "#22b4f0", CREAM = "#f5eee2";
const RED = "#ef4444", AMBER = "#f59e0b", GREEN = "#10b981";

const cardStyle: React.CSSProperties = {
  background: "#fff", border: "1px solid #e5e7eb", borderRadius: "14px",
  padding: "1rem 1.15rem", boxShadow: "0 4px 14px rgba(10,18,29,0.05)",
};

function fmt(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
}

export default function ErrorLogsPage() {
  const navigate = useNavigate();
  const [logs, setLogs] = useState<ErrorLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"ALL" | "ERROR" | "WARNING" | "INFO">("ALL");

  async function load() {
    setLoading(true); setError(null);
    try {
      const res = await listErrorLogs();
      setLogs(res.results);
    } catch (e) {
      const status = (e as { response?: { status?: number } })?.response?.status;
      if (status === 403 || status === 401) setError("Administrator access required.");
      else setError(e instanceof Error ? e.message : String(e));
    } finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => {
    if (filter === "ALL") return logs;
    return logs.filter((l) => l.severity === filter);
  }, [logs, filter]);

  const counts = useMemo(() => {
    const m = { ERROR: 0, WARNING: 0, INFO: 0 };
    for (const l of logs) m[l.severity]++;
    return m;
  }, [logs]);

  return (
    <div style={{ padding: "2rem", maxWidth: "1300px", margin: "0 auto" }}>
      <button type="button" onClick={() => navigate(-1)} style={{
        display: "inline-flex", alignItems: "center", gap: "6px",
        background: "transparent", border: "none", color: BROWN2,
        fontWeight: 600, cursor: "pointer", marginBottom: "1rem",
      }}><ArrowLeft size={16} /> Back</button>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "1rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <div style={{
            width: "52px", height: "52px", borderRadius: "14px",
            background: `linear-gradient(135deg, ${RED}, #7f1d1d)`,
            color: "#fff", display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 6px 18px rgba(239,68,68,0.35)",
          }}><AlertCircle size={26} /></div>
          <div>
            <h1 style={{ margin: 0, fontSize: "1.7rem", color: "#1e2e40", fontWeight: 800 }}>
              Error & Warning Logs
            </h1>
            <p style={{ margin: "2px 0 0", color: "#748095", fontSize: "0.9rem" }}>
              Reported by the frontend and scheduler engine
            </p>
          </div>
        </div>
        <button type="button" onClick={load} disabled={loading} style={{
          display: "inline-flex", alignItems: "center", gap: "6px",
          background: SKY, color: "#fff", border: "none",
          padding: "0.55rem 1rem", borderRadius: "10px",
          cursor: loading ? "not-allowed" : "pointer",
          fontWeight: 700, fontSize: "0.85rem",
        }}>
          <RefreshCw size={15} /> Refresh
        </button>
      </div>

      {error && (
        <div style={{ padding: "0.8rem 1rem", borderRadius: "10px", background: "#fee2e2", color: "#991b1b", marginBottom: "1rem", display: "flex", gap: "8px", alignItems: "center" }}>
          <Shield size={16} /> {error}
        </div>
      )}

      <div style={{ display: "flex", gap: "10px", marginBottom: "1rem", flexWrap: "wrap" }}>
        {([
          ["ALL", "All", logs.length, BROWN2],
          ["ERROR", "Errors", counts.ERROR, RED],
          ["WARNING", "Warnings", counts.WARNING, AMBER],
          ["INFO", "Info", counts.INFO, "#1e40af"],
        ] as const).map(([k, label, n, color]) => {
          const on = filter === k;
          return (
            <button key={k} type="button" onClick={() => setFilter(k as any)}
              style={{
                padding: "5px 14px", borderRadius: "999px",
                border: `1px solid ${on ? color : "#e5e7eb"}`,
                background: on ? `${color}18` : "#fff",
                color: on ? color : "#64748b",
                fontSize: "0.82rem", fontWeight: 700, cursor: "pointer",
              }}>
              {label} · {n}
            </button>
          );
        })}
      </div>

      <div style={{ ...cardStyle, padding: 0, overflow: "hidden" }}>
        {loading ? (
          <div style={{ padding: "3rem", textAlign: "center", color: "#94a3b8" }}>Loading…</div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: "3rem", textAlign: "center", color: "#94a3b8" }}>
            No logs match this filter.
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
              <thead>
                <tr style={{ background: `linear-gradient(135deg, ${BROWN}, ${BROWN2})`, color: CREAM }}>
                  <th style={{ textAlign: "left", padding: "0.7rem 1rem", width: "160px" }}>When</th>
                  <th style={{ textAlign: "left", padding: "0.7rem 1rem", width: "100px" }}>Severity</th>
                  <th style={{ textAlign: "left", padding: "0.7rem 1rem", width: "120px" }}>Source</th>
                  <th style={{ textAlign: "left", padding: "0.7rem 1rem", width: "140px" }}>Code</th>
                  <th style={{ textAlign: "left", padding: "0.7rem 1rem" }}>Message</th>
                  <th style={{ textAlign: "left", padding: "0.7rem 1rem", width: "140px" }}>User</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((l) => {
                  const color = l.severity === "ERROR" ? RED : l.severity === "WARNING" ? AMBER : "#1e40af";
                  const Icon = l.severity === "ERROR" ? AlertCircle : l.severity === "WARNING" ? AlertTriangle : Info;
                  return (
                    <tr key={l.id} style={{ borderTop: "1px solid #f1f5f9" }}>
                      <td style={{ padding: "0.6rem 1rem", color: "#748095", fontSize: "0.78rem" }}>{fmt(l.created_at)}</td>
                      <td style={{ padding: "0.6rem 1rem" }}>
                        <span style={{
                          display: "inline-flex", alignItems: "center", gap: "4px",
                          padding: "2px 9px", borderRadius: "999px",
                          background: `${color}20`, color,
                          fontSize: "0.72rem", fontWeight: 800,
                        }}>
                          <Icon size={11} /> {l.severity}
                        </span>
                      </td>
                      <td style={{ padding: "0.6rem 1rem", color: BROWN2, fontWeight: 600 }}>{l.source}</td>
                      <td style={{ padding: "0.6rem 1rem", fontFamily: "monospace", fontSize: "0.78rem", color: "#64748b" }}>{l.code || "—"}</td>
                      <td style={{ padding: "0.6rem 1rem" }}>{l.message}</td>
                      <td style={{ padding: "0.6rem 1rem", color: "#475569" }}>{l.user ?? "—"}</td>
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