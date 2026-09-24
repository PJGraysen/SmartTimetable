import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, FileText, LineChart, Save, Search, X } from "lucide-react";
import { listStudents, updateStudent, type Student } from "../../services/academics";

const BROWN = "#2b1a0f";
const BROWN2 = "#5a3a1e";
const SKY = "#22b4f0";
const CREAM = "#f5eee2";

export default function StudentsPage() {
  const navigate = useNavigate();
  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [classFilter, setClassFilter] = useState<string>("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState<Partial<Student>>({});
  const [savingId, setSavingId] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await listStudents({ page_size: 500 });
      setStudents(data.results);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load students");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  const classOptions = useMemo(() => {
    const s = new Set<string>();
    for (const st of students) {
      const n = st.current_enrollment?.teaching_group_name;
      if (n) s.add(n);
    }
    return Array.from(s).sort();
  }, [students]);

  const filtered = useMemo(() => {
    let out = students;
    if (classFilter) {
      out = out.filter((s) => s.current_enrollment?.teaching_group_name === classFilter);
    }
    if (search) {
      const q = search.toLowerCase();
      out = out.filter(
        (s) =>
          s.admission_number.toLowerCase().includes(q) ||
          s.full_name.toLowerCase().includes(q),
      );
    }
    return out;
  }, [students, search, classFilter]);

  function startEdit(s: Student) {
    setEditingId(s.id);
    setDraft({
      first_name: s.first_name,
      middle_name: s.middle_name,
      last_name: s.last_name,
      status: s.status,
    });
  }

  function cancelEdit() {
    setEditingId(null);
    setDraft({});
  }

  async function commitEdit(id: string) {
    setSavingId(id);
    try {
      const updated = await updateStudent(id, {
        first_name: (draft.first_name ?? "").trim(),
        middle_name: (draft.middle_name ?? "").trim(),
        last_name: (draft.last_name ?? "").trim(),
        status: draft.status,
      });
      setStudents((prev) => prev.map((s) => (s.id === id ? updated : s)));
      cancelEdit();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSavingId(null);
    }
  }

  const classCounts = useMemo(() => {
    const m = new Map<string, number>();
    for (const s of students) {
      const n = s.current_enrollment?.teaching_group_name ?? "(no class)";
      m.set(n, (m.get(n) ?? 0) + 1);
    }
    return Array.from(m.entries()).sort();
  }, [students]);

  return (
    <div style={{ padding: "2rem", maxWidth: "1400px", margin: "0 auto" }}>
      <button
        type="button"
        onClick={() => navigate(-1)}
        style={{
          display: "inline-flex", alignItems: "center", gap: "6px",
          background: "transparent", border: "none", color: BROWN2,
          fontWeight: 600, cursor: "pointer", marginBottom: "1rem",
        }}
      >
        <ArrowLeft size={16} /> Back
      </button>

      <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "1.5rem" }}>
        <div style={{
          width: "48px", height: "48px", borderRadius: "12px",
          background: `linear-gradient(135deg, ${SKY}, #0b5d8c)`,
          color: "#fff", display: "flex", alignItems: "center", justifyContent: "center",
          boxShadow: "0 6px 18px rgba(34,180,240,0.35)",
          fontSize: "1.1rem", fontWeight: 800,
        }}>
          {students.length}
        </div>
        <div>
          <h1 style={{ margin: 0, fontSize: "1.6rem", color: "#1e2e40", fontWeight: 800 }}>
            Students
          </h1>
          <p style={{ margin: "2px 0 0", color: "#748095", fontSize: "0.9rem" }}>
            {loading ? "Loading…" : `${filtered.length} of ${students.length} shown`}
          </p>
        </div>
      </div>

      {classCounts.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", marginBottom: "1rem" }}>
          {classCounts.map(([name, count]) => (
            <button
              key={name}
              type="button"
              onClick={() => setClassFilter(classFilter === name ? "" : name)}
              style={{
                padding: "5px 12px", borderRadius: "999px",
                border: classFilter === name ? `1px solid ${SKY}` : "1px solid #e5e7eb",
                background: classFilter === name ? "#e0f2fe" : "#fff",
                color: classFilter === name ? "#075985" : "#475569",
                cursor: "pointer", fontSize: "0.82rem", fontWeight: 600,
              }}
            >
              {name} <span style={{ color: "#94a3b8", fontWeight: 500 }}>({count})</span>
            </button>
          ))}
        </div>
      )}

      <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", marginBottom: "1rem" }}>
        <div style={{
          display: "flex", alignItems: "center", gap: "8px",
          background: "#fff", border: "1px solid #e5e7eb", borderRadius: "10px",
          padding: "0.6rem 0.9rem", flex: "1 1 320px", maxWidth: "420px",
        }}>
          <Search size={16} style={{ color: "#748095" }} />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search name or admission number…"
            style={{ border: "none", outline: "none", flex: 1, fontSize: "0.9rem", background: "transparent" }}
          />
        </div>
        <select
          value={classFilter}
          onChange={(e) => setClassFilter(e.target.value)}
          style={{
            padding: "0.6rem 0.9rem", border: "1px solid #e5e7eb", borderRadius: "10px",
            background: "#fff", fontWeight: 600, color: BROWN2, minWidth: "200px",
            cursor: "pointer", fontSize: "0.9rem",
          }}
        >
          <option value="">All classes</option>
          {classOptions.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      {error && (
        <div style={{
          padding: "0.8rem 1rem", borderRadius: "10px",
          background: "#fee2e2", color: "#991b1b", marginBottom: "1rem",
        }}>{error}</div>
      )}

      <div style={{
        background: "#fff", borderRadius: "12px", overflow: "hidden",
        border: "1px solid #e5e7eb", boxShadow: "0 4px 14px rgba(10,18,29,0.06)",
      }}>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.86rem" }}>
            <thead>
              <tr style={{ background: `linear-gradient(135deg, ${BROWN}, ${BROWN2})`, color: CREAM }}>
                <th style={{ textAlign: "left", padding: "0.7rem 0.9rem", fontWeight: 700 }}>Adm No</th>
                <th style={{ textAlign: "left", padding: "0.7rem 0.9rem", fontWeight: 700 }}>Name</th>
                <th style={{ textAlign: "left", padding: "0.7rem 0.9rem", fontWeight: 700 }}>Class</th>
                <th style={{ textAlign: "right", padding: "0.7rem 0.9rem", fontWeight: 700 }}>KCPE</th>
                <th style={{ textAlign: "left", padding: "0.7rem 0.9rem", fontWeight: 700 }}>Status</th>
                <th style={{ textAlign: "right", padding: "0.7rem 0.9rem", fontWeight: 700 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s) => {
                const isEditing = editingId === s.id;
                const isSaving = savingId === s.id;
                return (
                  <tr key={s.id} style={{ borderTop: "1px solid #f1f5f9" }}>
                    <td style={{ padding: "0.6rem 0.9rem", color: BROWN2, fontWeight: 600 }}>
                      {s.admission_number}
                    </td>
                    {isEditing ? (
                      <>
                        <td style={{ padding: "0.6rem 0.9rem" }}>
                          <div style={{ display: "flex", gap: "4px" }}>
                            <input
                              value={draft.first_name ?? ""}
                              onChange={(e) => setDraft((d) => ({ ...d, first_name: e.target.value }))}
                              placeholder="First"
                              style={{ width: "100%", padding: "4px 6px", border: "1px solid #cbd5e1", borderRadius: "6px" }}
                            />
                            <input
                              value={draft.middle_name ?? ""}
                              onChange={(e) => setDraft((d) => ({ ...d, middle_name: e.target.value }))}
                              placeholder="Middle"
                              style={{ width: "100%", padding: "4px 6px", border: "1px solid #cbd5e1", borderRadius: "6px" }}
                            />
                            <input
                              value={draft.last_name ?? ""}
                              onChange={(e) => setDraft((d) => ({ ...d, last_name: e.target.value }))}
                              placeholder="Last"
                              style={{ width: "100%", padding: "4px 6px", border: "1px solid #cbd5e1", borderRadius: "6px" }}
                            />
                          </div>
                        </td>
                        <td style={{ padding: "0.6rem 0.9rem", color: "#94a3b8" }}>
                          {s.current_enrollment?.teaching_group_name ?? "—"}
                        </td>
                        <td style={{ padding: "0.6rem 0.9rem", textAlign: "right", color: "#94a3b8" }}>
                          {s.kcpe_mark ?? "—"}
                        </td>
                        <td style={{ padding: "0.6rem 0.9rem" }}>
                          <select
                            value={draft.status ?? s.status}
                            onChange={(e) => setDraft((d) => ({ ...d, status: e.target.value as Student["status"] }))}
                            style={{ padding: "4px 6px", border: "1px solid #cbd5e1", borderRadius: "6px" }}
                          >
                            <option value="ACTIVE">ACTIVE</option>
                            <option value="GRADUATED">GRADUATED</option>
                            <option value="TRANSFERRED">TRANSFERRED</option>
                            <option value="SUSPENDED">SUSPENDED</option>
                            <option value="WITHDRAWN">WITHDRAWN</option>
                          </select>
                        </td>
                        <td style={{ padding: "0.6rem 0.9rem", textAlign: "right", whiteSpace: "nowrap" }}>
                          <button
                            type="button"
                            onClick={() => commitEdit(s.id)}
                            disabled={isSaving}
                            style={{
                              display: "inline-flex", alignItems: "center", gap: "4px",
                              background: SKY, color: "#fff", border: "none",
                              padding: "5px 10px", borderRadius: "6px", cursor: "pointer",
                              fontSize: "0.8rem", fontWeight: 600, marginRight: "6px",
                            }}
                          ><Save size={13} /> {isSaving ? "Saving…" : "Save"}</button>
                          <button
                            type="button"
                            onClick={cancelEdit}
                            style={{
                              display: "inline-flex", alignItems: "center", gap: "4px",
                              background: "#e5e7eb", color: "#374151", border: "none",
                              padding: "5px 10px", borderRadius: "6px", cursor: "pointer",
                              fontSize: "0.8rem", fontWeight: 600,
                            }}
                          ><X size={13} /> Cancel</button>
                        </td>
                      </>
                    ) : (
                      <>
                        <td style={{ padding: "0.6rem 0.9rem" }}>
                          <div style={{ fontWeight: 600 }}>{s.full_name}</div>
                          <div style={{ fontSize: "0.72rem", color: "#94a3b8" }}>
                            {s.first_name} · {s.middle_name || "—"} · {s.last_name}
                          </div>
                        </td>
                        <td style={{ padding: "0.6rem 0.9rem" }}>
                          <span style={{
                            padding: "2px 8px", borderRadius: "6px", fontSize: "0.75rem",
                            fontWeight: 700, background: "#f0f9ff", color: "#075985",
                          }}>
                            {s.current_enrollment?.teaching_group_name ?? "—"}
                          </span>
                        </td>
                        <td style={{ padding: "0.6rem 0.9rem", textAlign: "right", fontWeight: 600, color: s.kcpe_mark ? "#1e2e40" : "#cbd5e1" }}>
                          {s.kcpe_mark ?? "—"}
                        </td>
                        <td style={{ padding: "0.6rem 0.9rem" }}>
                          <span style={{
                            fontSize: "0.72rem", fontWeight: 700, letterSpacing: "0.04em",
                            padding: "2px 8px", borderRadius: "999px",
                            background: s.status === "ACTIVE" ? "#dcfce7" : "#f1f5f9",
                            color: s.status === "ACTIVE" ? "#166534" : "#64748b",
                          }}>
                            {s.status}
                          </span>
                        </td>
                        <td style={{ padding: "0.6rem 0.9rem", textAlign: "right", whiteSpace: "nowrap" }}>
                          <button
                            type="button"
                            onClick={() => startEdit(s)}
                            style={{
                              background: "transparent", border: `1px solid #94a3b8`,
                              color: "#475569", padding: "5px 12px", borderRadius: "6px",
                              cursor: "pointer", fontSize: "0.8rem", fontWeight: 600,
                              marginRight: "6px",
                            }}
                          >Edit</button>
                          <button
                            type="button"
                            onClick={() => navigate("/academics/students/" + s.id + "/analysis")}
                            style={{
                              display: "inline-flex", alignItems: "center", gap: "4px",
                              background: SKY, border: "none",
                              color: "#fff", padding: "5px 12px", borderRadius: "6px",
                              cursor: "pointer", fontSize: "0.8rem", fontWeight: 600,
                              marginRight: "6px",
                            }}
                          ><LineChart size={13} /> Analyse</button>
                          <button
                            type="button"
                            onClick={() => navigate("/academics/students/" + s.id + "/report-card")}
                            style={{
                              display: "inline-flex", alignItems: "center", gap: "4px",
                              background: "transparent", border: `1px solid ${BROWN2}`,
                              color: BROWN2, padding: "5px 12px", borderRadius: "6px",
                              cursor: "pointer", fontSize: "0.8rem", fontWeight: 600,
                            }}
                          ><FileText size={13} /> Report Card</button>
                          <button
                            type="button"
                            onClick={() => navigate("/academics/students/" + s.id + "/report-form")}
                            style={{
                              display: "inline-flex", alignItems: "center", gap: "4px",
                              background: "transparent", border: `1px solid #10b981`,
                              color: "#10b981", padding: "5px 12px", borderRadius: "6px",
                              cursor: "pointer", fontSize: "0.8rem", fontWeight: 600,
                              marginLeft: "6px",
                            }}
                          ><FileText size={13} /> Report Form</button>
                        </td>
                      </>
                    )}
                  </tr>
                );
              })}
              {!loading && filtered.length === 0 && (
                <tr>
                  <td colSpan={6} style={{ padding: "2rem", textAlign: "center", color: "#94a3b8" }}>
                    No students match.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}