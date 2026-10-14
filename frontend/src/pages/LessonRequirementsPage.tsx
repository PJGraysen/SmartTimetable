import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AlertCircle, CheckCircle2, Copy, Loader2, RefreshCw, XCircle,
} from "lucide-react";
import { useToast } from "../components/Toast";
import {
  copyLessonRequirements,
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
