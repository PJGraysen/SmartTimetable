import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, MessageSquare, Save, Shield } from "lucide-react";
import { listStudents } from "../../services/academics";
import { listAllComments, upsertComment, type ReportComment } from "../../services/comments";
import { getAcademicTerms } from "../../services/core";
import { fetchMarksContext, type MarksContext } from "../../services/assessments";

const BROWN = "#2b1a0f", BROWN2 = "#5a3a1e", SKY = "#22b4f0", CREAM = "#f5eee2";
const cardStyle: React.CSSProperties = {
  background: "#fff", border: "1px solid #e5e7eb", borderRadius: "14px",
  padding: "1.1rem 1.25rem", boxShadow: "0 4px 14px rgba(10,18,29,0.05)",
};

type Draft = { conduct: string; class_teacher_comment: string; rector_comment: string; mission_comment: string };
type Row = { id: string; name: string; admission_number: string; class_id: string; class_name: string };

export default function CommentsPage() {
  const navigate = useNavigate();
  const [context, setContext] = useState<MarksContext | null>(null);
  const [classes, setClasses] = useState<Array<{ id: string; name: string }>>([]);
  const [classFilter, setClassFilter] = useState("");
  const [students, setStudents] = useState<Row[]>([]);
  const [existing, setExisting] = useState<Record<string, ReportComment>>({});
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});
  const [savingId, setSavingId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [termId, setTermId] = useState("");
  const [yearId, setYearId] = useState("");

  useEffect(() => {
    Promise.all([
      listStudents({ page_size: 500 }),
      listAllComments(),
      getAcademicTerms(),
      fetchMarksContext(),
    ])
      .then(([sPage, comments, terms, ctx]) => {
        setContext(ctx);
        const allowedClassIds = new Set(ctx.classes.map((c) => c.id));
        const allowedClassNames = new Set(ctx.classes.map((c) => c.name));

        const rows: Row[] = sPage.results
          .filter((s) => {
            const e = s.current_enrollment;
            if (!e) return false;
            if (ctx.is_admin) return true;
            return allowedClassIds.has(e.teaching_group_id) || allowedClassNames.has(e.teaching_group_name);
          })
          .map((s) => ({
            id: s.id,
            name: s.full_name,
            admission_number: s.admission_number,
            class_id: s.current_enrollment?.teaching_group_id ?? "",
            class_name: s.current_enrollment?.teaching_group_name ?? "",
          }))
          .sort((a, b) => a.class_name.localeCompare(b.class_name) || a.name.localeCompare(b.name));

        setStudents(rows);
        // Only show classes the user is allowed to filter by
        const cs = new Map<string, string>();
        for (const r of rows) if (r.class_id) cs.set(r.class_id, r.class_name);
        setClasses(Array.from(cs.entries()).map(([id, name]) => ({ id, name })).sort((a, b) => a.name.localeCompare(b.name)));

        const byStudent: Record<string, ReportComment> = {};
        for (const c of comments) byStudent[c.student] = c;
        setExisting(byStudent);

        const active = terms.find((t) => t.is_active) ?? terms[0];
        if (active) {
          setTermId(active.id);
          setYearId((active as unknown as { academic_year: string }).academic_year);
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, []);

  const visible = useMemo(() => {
    if (!classFilter) return students;
    return students.filter((s) => s.class_id === classFilter);
  }, [students, classFilter]);

  function getDraft(sid: string): Draft {
    if (drafts[sid]) return drafts[sid];
    const ex = existing[sid];
    return {
      conduct: ex?.conduct ?? "",
      class_teacher_comment: ex?.class_teacher_comment ?? "",
      rector_comment: ex?.rector_comment ?? "",
      mission_comment: ex?.mission_comment ?? "",
    };
  }

  function setField(sid: string, field: keyof Draft, value: string) {
    setDrafts((prev) => ({ ...prev, [sid]: { ...getDraft(sid), [field]: value } }));
  }

  async function save(sid: string) {
    if (!termId || !yearId) { setError("No active term — set one in core first."); return; }
    setSavingId(sid); setError(null); setMessage(null);
    try {
      const d = getDraft(sid);
      const res = await upsertComment({
        student: sid, academic_year: yearId, term: termId,
        conduct: d.conduct, class_teacher_comment: d.class_teacher_comment,
        rector_comment: d.rector_comment, mission_comment: d.mission_comment,
      });
      setExisting((prev) => ({ ...prev, [sid]: res }));
      setDrafts((prev) => { const n = { ...prev }; delete n[sid]; return n; });
      setMessage("Comments saved.");
      window.setTimeout(() => setMessage(null), 1500);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally { setSavingId(null); }
  }

  return (
    <div style={{ padding: "2rem", maxWidth: "1400px", margin: "0 auto" }}>
      <button type="button" onClick={() => navigate(-1)} style={{
        display: "inline-flex", alignItems: "center", gap: "6px",
        background: "transparent", border: "none", color: BROWN2,
        fontWeight: 600, cursor: "pointer", marginBottom: "1rem",
      }}><ArrowLeft size={16} /> Back</button>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "14px", marginBottom: "1.5rem", flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <div style={{
            width: "52px", height: "52px", borderRadius: "14px",
            background: `linear-gradient(135deg, ${SKY}, #0b5d8c)`,
            color: "#fff", display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 6px 18px rgba(34,180,240,0.35)",
          }}><MessageSquare size={26} /></div>
          <div>
            <h1 style={{ margin: 0, fontSize: "1.7rem", color: "#1e2e40", fontWeight: 800 }}>Report Comments</h1>
            <p style={{ margin: "2px 0 0", color: "#748095", fontSize: "0.9rem" }}>
              Conduct and teacher/rector/mission comments per student.
            </p>
          </div>
        </div>
        {context && (
          <div style={{
            display: "inline-flex", alignItems: "center", gap: "6px",
            padding: "6px 12px", borderRadius: "999px",
            background: context.is_admin ? "#dcfce7" : "#e0f2fe",
            color: context.is_admin ? "#166534" : "#075985",
            fontSize: "0.78rem", fontWeight: 700,
          }}>
            <Shield size={13} />
            {context.is_admin ? "Admin · all classes" : (context.teacher_name ? `Teacher · ${context.teacher_name}` : "Teacher")}
          </div>
        )}
      </div>

      <div style={{ ...cardStyle, marginBottom: "1rem", display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
        <label style={{ fontSize: "0.72rem", fontWeight: 700, color: "#748095", letterSpacing: "0.06em" }}>CLASS:</label>
        <select value={classFilter} onChange={(e) => setClassFilter(e.target.value)}
          style={{ padding: "5px 8px", border: `1px solid ${SKY}`, borderRadius: "8px", fontWeight: 600, color: BROWN2, minWidth: "220px" }}>
          <option value="">All accessible classes ({students.length})</option>
          {classes.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <span style={{ color: "#94a3b8", fontSize: "0.85rem" }}>{visible.length} shown</span>
      </div>

      {error && <div style={{ padding: "0.7rem 1rem", borderRadius: "10px", background: "#fee2e2", color: "#991b1b", marginBottom: "1rem" }}>{error}</div>}
      {message && <div style={{ padding: "0.7rem 1rem", borderRadius: "10px", background: "#dcfce7", color: "#166534", marginBottom: "1rem" }}>{message}</div>}

      {loading ? (
        <div style={{ padding: "3rem", textAlign: "center", color: "#94a3b8" }}>Loading…</div>
      ) : visible.length === 0 ? (
        <div style={{ padding: "3rem", textAlign: "center", color: "#94a3b8" }}>
          {students.length === 0
            ? "No students in classes you can access."
            : "No students match this filter."}
        </div>
      ) : (
        <div style={{ display: "grid", gap: "12px" }}>
          {visible.map((s) => {
            const d = getDraft(s.id);
            const dirty = !!drafts[s.id];
            const hasExisting = !!existing[s.id];
            return (
              <div key={s.id} style={{ ...cardStyle, borderLeft: `4px solid ${dirty ? SKY : "#e5e7eb"}` }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
                  <div>
                    <div style={{ fontWeight: 700, color: "#1e2e40" }}>{s.name}</div>
                    <div style={{ fontSize: "0.78rem", color: "#748095" }}>
                      {s.admission_number} · {s.class_name}
                      {hasExisting && <span style={{ marginLeft: "8px", color: "#10b981" }}>· saved</span>}
                    </div>
                  </div>
                  <button type="button" onClick={() => save(s.id)} disabled={savingId === s.id}
                    style={{
                      display: "inline-flex", alignItems: "center", gap: "4px",
                      background: dirty ? SKY : "#cbd5e1", color: "#fff", border: "none",
                      padding: "6px 12px", borderRadius: "8px",
                      cursor: dirty ? "pointer" : "not-allowed",
                      fontWeight: 700, fontSize: "0.8rem",
                    }}>
                    <Save size={13} /> {savingId === s.id ? "…" : "Save"}
                  </button>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1.4fr 1.4fr 1.4fr", gap: "10px" }}>
                  <div>
                    <label style={{ fontSize: "0.68rem", fontWeight: 700, color: "#748095" }}>CONDUCT</label>
                    <input value={d.conduct} onChange={(e) => setField(s.id, "conduct", e.target.value)}
                      style={{ width: "100%", padding: "5px 8px", border: "1px solid #cbd5e1", borderRadius: "6px" }} />
                  </div>
                  <div>
                    <label style={{ fontSize: "0.68rem", fontWeight: 700, color: "#748095" }}>CLASS TEACHER</label>
                    <textarea value={d.class_teacher_comment} rows={2}
                      onChange={(e) => setField(s.id, "class_teacher_comment", e.target.value)}
                      style={{ width: "100%", padding: "5px 8px", border: "1px solid #cbd5e1", borderRadius: "6px", fontFamily: "inherit", fontSize: "0.85rem", resize: "vertical" }} />
                  </div>
                  <div>
                    <label style={{ fontSize: "0.68rem", fontWeight: 700, color: "#748095" }}>RECTOR</label>
                    <textarea value={d.rector_comment} rows={2}
                      onChange={(e) => setField(s.id, "rector_comment", e.target.value)}
                      style={{ width: "100%", padding: "5px 8px", border: "1px solid #cbd5e1", borderRadius: "6px", fontFamily: "inherit", fontSize: "0.85rem", resize: "vertical" }} />
                  </div>
                  <div>
                    <label style={{ fontSize: "0.68rem", fontWeight: 700, color: "#748095" }}>MISSION</label>
                    <textarea value={d.mission_comment} rows={2}
                      onChange={(e) => setField(s.id, "mission_comment", e.target.value)}
                      style={{ width: "100%", padding: "5px 8px", border: "1px solid #cbd5e1", borderRadius: "6px", fontFamily: "inherit", fontSize: "0.85rem", resize: "vertical" }} />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}