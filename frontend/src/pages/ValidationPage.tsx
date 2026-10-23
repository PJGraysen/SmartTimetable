import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  AlertCircle, CheckCircle2, ShieldAlert, Info, ChevronDown, CheckCheck,
  LayoutGrid, ListFilter, Send
} from "lucide-react";
import { fetchSchedulingRuns, getSchedulingRunReport, resolveValidation, approveSchedulingRun, type SchedulingRun } from "../services/scheduling";

type Constraint = {
  id: string;
  category: string;
  category_display: string;
  message: string;
  mitigation: string;
  is_resolved: boolean;
};

type Severity = "hard" | "soft" | "info";
type ConstraintWithSeverity = Constraint & { severity: Severity };

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

const SEVERITY_COLORS: Record<Severity, { bg: string; border: string; fg: string; badgeBg: string }> = {
  hard: { bg: "#fef2f2", border: "#fecaca", fg: "#991b1b", badgeBg: "#fee2e2" },
  soft: { bg: "#fffbeb", border: "#fde68a", fg: "#92400e", badgeBg: "#fef3c7" },
  info: { bg: "#eff6ff", border: "#bfdbfe", fg: "#1e40af", badgeBg: "#dbeafe" },
};

const SEVERITY_ICONS: Record<Severity, any> = {
  hard: AlertCircle,
  soft: ShieldAlert,
  info: Info,
};

