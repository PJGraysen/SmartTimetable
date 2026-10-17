import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle, CheckCircle2, Copy, Loader2, RefreshCw, XCircle,
} from "lucide-react";
import { useToast } from "../components/Toast";
import {
  copyLessonRequirements,
  fetchRuleConfig,
  fetchInstructionalGroups,
  fetchLessonRequirements,
  fetchSubjects,
  fetchTerms,
  patchLessonRequirement,
  validateTerm,
  type InstructionalGroup,
  type LessonRequirement,
  type RequirementType,
  type Subject,
  applyProposal,
  patchRuleConfig,
  runPreflight,
  type PreflightResult,
  type RuleConfig,
  type Term,
  type ValidationReport,
} from "../services/lessonRequirements";
import "./LessonRequirementsPage.css";

const TYPE_ORDER: RequirementType[] = ["STANDALONE", "BLOCK", "PRACTICAL"];

type CellSum = {
  total: number;
  types: Set<RequirementType>;
  lrs: LessonRequirement[];
};

export default function LessonRequirementsPage() {
  const toast = useToast();
  const [terms, setTerms] = useState<Term[]>([]);
  const [termId, setTermId] = useState<string>("");
  const [groups, setGroups] = useState<InstructionalGroup[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [lrs, setLrs] = useState<LessonRequirement[]>([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState<string>("");
  const [report, setReport] = useState<ValidationReport | null>(null);
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null);
  const [edits, setEdits] = useState<Record<string, number>>({});
  const [error, setError] = useState<string>("");
  const [ruleConfig, setRuleConfig] = useState<RuleConfig | null>(null);
  const [preflight, setPreflight] = useState<PreflightResult | null>(null);
  const [preflightLoading, setPreflightLoading] = useState(false);

  // -------------------------------------------------------------------
  // Load terms, groups, subjects on mount
  // -------------------------------------------------------------------
  useEffect(() => {
    (async () => {
      try {
        const [t, g, s] = await Promise.all([
          fetchTerms(),
          fetchInstructionalGroups(),
          fetchSubjects(),
        ]);
        setTerms(t);
        setGroups(g.filter((x) => (x.code || "").length > 0));
        setSubjects(s);
        const active = t.find((x) => x.name.toLowerCase().includes("term 1")) ?? t[0];
        if (active) setTermId(active.id);
      } catch (e) {
        setError("Failed to load reference data.");
      }
    })();
  }, []);

  // -------------------------------------------------------------------
  // Load LRs whenever the term changes
  // -------------------------------------------------------------------
  const loadLrs = useCallback(async () => {
    if (!termId) return;
    setLoading(true);
    setError("");
    try {
      const data = await fetchLessonRequirements(termId);
      setLrs(data);
      setEdits({});
      setReport(null);
    } catch (e) {
      setError("Failed to load lesson requirements.");
    } finally {
      setLoading(false);
    }
  }, [termId]);

  useEffect(() => { void loadLrs(); }, [loadLrs]);

  useEffect(() => {
    if (!termId) {
      setRuleConfig(null);
      setPreflight(null);
      return;
    }
    let cancelled = false;
    (async () => {
      setPreflightLoading(true);
      try {
        const [cfg, pf] = await Promise.all([
          fetchRuleConfig(termId),
          runPreflight(termId),
        ]);
        if (!cancelled) {
          setRuleConfig(cfg);
          setPreflight(pf);
        }
      } catch {
        if (!cancelled) {
          setRuleConfig(null);
          setPreflight(null);
        }
      } finally {
        if (!cancelled) setPreflightLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [termId]);

  // -------------------------------------------------------------------
  // Build (group, subject) -> CellSum
  // -------------------------------------------------------------------
  const cellMap = useMemo(() => {
    const m = new Map<string, CellSum>();
    for (const lr of lrs) {
      if (!lr.instructional_group) continue;
      const g = groups.find((x) => x.id === lr.instructional_group);
      const s = subjects.find((x) => x.id === lr.subject);
      if (!g || !s) continue;
      const key = `${g.code}::${s.code}`;
      const cur = m.get(key) ?? { total: 0, types: new Set(), lrs: [] };
      if (lr.is_active) cur.total += lr.lessons_per_week;
      cur.types.add(lr.requirement_type);
      cur.lrs.push(lr);
      m.set(key, cur);
    }
    return m;
  }, [lrs, groups, subjects]);

  // -------------------------------------------------------------------
  // Sorted display order
  // -------------------------------------------------------------------
  const activeGroups = useMemo(
    () => groups.slice().sort((a, b) => a.code.localeCompare(b.code)),
    [groups],
  );
  const activeSubjects = useMemo(
    () => subjects.slice().sort((a, b) => a.code.localeCompare(b.code)),
    [subjects],
  );

  // -------------------------------------------------------------------
  // Row selection + side panel LRs
  // -------------------------------------------------------------------
  const panelLrs = useMemo(() => {
    if (!selectedGroup) return [];
    return lrs
      .filter((lr) => {
        const g = groups.find((x) => x.id === lr.instructional_group);
        return g?.code === selectedGroup;
      })
      .sort((a, b) => {
        const sa = subjects.find((x) => x.id === a.subject)?.code ?? "";
        const sb = subjects.find((x) => x.id === b.subject)?.code ?? "";
        if (sa !== sb) return sa.localeCompare(sb);
        return TYPE_ORDER.indexOf(a.requirement_type) - TYPE_ORDER.indexOf(b.requirement_type);
      });
  }, [selectedGroup, lrs, groups, subjects]);

  // -------------------------------------------------------------------
  const toggleRule = async (key: keyof RuleConfig) => {
    if (!ruleConfig || !termId) return;
    const next = !ruleConfig[key];
    // eslint-disable-next-line no-console
    console.log("[rule-config] toggling", key, "->", next);
    setRuleConfig({ ...ruleConfig, [key]: next } as RuleConfig);
    try {
      const updated = await patchRuleConfig(
        termId,
        { [key]: next } as Partial<RuleConfig>,
      );
      // eslint-disable-next-line no-console
      console.log("[rule-config] server responded with", updated);
      setRuleConfig(updated);
      setPreflightLoading(true);
      const pf = await runPreflight(termId);
      setPreflight(pf);
    } catch {
      toast?.push?.({ type: "error", title: "Rule update failed" });
    } finally {
      setPreflightLoading(false);
    }
  };

  const refetchPreflight = async () => {
    if (!termId) return;
    setPreflightLoading(true);
    try {
      const pf = await runPreflight(termId);
      setPreflight(pf);
    } finally {
      setPreflightLoading(false);
    }
  };

  const applyOneProposal = async (proposalId: string) => {
    if (!termId) return;
    setBusy(`apply:${proposalId}`);
    try {
      const updated = await applyProposal(termId, proposalId);
      setPreflight(updated);
      toast?.push?.({
        type: "success",
        title: "Proposal applied",
      });
      await loadLrs();
    } catch (e: any) {
      const msg =
        e?.response?.data?.detail ||
        (e instanceof Error ? e.message : "Apply failed");
      toast?.push?.({ type: "error", title: "Apply failed", message: msg });
    } finally {
      setBusy("");
    }
  };

  // Save all pending edits
  // -------------------------------------------------------------------
  const dirtyCount = Object.keys(edits).length;

  const saveEdits = async () => {
    if (dirtyCount === 0) return;
    setBusy("save");
    try {
      await Promise.all(
        Object.entries(edits).map(([id, value]) =>
          patchLessonRequirement(id, { lessons_per_week: value }),
        ),
      );
      toast?.push?.({ type: "success", title: `Saved ${dirtyCount} change(s)` });
      await loadLrs();
    } catch (e) {
      toast?.push?.({ type: "error", title: "Save failed" });
    } finally {
      setBusy("");
    }
  };

  // -------------------------------------------------------------------
  // Validate
  // -------------------------------------------------------------------
  const runValidate = async () => {
    if (!termId) return;
    setBusy("validate");
    try {
      const r = await validateTerm(termId);
      setReport(r);
    } catch (e) {
      toast?.push?.({ type: "error", title: "Validation failed" });
    } finally {
      setBusy("");
    }
  };

  // -------------------------------------------------------------------
  // Copy from another term
  // -------------------------------------------------------------------
  const copyFrom = async (sourceId: string) => {
    if (!termId || sourceId === termId) return;
    setBusy("copy");
    try {
      const r = await copyLessonRequirements(sourceId, termId, true);
      toast?.push?.({
        type: "success",
        title: `Copied: ${r.created ?? 0} created, ${r.updated ?? 0} updated`,
      });
      await loadLrs();
    } catch (e) {
      toast?.push?.({ type: "error", title: "Copy failed" });
    } finally {
      setBusy("");
    }
  };

  return (
    <div className="lr-page">
      <div className="lr-header">
        <h1>Lesson Requirements</h1>
        <a href="/scheduling" className="lr-btn" style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '6px', background: '#22b4f0', color: '#fff', borderColor: '#22b4f0' }}>
          <RefreshCw size={14} /> Go to Scheduling
        </a>
        <div className="lr-controls">
          <select
            className="lr-select"
            value={termId}
            onChange={(e) => { setTermId(e.target.value); setSelectedGroup(null); }}
            disabled={terms.length === 0}
          >
            {terms.map((t) => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>
          <button className="lr-btn" onClick={() => void loadLrs()} disabled={loading}>
            {loading ? <Loader2 size={14} className="spin" /> : <RefreshCw size={14} />}
            Reload
          </button>
          <button className="lr-btn" onClick={() => void runValidate()} disabled={!!busy}>
            {busy === "validate" ? <Loader2 size={14} className="spin" /> : <CheckCircle2 size={14} />}
            Validate
          </button>
          {dirtyCount > 0 && (
            <button
              className="lr-btn lr-btn-primary"
              onClick={() => void saveEdits()}
              disabled={busy === "save"}
            >
              {busy === "save" ? <Loader2 size={14} className="spin" /> : <CheckCircle2 size={14} />}
              Save {dirtyCount}
            </button>
          )}
          {terms.length > 1 && (
            <select
              className="lr-select"
              value=""
              onChange={(e) => e.target.value && void copyFrom(e.target.value)}
              disabled={!!busy}
            >
              <option value="">Copy from…</option>
              {terms.filter((t) => t.id !== termId).map((t) => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          )}
        </div>
      </div>

      {ruleConfig && (
        <div className="lr-rules-panel" style={{
          marginBottom: "0.75rem",
          padding: "0.75rem 1rem",
          border: "1px solid #e5e7eb",
          borderRadius: "10px",
          background: "#fff",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
            <strong style={{ fontSize: "0.9rem" }}>Generation Rules</strong>
            <button
              type="button"
              className="lr-btn"
              style={{ marginLeft: "auto" }}
              onClick={() => void refetchPreflight()}
              disabled={preflightLoading}
            >
              {preflightLoading ? <Loader2 size={14} className="spin" /> : <CheckCircle2 size={14} />}
              Re-check
            </button>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.35rem 1rem", marginBottom: "0.5rem" }}>
            {([
              ["cross_stream_practicals_enabled", "Cross-stream practicals (hard)"],
              ["block_sync_enabled", "Block synchronization (hard)"],
              ["complex_adjacency_enabled", "Complex-subject adjacency (hard)"],
              ["eng_grade10_sync_enabled", "ENG-10E/10W sync (hard)"],
              ["single_lesson_per_day_enabled", "Single lesson per day (hard)"],
              ["practical_double_lesson_enabled", "Practical double-lesson (hard)"],
              ["teacher_free_afternoon_enabled", "Teacher free afternoon (hard)"],
              ["teacher_max_consecutive_enabled", "Teacher max-consecutive (soft)"],
            ] as Array<[keyof RuleConfig, string]>).map(([key, label]) => {
              const on = Boolean(ruleConfig[key]);
              return (
                <label key={String(key)} style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.85rem" }}>
                  <input
                    type="checkbox"
                    checked={on}
                    onChange={() => void toggleRule(key)}
                  />
                  {label}
                </label>
              );
            })}
          </div>
          {(() => {
            // Only HARD rules being off is a warning. Soft rules
            // (e.g. teacher max-consecutive) are preferences that the
            // solver minimizes rather than enforces; leaving them off
            // is a deliberate operational choice, not a risk.
            const hardOff: string[] = [];
            if (!ruleConfig.cross_stream_practicals_enabled) hardOff.push("Cross-stream practicals");
            if (!ruleConfig.block_sync_enabled) hardOff.push("Block synchronization");
            if (!ruleConfig.complex_adjacency_enabled) hardOff.push("Complex-subject adjacency");
            if (!ruleConfig.eng_grade10_sync_enabled) hardOff.push("ENG-10E/10W sync");
            if (!ruleConfig.single_lesson_per_day_enabled) hardOff.push("Single lesson per day");
            if (!ruleConfig.practical_double_lesson_enabled) hardOff.push("Practical double-lesson");
            if (!ruleConfig.teacher_free_afternoon_enabled) hardOff.push("Teacher free afternoon");
            if (hardOff.length === 0) return null;
            return (
              <div style={{
                padding: "0.5rem 0.75rem",
                borderRadius: "8px",
                fontSize: "0.85rem",
                background: "#fffbeb",
                border: "1px solid #fde68a",
                color: "#92400e",
                marginBottom: "0.5rem",
              }}>
                <b>Hard rules off:</b> {hardOff.join(", ")}. The solver may produce a timetable that violates these. Re-enable before generating for a strict schedule.
              </div>
            );
          })()}
          {preflight && (
            <div style={{
              padding: "0.5rem 0.75rem",
              borderRadius: "8px",
              fontSize: "0.85rem",
              background: preflight.clean ? "#ecfdf5" : "#fef2f2",
              border: preflight.clean ? "1px solid #86efac" : "1px solid #fecaca",
            }}>
              {preflight.clean ? (
                <span style={{ color: "#047857", fontWeight: 700 }}>
                  Ready to generate - no provable conflicts detected.
                </span>
              ) : (
                <div>
                  <div style={{ color: "#b91c1c", fontWeight: 700, marginBottom: "0.35rem" }}>
                    Pre-flight detected {preflight.diagnostics.length} conflict(s). Generation would fail.
                  </div>
                  {(() => {
                    const severityStyle = (sev?: string) => {
                      if (sev === "critical") return { bg: "#fef2f2", bd: "#fecaca" };
                      if (sev === "warning") return { bg: "#fffbeb", bd: "#fde68a" };
                      return { bg: "#eff6ff", bd: "#bfdbfe" };
                    };
                    const ProposalCard = ({ p }: { p: any }) => {
                      const busyKey = `apply:${p.id}`;
                      const isBusy = busy === busyKey;
                      const s = severityStyle(p.severity);
                      return (
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "0.5rem",
                            padding: "0.4rem 0.6rem",
                            background: s.bg,
                            border: `1px solid ${s.bd}`,
                            borderRadius: "6px",
                            marginBottom: "0.25rem",
                          }}
                        >
                          <div style={{ flex: 1, fontSize: "0.82rem" }}>
                            <div style={{ fontWeight: 600 }}>{p.description}</div>
                            <div style={{ color: "#6b7280", fontSize: "0.75rem" }}>{p.rationale}</div>
                          </div>
                          <button
                            type="button"
                            className="lr-btn lr-btn-primary"
                            disabled={isBusy}
                            onClick={() => void applyOneProposal(p.id)}
                          >
                            {isBusy ? <Loader2 size={12} className="spin" /> : <CheckCircle2 size={12} />}
                            Apply
                          </button>
                        </div>
                      );
                    };
                    return (
                      <>
                        {preflight.diagnostics.length > 0 && (
                          <ul style={{ margin: 0, paddingLeft: "1.1rem", color: "#7f1d1d", listStyle: "none" }}>
                            {preflight.diagnostics.map((d, i) => (
                              <li key={i} style={{ marginBottom: "0.6rem" }}>
                                <b>{d.rule}</b>: {d.message}{" "}
                                <div style={{ color: "#92400e", marginTop: "0.15rem" }}>
                                  What to do: {d.required_input}
                                </div>
                                {Array.isArray(d.proposals) && d.proposals.length > 0 && (
                                  <div style={{ marginTop: "0.4rem" }}>
                                    <div style={{ fontSize: "0.78rem", color: "#6b7280", marginBottom: "0.2rem" }}>
                                      Proposed fixes:
                                    </div>
                                    {d.proposals.map((p: any) => <ProposalCard key={p.id} p={p} />)}
                                  </div>
                                )}
                              </li>
                            ))}
                          </ul>
                        )}
                        {preflight.clean &&
                          Array.isArray(preflight.proposals) &&
                          preflight.proposals.length > 0 && (
                            <div style={{ marginTop: "0.4rem" }}>
                              <div style={{ fontSize: "0.78rem", color: "#6b7280", marginBottom: "0.3rem" }}>
                                Contract deviations (do not block generation):
                              </div>
                              {preflight.proposals.map((p: any) => (
                                <ProposalCard key={p.id} p={p} />
                              ))}
                            </div>
                          )}
                      </>
                    );
                  })()}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {error && (
        <div className="lr-error">
          <AlertCircle size={14} /> {error}
        </div>
      )}

      {report && (
        <div className="lr-status-wrap">
          <span className={`lr-status ${report.groups_ok ? "ok" : "bad"}`}>
            {report.groups_ok ? <CheckCircle2 size={12} /> : <XCircle size={12} />}
            {report.groups_ok
              ? `All groups match the ${report.term} contract`
              : `Mismatches in ${report.report.filter((r) => !r.ok).length} group(s)`}
          </span>
        </div>
      )}

      <div className="lr-matrix-wrap">
        <div className="lr-matrix">
          <table>
            <thead>
              <tr>
                <th>Group</th>
                {activeSubjects.map((s) => (
                  <th key={s.id} title={s.name}>{s.code}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {activeGroups.map((g) => (
                <tr
                  key={g.id}
                  className={selectedGroup === g.code ? "selected" : ""}
                  onClick={() => setSelectedGroup(g.code)}
                >
                  <td style={{ fontWeight: 700 }}>{g.code}</td>
                  {activeSubjects.map((s) => {
                    const cell = cellMap.get(`${g.code}::${s.code}`);
                    if (!cell || cell.lrs.length === 0) {
                      return <td key={s.id} className="lr-cell empty">–</td>;
                    }
                    const typeClass = cell.types.has("BLOCK") ? "block"
                      : cell.types.has("PRACTICAL") ? "practical" : "";
                    return (
                      <td key={s.id} className={`lr-cell ${typeClass}`}>
                        {cell.total || "–"}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="lr-panel">
          <h2>{selectedGroup ? `Group ${selectedGroup}` : "Select a group"}</h2>
          {!selectedGroup && (
            <div className="lr-panel-empty">
              Click any group row or matrix cell to edit its lesson requirements.
            </div>
          )}
          {selectedGroup && panelLrs.length === 0 && (
            <div className="lr-panel-empty">No lesson requirements yet for this group.</div>
          )}
          {selectedGroup && panelLrs.map((lr) => {
            const subj = subjects.find((x) => x.id === lr.subject);
            return (
              <div key={lr.id} className="lr-lr-row">
                <div className="lr-lr-name">
                  {subj?.code ?? lr.subject}
                  <span className="lr-lr-type">{lr.requirement_type}</span>
                </div>
                <input
                  className="lr-input"
                  type="number"
                  min={1}
                  value={edits[lr.id] ?? lr.lessons_per_week}
                  onChange={(e) => {
                    const v = parseInt(e.target.value, 10);
                    if (Number.isFinite(v) && v > 0) {
                      setEdits((prev) => ({ ...prev, [lr.id]: v }));
                    }
                  }}
                />
                <span style={{ fontSize: "0.7rem", color: lr.is_active ? "#047857" : "#94a3b8" }}>
                  {lr.is_active ? "active" : "off"}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {report && report.report.length > 0 && (
        <div className="lr-report">
          <h2>Validation — {report.term}</h2>
          <table>
            <thead>
              <tr>
                <th>Group</th>
                <th>Status</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {report.report.map((r) => (
                <tr key={r.group}>
                  <td style={{ fontWeight: 700 }}>{r.group}</td>
                  <td>
                    {r.ok
                      ? <span className="lr-status ok"><CheckCircle2 size={12} />OK</span>
                      : <span className="lr-status bad"><XCircle size={12} />Mismatch</span>}
                  </td>
                  <td>
                    {r.short.map((x) => (
                      <div key={`s-${x.subject}-${x.type}`}>
                        SHORT {x.subject} {x.type}: {x.have}/{x.want}
                      </div>
                    ))}
                    {r.over.map((x) => (
                      <div key={`o-${x.subject}-${x.type}`}>
                        OVER {x.subject} {x.type}: {x.have}/{x.want}
                      </div>
                    ))}
                    {r.extra.map((x) => (
                      <div key={`e-${x.subject}-${x.type}`}>
                        EXTRA {x.subject} {x.type}: {x.have}
                      </div>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
