import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft, RefreshCw, Snowflake, Trash2, UserCheck, UserX, X, Plus, Save,
} from "lucide-react";
import {
  deleteTeacher, listTeachers, teacherAction,
  getTeacherAssignments, assignTeacher, unassignTeacher, createTeacher,
  listSubjects, listClasses, listDepartments, updateTeacherProfile, bulkAssignTeacher,
  ROLE_OPTIONS,
  type TeacherRow, type Assignment,
} from "../../services/teachersAdmin";
import { useToast } from "../../components/Toast";

const BROWN = "#2b1a0f", BROWN2 = "#5a3a1e", SKY = "#22b4f0";
const GREEN = "#10b981", RED = "#ef4444", AMBER = "#f59e0b", BLUE = "#3b82f6";
const BORDER = "#e5e7eb", MUTED = "#64748b";
const CAP = 46;

const cardStyle: React.CSSProperties = {
  background: "#fff", border: "1px solid #e5e7eb", borderRadius: "14px",
  padding: "1rem 1.15rem", boxShadow: "0 4px 14px rgba(10,18,29,0.05)",
};
const inputStyle: React.CSSProperties = {
  padding: "0.5rem 0.7rem", borderRadius: 6, border: `1px solid ${BORDER}`,
  fontSize: "0.88rem", width: "100%", background: "#fff",
};
const btnPrimary: React.CSSProperties = {
  padding: "0.5rem 1rem", borderRadius: 6, border: "none",
  background: BROWN, color: "#fff", cursor: "pointer",
  fontSize: "0.85rem", fontWeight: 600,
};
const btnSecondary: React.CSSProperties = {
  padding: "0.4rem 0.8rem", borderRadius: 6,
  border: `1px solid ${BORDER}`, background: "#fff",
  cursor: "pointer", fontSize: "0.82rem",
};
const smallBtn: React.CSSProperties = {
  padding: "0.28rem 0.55rem", borderRadius: 6,
  border: `1px solid ${BORDER}`, background: "#fff",
  cursor: "pointer", fontSize: "0.75rem", fontWeight: 600,
};
const lbl: React.CSSProperties = {
  display: "block", fontSize: "0.75rem", color: MUTED, marginBottom: 3, fontWeight: 600,
};

type Filter = "ALL" | "ACTIVE" | "FROZEN" | "DEACTIVATED" | "OVERLOADED";