export default function ValidationPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [runs, setRuns] = useState<SchedulingRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string>("");
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  useEffect(() => {
    fetchSchedulingRuns().then(data => {
      const completed = data.filter(r => r.status === "COMPLETED");
      setRuns(completed);
      const urlRunId = searchParams.get("run");
      if (urlRunId && completed.some(r => r.id === urlRunId)) {
        setSelectedRunId(urlRunId);
      } else if (completed.length > 0) {
        setSelectedRunId(completed[0].id);
      }
    });
  }, []);

  useEffect(() => {
    if (!selectedRunId) return;
    setLoading(true);
    setActiveCategory(null);
    setSearchParams({ run: selectedRunId });
    getSchedulingRunReport(selectedRunId)
      .then((data: any) => setReport(data))
      .catch(() => setReport(null))
      .finally(() => setLoading(false));
  }, [selectedRunId]);

  const toggleResolve = async (validationId: string, next: boolean) => {
    try {
      await resolveValidation(selectedRunId, validationId, next);
      const data = await getSchedulingRunReport(selectedRunId);
      setReport(data as any);
    } catch {
      alert("Failed to update status.");
    }
  };

  const handlePublish = async () => {
    if (!report?.approvable) return;
    setPublishing(true);
    try {
      await approveSchedulingRun(selectedRunId, "Approved via Validation Dashboard");
      // Redirect to the main timetable page after distribution
      window.location.href = "/timetables";
    } catch (e: any) {
      alert("Failed to publish: " + (e?.response?.data?.detail || e.message));
      setPublishing(false);
    }
  };

  const categoryBuckets = useMemo(() => {
    if (!report) return [];
    const map = new Map<string, { category: string; display: string; severity: Severity; total: number; unresolved: number }>();
    const add = (c: Constraint, sev: Severity) => {
      const key = c.category;
      if (!map.has(key)) {
        map.set(key, { category: key, display: c.category_display, severity: sev, total: 0, unresolved: 0 });
      }
      const entry = map.get(key)!;
      entry.total += 1;
      if (!c.is_resolved) entry.unresolved += 1;
      if (sev === "hard") entry.severity = "hard";
      else if (sev === "soft" && entry.severity === "info") entry.severity = "soft";
    };
    report.hard_constraints.forEach(c => add(c, "hard"));
    report.soft_constraints.forEach(c => add(c, "soft"));
    report.info.forEach(c => add(c, "info"));
    return Array.from(map.values()).sort((a, b) => b.unresolved - a.unresolved || b.total - a.total);
  }, [report]);

  const allConstraints = useMemo<ConstraintWithSeverity[]>(() => {
    if (!report) return [];
    const h = report.hard_constraints.map(c => ({ ...c, severity: "hard" as Severity }));
    const s = report.soft_constraints.map(c => ({ ...c, severity: "soft" as Severity }));
    const i = report.info.map(c => ({ ...c, severity: "info" as Severity }));
    return [...h, ...s, ...i];
  }, [report]);

  const visibleConstraints = useMemo(() => {
    if (!activeCategory) return allConstraints;
    return allConstraints.filter(c => c.category === activeCategory);
  }, [allConstraints, activeCategory]);

  const totalConstraints = allConstraints.length;
  const totalResolved = allConstraints.filter(c => c.is_resolved).length;
  const overallCompliance = totalConstraints > 0 ? Math.round((totalResolved / totalConstraints) * 100) : 100;
  const selectedRun = runs.find(r => r.id === selectedRunId);

  return (
    <div style={{ padding: "2rem", maxWidth: "1400px", margin: "0 auto", fontFamily: "system-ui, sans-serif", background: "#f8fafc", minHeight: "100vh" }}>
      
      {/* HEADER */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "2rem", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <h1 style={{ fontSize: "1.8rem", fontWeight: 900, color: "#0f172a", margin: 0 }}>Validation & Distribution</h1>
          <p style={{ color: "#64748b", margin: "6px 0 0 0", fontSize: "0.95rem" }}>Review constraint compliance. Once all hard constraints are resolved, distribute the timetable.</p>
        </div>
        {report && (
          <button 
            onClick={handlePublish} 
            disabled={!report.approvable || publishing}
            style={{ 
              display: "flex", alignItems: "center", gap: "10px", padding: "14px 24px", borderRadius: "12px", 
              background: report.approvable ? "linear-gradient(135deg, #10b981, #059669)" : "#e2e8f0", 
              color: report.approvable ? "#fff" : "#94a3b8",
              fontWeight: 900, fontSize: "1rem", border: "none", 
              cursor: report.approvable && !publishing ? "pointer" : "not-allowed",
              boxShadow: report.approvable ? "0 8px 24px rgba(16,185,129,0.4)" : "none",
              transition: "all 0.2s ease"
            }}
          >
            <Send size={20} />
            {publishing ? "Distributing..." : "Validate & Distribute"}
          </button>
        )}
      </div>

      {/* RUN SELECTOR */}
      <div style={{ display: "flex", gap: "12px", alignItems: "stretch", marginBottom: "2rem", flexWrap: "wrap" }} ref={dropdownRef}>
        <div style={{ position: "relative", flex: 1, minWidth: "300px", maxWidth: "500px" }}>
          <button onClick={() => setDropdownOpen(v => !v)} style={{ width: "100%", display: "flex", justifyContent: "space-between", alignItems: "center", padding: "14px 20px", background: "#fff", border: "2px solid #0284c7", borderRadius: "12px", cursor: "pointer", textAlign: "left", fontWeight: 700, fontSize: "0.9rem", color: "#0f172a" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
              <span style={{ fontSize: "0.7rem", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em" }}>Selected Run</span>
              <span>{selectedRun ? "Run " + selectedRun.id.slice(0, 8) + " - " + new Date(selectedRun.created_at).toLocaleString() : "Select a run..."}</span>
            </div>
            <ChevronDown size={20} color="#0284c7" />
          </button>
          {dropdownOpen && (
            <div style={{ position: "absolute", top: "calc(100% + 8px)", left: 0, right: 0, background: "#fff", border: "2px solid #0284c7", borderRadius: "12px", boxShadow: "0 10px 40px rgba(2,132,199,0.2)", zIndex: 100, maxHeight: "400px", overflowY: "auto" }}>
              {runs.length === 0 && <div style={{ padding: "20px", textAlign: "center", color: "#64748b" }}>No completed runs yet</div>}
              {runs.map(r => (
                <button key={r.id} onClick={() => { setSelectedRunId(r.id); setDropdownOpen(false); }} style={{ width: "100%", padding: "12px 20px", background: r.id === selectedRunId ? "#e0f2fe" : "transparent", border: "none", borderBottom: "1px solid #e2e8f0", textAlign: "left", cursor: "pointer", fontWeight: r.id === selectedRunId ? 800 : 600, color: r.id === selectedRunId ? "#0284c7" : "#334155", fontSize: "0.85rem", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span>Run {r.id.slice(0, 8)}</span>
                  <span style={{ fontSize: "0.75rem", color: "#64748b" }}>{new Date(r.created_at).toLocaleString()}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {loading && <div style={{ textAlign: "center", padding: "3rem", color: "#64748b" }}>Loading validation report...</div>}

      {!loading && !report && (
        <div style={{ textAlign: "center", padding: "3rem", color: "#ef4444", background: "#fef2f2", borderRadius: "12px", border: "2px solid #fecaca" }}>No report available for this run.</div>
      )}

      {!loading && report && (
        <>
          {/* SUMMARY TILES */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "16px", marginBottom: "2rem" }}>
            <div className="motion-tile" style={{ padding: "20px", background: "#fff", border: "2px solid #e2e8f0", borderRadius: "14px" }}>
              <div style={{ fontSize: "0.72rem", color: "#64748b", textTransform: "uppercase", fontWeight: 700, letterSpacing: "0.05em" }}>Overall Compliance</div>
              <div style={{ fontSize: "2.2rem", fontWeight: 900, color: overallCompliance === 100 ? "#16a34a" : overallCompliance >= 75 ? "#d97706" : "#dc2626", marginTop: "4px" }}>{overallCompliance}%</div>
              <div style={{ fontSize: "0.8rem", color: "#64748b" }}>{totalResolved} of {totalConstraints} resolved</div>
            </div>
            <div className="motion-tile" style={{ padding: "20px", background: "#fef2f2", border: "2px solid #fecaca", borderRadius: "14px" }}>
              <div style={{ fontSize: "0.72rem", color: "#991b1b", textTransform: "uppercase", fontWeight: 700, letterSpacing: "0.05em" }}>Hard Unresolved</div>
              <div style={{ fontSize: "2.2rem", fontWeight: 900, color: "#dc2626", marginTop: "4px" }}>{report.counts.hard_unresolved}</div>
              <div style={{ fontSize: "0.8rem", color: "#991b1b" }}>{report.counts.hard} total hard</div>
            </div>
            <div className="motion-tile" style={{ padding: "20px", background: "#fffbeb", border: "2px solid #fde68a", borderRadius: "14px" }}>
              <div style={{ fontSize: "0.72rem", color: "#92400e", textTransform: "uppercase", fontWeight: 700, letterSpacing: "0.05em" }}>Soft Warnings</div>
              <div style={{ fontSize: "2.2rem", fontWeight: 900, color: "#d97706", marginTop: "4px" }}>{report.counts.soft}</div>
              <div style={{ fontSize: "0.8rem", color: "#92400e" }}>soft rules</div>
            </div>
            <div className="motion-tile" style={{ padding: "20px", background: "#eff6ff", border: "2px solid #bfdbfe", borderRadius: "14px" }}>
              <div style={{ fontSize: "0.72rem", color: "#1e40af", textTransform: "uppercase", fontWeight: 700, letterSpacing: "0.05em" }}>Info</div>
              <div style={{ fontSize: "2.2rem", fontWeight: 900, color: "#2563eb", marginTop: "4px" }}>{report.counts.info}</div>
              <div style={{ fontSize: "0.8rem", color: "#1e40af" }}>informational</div>
            </div>
          </div>

          {/* CATEGORY TILES */}
          {categoryBuckets.length > 0 && (
            <div style={{ marginBottom: "2rem" }}>
              <h2 style={{ fontSize: "1.1rem", fontWeight: 800, color: "#0f172a", marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
                <LayoutGrid size={20} color="#0284c7" /> Constraint Categories
                {activeCategory && (
                  <button onClick={() => setActiveCategory(null)} style={{ marginLeft: "auto", padding: "4px 12px", background: "#fff", border: "2px solid #0284c7", borderRadius: "8px", cursor: "pointer", fontSize: "0.75rem", fontWeight: 700, color: "#0284c7" }}>Clear filter</button>
                )}
              </h2>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: "12px" }}>
                {categoryBuckets.map(b => {
                  const colors = SEVERITY_COLORS[b.severity];
                  const Icon = SEVERITY_ICONS[b.severity];
                  const isActive = activeCategory === b.category;
                  const compliance = b.total > 0 ? Math.round(((b.total - b.unresolved) / b.total) * 100) : 100;
                  return (
                    <button key={b.category} onClick={() => setActiveCategory(isActive ? null : b.category)} className="motion-tile" style={{ padding: "16px", background: isActive ? colors.bg : "#fff", border: "2px solid " + (isActive ? colors.border : "#e2e8f0"), borderLeft: "6px solid " + colors.fg, borderRadius: "12px", cursor: "pointer", textAlign: "left", transform: isActive ? "translateY(-4px) scale(1.02)" : "none", boxShadow: isActive ? "0 12px 30px rgba(0,0,0,0.12)" : "0 2px 6px rgba(0,0,0,0.03)", zIndex: 10, position: "relative" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "10px" }}>
                        <Icon size={18} color={colors.fg} />
                        <span style={{ fontSize: "0.7rem", textTransform: "uppercase", fontWeight: 800, letterSpacing: "0.05em", color: colors.fg }}>{b.severity}</span>
                      </div>
                      <div style={{ fontSize: "0.95rem", fontWeight: 800, color: "#0f172a", marginBottom: "8px" }}>{b.display}</div>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                        <span style={{ fontSize: "0.8rem", color: "#64748b" }}>{b.unresolved} unresolved / {b.total} total</span>
                        <span style={{ fontSize: "0.85rem", fontWeight: 800, color: colors.fg }}>{compliance}%</span>
                      </div>
                      <div style={{ height: "6px", background: "#e2e8f0", borderRadius: "3px", overflow: "hidden" }}>
                        <div style={{ height: "100%", width: compliance + "%", background: colors.fg, transition: "width 0.3s" }} />
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* DETAILS LIST */}
          <div>
            <h2 style={{ fontSize: "1.1rem", fontWeight: 800, color: "#0f172a", marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
              <ListFilter size={20} color="#0284c7" />
              {activeCategory ? (categoryBuckets.find(b => b.category === activeCategory)?.display || activeCategory) + " (" + visibleConstraints.length + ")" : "All Violations (" + visibleConstraints.length + ")"}
            </h2>
            {visibleConstraints.length === 0 ? (
              <div style={{ textAlign: "center", padding: "3rem", background: "#f0fdf4", border: "2px solid #86efac", borderRadius: "12px", color: "#166534", fontWeight: 600 }}>
                <CheckCircle2 size={32} style={{ marginBottom: "8px" }} />
                <div>No violations in this category. Great!</div>
              </div>
            ) : (
              <div style={{ display: "grid", gap: "12px" }}>
                {visibleConstraints.map(c => {
                  const colors = SEVERITY_COLORS[c.severity];
                  const Icon = SEVERITY_ICONS[c.severity];
                  return (
                    <div key={c.id} className="motion-tile" style={{ background: "#fff", border: "1px solid " + (c.is_resolved ? "#86efac" : colors.border), borderLeft: "5px solid " + (c.is_resolved ? "#16a34a" : colors.fg), padding: "16px", borderRadius: "10px", display: "flex", gap: "14px", opacity: c.is_resolved ? 0.7 : 1 }}>
                      <div style={{ marginTop: "2px" }}>{c.is_resolved ? <CheckCircle2 size={20} color="#16a34a" /> : <Icon size={20} color={colors.fg} />}</div>
                      <div style={{ flex: 1 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px", flexWrap: "wrap" }}>
                          <span style={{ fontWeight: 800, fontSize: "0.95rem", color: "#0f172a" }}>{c.category_display}</span>
                          <span style={{ fontSize: "0.65rem", fontWeight: 800, textTransform: "uppercase", padding: "2px 6px", borderRadius: "4px", background: colors.badgeBg, color: colors.fg }}>{c.severity}</span>
                          {c.is_resolved && <span style={{ fontSize: "0.65rem", fontWeight: 800, textTransform: "uppercase", padding: "2px 6px", borderRadius: "4px", background: "#dcfce7", color: "#166534" }}>resolved</span>}
                        </div>
                        <div style={{ fontSize: "0.85rem", margin: "4px 0 8px 0", color: "#334155" }}>{c.message}</div>
                        <div style={{ fontSize: "0.8rem", background: "#f8fafc", padding: "8px 12px", borderRadius: "6px", fontStyle: "italic", color: "#475569" }}>
                          <strong style={{ fontStyle: "normal" }}>Fix:</strong> {c.mitigation}
                        </div>
                      </div>
                      <button onClick={() => toggleResolve(c.id, !c.is_resolved)} style={{ alignSelf: "flex-start", padding: "8px 14px", borderRadius: "8px", cursor: "pointer", fontWeight: 800, fontSize: "0.75rem", background: c.is_resolved ? "#fff" : "#0284c7", color: c.is_resolved ? "#64748b" : "#fff", border: "2px solid " + (c.is_resolved ? "#cbd5e1" : "#0284c7"), transition: "all 0.2s", whiteSpace: "nowrap" }}>
                        {c.is_resolved ? "Reopen" : "Mark Resolved"}
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </>
      )}
      <style>{`
        .motion-tile {
          transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .motion-tile:hover {
          transform: translateY(-4px) scale(1.01);
          box-shadow: 0 12px 30px rgba(0,0,0,0.12);
          z-index: 20;
          position: relative;
        }
      `}</style>
    </div>
  );
}
