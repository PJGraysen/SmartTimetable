import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft, Award, Hash, Plus, Save, Trash2, Trophy, Wand2,
} from "lucide-react";
import { listAssessments } from "../../services/assessments";
import { listTeachingGroups } from "../../services/analysis";
import {
  createRankingRule, deleteRankingRule, listRankingRules,
  previewRanking, updateRankingRule,
  type RankingResult, type RankingRule,
} from "../../services/ranking";

const BROWN = "#2b1a0f", BROWN2 = "#5a3a1e", SKY = "#22b4f0", CREAM = "#f5eee2";
const GRADE_COLOR: Record<string, string> = {
  A: "#10b981", B: "#22b4f0", C: "#f59e0b", D: "#f97316", E: "#ef4444", "-": "#94a3b8",
};
const METHODS = [
  { v: "MEAN_PCT", label: "Mean %" },
  { v: "TOTAL", label: "Total Marks" },
  { v: "MEAN_POINTS", label: "Mean Points" },
  { v: "SUBJECT_COMBO", label: "Subject Combination" },
];
const TIE_POLICIES = [
  { v: "COMPETITION", label: "Competition (1, 2, 2, 4)" },
  { v: "DENSE", label: "Dense (1, 2, 2, 3)" },
  { v: "ORDINAL", label: "Ordinal (1, 2, 3, 4)" },
];

const cardStyle: React.CSSProperties = {
  background: "#fff", border: "1px solid #e5e7eb", borderRadius: "14px",
  padding: "1.1rem 1.25rem", boxShadow: "0 4px 14px rgba(10,18,29,0.05)",
};

