import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft, Filter, Pencil, RefreshCw, Shield, Snowflake, Trash2, UserCheck, UserX, X, Save,
} from "lucide-react";
import {
  deleteTeacher, listTeachers, teacherAction, updateTeacher, type TeacherRow,
} from "../../services/teachersAdmin";
import { useToast } from "../../components/Toast";

const BROWN = "#2b1a0f", BROWN2 = "#5a3a1e", SKY = "#22b4f0", CREAM = "#f5eee2";
const GREEN = "#10b981", RED = "#ef4444", AMBER = "#f59e0b", BLUE = "#3b82f6";

const cardStyle: React.CSSProperties = {
  background: "#fff", border: "1px solid #e5e7eb", borderRadius: "14px",
  padding: "1rem 1.15rem", boxShadow: "0 4px 14px rgba(10,18,29,0.05)",
};

type Filter = "ALL" | "ACTIVE" | "FROZEN" | "DEACTIVATED";

export default function TeachersAdminPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const [rows, setRows] = useState<TeacherRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState<Filter>("ALL");

  const [editId, setEditId] = useState<string | null>(null);
  const [draft, setDraft] = useState<Partial<TeacherRow>>({});

  async function load() {
    setLoading(true); setError(null);
    try {
      const res = await listTeachers(q || undefined);
      setRows(res.results);
    } catch (e) {
      const status = (e as { response?: { status?: number } })?.response?.status;
      if (status === 403 || status === 401) setError("Administrator access required.");
      else setError(e instanceof Error ? e.message : String(e));
    } finally { setLoading(false); }
  }

  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);
  useEffect(() => { const t = setTimeout(load, 250); return () => clearTimeout(t); /* eslint-disable-next-line */ }, [q]);

  const counts = useMemo(() => ({
    total: rows.length,
    active: rows.filter((r) => r.is_active).length,
    frozen: rows.filter((r) => r.is_frozen).length,
    inactive: rows.filter((r) => !r.is_active).length,
  }), [rows]);

  const filtered = useMemo(() => {
    switch (filter) {
      case "ACTIVE":      return rows.filter((r) => r.is_active && !r.is_frozen);
      case "FROZEN":      return rows.filter((r) => r.is_frozen);
      case "DEACTIVATED": return rows.filter((r) => !r.is_active);
      default:            return rows;
    }
  }, [rows, filter]);

  async function runAction(id: string, action: "freeze" | "unfreeze" | "activate" | "deactivate") {
    try {
      const updated = await teacherAction(id, action);
      setRows((prev) => prev.map((r) => r.id === id ? updated : r));
      toast.push({ type: "success", title: `${action} OK`, message: `${updated.full_name} — action applied.` });
    } catch (e) {
      toast.push({ type: "error", title: "Action failed", message: e instanceof Error ? e.message : String(e) });
    }
  }

  async function removeTeacher(id: string, name: string) {
    if (!confirm(`Delete ${name}? This is only permitted if the teacher has no lesson requirements or timetable entries.`)) return;
    try {
      await deleteTeacher(id);
      setRows((prev) => prev.filter((r) => r.id !== id));
      toast.push({ type: "success", title: "Deleted", message: name });
    } catch (e: any) {
      toast.push({
        type: "error", title: "Delete blocked",
        message: e?.response?.data?.detail || (e instanceof Error ? e.message : String(e)),
        mitigation: "Freeze or deactivate instead, or reassign the teacher's lesson requirements first.",
      });
    }
  }

  async function saveEdit() {
    if (!editId) return;
    try {
      const updated = await updateTeacher(editId, draft);
      setRows((prev) => prev.map((r) => r.id === editId ? updated : r));
      setEditId(null); setDraft({});
      toast.push({ type: "success", title: "Saved" });
    } catch (e) {
      toast.push({ type: "error", title: "Save failed", message: e instanceof Error ? e.message : String(e) });
    }
  }

  return (
    <div style={{ padding: "2rem", maxWidth: "1500px", margin: "0 auto" }}>
      <button type="button" onClick={() => navigate(-1)} style={{
        display: "inline-flex", alignItems: "center", gap: "6px",
        background: "transparent", border: "none", color: BROWN2,
        fontWeight: 600, cursor: "pointer", marginBottom: "1rem",
      }}><ArrowLeft size={16} /> Back</button>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "1rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <div style={{
            width: "52px", height: "52px", borderRadius: "14px",
            background: `linear-gradient(135deg, ${SKY}, #0b5d8c)`,
            color: "#fff", display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 6px 18px rgba(34,180,240,0.35)",
          }}><UserCheck size={26} /></div>
          <div>
            <h1 style={{ margin: 0, fontSize: "1.7rem", color: "#1e2e40", fontWeight: 800 }}>
              Teachers
            </h1>
            <p style={{ margin: "2px 0 0", color: "#748095", fontSize: "0.9rem" }}>
              Activate · deactivate · freeze · unfreeze · delete
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

      {error && <div style={{ padding: "0.8rem 1rem", borderRadius: "10px", background: "#fee2e2", color: "#991b1b", marginBottom: "1rem", display: "flex", gap: "8px", alignItems: "center" }}>
        <Shield size={16} /> {error}
      </div>}

      <div style={{ ...cardStyle, display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap", marginBottom: "1rem" }}>
        <input placeholder="Search code / name…" value={q} onChange={(e) => setQ(e.target.value)}
          style={{ flex: "1 1 260px", padding: "0.55rem 0.9rem", border: "1px solid #cbd5e1", borderRadius: "10px", fontSize: "0.9rem" }} />
        <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
          {([
            ["ALL", "All", counts.total, BROWN2],
            ["ACTIVE", "Active", counts.active, GREEN],
            ["FROZEN", "Frozen", counts.frozen, BLUE],
            ["DEACTIVATED", "Deactivated", counts.inactive, RED],
          ] as const).map(([k, label, n, color]) => {
            const on = filter === k;
            return (
              <button key={k} type="button" onClick={() => setFilter(k as Filter)}
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
      </div>

      <div style={{ ...cardStyle, padding: 0, overflow: "hidden" }}>
        {loading ? (
          <div style={{ padding: "3rem", textAlign: "center", color: "#94a3b8" }}>Loading…</div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: "3rem", textAlign: "center", color: "#94a3b8" }}>No teachers match.</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
              <thead>
                <tr style={{ background: `linear-gradient(135deg, ${BROWN}, ${BROWN2})`, color: CREAM }}>
                  <th style={{ textAlign: "left", padding: "0.7rem 1rem", width: "90px" }}>Code</th>
                  <th style={{ textAlign: "left", padding: "0.7rem 1rem", width: "70px" }}>No.</th>
                  <th style={{ textAlign: "left", padding: "0.7rem 1rem" }}>Name</th>
                  <th style={{ textAlign: "left", padding: "0.7rem 1rem" }}>Assignments</th>
                  <th style={{ textAlign: "center", padding: "0.7rem 1rem", width: "100px" }}>Status</th>
                  <th style={{ textAlign: "right", padding: "0.7rem 1rem", width: "280px" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((r) => {
                  const isEdit = editId === r.id;
                  let statusLabel = "Active";
                  let statusColor = GREEN;
                  if (!r.is_active) { statusLabel = "Deactivated"; statusColor = RED; }
                  else if (r.is_frozen) { statusLabel = "Frozen"; statusColor = BLUE; }
                  return (
                    <tr key={r.id} style={{ borderTop: "1px solid #f1f5f9" }}>
                      <td style={{ padding: "0.6rem 1rem", fontWeight: 700, color: BROWN2 }}>{r.employee_code}</td>
                      <td style={{ padding: "0.6rem 1rem", color: "#94a3b8" }}>{r.teacher_number ?? "—"}</td>
                      {isEdit ? (
                        <>
                          <td style={{ padding: "0.6rem 1rem" }}>
                            <input value={draft.first_name ?? r.first_name}
                              onChange={(e) => setDraft({ ...draft, first_name: e.target.value })}
                              style={{ width: "100%", padding: "4px 6px", border: "1px solid #cbd5e1", borderRadius: "6px", marginBottom: "2px" }} />
                            <input value={draft.last_name ?? r.last_name}
                              onChange={(e) => setDraft({ ...draft, last_name: e.target.value })}
                              style={{ width: "100%", padding: "4px 6px", border: "1px solid #cbd5e1", borderRadius: "6px" }} />
                          </td>
                          <td style={{ padding: "0.6rem 1rem", color: "#94a3b8", fontSize: "0.75rem" }}>
                            {r.assignments.length} subject/class pair(s)
                          </td>
                          <td style={{ padding: "0.6rem 1rem", textAlign: "center" }}>
                            <span style={{ padding: "2px 9px", borderRadius: "999px", background: `${statusColor}20`, color: statusColor, fontSize: "0.72rem", fontWeight: 800 }}>
                              {statusLabel}
                            </span>
                          </td>
                          <td style={{ padding: "0.6rem 1rem", textAlign: "right", whiteSpace: "nowrap" }}>
                            <button type="button" onClick={saveEdit}
                              style={{ background: SKY, color: "#fff", border: "none", padding: "5px 10px", borderRadius: "6px", fontWeight: 700, cursor: "pointer", fontSize: "0.78rem", marginRight: "4px", display: "inline-flex", alignItems: "center", gap: "4px" }}>
                              <Save size={12} /> Save
                            </button>
                            <button type="button" onClick={() => { setEditId(null); setDraft({}); }}
                              style={{ background: "#e5e7eb", color: "#374151", border: "none", padding: "5px 10px", borderRadius: "6px", fontWeight: 700, cursor: "pointer", fontSize: "0.78rem" }}>
                              <X size={12} />
                            </button>
                          </td>
                        </>
                      ) : (
                        <>
                          <td style={{ padding: "0.6rem 1rem" }}>
                            <div style={{ fontWeight: 600 }}>{r.full_name}</div>
                            <div style={{ fontSize: "0.72rem", color: "#94a3b8" }}>{r.username}{r.email ? ` · ${r.email}` : ""}</div>
                          </td>
                          <td style={{ padding: "0.6rem 1rem", fontSize: "0.78rem", color: "#475569" }}>
                            {r.assignments.length === 0 ? <span style={{ color: "#cbd5e1" }}>— none —</span> :
                              r.assignments.slice(0, 4).map((a, i) => (
                                <div key={i} style={{ whiteSpace: "nowrap" }}>{a}</div>
                              ))}
                            {r.assignments.length > 4 && (
                              <div style={{ color: "#94a3b8", fontSize: "0.72rem" }}>+{r.assignments.length - 4} more</div>
                            )}
                          </td>
                          <td style={{ padding: "0.6rem 1rem", textAlign: "center" }}>
                            <span style={{ padding: "2px 9px", borderRadius: "999px", background: `${statusColor}20`, color: statusColor, fontSize: "0.72rem", fontWeight: 800 }}>
                              {statusLabel}
                            </span>
                          </td>
                          <td style={{ padding: "0.6rem 1rem", textAlign: "right", whiteSpace: "nowrap" }}>
                            <button type="button" onClick={() => { setEditId(r.id); setDraft({}); }}
                              title="Edit"
                              style={{ background: "transparent", border: "1px solid #94a3b8", color: "#475569", padding: "5px 8px", borderRadius: "6px", cursor: "pointer", fontSize: "0.75rem", marginRight: "4px" }}>
                              <Pencil size={12} />
                            </button>
                            {r.is_active ? (
                              <button type="button" onClick={() => runAction(r.id, "deactivate")}
                                title="Deactivate"
                                style={{ background: "transparent", border: `1px solid ${RED}`, color: RED, padding: "5px 8px", borderRadius: "6px", cursor: "pointer", fontSize: "0.75rem", marginRight: "4px" }}>
                                <UserX size={12} />
                              </button>
                            ) : (
                              <button type="button" onClick={() => runAction(r.id, "activate")}
                                title="Activate"
                                style={{ background: "transparent", border: `1px solid ${GREEN}`, color: GREEN, padding: "5px 8px", borderRadius: "6px", cursor: "pointer", fontSize: "0.75rem", marginRight: "4px" }}>
                                <UserCheck size={12} />
                              </button>
                            )}
                            {r.is_frozen ? (
                              <button type="button" onClick={() => runAction(r.id, "unfreeze")}
                                title="Unfreeze"
                                style={{ background: "transparent", border: `1px solid ${AMBER}`, color: AMBER, padding: "5px 8px", borderRadius: "6px", cursor: "pointer", fontSize: "0.75rem", marginRight: "4px" }}>
                                <Snowflake size={12} />
                              </button>
                            ) : (
                              <button type="button" onClick={() => runAction(r.id, "freeze")}
                                title="Freeze"
                                style={{ background: "transparent", border: `1px solid ${BLUE}`, color: BLUE, padding: "5px 8px", borderRadius: "6px", cursor: "pointer", fontSize: "0.75rem", marginRight: "4px" }}>
                                <Snowflake size={12} />
                              </button>
                            )}
                            <button type="button" onClick={() => removeTeacher(r.id, r.full_name)}
                              title="Delete"
                              style={{ background: "transparent", border: `1px solid ${RED}`, color: RED, padding: "5px 8px", borderRadius: "6px", cursor: "pointer", fontSize: "0.75rem" }}>
                              <Trash2 size={12} />
                            </button>
                          </td>
                        </>
                      )}
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