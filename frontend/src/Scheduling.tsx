import { useEffect, useMemo, useState } from "react";
import {
  AlertCircle, AlertTriangle, CheckCircle2, ChevronDown, ChevronUp,
  Eye, EyeOff, Info, Loader2, Printer, RefreshCw, Rocket,
  ThumbsUp, X, XCircle, ZoomIn, ZoomOut,
} from "lucide-react";
import Timetable from "./pages/Timetable";
import { useToast } from "./components/Toast";
import { reportError } from "./services/errors";
import {
  approveSchedulingRun, createSchedulingRun, executeSchedulingRun,
  fetchSchedulingDashboard, fetchSchedulingRunResult,
  unapproveSchedulingRun,
  type ScheduleRunSummary, type SchedulingDashboard, pollRunUntilDone,
  discardSchedulingRun} from "./services/scheduling";
import "./styles/analysis.css";
import { GeneratingOverlay } from "./components/GeneratingOverlay";
import ScopePicker from "./components/ScopePicker";
import type { ScopePick } from "./services/scheduling";

const BROWN = "#2b1a0f", BROWN2 = "#5a3a1e", SKY = "#22b4f0", CREAM = "#f5eee2";
const GREEN = "#10b981", RED = "#ef4444", AMBER = "#f59e0b";

const cardStyle: React.CSSProperties = {
  background: "#fff", border: "1px solid #e5e7eb", borderRadius: "14px",
  padding: "1rem 1.15rem", boxShadow: "0 4px 14px rgba(10,18,29,0.05)",
};

type PrintFormat = "master" | "junior" | "senior" | "by-class" | "by-teacher";

const PRINT_FORMATS: Array<{ v: PrintFormat; label: string }> = [
  { v: "master", label: "Master (all classes)" },
  { v: "junior", label: "Junior (Grade 7-9)" },
  { v: "senior", label: "Senior (Grade 10-12 + Forms)" },
  { v: "by-class", label: "By Class (one page per class)" },
  { v: "by-teacher", label: "By Teacher (one page per teacher)" },
];

const printCSS = `
  @media print {
    @page { size: A3 landscape; margin: 3mm; }

    html, body {
      margin: 0 !important;
      padding: 0 !important;
      background: #fff !important;
      height: auto !important;
      max-height: none !important;
      overflow: visible !important;
      -webkit-print-color-adjust: exact !important;
      print-color-adjust: exact !important;
    }

    body * { visibility: hidden !important; }
    #tt-printable, #tt-printable * { visibility: visible !important; }

    #tt-printable {
      display: block !important;
      position: static !important;
      width: 100% !important;
      max-width: 100% !important;
      max-height: none !important;
      height: auto !important;
      overflow: visible !important;
      background: #fff !important;
      /* zoom ACTUALLY shrinks the layout, unlike transform: scale */
      zoom: 0.48 !important;
    }

    /* Reset the interactive transform (user zoom slider) */
    #tt-printable > div {
      transform: none !important;
      transition: none !important;
    }

    #tt-printable table {
      width: 100% !important;
      table-layout: fixed !important;
      font-size: 4.5pt !important;
      border-collapse: collapse !important;
    }
    #tt-printable th,
    #tt-printable td {
      padding: 0.1mm 0.3mm !important;
      font-size: 4.5pt !important;
      line-height: 0.95 !important;
      word-break: break-word !important;
      overflow: hidden !important;
    }

    /* Force every ancestor to not clip / scroll / fix height */
    html, body, #root,
    .app-shell, .main-area, .content,
    .ssp-page-transition, .scheduling-page {
      display: block !important;
      overflow: visible !important;
      max-height: none !important;
      height: auto !important;
      margin: 0 !important;
      padding: 0 !important;
      width: 100% !important;
      max-width: 100% !important;
    }
    .ssp-page-transition { animation: none !important; }
    #tt-printable tr { page-break-inside: avoid !important; }

    /* Print suite (format-specific) layouts */
    .print-page { page-break-after: always; break-after: page; }
    .print-page:last-child { page-break-after: auto; break-after: auto; }
    .print-page-title { display: block; font-size: 16pt; font-weight: 800; text-align: center; margin-bottom: 4mm; color: #2b1a0f; }
    .print-tbl { display: table; width: 100%; border-collapse: collapse; font-size: 8pt; }
    .print-tbl th, .print-tbl td { border: 1px solid #333; padding: 1.5mm 2mm; text-align: left; }
    .print-tbl th { background: #f0f0f0; }
  }

  .no-print { display: none !important; }
  .print-page-title { display: none; }
  .print-tbl { display: none; }
`;

function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

type Constraint = {
  id?: string;
  category: string;
  category_display: string;
  message: string;
  mitigation: string;
  details: Record<string, unknown>;
  is_resolved: boolean;
};
type Report = {
  run_id: string;
  status: string;
  approvable: boolean;
  reason_if_blocked: string | null;
  hard_constraints: Constraint[];
  soft_constraints: Constraint[];
  info: Constraint[];
  counts: { hard: number; hard_unresolved: number; soft: number; info: number };
};

type Entry = {
  id: string;
  day: string;
  day_display?: string;
  period_number?: number;
  period_name?: string;
  instructional_group_name?: string;
  subject_name?: string;
  subject_code?: string;
  teacher_name?: string;
  room_name?: string;
};