export default function RankingPage() {
  const navigate = useNavigate();
  const [rules, setRules] = useState<RankingRule[]>([]);
  const [ruleId, setRuleId] = useState<string>("");
  const [assessments, setAssessments] = useState<Array<{ id: string; name: string }>>([]);
  const [classes, setClasses] = useState<Array<{ id: string; name: string }>>([]);
  const [assessmentId, setAssessmentId] = useState<string>("");
  const [classId, setClassId] = useState<string>("");
  const [result, setResult] = useState<RankingResult | null>(null);
  const [running, setRunning] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [creating, setCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState<Partial<RankingRule>>({});
  const [newDraft, setNewDraft] = useState<Partial<RankingRule>>({
    name: "", method: "MEAN_PCT", tie_policy: "COMPETITION", subject_codes: [], min_subjects: 1, is_active: true,
  });

  async function loadRules() {
    const rows = await listRankingRules();
    setRules(rows);
    if (rows.length > 0 && !ruleId) setRuleId(rows[0].id);
  }

  useEffect(() => {
    Promise.all([loadRules(), listAssessments(), listTeachingGroups()])
      .then(([, a, c]) => {
        setAssessments(a);
        setClasses(c);
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function run(persist: boolean) {
    if (!ruleId) return;
    setRunning(true); setError(null); setMessage(null);
    try {
      const data = await previewRanking({
        rule: ruleId,
        assessment: assessmentId || undefined,
        teaching_group: classId || undefined,
        persist,
      });
      setResult(data);
      if (persist) setMessage(`Ranking saved (${data.count} students).`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ranking failed");
    } finally { setRunning(false); }
  }

  async function saveEdit() {
    if (!editingId) return;
    setSaving(true); setError(null);
    try {
      const updated = await updateRankingRule(editingId, draft);
      setRules((prev) => prev.map((r) => r.id === editingId ? updated : r));
      setEditingId(null); setDraft({});
      setMessage("Rule updated (version bumped).");
      setTimeout(() => setMessage(null), 2000);
    } catch (e) { setError(e instanceof Error ? e.message : "Save failed"); }
    finally { setSaving(false); }
  }

  async function createNew() {
    if (!newDraft.name?.trim()) return;
    setSaving(true); setError(null);
    try {
      const created = await createRankingRule(newDraft);
      setRules((prev) => [...prev, created]);
      setCreating(false);
      setNewDraft({ name: "", method: "MEAN_PCT", tie_policy: "COMPETITION", subject_codes: [], min_subjects: 1, is_active: true });
      setMessage("Rule created.");
      setTimeout(() => setMessage(null), 2000);
    } catch (e) { setError(e instanceof Error ? e.message : "Create failed"); }
    finally { setSaving(false); }
  }

  async function removeRule(id: string) {
    if (!confirm("Delete this rule? Historical runs will keep their snapshot.")) return;
    try {
      await deleteRankingRule(id);
      setRules((prev) => prev.filter((r) => r.id !== id));
      if (ruleId === id) setRuleId("");
    } catch (e) { setError(e instanceof Error ? e.message : "Delete failed"); }
  }

  const currentRule = useMemo(() => rules.find((r) => r.id === ruleId) ?? null, [rules, ruleId]);

  return (
    <div style={{ padding: "2rem", maxWidth: "1400px", margin: "0 auto" }}>
      <button type="button" onClick={() => navigate(-1)} style={{
        display: "inline-flex", alignItems: "center", gap: "6px",
        background: "transparent", border: "none", color: BROWN2,
        fontWeight: 600, cursor: "pointer", marginBottom: "1rem",
      }}><ArrowLeft size={16} /> Back</button>

      <div style={{ display: "flex", alignItems: "center", gap: "14px", marginBottom: "1.5rem" }}>
        <div style={{
          width: "52px", height: "52px", borderRadius: "14px",
          background: `linear-gradient(135deg, ${SKY}, #0b5d8c)`,
          color: "#fff", display: "flex", alignItems: "center", justifyContent: "center",
          boxShadow: "0 6px 18px rgba(34,180,240,0.35)",
        }}><Trophy size={26} /></div>
        <div>
          <h1 style={{ margin: 0, fontSize: "1.7rem", color: "#1e2e40", fontWeight: 800 }}>Ranking</h1>
          <p style={{ margin: "2px 0 0", color: "#748095", fontSize: "0.9rem" }}>
            Rule-based, configurable, versioned — every saved run records the exact rule used.
          </p>
        </div>
      </div>

      {error && <div style={{ padding: "0.7rem 1rem", borderRadius: "10px", background: "#fee2e2", color: "#991b1b", marginBottom: "1rem" }}>{error}</div>}
      {message && <div style={{ padding: "0.7rem 1rem", borderRadius: "10px", background: "#dcfce7", color: "#166534", marginBottom: "1rem" }}>{message}</div>}

      {/* Controls */}
      <div style={{ ...cardStyle, display: "grid", gridTemplateColumns: "1.3fr 1.3fr 1.3fr auto auto", gap: "10px", alignItems: "end", marginBottom: "1rem" }}>
        <div>
          <label style={{ fontSize: "0.72rem", fontWeight: 700, color: "#748095", letterSpacing: "0.06em" }}>RULE</label>
          <select value={ruleId} onChange={(e) => setRuleId(e.target.value)}
            style={{ width: "100%", padding: "0.5rem 0.7rem", border: `1px solid ${SKY}`, borderRadius: "8px", fontWeight: 600, color: BROWN2 }}>
            <option value="">— pick a rule —</option>
            {rules.map((r) => (
              <option key={r.id} value={r.id}>{r.name} · v{r.version}</option>
            ))}
          </select>
        </div>
        <div>
          <label style={{ fontSize: "0.72rem", fontWeight: 700, color: "#748095", letterSpacing: "0.06em" }}>ASSESSMENT</label>
          <select value={assessmentId} onChange={(e) => setAssessmentId(e.target.value)}
            style={{ width: "100%", padding: "0.5rem 0.7rem", border: "1px solid #cbd5e1", borderRadius: "8px", color: BROWN2 }}>
            <option value="">All assessments</option>
            {assessments.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
          </select>
        </div>
        <div>
          <label style={{ fontSize: "0.72rem", fontWeight: 700, color: "#748095", letterSpacing: "0.06em" }}>CLASS</label>
          <select value={classId} onChange={(e) => setClassId(e.target.value)}
            style={{ width: "100%", padding: "0.5rem 0.7rem", border: "1px solid #cbd5e1", borderRadius: "8px", color: BROWN2 }}>
            <option value="">Whole school</option>
            {classes.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
        </div>
        <button type="button" onClick={() => run(false)} disabled={running || !ruleId}
          style={{
            display: "inline-flex", alignItems: "center", gap: "6px",
            background: running || !ruleId ? "#cbd5e1" : "#5a3a1e", color: "#fff",
            border: "none", padding: "0.6rem 1.1rem", borderRadius: "10px",
            cursor: running || !ruleId ? "not-allowed" : "pointer",
            fontWeight: 700, fontSize: "0.85rem",
          }}>
          <Wand2 size={15} /> {running ? "…" : "Preview"}
        </button>
        <button type="button" onClick={() => run(true)} disabled={running || !ruleId}
          style={{
            display: "inline-flex", alignItems: "center", gap: "6px",
            background: running || !ruleId ? "#cbd5e1" : SKY, color: "#fff",
            border: "none", padding: "0.6rem 1.1rem", borderRadius: "10px",
            cursor: running || !ruleId ? "not-allowed" : "pointer",
            fontWeight: 700, fontSize: "0.85rem",
          }}>
          <Save size={15} /> Run & save
        </button>
      </div>

      {/* Rules manager */}
      <div style={{ ...cardStyle, marginBottom: "1rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.8rem" }}>
          <h3 style={{ margin: 0, color: BROWN2, fontSize: "0.95rem", fontWeight: 700, letterSpacing: "0.02em" }}>
            Rules ({rules.length})
          </h3>
          <button type="button" onClick={() => setCreating(true)}
            style={{
              display: "inline-flex", alignItems: "center", gap: "4px",
              background: SKY, color: "#fff", border: "none",
              padding: "5px 12px", borderRadius: "8px",
              cursor: "pointer", fontWeight: 700, fontSize: "0.8rem",
            }}><Plus size={13} /> New rule</button>
        </div>

        {creating && (
          <div style={{ background: "#f8fafc", border: `1px solid ${SKY}`, borderRadius: "10px", padding: "0.8rem", marginBottom: "0.8rem", display: "grid", gridTemplateColumns: "1.4fr 1fr 1.2fr 0.7fr auto auto", gap: "8px", alignItems: "end" }}>
            <div>
              <label style={{ fontSize: "0.68rem", fontWeight: 700, color: "#748095" }}>NAME</label>
              <input value={newDraft.name ?? ""} onChange={(e) => setNewDraft({ ...newDraft, name: e.target.value })}
                style={{ width: "100%", padding: "5px 8px", border: "1px solid #cbd5e1", borderRadius: "6px" }} />
            </div>
            <div>
              <label style={{ fontSize: "0.68rem", fontWeight: 700, color: "#748095" }}>METHOD</label>
              <select value={newDraft.method} onChange={(e) => setNewDraft({ ...newDraft, method: e.target.value as RankingRule["method"] })}
                style={{ width: "100%", padding: "5px 8px", border: "1px solid #cbd5e1", borderRadius: "6px" }}>
                {METHODS.map((m) => <option key={m.v} value={m.v}>{m.label}</option>)}
              </select>
            </div>
            <div>
              <label style={{ fontSize: "0.68rem", fontWeight: 700, color: "#748095" }}>TIE POLICY</label>
              <select value={newDraft.tie_policy} onChange={(e) => setNewDraft({ ...newDraft, tie_policy: e.target.value as RankingRule["tie_policy"] })}
                style={{ width: "100%", padding: "5px 8px", border: "1px solid #cbd5e1", borderRadius: "6px" }}>
                {TIE_POLICIES.map((t) => <option key={t.v} value={t.v}>{t.label}</option>)}
              </select>
            </div>
            <div>
              <label style={{ fontSize: "0.68rem", fontWeight: 700, color: "#748095" }}>MIN SUBJ</label>
              <input type="number" min={1} value={newDraft.min_subjects ?? 1}
                onChange={(e) => setNewDraft({ ...newDraft, min_subjects: Number(e.target.value) })}
                style={{ width: "100%", padding: "5px 8px", border: "1px solid #cbd5e1", borderRadius: "6px" }} />
            </div>
            <button type="button" onClick={createNew} disabled={saving}
              style={{ background: SKY, color: "#fff", border: "none", padding: "6px 14px", borderRadius: "6px", fontWeight: 700, cursor: "pointer", fontSize: "0.8rem" }}>Create</button>
            <button type="button" onClick={() => setCreating(false)}
              style={{ background: "#e5e7eb", color: "#374151", border: "none", padding: "6px 14px", borderRadius: "6px", fontWeight: 700, cursor: "pointer", fontSize: "0.8rem" }}>Cancel</button>
          </div>
        )}

        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
            <thead>
              <tr style={{ background: "#f8fafc", color: "#748095" }}>
                <th style={{ textAlign: "left", padding: "0.6rem 0.9rem" }}>Name</th>
                <th style={{ textAlign: "left", padding: "0.6rem 0.9rem" }}>Method</th>
                <th style={{ textAlign: "left", padding: "0.6rem 0.9rem" }}>Tie</th>
                <th style={{ textAlign: "right", padding: "0.6rem 0.9rem" }}>Min Subj</th>
                <th style={{ textAlign: "right", padding: "0.6rem 0.9rem" }}>Version</th>
                <th style={{ textAlign: "right", padding: "0.6rem 0.9rem" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rules.map((r) => {
                const isEdit = editingId === r.id;
                return (
                  <tr key={r.id} style={{ borderTop: "1px solid #f1f5f9" }}>
                    {isEdit ? (
                      <>
                        <td style={{ padding: "0.5rem 0.9rem" }}>
                          <input value={draft.name ?? r.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                            style={{ width: "100%", padding: "4px 6px", border: "1px solid #cbd5e1", borderRadius: "6px" }} />
                        </td>
                        <td style={{ padding: "0.5rem 0.9rem" }}>
                          <select value={draft.method ?? r.method} onChange={(e) => setDraft({ ...draft, method: e.target.value as RankingRule["method"] })}
                            style={{ padding: "4px 6px", border: "1px solid #cbd5e1", borderRadius: "6px" }}>
                            {METHODS.map((m) => <option key={m.v} value={m.v}>{m.label}</option>)}
                          </select>
                        </td>
                        <td style={{ padding: "0.5rem 0.9rem" }}>
                          <select value={draft.tie_policy ?? r.tie_policy} onChange={(e) => setDraft({ ...draft, tie_policy: e.target.value as RankingRule["tie_policy"] })}
                            style={{ padding: "4px 6px", border: "1px solid #cbd5e1", borderRadius: "6px" }}>
                            {TIE_POLICIES.map((t) => <option key={t.v} value={t.v}>{t.label}</option>)}
                          </select>
                        </td>
                        <td style={{ padding: "0.5rem 0.9rem", textAlign: "right" }}>
                          <input type="number" min={1} value={draft.min_subjects ?? r.min_subjects}
                            onChange={(e) => setDraft({ ...draft, min_subjects: Number(e.target.value) })}
                            style={{ width: "60px", padding: "4px 6px", border: "1px solid #cbd5e1", borderRadius: "6px", textAlign: "right" }} />
                        </td>
                        <td style={{ padding: "0.5rem 0.9rem", textAlign: "right", color: "#94a3b8" }}>v{r.version}</td>
                        <td style={{ padding: "0.5rem 0.9rem", textAlign: "right", whiteSpace: "nowrap" }}>
                          <button type="button" onClick={saveEdit} disabled={saving}
                            style={{ background: SKY, color: "#fff", border: "none", padding: "4px 10px", borderRadius: "6px", fontWeight: 600, cursor: "pointer", fontSize: "0.78rem", marginRight: "6px" }}>Save</button>
                          <button type="button" onClick={() => { setEditingId(null); setDraft({}); }}
                            style={{ background: "#e5e7eb", color: "#374151", border: "none", padding: "4px 10px", borderRadius: "6px", fontWeight: 600, cursor: "pointer", fontSize: "0.78rem" }}>Cancel</button>
                        </td>
                      </>
                    ) : (
                      <>
                        <td style={{ padding: "0.5rem 0.9rem", fontWeight: 600, color: "#1e2e40" }}>{r.name}</td>
                        <td style={{ padding: "0.5rem 0.9rem", color: "#475569" }}>{r.method}</td>
                        <td style={{ padding: "0.5rem 0.9rem", color: "#475569" }}>{r.tie_policy}</td>
                        <td style={{ padding: "0.5rem 0.9rem", textAlign: "right" }}>{r.min_subjects}</td>
                        <td style={{ padding: "0.5rem 0.9rem", textAlign: "right", color: "#94a3b8" }}>v{r.version}</td>
                        <td style={{ padding: "0.5rem 0.9rem", textAlign: "right", whiteSpace: "nowrap" }}>
                          <button type="button" onClick={() => { setEditingId(r.id); setDraft({}); }}
                            style={{ background: "transparent", border: "1px solid #94a3b8", color: "#475569", padding: "4px 10px", borderRadius: "6px", fontWeight: 600, cursor: "pointer", fontSize: "0.78rem", marginRight: "6px" }}>Edit</button>
                          <button type="button" onClick={() => removeRule(r.id)}
                            style={{ background: "transparent", border: "1px solid #ef4444", color: "#ef4444", padding: "4px 10px", borderRadius: "6px", fontWeight: 600, cursor: "pointer", fontSize: "0.78rem", display: "inline-flex", alignItems: "center", gap: "4px" }}>
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
      </div>

      {/* Result */}
      {result && (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem", marginBottom: "1rem" }}>
            <div style={cardStyle}>
              <div style={{ fontSize: "0.72rem", letterSpacing: "0.08em", textTransform: "uppercase", color: "#748095", fontWeight: 700 }}>Rule</div>
              <div style={{ fontSize: "1.05rem", fontWeight: 800, color: "#1e2e40", marginTop: "2px" }}>{result.rule.name}</div>
              <div style={{ fontSize: "0.78rem", color: "#94a3b8" }}>v{result.rule.version} · {result.rule.method} · {result.rule.tie_policy}</div>
            </div>
            <div style={cardStyle}>
              <div style={{ fontSize: "0.72rem", letterSpacing: "0.08em", textTransform: "uppercase", color: "#748095", fontWeight: 700 }}>Scope</div>
              <div style={{ fontSize: "1.05rem", fontWeight: 800, color: "#1e2e40", marginTop: "2px" }}>{result.scope_label}</div>
              <div style={{ fontSize: "0.78rem", color: "#94a3b8" }}>{result.count} students ranked</div>
            </div>
            <div style={cardStyle}>
              <div style={{ fontSize: "0.72rem", letterSpacing: "0.08em", textTransform: "uppercase", color: "#748095", fontWeight: 700 }}>Saved run</div>
              <div style={{ fontSize: "1.05rem", fontWeight: 800, color: result.run_id ? "#10b981" : "#94a3b8", marginTop: "2px" }}>
                {result.run_id ? "Yes" : "Preview only"}
              </div>
              <div style={{ fontSize: "0.78rem", color: "#94a3b8" }}>{result.run_id ? result.run_id.slice(0, 8) : "click Run & save to persist"}</div>
            </div>
          </div>

          <div style={{ ...cardStyle, padding: 0, overflow: "hidden" }}>
            <div style={{ padding: "1rem 1.25rem", borderBottom: "1px solid #eef2f7", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ margin: 0, color: BROWN2, fontSize: "0.95rem", fontWeight: 700, letterSpacing: "0.02em" }}>
                Ranked list
              </h3>
              <span style={{ fontSize: "0.78rem", color: "#748095" }}>
                Ties: {result.rule.tie_policy.toLowerCase()}
              </span>
            </div>
            <div style={{ overflowX: "auto", maxHeight: "60vh", overflowY: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.86rem" }}>
                <thead>
                  <tr style={{ background: `linear-gradient(135deg, ${BROWN}, ${BROWN2})`, color: CREAM, position: "sticky", top: 0 }}>
                    <th style={{ textAlign: "left", padding: "0.6rem 1rem", width: "70px" }}>Rank</th>
                    <th style={{ textAlign: "left", padding: "0.6rem 1rem", width: "120px" }}>Adm No</th>
                    <th style={{ textAlign: "left", padding: "0.6rem 1rem" }}>Name</th>
                    <th style={{ textAlign: "right", padding: "0.6rem 1rem" }}>Score</th>
                    <th style={{ textAlign: "right", padding: "0.6rem 1rem" }}>Mean %</th>
                    <th style={{ textAlign: "right", padding: "0.6rem 1rem" }}>Points</th>
                    <th style={{ textAlign: "center", padding: "0.6rem 1rem" }}>Subjects</th>
                    <th style={{ textAlign: "center", padding: "0.6rem 1rem" }}>Grade</th>
                    <th style={{ textAlign: "right", padding: "0.6rem 1rem" }}>%ile</th>
                  </tr>
                </thead>
                <tbody>
                  {result.entries.map((e) => {
                    const top3 = e.rank <= 3;
                    return (
                      <tr key={e.student_id} style={{ borderTop: "1px solid #f1f5f9", background: top3 ? "#f0f9ff" : "transparent" }}>
                        <td style={{ padding: "0.55rem 1rem", fontWeight: 800, color: top3 ? SKY : "#1e2e40" }}>#{e.rank}</td>
                        <td style={{ padding: "0.55rem 1rem", color: BROWN2, fontWeight: 600 }}>{e.admission_number}</td>
                        <td style={{ padding: "0.55rem 1rem" }}>{e.name}</td>
                        <td style={{ padding: "0.55rem 1rem", textAlign: "right", fontWeight: 700 }}>{e.score}</td>
                        <td style={{ padding: "0.55rem 1rem", textAlign: "right", color: "#475569" }}>{e.mean_pct}%</td>
                        <td style={{ padding: "0.55rem 1rem", textAlign: "right", color: "#475569" }}>{e.mean_points}</td>
                        <td style={{ padding: "0.55rem 1rem", textAlign: "center", color: "#94a3b8" }}>{e.subjects_count}</td>
                        <td style={{ padding: "0.55rem 1rem", textAlign: "center" }}>
                          <span style={{
                            padding: "2px 10px", borderRadius: "999px", fontSize: "0.75rem", fontWeight: 800,
                            background: (GRADE_COLOR[e.grade] ?? "#94a3b8") + "22",
                            color: GRADE_COLOR[e.grade] ?? "#64748b",
                          }}>{e.grade}</span>
                        </td>
                        <td style={{ padding: "0.55rem 1rem", textAlign: "right", color: "#748095", fontSize: "0.8rem" }}>{e.percentile}%</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}