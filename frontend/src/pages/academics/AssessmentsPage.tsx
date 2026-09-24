import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, ClipboardList, Edit3, Plus, Save, Trash2, X } from "lucide-react";
import {
  createAssessment, deleteAssessment, listAssessments,
  setAssessmentStatus, updateAssessment, type AssessmentFull,
} from "../../services/assessments";

const BROWN = "#2b1a0f", BROWN2 = "#5a3a1e", SKY = "#22b4f0", CREAM = "#f5eee2";
const cardStyle: React.CSSProperties = {
  background: "#fff", border: "1px solid #e5e7eb", borderRadius: "14px",
  padding: "1.1rem 1.25rem", boxShadow: "0 4px 14px rgba(10,18,29,0.05)",
};
const STATUS_COLOR: Record<string, { bg: string; fg: string }> = {
  DRAFT: { bg: "#f1f5f9", fg: "#64748b" },
  MARK_ENTRY: { bg: "#fef3c7", fg: "#92400e" },
  PUBLISHED: { bg: "#dcfce7", fg: "#166534" },
  ARCHIVED: { bg: "#e0e7ff", fg: "#3730a3" },
};
const TYPES = ["CAT", "MIDTERM", "ENDTERM", "MOCK", "INTERNAL"];

export default function AssessmentsPage() {
  const navigate = useNavigate();
  const [rows, setRows] = useState<AssessmentFull[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState<Partial<AssessmentFull>>({});
  const [creating, setCreating] = useState(false);
  const [newDraft, setNewDraft] = useState({
    name: "", assessment_type: "CAT", date: new Date().toISOString().slice(0, 10), max_mark: 100,
  });

  async function load() {
    setLoading(true); setError(null);
    try { setRows(await listAssessments()); }
    catch (e) { setError(e instanceof Error ? e.message : "Load failed"); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  async function onCreate() {
    if (!newDraft.name.trim()) return;
    try {
      const created = await createAssessment({
        name: newDraft.name.trim(),
        assessment_type: newDraft.assessment_type,
        date: newDraft.date,
        max_mark: Number(newDraft.max_mark),
      });
      setRows((prev) => [...prev, created].sort((a, b) => a.date.localeCompare(b.date)));
      setCreating(false);
      setNewDraft({ name: "", assessment_type: "CAT", date: new Date().toISOString().slice(0, 10), max_mark: 100 });
    } catch (e) { alert(e instanceof Error ? e.message : "Create failed"); }
  }

  async function onSave(id: string) {
    try {
      const updated = await updateAssessment(id, draft);
      setRows((prev) => prev.map((r) => (r.id === id ? updated : r)));
      setEditing(null); setDraft({});
    } catch (e) { alert(e instanceof Error ? e.message : "Save failed"); }
  }

  async function onStatus(id: string, action: "publish" | "archive" | "draft" | "open-marks") {
    try {
      const updated = await setAssessmentStatus(id, action);
      setRows((prev) => prev.map((r) => (r.id === id ? updated : r)));
    } catch (e) { alert(e instanceof Error ? e.message : "Status change failed"); }
  }

  async function onDelete(id: string) {
    if (!confirm("Delete this assessment and ALL its results? This cannot be undone.")) return;
    try { await deleteAssessment(id); setRows((prev) => prev.filter((r) => r.id !== id)); }
    catch (e) { alert(e instanceof Error ? e.message : "Delete failed"); }
  }

  return (
    <div style={{ padding: "2rem", maxWidth: "1200px", margin: "0 auto" }}>
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
          }}><ClipboardList size={26} /></div>
          <div>
            <h1 style={{ margin: 0, fontSize: "1.7rem", color: "#1e2e40", fontWeight: 800 }}>Assessments</h1>
            <p style={{ margin: "2px 0 0", color: "#748095", fontSize: "0.9rem" }}>
              {loading ? "Loading…" : `${rows.length} assessment${rows.length === 1 ? "" : "s"}`}
            </p>
          </div>
        </div>
        <button type="button" onClick={() => setCreating(true)} style={{
          display: "inline-flex", alignItems: "center", gap: "6px",
          background: SKY, color: "#fff", border: "none",
          padding: "0.6rem 1rem", borderRadius: "10px", cursor: "pointer",
          fontWeight: 700, fontSize: "0.85rem",
        }}><Plus size={16} /> New assessment</button>
      </div>

      {error && <div style={{ padding: "0.8rem 1rem", borderRadius: "10px", background: "#fee2e2", color: "#991b1b", marginBottom: "1rem" }}>{error}</div>}

      {creating && (
        <div style={{ ...cardStyle, marginBottom: "1rem", border: `1px solid ${SKY}` }}>
          <h3 style={{ margin: "0 0 0.75rem", color: BROWN2, fontSize: "0.95rem", fontWeight: 700 }}>New assessment</h3>
          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr 1fr auto", gap: "10px", alignItems: "end" }}>
            <div><label style={{ fontSize: "0.72rem", fontWeight: 700, color: "#748095" }}>NAME</label>
              <input value={newDraft.name} onChange={(e) => setNewDraft({ ...newDraft, name: e.target.value })}
                style={{ width: "100%", padding: "6px 8px", border: "1px solid #cbd5e1", borderRadius: "6px" }} /></div>
            <div><label style={{ fontSize: "0.72rem", fontWeight: 700, color: "#748095" }}>TYPE</label>
              <select value={newDraft.assessment_type} onChange={(e) => setNewDraft({ ...newDraft, assessment_type: e.target.value })}
                style={{ width: "100%", padding: "6px 8px", border: "1px solid #cbd5e1", borderRadius: "6px" }}>
                {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select></div>
            <div><label style={{ fontSize: "0.72rem", fontWeight: 700, color: "#748095" }}>DATE</label>
              <input type="date" value={newDraft.date} onChange={(e) => setNewDraft({ ...newDraft, date: e.target.value })}
                style={{ width: "100%", padding: "6px 8px", border: "1px solid #cbd5e1", borderRadius: "6px" }} /></div>
            <div><label style={{ fontSize: "0.72rem", fontWeight: 700, color: "#748095" }}>MAX</label>
              <input type="number" value={newDraft.max_mark} onChange={(e) => setNewDraft({ ...newDraft, max_mark: Number(e.target.value) })}
                style={{ width: "100%", padding: "6px 8px", border: "1px solid #cbd5e1", borderRadius: "6px" }} /></div>
            <div style={{ display: "flex", gap: "6px" }}>
              <button type="button" onClick={onCreate} style={{ background: SKY, color: "#fff", border: "none", padding: "6px 12px", borderRadius: "6px", fontWeight: 700, cursor: "pointer" }}>Create</button>
              <button type="button" onClick={() => setCreating(false)} style={{ background: "#e5e7eb", color: "#374151", border: "none", padding: "6px 12px", borderRadius: "6px", fontWeight: 700, cursor: "pointer" }}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      <div style={{ ...cardStyle, padding: 0, overflow: "hidden" }}>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.88rem" }}>
            <thead>
              <tr style={{ background: `linear-gradient(135deg, ${BROWN}, ${BROWN2})`, color: CREAM }}>
                <th style={{ textAlign: "left", padding: "0.7rem 1rem" }}>Name</th>
                <th style={{ textAlign: "left", padding: "0.7rem 1rem" }}>Type</th>
                <th style={{ textAlign: "left", padding: "0.7rem 1rem" }}>Date</th>
                <th style={{ textAlign: "right", padding: "0.7rem 1rem" }}>Max</th>
                <th style={{ textAlign: "center", padding: "0.7rem 1rem" }}>Status</th>
                <th style={{ textAlign: "right", padding: "0.7rem 1rem" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const isEditing = editing === r.id;
                const sc = STATUS_COLOR[r.status] ?? { bg: "#f1f5f9", fg: "#64748b" };
                return (
                  <tr key={r.id} style={{ borderTop: "1px solid #f1f5f9" }}>
                    {isEditing ? (
                      <>
                        <td style={{ padding: "0.55rem 1rem" }}><input value={draft.name ?? r.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} style={{ width: "100%", padding: "4px 6px", border: "1px solid #cbd5e1", borderRadius: "6px" }} /></td>
                        <td style={{ padding: "0.55rem 1rem" }}><select value={draft.assessment_type ?? r.assessment_type} onChange={(e) => setDraft({ ...draft, assessment_type: e.target.value })} style={{ padding: "4px 6px", border: "1px solid #cbd5e1", borderRadius: "6px" }}>{TYPES.map((t) => <option key={t} value={t}>{t}</option>)}</select></td>
                        <td style={{ padding: "0.55rem 1rem" }}><input type="date" value={draft.date ?? r.date} onChange={(e) => setDraft({ ...draft, date: e.target.value })} style={{ padding: "4px 6px", border: "1px solid #cbd5e1", borderRadius: "6px" }} /></td>
                        <td style={{ padding: "0.55rem 1rem", textAlign: "right" }}><input type="number" value={draft.max_mark ?? r.max_mark} onChange={(e) => setDraft({ ...draft, max_mark: Number(e.target.value) })} style={{ width: "80px", padding: "4px 6px", border: "1px solid #cbd5e1", borderRadius: "6px", textAlign: "right" }} /></td>
                        <td style={{ padding: "0.55rem 1rem", textAlign: "center" }}><span style={{ padding: "2px 10px", borderRadius: "999px", fontSize: "0.72rem", fontWeight: 700, background: sc.bg, color: sc.fg }}>{r.status}</span></td>
                        <td style={{ padding: "0.55rem 1rem", textAlign: "right" }}>
                          <button onClick={() => onSave(r.id)} style={{ background: SKY, color: "#fff", border: "none", padding: "5px 10px", borderRadius: "6px", fontWeight: 600, cursor: "pointer", marginRight: "6px", fontSize: "0.8rem", display: "inline-flex", alignItems: "center", gap: "4px" }}><Save size={13} /> Save</button>
                          <button onClick={() => { setEditing(null); setDraft({}); }} style={{ background: "#e5e7eb", color: "#374151", border: "none", padding: "5px 10px", borderRadius: "6px", fontWeight: 600, cursor: "pointer", fontSize: "0.8rem", display: "inline-flex", alignItems: "center", gap: "4px" }}><X size={13} /> Cancel</button>
                        </td>
                      </>
                    ) : (
                      <>
                        <td style={{ padding: "0.55rem 1rem", fontWeight: 600, color: "#1e2e40" }}>{r.name}</td>
                        <td style={{ padding: "0.55rem 1rem", color: "#748095" }}>{r.assessment_type}</td>
                        <td style={{ padding: "0.55rem 1rem", color: "#748095" }}>{r.date}</td>
                        <td style={{ padding: "0.55rem 1rem", textAlign: "right" }}>{r.max_mark}</td>
                        <td style={{ padding: "0.55rem 1rem", textAlign: "center" }}><span style={{ padding: "2px 10px", borderRadius: "999px", fontSize: "0.72rem", fontWeight: 700, background: sc.bg, color: sc.fg }}>{r.status}</span></td>
                        <td style={{ padding: "0.55rem 1rem", textAlign: "right" }}>
                          <button onClick={() => navigate(`/academics/marks?assessment=${r.id}`)} style={{ background: "transparent", border: `1px solid ${SKY}`, color: SKY, padding: "5px 10px", borderRadius: "6px", fontWeight: 600, cursor: "pointer", marginRight: "6px", fontSize: "0.8rem" }}>Enter marks</button>
                          {r.status !== "MARK_ENTRY" && r.status !== "PUBLISHED" && (<button onClick={() => onStatus(r.id, "open-marks")} style={{ background: "transparent", border: "1px solid #f59e0b", color: "#b45309", padding: "5px 10px", borderRadius: "6px", fontWeight: 600, cursor: "pointer", marginRight: "6px", fontSize: "0.8rem" }}>Open</button>) }
                          {r.status !== "PUBLISHED" && <button onClick={() => onStatus(r.id, "publish")} style={{ background: "transparent", border: "1px solid #10b981", color: "#10b981", padding: "5px 10px", borderRadius: "6px", fontWeight: 600, cursor: "pointer", marginRight: "6px", fontSize: "0.8rem" }}>Publish</button>}
                          {r.status === "PUBLISHED" && <button onClick={() => onStatus(r.id, "draft")} style={{ background: "transparent", border: "1px solid #f59e0b", color: "#f59e0b", padding: "5px 10px", borderRadius: "6px", fontWeight: 600, cursor: "pointer", marginRight: "6px", fontSize: "0.8rem" }}>Reopen</button>}
                          <button onClick={() => { setEditing(r.id); setDraft({}); }} style={{ background: "transparent", border: "1px solid #94a3b8", color: "#475569", padding: "5px 10px", borderRadius: "6px", fontWeight: 600, cursor: "pointer", marginRight: "6px", fontSize: "0.8rem", display: "inline-flex", alignItems: "center", gap: "4px" }}><Edit3 size={13} /> Edit</button>
                          <button onClick={() => onDelete(r.id)} style={{ background: "transparent", border: "1px solid #ef4444", color: "#ef4444", padding: "5px 10px", borderRadius: "6px", fontWeight: 600, cursor: "pointer", fontSize: "0.8rem", display: "inline-flex", alignItems: "center", gap: "4px" }}><Trash2 size={13} /></button>
                        </td>
                      </>
                    )}
                  </tr>
                );
              })}
              {!loading && rows.length === 0 && (
                <tr><td colSpan={6} style={{ padding: "2rem", textAlign: "center", color: "#94a3b8" }}>No assessments yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}