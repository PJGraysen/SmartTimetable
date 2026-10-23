import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { AlertCircle, CheckCircle2, ShieldAlert, Info } from "lucide-react";
import { fetchSchedulingRuns, getSchedulingRunReport, resolveValidation, type SchedulingRun } from "../services/scheduling";

type Constraint = {
  id: string;
  category: string;
  category_display: string;
  message: string;
  mitigation: string;
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

export default function ValidationPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [runs, setRuns] = useState<SchedulingRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string>("");
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(false);

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
    } catch (e) {
      alert("Failed to update status.");
    }
  };

  const renderConstraint = (c: Constraint, type: "hard" | "soft" | "info") => {
    const bg = type === "hard" ? "#fef2f2" : type === "soft" ? "#fffbeb" : "#eff6ff";
    const border = type === "hard" ? "#fecaca" : type === "soft" ? "#fde68a" : "#bfdbfe";
    const icon = type === "hard" ? <AlertCircle size={18} color="#dc2626" /> : 
                 type === "soft" ? <ShieldAlert size={18} color="#d97706" /> : 
                 <Info size={18} color="#2563eb" />;

    return (
      <div key={c.id} style={{ background: bg, border: "1px solid " + border, padding: "16px", borderRadius: "10px", display: "flex", gap: "12px", opacity: c.is_resolved ? 0.6 : 1 }}>
        <div style={{ marginTop: "2px" }}>{icon}</div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 800, fontSize: "0.95rem", color: type === "hard" ? "#991b1b" : type === "soft" ? "#92400e" : "#1e40af" }}>
            {c.category_display}
          </div>
          <div style={{ fontSize: "0.85rem", margin: "4px 0 8px 0", color: "#334155" }}>{c.message}</div>
          <div style={{ fontSize: "0.8rem", background: "rgba(255,255,255,0.5)", padding: "6px 10px", borderRadius: "6px", fontStyle: "italic", color: "#475569" }}>
            <strong style={{ fontStyle: "normal" }}>Fix:</strong> {c.mitigation}
          </div>
        </div>
        <button 
          onClick={() => toggleResolve(c.id, !c.is_resolved)}
          style={{ 
            alignSelf: "flex-start", padding: "6px 12px", borderRadius: "6px", cursor: "pointer", fontWeight: 700, fontSize: "0.75rem",
            background: c.is_resolved ? "#e2e8f0" : "#fff", 
            border: "2px solid " + (c.is_resolved ? "#cbd5e1" : border),
            color: c.is_resolved ? "#64748b" : "#334155"
          }}
        >
          {c.is_resolved ? "Reopen" : "Mark Resolved"}
        </button>
      </div>
    );
  };

  return (
    <div style={{ padding: "2rem", maxWidth: "1200px", margin: "0 auto", fontFamily: "sans-serif" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "2rem" }}>
        <div>
          <h1 style={{ fontSize: "1.8rem", fontWeight: 900, color: "#0f172a", margin: 0 }}>Validation & Constraints</h1>
          <p style={{ color: "#64748b", margin: "4px 0 0 0" }}>Review hard constraints, soft rules, and resolve issues before approval.</p>
        </div>
        <select 
          value={selectedRunId} 
          onChange={(e) => setSelectedRunId(e.target.value)}
          style={{ padding: "10px 16px", borderRadius: "8px", border: "2px solid #0284c7", fontWeight: 700, color: "#0284c7", outline: "none" }}
        >
          {runs.map(r => (
            <option key={r.id} value={r.id}>
              Run {r.id.slice(0, 8)} ({new Date(r.created_at).toLocaleTimeString()})
            </option>
          ))}
        </select>
      </div>

      {loading && <div style={{ textAlign: "center", padding: "3rem", color: "#64748b" }}>Loading validation report...</div>}

      {!loading && !report && (
        <div style={{ textAlign: "center", padding: "3rem", color: "#ef4444", background: "#fef2f2", borderRadius: "12px" }}>
          No report available for this run.
        </div>
      )}

      {!loading && report && (
        <div style={{ display: "grid", gap: "1.5rem" }}>
          <div style={{ padding: "20px", borderRadius: "12px", background: report.approvable ? "#f0fdf4" : "#fef2f2", border: "2px solid " + (report.approvable ? "#86efac" : "#fecaca"), display: "flex", alignItems: "center", gap: "12px" }}>
            {report.approvable ? <CheckCircle2 size={24} color="#16a34a" /> : <AlertCircle size={24} color="#dc2626" />}
            <div>
              <div style={{ fontWeight: 800, fontSize: "1.1rem", color: report.approvable ? "#166534" : "#991b1b" }}>
                {report.approvable ? "Ready for Approval" : "Blocked from Approval"}
              </div>
              <div style={{ fontSize: "0.9rem", color: report.approvable ? "#166534" : "#991b1b" }}>
                {report.approvable ? "All hard constraints have been resolved." : report.reason_if_blocked}
              </div>
            </div>
          </div>

          {report.hard_constraints.length > 0 && (
            <section>
              <h3 style={{ fontSize: "1.1rem", fontWeight: 800, color: "#0f172a", marginBottom: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
                <AlertCircle size={20} color="#dc2626" /> Hard Constraints ({report.counts.hard_unresolved} unresolved)
              </h3>
              <div style={{ display: "grid", gap: "10px" }}>
                {report.hard_constraints.map(c => renderConstraint(c, "hard"))}
              </div>
            </section>
          )}

          {report.soft_constraints.length > 0 && (
            <section>
              <h3 style={{ fontSize: "1.1rem", fontWeight: 800, color: "#0f172a", marginBottom: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
                <ShieldAlert size={20} color="#d97706" /> Soft Constraints ({report.counts.soft})
              </h3>
              <div style={{ display: "grid", gap: "10px" }}>
                {report.soft_constraints.map(c => renderConstraint(c, "soft"))}
              </div>
            </section>
          )}

          {report.info.length > 0 && (
            <section>
              <h3 style={{ fontSize: "1.1rem", fontWeight: 800, color: "#0f172a", marginBottom: "12px", display: "flex", alignItems: "center", gap: "8px" }}>
                <Info size={20} color="#2563eb" /> Information ({report.counts.info})
              </h3>
              <div style={{ display: "grid", gap: "10px" }}>
                {report.info.map(c => renderConstraint(c, "info"))}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