function ConstraintCard({
  c, tone, onToggle,
}: { c: Constraint; tone: "hard" | "soft" | "info"; onToggle?: (id: string, next: boolean) => void }) {
  const fg = tone === "hard" ? RED : tone === "soft" ? AMBER : "#1e40af";
  const bg = tone === "hard" ? "#fef2f2" : tone === "soft" ? "#fffbeb" : "#eff6ff";
  const border = tone === "hard" ? "#fecaca" : tone === "soft" ? "#fde68a" : "#bfdbfe";
  const Icon = tone === "hard" ? XCircle : tone === "soft" ? AlertTriangle : Info;

  return (
    <div style={{
      display: "flex", gap: "8px",
      padding: "0.55rem 0.75rem",
      background: c.is_resolved ? "#f0fdf4" : bg,
      border: `1px solid ${c.is_resolved ? "#86efac" : border}`,
      borderRadius: "8px", fontSize: "0.82rem",
      opacity: c.is_resolved ? 0.75 : 1,
    }}>
      <Icon size={16} color={c.is_resolved ? GREEN : fg} style={{ marginTop: "2px", flexShrink: 0 }} />
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 700, color: c.is_resolved ? "#166534" : fg, marginBottom: "2px", display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
          <span>{c.category_display}</span>
          {c.is_resolved && (
            <span style={{ fontSize: "0.68rem", background: "#dcfce7", color: "#166534", padding: "1px 7px", borderRadius: "999px", fontWeight: 800 }}>
              RESOLVED
            </span>
          )}
        </div>
        <div style={{ color: "#475569", marginBottom: "4px" }}>{c.message}</div>
        <div style={{
          fontSize: "0.76rem", fontStyle: "italic",
          background: "rgba(255,255,255,0.6)", padding: "4px 7px",
          borderRadius: "5px", color: "#64748b",
        }}>
          <strong style={{ fontStyle: "normal" }}>Mitigation:</strong> {c.mitigation}
        </div>
      </div>
      {onToggle && c.id && (
        <button type="button" onClick={() => onToggle(c.id!, !c.is_resolved)}
          style={{
            alignSelf: "flex-start",
            background: "transparent",
            border: `1px solid ${c.is_resolved ? AMBER : GREEN}`,
            color: c.is_resolved ? "#b45309" : "#166534",
            padding: "3px 9px", borderRadius: "6px",
            cursor: "pointer", fontSize: "0.72rem", fontWeight: 700,
            whiteSpace: "nowrap",
          }}>
          {c.is_resolved ? "Reopen" : "Mark resolved"}
        </button>
      )}
    </div>
  );
}