export default function TeachersAdminPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const [rows, setRows] = useState<TeacherRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState<Filter>("ALL");

  const [drawerId, setDrawerId] = useState<string | null>(null);
  const [showNew, setShowNew] = useState(false);

  async function load() {
    setLoading(true); setError(null);
    try {
      const res = await listTeachers(q || undefined);
      setRows(res.results);
    } catch (e: any) {
      const status = e?.response?.status;
      if (status === 403 || status === 401) setError("Administrator access required.");
      else setError(e instanceof Error ? e.message : String(e));
    } finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);
  useEffect(() => { const t = setTimeout(load, 250); return () => clearTimeout(t); }, [q]);

  const counts = useMemo(() => ({
    total: rows.length,
    active: rows.filter(r => r.is_active && !r.is_frozen).length,
    frozen: rows.filter(r => r.is_frozen).length,
    inactive: rows.filter(r => !r.is_active).length,
    over: rows.filter(r => (r.lr_count || 0) > CAP).length,
  }), [rows]);

  const filtered = useMemo(() => {
    switch (filter) {
      case "ACTIVE":      return rows.filter(r => r.is_active && !r.is_frozen);
      case "FROZEN":      return rows.filter(r => r.is_frozen);
      case "DEACTIVATED": return rows.filter(r => !r.is_active);
      case "OVERLOADED":  return rows.filter(r => (r.lr_count || 0) > CAP);
      default:            return rows;
    }
  }, [rows, filter]);

  async function runAction(id: string, action: "freeze" | "unfreeze" | "activate" | "deactivate") {
    try {
      const updated = await teacherAction(id, action);
      setRows(prev => prev.map(r => r.id === id ? updated : r));
      toast.push({ type: "success", title: `${action} OK`, message: updated.full_name });
    } catch (e) {
      toast.push({ type: "error", title: "Action failed", message: e instanceof Error ? e.message : String(e) });
    }
  }

  async function removeTeacher(id: string, name: string) {
    if (!confirm(
      `Delete ${name}?\n\n` +
      `This will remove all of their lesson assignments.\n` +
      `Timetable history will be preserved.`
    )) return;
    try {
      const res = await deleteTeacher(id);
      setRows(prev => prev.filter(r => r.id !== id));
      const deleted = (res as any)?.deleted_assignments ?? 0;
      toast.push({
        type: "success",
        title: "Deleted",
        message: deleted ? `${name} and ${deleted} assignment(s) removed` : name,
      });
    } catch (e: any) {
      const status = e?.response?.status;
      const detail = e?.response?.data?.detail || String(e);
      const suggestion = e?.response?.data?.suggestion;
      if (status === 409 && suggestion === "deactivate") {
        // Offer to deactivate instead
        const doDeactivate = confirm(
          detail + "\n\nDeactivate this teacher instead? " +
          "(History preserved, teacher hidden from future generation)"
        );
        if (doDeactivate) {
          try {
            const updated = await teacherAction(id, "deactivate");
            setRows(prev => prev.map(r => r.id === id ? updated : r));
            toast.push({ type: "success", title: "Deactivated", message: name });
            return;
          } catch (e2: any) {
            toast.push({ type: "error", title: "Deactivate failed", message: e2?.response?.data?.detail || String(e2) });
            return;
          }
        }
      } else {
        toast.push({ type: "error", title: "Delete failed", message: detail });
      }
    }
  }

  function exportCSV() {
    const headers = ["Code", "Number", "Name", "Email", "Role", "Department", "Active", "Frozen", "Lessons"];
    const rowsCsv = filtered.map(r => [
      r.employee_code, r.teacher_number ?? "", r.full_name, r.email || "",
      (r as any).role || "", (r as any).department_name || "",
      r.is_active ? "yes" : "no", r.is_frozen ? "yes" : "no", r.lr_count || 0,
    ]);
    const csv = [headers.join(","), ...rowsCsv.map(r => r.map(x => {
      const s = String(x ?? "");
      return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    }).join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "teachers.csv";
    a.click();
    URL.revokeObjectURL(a.href);
  }

  return (
    <div style={{ padding: "1.5rem", maxWidth: 1500, margin: "0 auto" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
        <button onClick={() => navigate("/admin")} style={btnSecondary}>
          <ArrowLeft size={14} /> Back
        </button>
        <h1 style={{ margin: 0, fontSize: "1.4rem", color: BROWN, fontWeight: 700 }}>Teachers</h1>
        <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
          <button style={btnPrimary} onClick={() => setShowNew(true)}>
            <Plus size={14} /> New Teacher
          </button>
          <button style={btnSecondary} onClick={exportCSV}>CSV</button>
          <button style={btnSecondary} onClick={load}>
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 10, marginBottom: 16 }}>
        {[
          { label: "TOTAL",       value: counts.total,    filter: "ALL" as Filter },
          { label: "ACTIVE",      value: counts.active,   filter: "ACTIVE" as Filter },
          { label: "FROZEN",      value: counts.frozen,   filter: "FROZEN" as Filter },
          { label: "DEACTIVATED", value: counts.inactive, filter: "DEACTIVATED" as Filter },
          { label: "OVER 46",     value: counts.over,     filter: "OVERLOADED" as Filter },
        ].map(s => (
          <div key={s.label} style={{
            ...cardStyle, cursor: "pointer",
            borderColor: filter === s.filter ? BROWN : BORDER,
            borderWidth: filter === s.filter ? 2 : 1,
          }} onClick={() => setFilter(s.filter)}>
            <div style={{ fontSize: "0.72rem", color: MUTED, letterSpacing: 0.5 }}>{s.label}</div>
            <div style={{ fontSize: "1.5rem", fontWeight: 700, color: BROWN, marginTop: 4 }}>{s.value}</div>
          </div>
        ))}
      </div>

      <div style={{ marginBottom: 12 }}>
        <input
          style={{ ...inputStyle, maxWidth: 340 }}
          placeholder="Search by code, first name, last name..."
          value={q}
          onChange={e => setQ(e.target.value)}
        />
      </div>

      {error && (
        <div style={{ padding: 12, background: "#fef2f2", color: "#b91c1c", borderRadius: 8, marginBottom: 12 }}>
          {error}
        </div>
      )}

      {loading ? <div>Loading...</div> : (
        <div style={{ ...cardStyle, padding: 0, overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
            <thead>
              <tr style={{ background: "#f8fafc", textAlign: "left" }}>
                <th style={th}>Code</th>
                <th style={th}>#</th>
                <th style={th}>Name</th>
                <th style={th}>Role</th>
                <th style={th}>Department</th>
                <th style={th}>Load</th>
                <th style={th}>State</th>
                <th style={th}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 && (
                <tr><td colSpan={8} style={{ padding: "1rem", textAlign: "center", color: MUTED }}>No teachers match.</td></tr>
              )}
              {filtered.map(r => {
                const load = r.lr_count || 0;
                const over = load > CAP;
                const roleLabel = ROLE_OPTIONS.find(o => o.value === (r as any).role)?.label
                                || (r as any).role || "Teacher";
                return (
                  <tr key={r.id} style={{ borderTop: "1px solid #f1f5f9" }}>
                    <td style={{ padding: "0.5rem 0.6rem", fontWeight: 600 }}>
                      <a href="#" onClick={e => { e.preventDefault(); setDrawerId(r.id); }}
                         style={{ color: BROWN, textDecoration: "none" }}>{r.employee_code}</a>
                    </td>
                    <td style={{ padding: "0.5rem 0.6rem", color: MUTED }}>{r.teacher_number ?? "-"}</td>
                    <td style={{ padding: "0.5rem 0.6rem" }}>{r.full_name}</td>
                    <td style={{ padding: "0.5rem 0.6rem", color: MUTED, fontSize: "0.78rem" }}>{roleLabel}</td>
                    <td style={{ padding: "0.5rem 0.6rem", color: MUTED }}>{(r as any).department_name || "-"}</td>
                    <td style={{ padding: "0.5rem 0.6rem", fontWeight: 700, color: over ? RED : BROWN }}>
                      {load}/{CAP}{over ? " !" : ""}
                    </td>
                    <td style={{ padding: "0.5rem 0.6rem" }}>
                      {!r.is_active ? <Badge text="DEACTIVATED" color={RED} /> :
                       r.is_frozen  ? <Badge text="FROZEN" color={AMBER} /> :
                                      <Badge text="ACTIVE" color={GREEN} />}
                    </td>
                    <td style={{ padding: "0.5rem 0.6rem" }}>
                      <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                        <button style={smallBtn} onClick={() => setDrawerId(r.id)}>Manage</button>
                        {r.is_active && !r.is_frozen && (
                          <button style={smallBtn} title="Freeze" onClick={() => runAction(r.id, "freeze")}>
                            <Snowflake size={11} />
                          </button>
                        )}
                        {r.is_frozen && (
                          <button style={smallBtn} title="Unfreeze" onClick={() => runAction(r.id, "unfreeze")}>
                            <UserCheck size={11} />
                          </button>
                        )}
                        {r.is_active ? (
                          <button style={smallBtn} title="Deactivate" onClick={() => runAction(r.id, "deactivate")}>
                            <UserX size={11} />
                          </button>
                        ) : (
                          <button style={smallBtn} title="Activate" onClick={() => runAction(r.id, "activate")}>
                            <UserCheck size={11} />
                          </button>
                        )}
                        <button style={{ ...smallBtn, color: RED, borderColor: RED }}
                                title="Delete" onClick={() => removeTeacher(r.id, r.full_name)}>
                          <Trash2 size={11} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <TeacherDrawer teacherId={drawerId} onClose={() => setDrawerId(null)} onChanged={load} />

      <NewTeacherModal open={showNew} onClose={() => setShowNew(false)} onDone={load} />
    </div>
  );
}

const th: React.CSSProperties = {
  padding: "0.55rem 0.6rem", color: MUTED, fontSize: "0.72rem",
  textTransform: "uppercase", letterSpacing: 0.5, fontWeight: 700,
};

function Badge({ text, color }: { text: string; color: string }) {
  return (
    <span style={{
      display: "inline-block", padding: "2px 8px", borderRadius: 999,
      background: color + "22", color, fontSize: "0.68rem", fontWeight: 700,
    }}>{text}</span>
  );
}

// ============================================================
// TEACHER DRAWER — profile edit + assignments + bulk assign
// ============================================================
function TeacherDrawer({
  teacherId, onClose, onChanged,
}: { teacherId: string | null; onClose: () => void; onChanged: () => void }) {
  const toast = useToast();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [subjects, setSubjects] = useState<any[]>([]);
  const [classes, setClasses] = useState<any[]>([]);
  const [departments, setDepartments] = useState<any[]>([]);
  const [err, setErr] = useState("");
  const [saving, setSaving] = useState(false);

  // Profile edit draft
  const [p, setP] = useState<any>({});

  // Add-assignment mode: 'single' | 'bulk' | null
  const [addMode, setAddMode] = useState<"single" | "bulk" | null>(null);
  const [newA, setNewA] = useState<any>({ subject_id: "", class_id: "", lessons_per_week: "" });
  const [bulkA, setBulkA] = useState<any>({ subject_id: "", lessons_per_week: "", class_ids: [] });

  async function loadDrawer() {
    if (!teacherId) { setData(null); return; }
    setLoading(true);
    try {
      const d = await getTeacherAssignments(teacherId);
      setData(d);
      // seed profile draft only once per teacher
      setP((prev: any) => {
        if (prev && prev.employee_code === d.employee_code) return prev;
        return {
          first_name: d.full_name.split(" ")[0] || "",
          last_name: d.full_name.split(" ").slice(1).join(" ") || "",
          employee_code: d.employee_code,
          teacher_number: d.teacher_number ?? "",
          email: (d as any).email || "",
          phone: (d as any).phone || "",
          role: (d as any).role || "TEACHER",
          department_id: (d as any).department_id ?? "",
          hire_date: (d as any).hire_date || "",
        };
      });
    } catch (e: any) {
      setErr(e?.response?.data?.detail || String(e));
    } finally { setLoading(false); }
  }

  useEffect(() => {
    loadDrawer();
    listSubjects().then(r => setSubjects(r.results || []));
    listClasses().then(r => setClasses(r.results || []));
    listDepartments().then(r => setDepartments(r.results || []));
  }, [teacherId]);

  if (teacherId == null) return null;

  const load = data?.total_lessons || 0;
  const over = load > CAP;

  async function saveProfile() {
    if (!teacherId) return;
    setErr(""); setSaving(true);
    try {
      const payload: any = {
        first_name: p.first_name,
        last_name: p.last_name,
        employee_code: p.employee_code,
        teacher_number: p.teacher_number === "" ? null : p.teacher_number,
        email: p.email,
        phone: p.phone,
        role: p.role,
        department_id: p.department_id === "" ? null : Number(p.department_id),
        hire_date: p.hire_date || null,
      };
      await updateTeacherProfile(teacherId, payload);
      toast.push({ type: "success", title: "Profile updated" });
      await loadDrawer();
      onChanged();
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      setErr(detail || String(e));
      toast.push({ type: "error", title: "Save failed", message: detail || "See drawer for details" });
    } finally { setSaving(false); }
  }

  async function saveSingle() {
    if (!teacherId) return;
    setErr("");
    if (!newA.subject_id || !newA.class_id || !newA.lessons_per_week) {
      setErr("Subject, class and lessons/week are required."); return;
    }
    try {
      await assignTeacher(teacherId, {
        subject_id: Number(newA.subject_id),
        class_id: newA.class_id,
        lessons_per_week: Number(newA.lessons_per_week),
      });
      setNewA({ subject_id: "", class_id: "", lessons_per_week: "" });
      setAddMode(null);
      await loadDrawer();
      onChanged();
      toast.push({ type: "success", title: "Assigned" });
    } catch (e: any) {
      setErr(e?.response?.data?.detail || String(e));
    }
  }

  async function saveBulk() {
    if (!teacherId) return;
    setErr("");
    if (!bulkA.subject_id || !bulkA.lessons_per_week || bulkA.class_ids.length === 0) {
      setErr("Subject, lessons/week and at least one class are required."); return;
    }
    try {
      const res = await bulkAssignTeacher(teacherId, {
        subject_id: Number(bulkA.subject_id),
        class_ids: bulkA.class_ids,
        lessons_per_week: Number(bulkA.lessons_per_week),
      });
      const created = res.results.filter(r => r.status === "created").length;
      const updated = res.results.filter(r => r.status === "updated").length;
      toast.push({
        type: "success",
        title: "Bulk assign complete",
        message: `${created} created, ${updated} updated. Load now ${res.teacher_new_load}/${res.capacity}${res.over_capacity ? " (OVER)" : ""}`,
      });
      setBulkA({ subject_id: "", lessons_per_week: "", class_ids: [] });
      setAddMode(null);
      await loadDrawer();
      onChanged();
    } catch (e: any) {
      setErr(e?.response?.data?.detail || String(e));
    }
  }

  async function removeAssignment(lrId: string) {
    if (!teacherId || !confirm("Remove this assignment?")) return;
    try {
      await unassignTeacher(teacherId, lrId);
      await loadDrawer();
      onChanged();
    } catch (e: any) {
      setErr(e?.response?.data?.detail || String(e));
    }
  }

  const drawer = (
    <div
         style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)",
                  display: "flex", justifyContent: "flex-end", zIndex: 9999 }}>
      <div onClick={e => e.stopPropagation()}
           style={{ width: 780, maxWidth: "96vw", background: "#fff", height: "100vh", overflowY: "auto" }}>
        <div style={{ padding: "1rem 1.2rem", borderBottom: `1px solid ${BORDER}`,
                      position: "sticky", top: 0, background: "#fff", zIndex: 2,
                      display: "flex", justifyContent: "space-between" }}>
          <div>
            <h3 style={{ margin: 0, color: BROWN }}>
              {data?.full_name || "Teacher"} · {data?.employee_code || ""}
            </h3>
            <div style={{ fontSize: "0.8rem", color: MUTED }}>
              Load: <b style={{ color: over ? RED : BROWN }}>{load}/{CAP}</b>
              {over && <span style={{ color: RED }}> · OVER CAPACITY</span>}
            </div>
          </div>
          <button onClick={onClose} style={btnSecondary}><X size={14} /></button>
        </div>

        <div style={{ padding: "1rem 1.2rem" }}>
          {err && <div style={{ padding: 10, background: "#fef2f2", color: "#b91c1c", borderRadius: 8, marginBottom: 10, fontSize: "0.85rem" }}>{err}</div>}
          {loading && !data ? <div>Loading...</div> : !data ? null : (
            <>
              {/* ---------- PROFILE ---------- */}
              <div style={{ marginBottom: 18 }}>
                <b style={{ color: BROWN, fontSize: "0.95rem" }}>Profile</b>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 8 }}>
                  <L label="First Name *"><input style={inputStyle} value={p.first_name || ""} onChange={e => setP({ ...p, first_name: e.target.value })} /></L>
                  <L label="Last Name"><input style={inputStyle} value={p.last_name || ""} onChange={e => setP({ ...p, last_name: e.target.value })} /></L>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
                  <L label="Employee Code *"><input style={inputStyle} value={p.employee_code || ""} onChange={e => setP({ ...p, employee_code: e.target.value })} /></L>
                  <L label="Teacher #"><input style={inputStyle} type="number" value={p.teacher_number ?? ""} onChange={e => setP({ ...p, teacher_number: e.target.value })} /></L>
                  <L label="Email"><input style={inputStyle} type="email" value={p.email || ""} onChange={e => setP({ ...p, email: e.target.value })} /></L>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
                  <L label="Phone"><input style={inputStyle} value={p.phone || ""} onChange={e => setP({ ...p, phone: e.target.value })} /></L>
                  <L label="Role">
                    <select style={inputStyle} value={p.role || "TEACHER"} onChange={e => setP({ ...p, role: e.target.value })}>
                      {ROLE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </select>
                  </L>
                  <L label="Department">
                    <select style={inputStyle} value={p.department_id ?? ""} onChange={e => setP({ ...p, department_id: e.target.value })}>
                      <option value="">- None -</option>
                      {departments.map(d => <option key={d.id} value={d.id}>{d.code} - {d.name}</option>)}
                    </select>
                  </L>
                </div>
                <L label="Hire Date"><input style={inputStyle} type="date" value={p.hire_date || ""} onChange={e => setP({ ...p, hire_date: e.target.value })} /></L>
                <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
                  <button style={btnPrimary} disabled={saving} onClick={saveProfile}>
                    <Save size={12} /> {saving ? "Saving..." : "Save Profile"}
                  </button>
                </div>
              </div>

              {/* ---------- ASSIGNMENTS ---------- */}
              <div style={{ borderTop: `1px solid ${BORDER}`, paddingTop: 14 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                  <b style={{ color: BROWN, fontSize: "0.95rem" }}>Assignments ({data.assignments.length})</b>
                  <div style={{ display: "flex", gap: 4 }}>
                    <button style={btnPrimary} onClick={() => setAddMode(addMode === "single" ? null : "single")}>
                      <Plus size={12} /> Add one
                    </button>
                    <button style={btnSecondary} onClick={() => setAddMode(addMode === "bulk" ? null : "bulk")}>
                      <Plus size={12} /> Bulk assign
                    </button>
                  </div>
                </div>

                {addMode === "single" && (
                  <div style={{ border: `1px solid ${BORDER}`, borderRadius: 8, padding: 12, marginBottom: 12, background: "#f8fafc" }}>
                    <div style={{ display: "grid", gridTemplateColumns: "2fr 2fr 1fr", gap: 8 }}>
                      <select style={inputStyle} value={newA.subject_id}
                              onChange={e => setNewA({ ...newA, subject_id: e.target.value })}>
                        <option value="">- Subject -</option>
                        {subjects.map(s => <option key={s.id} value={s.id}>{s.code} - {s.name}</option>)}
                      </select>
                      <select style={inputStyle} value={newA.class_id}
                              onChange={e => setNewA({ ...newA, class_id: e.target.value })}>
                        <option value="">- Class -</option>
                        {classes.map(c => (
                          <option key={c.id} value={c.id}>{c.name}{c.is_active ? "" : " (inactive)"}</option>
                        ))}
                      </select>
                      <input style={inputStyle} type="number" placeholder="N/wk"
                             value={newA.lessons_per_week}
                             onChange={e => setNewA({ ...newA, lessons_per_week: e.target.value })} />
                    </div>
                    <div style={{ marginTop: 8, display: "flex", gap: 6 }}>
                      <button style={btnPrimary} onClick={saveSingle}>Save</button>
                      <button style={btnSecondary} onClick={() => setAddMode(null)}>Cancel</button>
                    </div>
                  </div>
                )}

                {addMode === "bulk" && (
                  <div style={{ border: `1px solid ${BORDER}`, borderRadius: 8, padding: 12, marginBottom: 12, background: "#f8fafc" }}>
                    <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 8 }}>
                      <select style={inputStyle} value={bulkA.subject_id}
                              onChange={e => setBulkA({ ...bulkA, subject_id: e.target.value })}>
                        <option value="">- Subject -</option>
                        {subjects.map(s => <option key={s.id} value={s.id}>{s.code} - {s.name}</option>)}
                      </select>
                      <input style={inputStyle} type="number" placeholder="Lessons/week"
                             value={bulkA.lessons_per_week}
                             onChange={e => setBulkA({ ...bulkA, lessons_per_week: e.target.value })} />
                    </div>
                    <div style={{ marginTop: 8 }}>
                      <label style={lbl}>Pick classes ({bulkA.class_ids.length} selected)</label>
                      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                        {classes.map(c => {
                          const on = bulkA.class_ids.includes(c.id);
                          return (
                            <button key={c.id} type="button"
                                    onClick={() => setBulkA({
                                      ...bulkA,
                                      class_ids: on
                                        ? bulkA.class_ids.filter((x: string) => x !== c.id)
                                        : [...bulkA.class_ids, c.id],
                                    })}
                                    style={{
                                      ...smallBtn,
                                      background: on ? BROWN : "#fff",
                                      color: on ? "#fff" : BROWN,
                                      borderColor: on ? BROWN : BORDER,
                                    }}>
                              {c.name}{c.is_active ? "" : " (i)"}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                    <div style={{ marginTop: 10, display: "flex", gap: 6 }}>
                      <button style={btnPrimary} onClick={saveBulk}>Assign to {bulkA.class_ids.length} classes</button>
                      <button style={btnSecondary} onClick={() => setAddMode(null)}>Cancel</button>
                    </div>
                  </div>
                )}

                <table style={{ width: "100%", fontSize: "0.85rem", borderCollapse: "collapse" }}>
                  <thead>
                    <tr style={{ textAlign: "left", color: MUTED, fontSize: "0.72rem" }}>
                      <th style={{ padding: 6 }}>SUBJECT</th>
                      <th style={{ padding: 6 }}>CLASS</th>
                      <th style={{ padding: 6 }}>N/WK</th>
                      <th style={{ padding: 6 }}>TYPE</th>
                      <th style={{ padding: 6 }}>ACTIVE</th>
                      <th style={{ padding: 6 }}></th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.assignments.length === 0 && (
                      <tr><td colSpan={6} style={{ padding: 10, textAlign: "center", color: MUTED }}>No assignments yet.</td></tr>
                    )}
                    {data.assignments.map((a: Assignment) => (
                      <tr key={a.id} style={{ borderTop: "1px solid #f1f5f9" }}>
                        <td style={{ padding: 6, fontWeight: 600 }}>{a.subject_code} - {a.subject_name}</td>
                        <td style={{ padding: 6 }}>{a.class_name}</td>
                        <td style={{ padding: 6, fontWeight: 700 }}>{a.lessons_per_week}</td>
                        <td style={{ padding: 6, color: MUTED, fontSize: "0.75rem" }}>{a.requirement_type || "-"}</td>
                        <td style={{ padding: 6 }}>{a.is_active ? "OK" : "-"}</td>
                        <td style={{ padding: 6, textAlign: "right" }}>
                          <button style={{ ...smallBtn, color: RED, borderColor: RED }} onClick={() => removeAssignment(a.id)}>
                            Remove
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );

  return createPortal(drawer, document.body);
}

// ============================================================
// NEW TEACHER MODAL
// ============================================================
function NewTeacherModal({
  open, onClose, onDone,
}: { open: boolean; onClose: () => void; onDone: () => void }) {
  const toast = useToast();
  const [f, setF] = useState<any>({ role: "TEACHER" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [departments, setDepartments] = useState<any[]>([]);

  useEffect(() => {
    if (open) {
      setF({ role: "TEACHER" });
      setErr("");
      listDepartments().then(r => setDepartments(r.results || []));
    }
  }, [open]);

  if (!open) return null;

  async function save() {
    setBusy(true); setErr("");
    // Client-side validation
    if (!f.employee_code) { setErr("Employee Code is required, e.g. T021"); setBusy(false); return; }
    if (!f.first_name) { setErr("First Name is required."); setBusy(false); return; }
    if (f.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(f.email)) {
      setErr("Email is not valid. Example: name@school.ac.ke"); setBusy(false); return;
    }
    try {
      await createTeacher({
        employee_code: f.employee_code,
        first_name: f.first_name,
        last_name: f.last_name || "",
        teacher_number: f.teacher_number ? Number(f.teacher_number) : null,
        email: f.email || "",
        username: f.username || f.employee_code,
        password: f.password || undefined,
        ...(f.role ? { role: f.role } : {}),
        ...(f.phone ? { phone: f.phone } : {}),
        ...(f.hire_date ? { hire_date: f.hire_date } : {}),
        ...(f.department_id ? { department_id: Number(f.department_id) } : {}),
      } as any);
      toast.push({ type: "success", title: "Created", message: `${f.first_name} ${f.last_name}` });
      onDone(); onClose();
    } catch (e: any) {
      const detail = e?.response?.data?.detail || String(e);
      setErr(detail);
      toast.push({ type: "error", title: "Create failed", message: detail });
    } finally { setBusy(false); }
  }

  const modal = (
    <div
         style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)",
                  display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999 }}>
      <div onClick={e => e.stopPropagation()}
           style={{ background: "#fff", borderRadius: 12, width: 620, maxHeight: "92vh", overflowY: "auto", padding: "1.2rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
          <h3 style={{ margin: 0, color: BROWN }}>New Teacher</h3>
          <button onClick={onClose} style={btnSecondary}><X size={14} /></button>
        </div>
        {err && <div style={{ padding: 10, background: "#fef2f2", color: "#b91c1c", borderRadius: 8, marginBottom: 10, fontSize: "0.85rem" }}>{err}</div>}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <L label="Employee Code *"><input style={inputStyle} placeholder="e.g. T021" value={f.employee_code || ""} onChange={e => setF({ ...f, employee_code: e.target.value })} /></L>
          <L label="Teacher Number"><input style={inputStyle} type="number" placeholder="e.g. 21" value={f.teacher_number || ""} onChange={e => setF({ ...f, teacher_number: e.target.value })} /></L>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <L label="First Name / Title *"><input style={inputStyle} placeholder="e.g. Mr. John" value={f.first_name || ""} onChange={e => setF({ ...f, first_name: e.target.value })} /></L>
          <L label="Last Name"><input style={inputStyle} placeholder="e.g. Kamau" value={f.last_name || ""} onChange={e => setF({ ...f, last_name: e.target.value })} /></L>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <L label="Role">
            <select style={inputStyle} value={f.role || "TEACHER"} onChange={e => setF({ ...f, role: e.target.value })}>
              {ROLE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </L>
          <L label="Department">
            <select style={inputStyle} value={f.department_id || ""} onChange={e => setF({ ...f, department_id: e.target.value })}>
              <option value="">- None -</option>
              {departments.map(d => <option key={d.id} value={d.id}>{d.code} - {d.name}</option>)}
            </select>
          </L>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
          <L label="Email"><input style={inputStyle} type="email" placeholder="name@school.ac.ke" value={f.email || ""} onChange={e => setF({ ...f, email: e.target.value })} /></L>
          <L label="Phone"><input style={inputStyle} value={f.phone || ""} onChange={e => setF({ ...f, phone: e.target.value })} /></L>
          <L label="Hire Date"><input style={inputStyle} type="date" value={f.hire_date || ""} onChange={e => setF({ ...f, hire_date: e.target.value })} /></L>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <L label="Username (default = code)"><input style={inputStyle} value={f.username || ""} onChange={e => setF({ ...f, username: e.target.value })} /></L>
          <L label="Password (optional)"><input style={inputStyle} type="password" value={f.password || ""} onChange={e => setF({ ...f, password: e.target.value })} /></L>
        </div>
        <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
          <button style={btnPrimary} disabled={busy || !f.employee_code || !f.first_name} onClick={save}>
            {busy ? "Creating..." : "Create Teacher"}
          </button>
          <button style={btnSecondary} onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>
  );

  return createPortal(modal, document.body);
}

function L({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 8 }}>
      <label style={lbl}>{label}</label>
      {children}
    </div>
  );
}
