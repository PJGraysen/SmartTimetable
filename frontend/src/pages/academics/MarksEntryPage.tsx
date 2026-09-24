import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  AlertCircle, ArrowLeft, CheckCircle2, ClipboardEdit, Hash, Lock, Save, Shield, Users,
} from "lucide-react";
import {
  fetchMarksContext, fetchRosterForClass,
  listAssessments, saveBulkMarks, updateAssessment,
  type AssessmentFull, type MarksContext, type RosterEntry,
} from "../../services/assessments";

const BROWN = "#2b1a0f", BROWN2 = "#5a3a1e", SKY = "#22b4f0", CREAM = "#f5eee2";

const cardStyle: React.CSSProperties = {
  background: "#fff", border: "1px solid #e5e7eb", borderRadius: "14px",
  padding: "1.1rem 1.25rem", boxShadow: "0 4px 14px rgba(10,18,29,0.05)",
};

type RowState = { raw_mark: string; status: string; dirty: boolean };
type SubjectLite = { id: string; name: string; code: string };

const STATUS_LABEL: Record<string, string> = {
  DRAFT: "Draft",
  MARK_ENTRY: "Open for marks entry",
  PUBLISHED: "Published",
  ARCHIVED: "Archived",
};

export default function MarksEntryPage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();

  const [context, setContext] = useState<MarksContext | null>(null);
  const [assessments, setAssessments] = useState<AssessmentFull[]>([]);
  const [assessmentId, setAssessmentId] = useState<string>(params.get("assessment") ?? "");
  const [classId, setClassId] = useState<string>(params.get("class") ?? "");
  const [subjectId, setSubjectId] = useState<string>("");

  const [roster, setRoster] = useState<RosterEntry[]>([]);
  const [rows, setRows] = useState<Record<string, RowState>>({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRefs = useRef<Record<string, HTMLInputElement | null>>({});

  const [editableMax, setEditableMax] = useState<number>(100);
  const [savingMax, setSavingMax] = useState(false);
  const [maxSaved, setMaxSaved] = useState(false);

  useEffect(() => {
    Promise.all([fetchMarksContext(), listAssessments()])
      .then(([ctx, asses]) => {
        setContext(ctx);
        setAssessments(asses);
        if (!assessmentId && asses.length > 0) {
          setAssessmentId(asses[asses.length - 1].id);
          setEditableMax(asses[asses.length - 1].max_mark);
        }
        if (!classId && ctx.classes.length > 0) {
          setClassId(ctx.classes[0].id);
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Load failed"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const next: Record<string, string> = {};
    if (assessmentId) next.assessment = assessmentId;
    if (classId) next.class = classId;
    setParams(next, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assessmentId, classId]);

  useEffect(() => {
    const a = assessments.find((x) => x.id === assessmentId);
    if (a) setEditableMax(a.max_mark);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assessmentId]);

  const subjects: SubjectLite[] = useMemo(() => {
    if (!context || !classId) return [];
    return context.subjects_by_class[classId] ?? [];
  }, [context, classId]);

  useEffect(() => {
    if (subjects.length === 0) { setSubjectId(""); return; }
    if (!subjects.some((s) => s.id === subjectId)) {
      setSubjectId(subjects[0].id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [subjects]);

  const currentAssessment = useMemo(
    () => assessments.find((a) => a.id === assessmentId) ?? null,
    [assessments, assessmentId],
  );
  const currentClass = useMemo(
    () => context?.classes.find((c) => c.id === classId) ?? null,
    [context, classId],
  );
  const currentSubject = useMemo(
    () => subjects.find((s) => s.id === subjectId) ?? null,
    [subjects, subjectId],
  );

  // Role × status gating
  const isAdmin = !!context?.is_admin;
  const statusOpen = currentAssessment?.status === "MARK_ENTRY";
  const canEdit = isAdmin || statusOpen;

  useEffect(() => {
    if (!assessmentId || !classId || !subjectId) return;
    setLoading(true); setError(null); setMessage(null);
    fetchRosterForClass(assessmentId, subjectId, classId)
      .then((data) => {
        setRoster(data);
        const next: Record<string, RowState> = {};
        for (const r of data) {
          next[r.student_id] = {
            raw_mark: r.raw_mark === null ? "" : String(r.raw_mark),
            status: r.status === "MISSING" ? "MISSING" : r.status,
            dirty: false,
          };
        }
        setRows(next);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Roster failed"))
      .finally(() => setLoading(false));
  }, [assessmentId, classId, subjectId]);

  const activeMax = currentAssessment?.max_mark ?? editableMax;
  const maxChanged = editableMax !== activeMax;

  async function saveMaxMark() {
    if (!assessmentId || !currentAssessment || !canEdit) return;
    if (editableMax === currentAssessment.max_mark) return;
    if (!Number.isFinite(editableMax) || editableMax < 1 || editableMax > 1000) {
      setError("Total marks must be between 1 and 1000");
      return;
    }
    setSavingMax(true); setError(null); setMessage(null);
    try {
      await updateAssessment(assessmentId, { max_mark: editableMax });
      const fresh = await listAssessments();
      setAssessments(fresh);
      setMaxSaved(true);
      setMessage(`Total marks updated to ${editableMax}.`);
      window.setTimeout(() => setMaxSaved(false), 1800);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update total marks");
    } finally { setSavingMax(false); }
  }

  function setCell(studentId: string, patch: Partial<RowState>) {
    if (!canEdit) return;
    setRows((prev) => ({
      ...prev,
      [studentId]: { ...prev[studentId], ...patch, dirty: true },
    }));
  }

  function handleKey(studentId: string, e: React.KeyboardEvent<HTMLInputElement>, index: number) {
    if (e.key === "Enter" || e.key === "ArrowDown") {
      e.preventDefault();
      const n = roster[index + 1]?.student_id;
      if (n) inputRefs.current[n]?.focus();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      const p = roster[index - 1]?.student_id;
      if (p) inputRefs.current[p]?.focus();
    }
  }

  function handlePaste(e: React.ClipboardEvent<HTMLInputElement>, index: number) {
    if (!canEdit) return;
    const text = e.clipboardData.getData("text");
    if (!text.includes("\n") && !text.includes("\t")) return;
    e.preventDefault();
    const lines = text.split(/\r?\n/).filter((l) => l.trim().length > 0);
    setRows((prev) => {
      const next = { ...prev };
      for (let i = 0; i < lines.length; i++) {
        const target = roster[index + i];
        if (!target) break;
        const v = lines[i].split(/\t/)[0].trim();
        const num = v === "" ? null : Number(v);
        next[target.student_id] = {
          raw_mark: num === null || Number.isNaN(num) ? "" : String(num),
          status: num === null ? "MISSING" : "VALID",
          dirty: true,
        };
      }
      return next;
    });
  }

  async function onSave() {
    if (!assessmentId || !subjectId || !canEdit) return;
    setSaving(true); setError(null); setMessage(null);
    try {
      const marks = roster.map((r) => {
        const cell = rows[r.student_id];
        const num = cell.raw_mark === "" ? null : Number(cell.raw_mark);
        const status = num === null ? (cell.status === "VALID" ? "MISSING" : cell.status) : cell.status;
        return {
          student_id: r.student_id,
          raw_mark: num !== null && !Number.isNaN(num) ? num : null,
          status,
        };
      });
      const res = await saveBulkMarks({ assessment: assessmentId, subject: subjectId, marks });
      setMessage(`Saved — ${res.created} created, ${res.updated} updated.`);
      setRows((prev) => {
        const n: Record<string, RowState> = {};
        for (const [k, v] of Object.entries(prev)) n[k] = { ...v, dirty: false };
        return n;
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally { setSaving(false); }
  }

  const entered = useMemo(
    () => roster.filter((r) => rows[r.student_id]?.raw_mark !== "").length,
    [roster, rows],
  );
  const dirty = useMemo(
    () => roster.filter((r) => rows[r.student_id]?.dirty).length,
    [roster, rows],
  );

  return (
    <div style={{ padding: "2rem", maxWidth: "1200px", margin: "0 auto" }}>
      <button type="button" onClick={() => navigate("/academics/assessments")} style={{
        display: "inline-flex", alignItems: "center", gap: "6px",
        background: "transparent", border: "none", color: BROWN2,
        fontWeight: 600, cursor: "pointer", marginBottom: "1rem",
      }}><ArrowLeft size={16} /> Back to assessments</button>

      <div style={{ display: "flex", alignItems: "center", gap: "14px", marginBottom: "1.5rem" }}>
        <div style={{
          width: "52px", height: "52px", borderRadius: "14px",
          background: `linear-gradient(135deg, ${SKY}, #0b5d8c)`,
          color: "#fff", display: "flex", alignItems: "center", justifyContent: "center",
          boxShadow: "0 6px 18px rgba(34,180,240,0.35)",
        }}><ClipboardEdit size={26} /></div>
        <div style={{ flex: 1 }}>
          <h1 style={{ margin: 0, fontSize: "1.7rem", color: "#1e2e40", fontWeight: 800 }}>Marks Entry</h1>
          <p style={{ margin: "2px 0 0", color: "#748095", fontSize: "0.9rem" }}>
            Pick a class and subject — the roster loads automatically.
          </p>
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
            {context.is_admin ? "Admin · full access" : (context.teacher_name ? `Teacher · ${context.teacher_name}` : "Teacher")}
          </div>
        )}
      </div>

      {/* Status banner */}
      {currentAssessment && (
        <div style={{
          display: "flex", alignItems: "center", gap: "12px",
          padding: "0.7rem 1rem", borderRadius: "10px",
          background: canEdit ? "#dcfce7" : "#fef3c7",
          color: canEdit ? "#166534" : "#92400e",
          border: `1px solid ${canEdit ? "#86efac" : "#fde68a"}`,
          marginBottom: "1rem",
          fontWeight: 600, fontSize: "0.88rem",
        }}>
          {canEdit
            ? <><CheckCircle2 size={16} /> {isAdmin ? "Admin override — editing permitted." : "Assessment is open for marks entry."}</>
            : <><Lock size={16} /> Marks entry is closed for this assessment ({STATUS_LABEL[currentAssessment.status] ?? currentAssessment.status}). Only an administrator can edit.</>}
        </div>
      )}

      <div style={{
        display: "grid", gridTemplateColumns: "1.6fr 1.6fr 1.6fr 1fr 1fr",
        gap: "12px", alignItems: "end", ...cardStyle, marginBottom: "1rem",
        opacity: canEdit ? 1 : 0.85,
      }}>
        <div>
          <label style={{ fontSize: "0.72rem", fontWeight: 700, color: "#748095", letterSpacing: "0.06em" }}>CLASS</label>
          <select value={classId} onChange={(e) => setClassId(e.target.value)}
            style={{ width: "100%", padding: "0.5rem 0.7rem", border: `1px solid ${SKY}`, borderRadius: "8px", fontWeight: 600, color: BROWN2 }}>
            {(context?.classes ?? []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>

        <div>
          <label style={{ fontSize: "0.72rem", fontWeight: 700, color: "#748095", letterSpacing: "0.06em" }}>SUBJECT</label>
          <select value={subjectId} onChange={(e) => setSubjectId(e.target.value)}
            disabled={subjects.length === 0}
            style={{ width: "100%", padding: "0.5rem 0.7rem", border: `1px solid ${SKY}`, borderRadius: "8px", fontWeight: 600, color: BROWN2 }}>
            {subjects.length === 0
              ? <option value="">— no subjects for this class —</option>
              : subjects.map((s) => <option key={s.id} value={s.id}>{s.name} ({s.code})</option>)}
          </select>
        </div>

        <div>
          <label style={{ fontSize: "0.72rem", fontWeight: 700, color: "#748095", letterSpacing: "0.06em" }}>ASSESSMENT</label>
          <select value={assessmentId} onChange={(e) => setAssessmentId(e.target.value)}
            style={{ width: "100%", padding: "0.5rem 0.7rem", border: `1px solid ${SKY}`, borderRadius: "8px", fontWeight: 600, color: BROWN2 }}>
            {assessments.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name} — {STATUS_LABEL[a.status] ?? a.status}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label style={{ fontSize: "0.72rem", fontWeight: 700, color: "#748095", letterSpacing: "0.06em" }}>TOTAL</label>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <div style={{ position: "relative", flex: 1 }}>
              <Hash size={13} style={{ position: "absolute", left: "8px", top: "50%", transform: "translateY(-50%)", color: "#94a3b8" }} />
              <input type="number" min={1} max={1000}
                value={editableMax}
                disabled={!canEdit}
                onChange={(e) => setEditableMax(Number(e.target.value))}
                onBlur={saveMaxMark}
                onKeyDown={(e) => { if (e.key === "Enter") saveMaxMark(); }}
                style={{
                  width: "100%", padding: "0.5rem 0.5rem 0.5rem 26px",
                  border: maxChanged ? `1px solid ${SKY}` : "1px solid #cbd5e1",
                  borderRadius: "8px", fontWeight: 700, color: BROWN2,
                  background: !canEdit ? "#f1f5f9" : (maxChanged ? "#f0f9ff" : "#fff"),
                  cursor: !canEdit ? "not-allowed" : "text",
                }} />
            </div>
            <button type="button" onClick={saveMaxMark} disabled={!canEdit || !maxChanged || savingMax}
              style={{
                display: "inline-flex", alignItems: "center", gap: "4px",
                background: maxSaved ? "#10b981" : (maxChanged && canEdit ? SKY : "#cbd5e1"),
                color: "#fff", border: "none", padding: "0.5rem 0.7rem",
                borderRadius: "8px", fontWeight: 700, fontSize: "0.78rem",
                cursor: !canEdit || !maxChanged || savingMax ? "not-allowed" : "pointer",
              }}>
              {maxSaved ? <><CheckCircle2 size={13} /> Saved</> : savingMax ? "…" : "Set"}
            </button>
          </div>
        </div>

        <button type="button" onClick={onSave} disabled={saving || dirty === 0 || !canEdit}
          style={{
            display: "inline-flex", alignItems: "center", gap: "6px",
            background: (dirty === 0 || !canEdit) ? "#cbd5e1" : SKY,
            color: "#fff", border: "none",
            padding: "0.6rem 1.1rem", borderRadius: "10px",
            cursor: (dirty === 0 || !canEdit) ? "not-allowed" : "pointer",
            fontWeight: 700, fontSize: "0.85rem",
          }}>
          <Save size={16} /> {saving ? "Saving…" : `Save${dirty ? ` (${dirty})` : ""}`}
        </button>
      </div>

      {(currentClass || currentSubject) && (
        <div style={{
          display: "flex", alignItems: "center", gap: "14px",
          marginBottom: "1rem", color: "#748095", fontSize: "0.85rem",
          padding: "0.6rem 1rem", background: "#f8fafc",
          borderRadius: "10px", border: "1px solid #e5e7eb",
        }}>
          <Users size={16} />
          <span>{entered} of {roster.length} entered</span>
          <span style={{ color: "#cbd5e1" }}>•</span>
          <span>Total: <strong style={{ color: BROWN2 }}>{activeMax}</strong> marks</span>
          {currentClass && (<><span style={{ color: "#cbd5e1" }}>•</span><span>Class: <strong style={{ color: BROWN2 }}>{currentClass.name}</strong></span></>)}
          {currentSubject && (<><span style={{ color: "#cbd5e1" }}>•</span><span>Subject: <strong style={{ color: BROWN2 }}>{currentSubject.name}</strong></span></>)}
          {maxChanged && (<><span style={{ color: "#cbd5e1" }}>•</span><span style={{ color: SKY, fontWeight: 600 }}>Pending change → {editableMax} (Set)</span></>)}
        </div>
      )}

      {error && <div style={{ padding: "0.7rem 1rem", borderRadius: "10px", background: "#fee2e2", color: "#991b1b", marginBottom: "1rem", display: "flex", gap: "8px", alignItems: "center" }}><AlertCircle size={16} /> {error}</div>}
      {message && <div style={{ padding: "0.7rem 1rem", borderRadius: "10px", background: "#dcfce7", color: "#166534", marginBottom: "1rem" }}>{message}</div>}

      {loading ? (
        <div style={{ padding: "3rem", textAlign: "center", color: "#94a3b8" }}>Loading roster…</div>
      ) : roster.length === 0 ? (
        <div style={{ padding: "2rem", textAlign: "center", color: "#94a3b8" }}>
          {classId ? "No students found for this class." : "Pick a class to begin."}
        </div>
      ) : (
        <div style={{ ...cardStyle, padding: 0, overflow: "hidden" }}>
          <div style={{ overflowX: "auto", maxHeight: "70vh", overflowY: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.88rem" }}>
              <thead>
                <tr style={{ background: `linear-gradient(135deg, ${BROWN}, ${BROWN2})`, color: CREAM, position: "sticky", top: 0 }}>
                  <th style={{ textAlign: "left", padding: "0.7rem 1rem", width: "140px" }}>Adm No</th>
                  <th style={{ textAlign: "left", padding: "0.7rem 1rem" }}>Name</th>
                  <th style={{ textAlign: "right", padding: "0.7rem 1rem", width: "130px" }}>Mark / {activeMax}</th>
                  <th style={{ textAlign: "center", padding: "0.7rem 1rem", width: "160px" }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {roster.map((r, idx) => {
                  const cell = rows[r.student_id] ?? { raw_mark: "", status: "MISSING", dirty: false };
                  const num = cell.raw_mark === "" ? null : Number(cell.raw_mark);
                  const invalid = num !== null && (Number.isNaN(num) || num < 0 || num > activeMax);
                  return (
                    <tr key={r.student_id} style={{ borderTop: "1px solid #f1f5f9", background: cell.dirty ? "#f0f9ff" : "transparent" }}>
                      <td style={{ padding: "0.45rem 1rem", color: BROWN2, fontWeight: 600 }}>{r.admission_number}</td>
                      <td style={{ padding: "0.45rem 1rem" }}>{r.name}</td>
                      <td style={{ padding: "0.45rem 1rem", textAlign: "right" }}>
                        <input
                          ref={(el) => { inputRefs.current[r.student_id] = el; }}
                          value={cell.raw_mark}
                          disabled={!canEdit}
                          onChange={(e) => setCell(r.student_id, { raw_mark: e.target.value, status: e.target.value === "" ? "MISSING" : "VALID" })}
                          onKeyDown={(e) => handleKey(r.student_id, e, idx)}
                          onPaste={(e) => handlePaste(e, idx)}
                          type="number" step="0.5" min={0} max={activeMax}
                          style={{
                            width: "90px", padding: "5px 8px", textAlign: "right",
                            border: invalid ? "1px solid #ef4444" : "1px solid #cbd5e1",
                            borderRadius: "6px", fontWeight: 600,
                            background: !canEdit ? "#f1f5f9" : (invalid ? "#fef2f2" : "#fff"),
                            cursor: !canEdit ? "not-allowed" : "text",
                          }}
                        />
                      </td>
                      <td style={{ padding: "0.45rem 1rem", textAlign: "center" }}>
                        <select value={cell.status} disabled={!canEdit}
                          onChange={(e) => setCell(r.student_id, { status: e.target.value })}
                          style={{
                            padding: "4px 6px", border: "1px solid #cbd5e1",
                            borderRadius: "6px", fontSize: "0.8rem",
                            background: !canEdit ? "#f1f5f9" : "#fff",
                            cursor: !canEdit ? "not-allowed" : "pointer",
                          }}>
                          <option value="VALID">VALID</option>
                          <option value="MISSING">MISSING</option>
                          <option value="ABSENT">ABSENT</option>
                          <option value="EXEMPT">EXEMPT</option>
                          <option value="NOT_ASSESSED">NOT ASSESSED</option>
                        </select>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}