function ReportModal({
  runId, onClose, onChanged,
}: { runId: string; onClose: () => void; onChanged: () => void }) {
  const toast = useToast();
  const [report, setReport] = useState<Report | null>(null);
  const [entries, setEntries] = useState<Entry[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const [repRes, tt] = await Promise.all([
        fetch(`/api/scheduling/runs/${runId}/report/`, { credentials: "include" }).then((r) => r.json()),
        fetchSchedulingRunResult(runId).catch(() => null),
      ]);
      setReport(repRes);
      const list: Entry[] = Array.isArray((tt as { entries?: Entry[] })?.entries) ? (tt as { entries: Entry[] }).entries : [];
      setEntries(list);
    } catch (e) {
      toast.push({
        type: "error", title: "Could not load report",
        message: e instanceof Error ? e.message : String(e),
      });
    } finally { setLoading(false); }
  }

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [runId]);

  async function toggleResolve(validationId: string, next: boolean) {
    try {
      const res = await fetch(`/api/scheduling/runs/${runId}/validation/${validationId}/resolve/`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resolved: next }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      toast.push({ type: "success", title: next ? "Marked resolved" : "Reopened" });
      await load();
    } catch (e) {
      toast.push({ type: "error", title: "Action failed", message: e instanceof Error ? e.message : String(e) });
    }
  }

  async function handleApprove() {
    setBusy(true);
    try {
      await approveSchedulingRun(runId, "");
      toast.push({ type: "success", title: "Timetable approved", message: "Run approved and version published." });
      onChanged(); onClose();
    } catch (e: any) {
      const msg = e?.response?.data?.detail || (e instanceof Error ? e.message : String(e));
      toast.push({
        type: "error", title: "Approval blocked", message: msg,
        mitigation: e?.response?.data?.unresolved_hard_constraints
          ? "Resolve the hard-constraint violations shown below, then re-run generation."
          : undefined,
      });
      await reportError({ source: "scheduling", severity: "ERROR", code: "APPROVE_FAILED", message: String(msg), scheduling_run: runId });
    } finally { setBusy(false); }
  }

  async function handleUnapprove() {
    if (!confirm("Reopen this timetable? It will no longer be the active approved version.")) return;
    setBusy(true);
    try {
      await unapproveSchedulingRun(runId);
      toast.push({ type: "warning", title: "Timetable disapproved" });
      onChanged(); onClose();
    } catch (e: any) {
      toast.push({ type: "error", title: "Disapprove failed", message: e?.response?.data?.detail || String(e) });
    } finally { setBusy(false); }
  }

  return (
    <div className="no-print" onClick={(e) => e.target === e.currentTarget && onClose()}
      style={{
        position: "fixed", inset: 0, background: "rgba(10,18,29,0.55)",
        zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center", padding: "1rem",
      }}>
      <div style={{
        background: "#fff", borderRadius: "14px", maxWidth: "1100px", width: "100%",
        maxHeight: "92vh", overflow: "hidden", display: "flex", flexDirection: "column",
        boxShadow: "0 24px 60px rgba(10,18,29,0.4)",
      }}>
        <div style={{
          padding: "1rem 1.25rem", borderBottom: "1px solid #eef2f7",
          display: "flex", alignItems: "center", gap: "12px",
          background: `linear-gradient(135deg, ${BROWN}, ${BROWN2})`, color: CREAM,
        }}>
          <Eye size={20} />
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 800, fontSize: "1rem" }}>Timetable run review</div>
            <div style={{ fontSize: "0.78rem", opacity: 0.85 }}>Run {runId.slice(0, 8)}</div>
          </div>
          <button type="button" onClick={onClose} style={{ background: "transparent", border: "none", color: CREAM, cursor: "pointer", padding: 4 }}>
            <X size={20} />
          </button>
        </div>

        <div style={{ flex: 1, overflowY: "auto", padding: "1.1rem 1.25rem" }}>
          {loading ? (
            <div style={{ padding: "2rem", textAlign: "center", color: "#94a3b8" }}>
              <Loader2 size={22} className="spin" style={{ animation: "spin 1s linear infinite" }} />
              <div style={{ marginTop: "0.5rem" }}>Loading report…</div>
            </div>
          ) : !report ? (
            <div style={{ padding: "2rem", textAlign: "center", color: "#991b1b" }}>No report available.</div>
          ) : (
            <>
              <div style={{
                display: "flex", alignItems: "center", gap: "10px",
                padding: "0.75rem 1rem", borderRadius: "10px",
                background: report.approvable ? "#f0fdf4" : "#fef2f2",
                border: `1px solid ${report.approvable ? "#86efac" : "#fecaca"}`,
                color: report.approvable ? "#166534" : "#991b1b",
                fontWeight: 600, fontSize: "0.9rem", marginBottom: "1rem",
              }}>
                {report.approvable ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
                <div style={{ flex: 1 }}>
                  {report.approvable
                    ? "All hard constraints satisfied — ready for approval."
                    : report.reason_if_blocked || "Not approvable."}
                </div>
              </div>

              <div style={{ display: "grid", gap: "1rem", marginBottom: "1.25rem" }}>
                <div>
                  <div style={{ fontSize: "0.72rem", letterSpacing: "0.1em", textTransform: "uppercase", fontWeight: 800, color: RED, marginBottom: "0.4rem" }}>
                    Hard constraints · {report.hard_constraints.length}
                  </div>
                  {report.hard_constraints.length === 0 ? (
                    <div style={{
                      display: "flex", alignItems: "center", gap: "8px",
                      padding: "0.55rem 0.8rem", borderRadius: "8px",
                      background: "#f0fdf4", border: "1px solid #86efac",
                      color: "#166534", fontSize: "0.85rem", fontWeight: 600,
                    }}>
                      <CheckCircle2 size={16} /> All hard constraints satisfied
                    </div>
                  ) : (
                    <div style={{ display: "grid", gap: "0.5rem" }}>
                      {report.hard_constraints.map((c, i) => (
                        <ConstraintCard key={i} c={c} tone="hard" onToggle={toggleResolve} />
                      ))}
                    </div>
                  )}
                </div>

                <div>
                  <div style={{ fontSize: "0.72rem", letterSpacing: "0.1em", textTransform: "uppercase", fontWeight: 800, color: AMBER, marginBottom: "0.4rem" }}>
                    Soft constraints · {report.soft_constraints.length}
                  </div>
                  {report.soft_constraints.length === 0 ? (
                    <div style={{
                      display: "flex", alignItems: "center", gap: "8px",
                      padding: "0.55rem 0.8rem", borderRadius: "8px",
                      background: "#f0fdf4", border: "1px solid #86efac",
                      color: "#166534", fontSize: "0.85rem", fontWeight: 600,
                    }}>
                      <CheckCircle2 size={16} /> All soft constraints satisfied
                    </div>
                  ) : (
                    <div style={{ display: "grid", gap: "0.5rem" }}>
                      {report.soft_constraints.map((c, i) => (
                        <ConstraintCard key={i} c={c} tone="soft" onToggle={toggleResolve} />
                      ))}
                    </div>
                  )}
                </div>

                {report.info.length > 0 && (
                  <div>
                    <div style={{ fontSize: "0.72rem", letterSpacing: "0.1em", textTransform: "uppercase", fontWeight: 800, color: "#1e40af", marginBottom: "0.4rem" }}>
                      Information · {report.info.length}
                    </div>
                    <div style={{ display: "grid", gap: "0.5rem" }}>
                      {report.info.map((c, i) => <ConstraintCard key={i} c={c} tone="info" />)}
                    </div>
                  </div>
                )}
              </div>

              <div style={{ borderTop: "1px solid #eef2f7", paddingTop: "1rem" }}>
                <div style={{ fontSize: "0.72rem", letterSpacing: "0.1em", textTransform: "uppercase", fontWeight: 800, color: "#94a3b8", marginBottom: "0.5rem" }}>
                  Timetable entries · {entries.length}
                </div>
                {entries.length > 0 ? (
                  <div style={{ maxHeight: "280px", overflowY: "auto", border: "1px solid #e5e7eb", borderRadius: "8px" }}>
                    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.78rem" }}>
                      <thead>
                        <tr style={{ background: "#f8fafc", color: "#64748b", position: "sticky", top: 0 }}>
                          <th style={{ textAlign: "left", padding: "5px 8px" }}>Day</th>
                          <th style={{ textAlign: "left", padding: "5px 8px" }}>Period</th>
                          <th style={{ textAlign: "left", padding: "5px 8px" }}>Class</th>
                          <th style={{ textAlign: "left", padding: "5px 8px" }}>Subject</th>
                          <th style={{ textAlign: "left", padding: "5px 8px" }}>Teacher</th>
                          <th style={{ textAlign: "left", padding: "5px 8px" }}>Room</th>
                        </tr>
                      </thead>
                      <tbody>
                        {entries.slice(0, 300).map((e) => (
                          <tr key={e.id} style={{ borderTop: "1px solid #f1f5f9" }}>
                            <td style={{ padding: "4px 8px" }}>{e.day_display || e.day}</td>
                            <td style={{ padding: "4px 8px" }}>{e.period_name || e.period_number}</td>
                            <td style={{ padding: "4px 8px", fontWeight: 600, color: BROWN2 }}>{e.instructional_group_name}</td>
                            <td style={{ padding: "4px 8px" }}>{e.subject_name}</td>
                            <td style={{ padding: "4px 8px" }}>{e.teacher_name || "—"}</td>
                            <td style={{ padding: "4px 8px", color: "#94a3b8" }}>{e.room_name || "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div style={{ color: "#94a3b8", fontSize: "0.82rem" }}>No entries returned.</div>
                )}
              </div>
            </>
          )}
        </div>

        <div style={{
          padding: "0.9rem 1.25rem", borderTop: "1px solid #eef2f7",
          display: "flex", justifyContent: "flex-end", gap: "0.5rem", background: "#fafafa",
        }}>
          <button type="button" onClick={onClose} style={btnGhost}>Close</button>
          <button type="button" onClick={handleUnapprove} disabled={busy} style={btnOutline(AMBER, "#b45309")}>
            <EyeOff size={14} /> Disapprove
          </button>
          <button type="button" onClick={handleApprove} disabled={busy || !report?.approvable}
            style={{
              display: "inline-flex", alignItems: "center", gap: "5px",
              background: report?.approvable ? GREEN : "#cbd5e1",
              color: "#fff", border: "none",
              padding: "7px 14px", borderRadius: "8px",
              fontWeight: 700, fontSize: "0.85rem",
              cursor: !report?.approvable ? "not-allowed" : "pointer",
            }}>
            <ThumbsUp size={14} /> Approve
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================
// Print layouts
// ============================================================
function groupBy<T, K extends string>(rows: T[], keyFn: (r: T) => K): Record<K, T[]> {
  const out = {} as Record<K, T[]>;
  for (const r of rows) {
    const k = keyFn(r);
    if (!out[k]) out[k] = [];
    out[k].push(r);
  }
  return out;
}

function entriesToTable(rows: Entry[], showClass = true, showTeacher = true) {
  const sorted = [...rows].sort((a, b) => {
    const dayOrder = ["MON", "TUE", "WED", "THU", "FRI"];
    const dd = dayOrder.indexOf(a.day) - dayOrder.indexOf(b.day);
    if (dd !== 0) return dd;
    return (a.period_number ?? 0) - (b.period_number ?? 0);
  });
  return (
    <table className="print-tbl">
      <thead>
        <tr>
          <th>Day</th><th>Period</th>
          {showClass && <th>Class</th>}
          <th>Subject</th>
          {showTeacher && <th>Teacher</th>}
          <th>Room</th>
        </tr>
      </thead>
      <tbody>
        {sorted.map((e) => (
          <tr key={e.id}>
            <td>{e.day_display || e.day}</td>
            <td>{e.period_name || e.period_number}</td>
            {showClass && <td>{e.instructional_group_name}</td>}
            <td>{e.subject_name}</td>
            {showTeacher && <td>{e.teacher_name || "—"}</td>}
            <td>{e.room_name || "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function isJuniorClass(name: string | undefined): boolean {
  if (!name) return false;
  const n = name.toLowerCase();
  return n.includes("grade 7") || n.includes("grade 8") || n.includes("grade 9");
}
function isSeniorClass(name: string | undefined): boolean {
  if (!name) return false;
  const n = name.toLowerCase();
  return n.includes("grade 10") || n.includes("grade 11") || n.includes("grade 12")
    || n.includes("form 3") || n.includes("form 4");
}

function PrintSuite({ entries, format }: { entries: Entry[]; format: PrintFormat }) {
  if (entries.length === 0) return null;

  if (format === "master" || format === "junior" || format === "senior") {
    let filtered = entries;
    let title = "Master Timetable";
    if (format === "junior") {
      filtered = entries.filter((e) => isJuniorClass(e.instructional_group_name));
      title = "Junior School Timetable (Grade 7–9)";
    } else if (format === "senior") {
      filtered = entries.filter((e) => isSeniorClass(e.instructional_group_name));
      title = "Senior School Timetable (Grade 10–12 + Forms)";
    }
    return (
      <div className="print-page">
        <div className="print-page-title">{title}</div>
        {entriesToTable(filtered)}
      </div>
    );
  }

  if (format === "by-class") {
    const groups = groupBy(entries, (e) => e.instructional_group_name || "Unassigned");
    return (
      <>
        {Object.entries(groups).map(([cls, rows]) => (
          <div key={cls} className="print-page">
            <div className="print-page-title">{cls} — Timetable</div>
            {entriesToTable(rows, false, true)}
          </div>
        ))}
      </>
    );
  }

  // by-teacher
  const groups = groupBy(entries, (e) => e.teacher_name || "Unassigned");
  return (
    <>
      {Object.entries(groups).map(([teacher, rows]) => (
        <div key={teacher} className="print-page">
          <div className="print-page-title">{teacher} — Teaching Load</div>
          {entriesToTable(rows, true, false)}
        </div>
      ))}
    </>
  );
}

export default function Scheduling() {
  const toast = useToast();
  const [dashboard, setDashboard] = useState<SchedulingDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [genStatus, setGenStatus] = useState<string>("");
  const [currentTime, setCurrentTime] = useState(new Date());
  const [timetableRefreshKey, setTimetableRefreshKey] = useState(0);
  const [selectedTermId, setSelectedTermId] = useState("");
  const [scope, setScope] = useState<ScopePick | null>(null);
  const [baselineId, setBaselineId] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1.0);
  const [showAllRuns, setShowAllRuns] = useState(false);
  const [showAllFailed, setShowAllFailed] = useState(false);
  const [reportRunId, setReportRunId] = useState<string | null>(null);
  const [printFormat, setPrintFormat] = useState<PrintFormat>("master");
  const [activeEntries, setActiveEntries] = useState<Entry[]>([]);

  async function loadDashboard() {
    try {
      const d = await fetchSchedulingDashboard();
      setDashboard(d);
      if (!selectedTermId && d.active_term) setSelectedTermId(d.active_term.id);
      // Fetch entries for the active version (for print suite)
      if (d.active_version) {
        const latestRun = d.recent_runs[0];
        if (latestRun) {
          try {
            const tt: any = await fetchSchedulingRunResult(latestRun.id);
            if (Array.isArray(tt?.entries)) setActiveEntries(tt.entries);
          } catch { /* ignore */ }
        }
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      toast.push({
        type: "error", title: "Failed to load scheduling dashboard", message: msg,
        mitigation: "Check that the backend is running and the API is reachable.",
      });
      await reportError({ source: "scheduling", severity: "ERROR", code: "DASHBOARD_LOAD", message: msg });
    } finally { setLoading(false); }
  }

  useEffect(() => { loadDashboard(); /* eslint-disable-next-line */ }, []);

  useEffect(() => {
    const t = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);


  // Auto-resume polling for any run that's still RUNNING on mount
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const runs = await getSchedulingRuns();
        const arr = Array.isArray(runs) ? runs : [];
        const running = arr.find(
          (r) =>
            r.status === "RUNNING" ||
            r.status === "PENDING",
        );
        if (!running || cancelled) return;

        // eslint-disable-next-line no-console
        console.log("[Scheduling] resuming poll for run", running.id);
        setGenerating(true);
        setGenStatus("Resuming run " + running.id.slice(0, 8) + "...");

        const final = await pollRunUntilDone(running.id, {
          intervalMs: 4000,
          onTick: (_r, elapsedMs) => {
            const mins = Math.floor(elapsedMs / 60000);
            const secs = Math.floor((elapsedMs % 60000) / 1000);
            setGenStatus(
              "Solver running... " +
              (mins > 0 ? mins + "m " : "") + secs + "s",
            );
          },
        });
        if (cancelled) return;

        if (final.status === "COMPLETED") {
          toast.push({
            type: "success",
            title: "Generation complete",
            message: "Refreshing timetable...",
          });
        }
        await loadDashboard();
        setTimetableRefreshKey((k) => k + 1);
      } catch {
        /* ignore */
      } finally {
        if (!cancelled) {
          setGenerating(false);
          setGenStatus("");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line
  }, []);

  async function handleGenerate() {
    if (!selectedTermId) {
      toast.push({ type: "warning", title: "Pick a term first", message: "Select Term 1, 2, or 3 before generating." });
      return;
    }
    setGenerating(true);
    setGenStatus("Creating run...");
    try {
      const run = await createSchedulingRun(selectedTermId);

      // Fire-and-forget execute - the backend runs the solver in a worker
      // thread; we do NOT await its HTTP response.
      executeSchedulingRun(run.id, {
        scope_kind: scope?.kind ?? null,
        scope_id: scope?.id ?? null,
        baseline_version_id: baselineId,
      }).catch(() => {
        /* ignored - we poll for real status below */
      });

      setGenStatus("Solver running...");

      // Poll until terminal state
      const final = await pollRunUntilDone(run.id, {
        intervalMs: 4000,
        onTick: (_r, elapsedMs) => {
          const mins = Math.floor(elapsedMs / 60000);
          const secs = Math.floor((elapsedMs % 60000) / 1000);
          setGenStatus(
            "Solver running... " +
            (mins > 0 ? mins + "m " : "") +
            secs + "s",
          );
        },
      });

      if (final.status === "COMPLETED") {
        toast.push({
          type: "success",
          title: "Generation complete",
          message: "New timetable is ready.",
          ttlMs: 3000,
        });
        setReportRunId(run.id);

        // auto-navigate after scoped generate — Master stays on this page.
        const _s = scope;
        if (_s && _s.kind !== "master") {
          const slug =
            _s.kind === "grade" ? `grade-${_s.id}`
            : _s.kind === "subject" ? `subject-${_s.id}`
            : "master";
          window.setTimeout(() => {
            window.location.href = `/timetables?scope=${encodeURIComponent(slug)}`;
          }, 1200);
        }
      } else {
        toast.push({
          type: "error",
          title: "Generation " + final.status.toLowerCase(),
          message: (final as any).error_message || "See run details for cause.",
        });
      }

      // Hide the overlay the moment the run reaches a terminal state.
      // loadDashboard() below hits several endpoints and can be slow;
      // the user should see the result immediately, not wait on it.
      setGenerating(false);
      setGenStatus("");

      await loadDashboard();
      setTimetableRefreshKey((k) => k + 1);
    } catch (e: any) {
      const detail = e?.response?.data?.detail;
      const errMsg = e?.response?.data?.error_message || e?.response?.data?.error;
      const msg = detail || errMsg || (e instanceof Error ? e.message : String(e));
      toast.push({
        type: "error", title: "Generation failed", message: String(msg).slice(0, 500),
        mitigation: "Open the failed run's diagnostic, adjust lesson requirements or availability, then re-run.",
      });
      await reportError({ source: "scheduling", severity: "ERROR", code: "GENERATION_FAILED", message: String(msg) });
      await loadDashboard();
    } finally {
      setGenerating(false);
      setGenStatus("");
    }
  }

  async function handleApproveRun(runId: string) {
    console.log("[scheduling] Approve clicked for run", runId);
    try {
      await approveSchedulingRun(runId);
      toast.push({ type: "success", title: "Run approved", message: "The timetable is now active." });
      await loadDashboard();
    } catch (e: any) {
      const msg = e?.response?.data?.detail || (e instanceof Error ? e.message : String(e));
      toast.push({ type: "error", title: "Approve failed", message: String(msg).slice(0, 300) });
    }
  }

  async function handleDiscardRun(runId: string) {
    console.log("[scheduling] Discard clicked for run", runId);
    try {
      await discardSchedulingRun(runId);
      toast.push({ type: "info", title: "Run discarded", message: "Removed from recent runs." });
      await loadDashboard();
    } catch (e: any) {
      const msg = e?.response?.data?.detail || (e instanceof Error ? e.message : String(e));
      toast.push({ type: "error", title: "Discard failed", message: String(msg).slice(0, 300) });
    }
  }

  function handleViewRun(runId: string) {
    console.log("[scheduling] View clicked for run", runId);
    window.location.href = `/timetables?run=${runId}`;
  }

  async function handleRefresh() {
    await loadDashboard();
    setTimetableRefreshKey((k) => k + 1);
    toast.push({ type: "info", title: "Refreshed" });
  }

  function handlePrint() { window.print(); }

  const recentRuns = dashboard?.recent_runs ?? [];
  const failedRuns = dashboard?.failed_runs ?? [];
  const displayedRecent = showAllRuns ? recentRuns : recentRuns.slice(0, 5);
  const displayedFailed = showAllFailed ? failedRuns : failedRuns.slice(0, 5);
  const v = dashboard?.active_version;
  const term = dashboard?.active_term;

  const statusLine = useMemo(() => {
    if (!v) return "No active timetable — generate one to begin.";
    return [v.name, `${v.days} Days`, `${v.classes} Classes`, `${v.entries_count} entries loaded`].join(" • ");
  }, [v]);

  return (
    <>
      <style>{printCSS}</style>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>

      <div className="scheduling-page" style={{ padding: "1.5rem", maxWidth: "1500px", margin: "0 auto" }}>
        {/* HEADER */}
        <div style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
          <div style={cardStyle}>
            <div style={{ fontSize: "0.68rem", letterSpacing: "0.14em", textTransform: "uppercase", color: "#94a3b8", fontWeight: 800, marginBottom: "0.6rem" }}>
              TIMETABLE STATUS
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem 1.25rem" }}>
              <div><div style={{ fontSize: "0.7rem", color: "#94a3b8", fontWeight: 600 }}>Version</div>
                <div style={{ fontSize: "1.05rem", fontWeight: 800, color: BROWN2 }}>{v ? v.name : "—"}</div></div>
              <div><div style={{ fontSize: "0.7rem", color: "#94a3b8", fontWeight: 600 }}>Current Term</div>
                <div style={{ fontSize: "1.05rem", fontWeight: 800, color: BROWN2 }}>{term ? `${term.academic_year_name} / ${term.name}` : "—"}</div></div>
              <div><div style={{ fontSize: "0.7rem", color: "#94a3b8", fontWeight: 600 }}>Created</div>
                <div style={{ fontSize: "0.9rem", fontWeight: 700, color: "#1e2e40" }}>{v ? fmtDateTime(v.created_at) : "—"}</div></div>
              <div><div style={{ fontSize: "0.7rem", color: "#94a3b8", fontWeight: 600 }}>Last Successful Sync</div>
                <div style={{ fontSize: "0.9rem", fontWeight: 700, color: "#1e2e40" }}>{fmtDateTime(dashboard?.last_successful_sync)}</div></div>
              <div><div style={{ fontSize: "0.7rem", color: "#94a3b8", fontWeight: 600 }}>Current Time</div>
                <div style={{ fontSize: "0.9rem", fontWeight: 700, color: "#1e2e40" }}>{currentTime.toLocaleTimeString()}</div></div>
              <div><div style={{ fontSize: "0.7rem", color: "#94a3b8", fontWeight: 600 }}>Current Date</div>
                <div style={{ fontSize: "0.9rem", fontWeight: 700, color: "#1e2e40" }}>
                  {currentTime.toLocaleDateString(undefined, { weekday: "short", day: "2-digit", month: "short", year: "numeric" })}
                </div></div>
            </div>
          </div>

          <div style={cardStyle}>
            <div style={{ fontSize: "0.68rem", letterSpacing: "0.14em", textTransform: "uppercase", color: "#94a3b8", fontWeight: 800, marginBottom: "0.6rem" }}>
              ACTIONS
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: "0.5rem", marginBottom: "0.5rem" }}>
              <select value={selectedTermId} onChange={(e) => setSelectedTermId(e.target.value)}
                style={{ padding: "0.55rem 0.75rem", border: `1px solid ${SKY}`, borderRadius: "9px", fontWeight: 700, color: BROWN2, background: "#fff", fontSize: "0.85rem" }}>
                {(dashboard?.terms ?? []).map((t) => (
                  <option key={t.id} value={t.id}>{t.academic_year_name} · {t.name}{t.is_active ? " (active)" : ""}</option>
                ))}
              </select>
              <button type="button" onClick={handleGenerate} disabled={generating}
                style={{
                  display: "inline-flex", alignItems: "center", gap: "6px",
                  background: generating ? "#cbd5e1" : SKY, color: "#fff",
                  border: "none", padding: "0.55rem 1rem", borderRadius: "9px",
                  cursor: generating ? "not-allowed" : "pointer",
                  fontWeight: 700, fontSize: "0.82rem", whiteSpace: "nowrap",
                }}>
                <Rocket size={14} /> {generating ? "Generating…" : "Generate"}
              </button>
              {/* Generation overlay */}
              <GeneratingOverlay visible={generating} statusText={genStatus} />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1.5fr auto auto", gap: "0.4rem" }}>
              <select value={printFormat} onChange={(e) => setPrintFormat(e.target.value as PrintFormat)}
                style={{ padding: "6px 8px", border: `1px solid ${BROWN2}`, borderRadius: "8px", fontSize: "0.78rem", color: BROWN2, fontWeight: 600, background: "#fff" }}>
                {PRINT_FORMATS.map((f) => <option key={f.v} value={f.v}>{f.label}</option>)}
              </select>
              <button type="button" onClick={handlePrint} style={btnOutline(BROWN2, BROWN2)}>
                <Printer size={13} /> Print
              </button>
              <button type="button" onClick={handleRefresh} disabled={loading} style={btnOutline(BROWN2, BROWN2)}>
                <RefreshCw size={13} /> Refresh
              </button>
            </div>
            <details style={{ marginTop: "0.6rem" }}>
              <summary style={{ cursor: "pointer", fontSize: "0.78rem", fontWeight: 700, color: BROWN2 }}>
                Regeneration scope: {scope ? scope.label : "Master (full re-solve)"}
              </summary>
              <div style={{ marginTop: "0.5rem" }}>
                <ScopePicker
                  value={scope}
                  onChange={setScope}
                  showSubjects={false}
                  baselineId={baselineId}
                  onBaselineChange={setBaselineId}
                />
              </div>
            </details>
          </div>
        </div>

        {/* LIVE STRIP */}
        <div style={{
          display: "flex", alignItems: "center", gap: "0.9rem",
          padding: "0.55rem 1rem", marginBottom: "0.75rem",
          background: "linear-gradient(135deg, #f0f9ff, #ffffff)",
          border: `1px solid ${SKY}`, borderRadius: "10px",
          fontSize: "0.82rem", color: BROWN2, fontWeight: 600,
        }}>
          <span style={{
            display: "inline-flex", alignItems: "center", gap: "5px",
            padding: "2px 9px", background: SKY, color: "#fff",
            borderRadius: "999px", fontSize: "0.7rem", letterSpacing: "0.06em",
            textTransform: "uppercase", fontWeight: 800,
          }}>LIVE</span>
          <span>{statusLine}</span>
          <span style={{ marginLeft: "auto", color: "#94a3b8", fontSize: "0.75rem" }}>
            {dashboard?.counts && (
              <>{dashboard.counts.completed} completed · {dashboard.counts.failed} failed · {dashboard.counts.approved} approved</>
            )}
          </span>
        </div>

        {/* TIMETABLE */}
        <div style={cardStyle}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "1rem", marginBottom: "0.75rem" }}>
            <div>
              <div style={{ fontSize: "0.68rem", letterSpacing: "0.14em", textTransform: "uppercase", color: "#94a3b8", fontWeight: 800 }}>
                GENERATED TIMETABLE
              </div>
              <div style={{ fontSize: "0.82rem", color: "#64748b" }}>Database-backed live view</div>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
              <button type="button" onClick={() => setZoom((z) => Math.max(0.5, +(z - 0.1).toFixed(2)))} style={zoomBtn}><ZoomOut size={14} /></button>
              <span style={{ minWidth: "46px", textAlign: "center", fontSize: "0.78rem", fontWeight: 700, color: BROWN2 }}>{Math.round(zoom * 100)}%</span>
              <button type="button" onClick={() => setZoom((z) => Math.min(1.5, +(z + 0.1).toFixed(2)))} style={zoomBtn}><ZoomIn size={14} /></button>
              <button type="button" onClick={() => setZoom(1.0)} style={{ ...zoomBtn, width: "auto", padding: "4px 8px", fontSize: "0.72rem" }}>100%</button>
            </div>
          </div>
          <div id="tt-printable" style={{ overflow: "auto", maxHeight: "70vh" }}>
            <div style={{ transform: `scale(${zoom})`, transformOrigin: "top left", transition: "transform 180ms ease" }}>
              <Timetable key={timetableRefreshKey} />
            </div>
          </div>
        </div>

        {/* RECENT RUNS */}
        <div style={{ ...cardStyle, marginTop: "1rem" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.75rem" }}>
            <div>
              <div style={{ fontSize: "0.68rem", letterSpacing: "0.14em", textTransform: "uppercase", color: "#94a3b8", fontWeight: 800 }}>
                RECENT SUCCESSFUL RUNS
              </div>
              <div style={{ fontSize: "0.82rem", color: "#64748b" }}>Last 5 approved (or completed, if none approved yet)</div>
            </div>
            <button type="button" onClick={() => setShowAllRuns((v) => !v)} style={btnGhost}>
              {showAllRuns ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              {showAllRuns ? "Show 5" : "Show all"}
            </button>
          </div>
          {displayedRecent.length === 0 ? (
            <div style={{ textAlign: "center", padding: "1.25rem", color: "#94a3b8", fontSize: "0.85rem" }}>
              No successful runs yet.
            </div>
          ) : (
            <div style={{ display: "grid", gap: "0.5rem" }}>
              {displayedRecent.map((r) => (
                <RunRow
                          key={r.id}
                          run={r}
                          onView={() => handleViewRun(r.id)}
                          onApprove={handleApproveRun}
                          onDiscard={handleDiscardRun}
                  onUnapprove={async (id) => { await unapproveSchedulingRun(id); }}
                        />
              ))}
            </div>
          )}
        </div>

        {/* FAILED RUNS */}
        {failedRuns.length > 0 && (
          <div style={{ ...cardStyle, marginTop: "1rem", borderLeft: `4px solid ${RED}` }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.75rem" }}>
              <div>
                <div style={{ fontSize: "0.68rem", letterSpacing: "0.14em", textTransform: "uppercase", color: RED, fontWeight: 800 }}>
                  FAILED RUNS · {dashboard?.counts.failed ?? 0} TOTAL
                </div>
                <div style={{ fontSize: "0.82rem", color: "#64748b" }}>Recent failures with diagnostics and remediation</div>
              </div>
              {failedRuns.length > 5 && (
                <button type="button" onClick={() => setShowAllFailed((v) => !v)} style={btnOutline(RED, RED)}>
                  {showAllFailed ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                  {showAllFailed ? "Show 5" : "Show all"}
                </button>
              )}
            </div>
            <div style={{ display: "grid", gap: "0.5rem" }}>
              {displayedFailed.map((r) => (
                <div key={r.id} style={{
                  padding: "0.7rem 0.9rem", background: "#fef2f2",
                  border: `1px solid ${RED}`, borderRadius: "10px", fontSize: "0.82rem",
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                    <AlertCircle size={15} color={RED} />
                    <span style={{ fontWeight: 700, color: "#991b1b" }}>{r.term_name}</span>
                    <span style={{ fontSize: "0.72rem", color: "#94a3b8" }}>{fmtDateTime(r.created_at)}</span>
                    <button type="button" onClick={() => setReportRunId(r.id)} style={{
                      marginLeft: "auto", background: "transparent", border: `1px solid ${RED}`,
                      color: RED, padding: "3px 9px", borderRadius: "6px",
                      cursor: "pointer", fontSize: "0.72rem", fontWeight: 600,
                    }}>View diagnostic</button>
                  </div>
                  <div style={{ color: "#7f1d1d", fontSize: "0.78rem", lineHeight: 1.4, marginLeft: "23px" }}>
                    {r.error_message || "Scheduling run failed without a diagnostic."}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* PRINT-ONLY SECTIONS */}
      <div style={{ display: "none" }} className="print-suite">
        <PrintSuite entries={activeEntries} format={printFormat} />
      </div>

      {reportRunId && (
        <ReportModal runId={reportRunId} onClose={() => setReportRunId(null)} onChanged={loadDashboard} />
      )}
    </>
  );
}

function RunRow({ run, onView, onApprove, onDiscard, onUnapprove }: {
  run: ScheduleRunSummary;
  onView: () => void;
  onApprove: (runId: string) => Promise<void>;
  onDiscard: (runId: string) => Promise<void>;
  onUnapprove: (runId: string) => Promise<void>;
}) {
  const isApproved = !!run.approved_at;
  return (
    <div style={{
      display: "grid", gridTemplateColumns: "1.5fr 1.2fr 1fr 1fr auto",
      gap: "0.75rem", padding: "0.6rem 0.85rem",
      background: isApproved ? "#f0fdf4" : "#fff",
      border: `1px solid ${isApproved ? GREEN : "#e5e7eb"}`,
      borderRadius: "10px", fontSize: "0.82rem", alignItems: "center",
    }}>
      <div>
        <div style={{ fontWeight: 700, color: isApproved ? "#166534" : "#1e2e40" }}>
          {run.version_name ?? `Run ${run.id.slice(0, 8)}`}
        </div>
        <div style={{ fontSize: "0.72rem", color: "#94a3b8" }}>{run.term_name}</div>
      </div>
      <div style={{ fontSize: "0.75rem", color: "#64748b" }}>
        Completed {fmtDateTime(run.completed_at ?? run.created_at)}
      </div>
      <div style={{ fontSize: "0.75rem", color: "#64748b" }}>
        {isApproved
          ? <span style={{ color: "#166534", fontWeight: 600 }}>✓ Approved {fmtDateTime(run.approved_at)}</span>
          : <span style={{ color: "#94a3b8" }}>Not approved</span>}
      </div>
      <div style={{ fontSize: "0.72rem", color: "#94a3b8" }}>
        {run.approved_by ? `by ${run.approved_by}` : ""}
      </div>
      <div style={{ whiteSpace: "nowrap" }}>
        <button type="button" onClick={() => onApprove(run.id)}

          style={{ marginRight: 6, background: "#16a34a", color: "#fff", border: "none", borderRadius: 6, padding: "4px 10px", fontWeight: 700, fontSize: 12, cursor: "pointer" }}

          title="Approve this timetable">

          Approve

        </button>

        {isApproved && (
            <button type="button" onClick={() => onUnapprove(run.id)}
              style={{ /* same as Approve styling */ padding: "0.35rem 0.7rem", fontSize: "0.78rem", borderRadius: 6, border: "1px solid #f59e0b", background: "#fff7ed", color: "#b45309", cursor: "pointer", marginRight: 4 }}
              title="Reopen — timetable will no longer be active">
              Disapprove
            </button>
          )}
          <button type="button" onClick={() => onDiscard(run.id)}

          style={{ marginRight: 6, background: "#fff", color: "#b45309", border: "1px solid #fcd34d", borderRadius: 6, padding: "4px 10px", fontWeight: 700, fontSize: 12, cursor: "pointer" }}

          title="Hide this run from recent">

          Discard

        </button>
        <button type="button" onClick={onView}
          style={{
            display: "inline-flex", alignItems: "center", gap: "4px",
            background: SKY, color: "#fff", border: "none",
            padding: "4px 10px", borderRadius: "6px",
            cursor: "pointer", fontSize: "0.72rem", fontWeight: 700,
          }}>
          <Eye size={11} /> View
        </button>
      </div>
    </div>
  );
}

const zoomBtn: React.CSSProperties = {
  display: "inline-flex", alignItems: "center", justifyContent: "center",
  width: "28px", height: "28px",
  background: "#fff", border: "1px solid #cbd5e1", borderRadius: "7px",
  cursor: "pointer", color: "#475569",
};
const btnGhost: React.CSSProperties = {
  display: "inline-flex", alignItems: "center", gap: "4px",
  background: "transparent", border: "1px solid #cbd5e1",
  color: "#475569", padding: "4px 10px", borderRadius: "7px",
  cursor: "pointer", fontSize: "0.75rem", fontWeight: 600,
};
function btnOutline(color: string, textColor?: string): React.CSSProperties {
  return {
    display: "inline-flex", alignItems: "center", justifyContent: "center", gap: "5px",
    background: "transparent", border: `1px solid ${color}`,
    color: textColor ?? color,
    padding: "7px 10px", borderRadius: "8px", cursor: "pointer",
    fontSize: "0.78rem", fontWeight: 700,
  };
}