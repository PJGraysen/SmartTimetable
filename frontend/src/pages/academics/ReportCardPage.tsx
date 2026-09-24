import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Printer } from "lucide-react";
import { fetchStudentDeepAnalysis, type StudentDeepAnalysis } from "../../services/analysis";

const GRADE_COLOR: Record<string, string> = {
  A: "#10b981", B: "#22b4f0", C: "#f59e0b", D: "#f97316", E: "#ef4444", "-": "#94a3b8",
};

const printStyles = `
  @media print {
    @page { size: A4 portrait; margin: 14mm; }
    body { background: #fff !important; }
    .no-print { display: none !important; }
    .report-card { box-shadow: none !important; border: none !important; padding: 0 !important; margin: 0 !important; max-width: 100% !important; }
    .report-section { page-break-inside: avoid; }
  }
  .report-card { background: #fff; max-width: 820px; margin: 0 auto; padding: 2.2rem 2.4rem; border: 1px solid #e5e7eb; border-radius: 12px; box-shadow: 0 8px 24px rgba(10,18,29,0.08); color: #1e2e40; font-family: Georgia, "Times New Roman", serif; }
  .rc-header { text-align: center; border-bottom: 3px double #2b1a0f; padding-bottom: 0.9rem; margin-bottom: 1.2rem; }
  .rc-school { font-size: 1.35rem; font-weight: 800; letter-spacing: 0.06em; color: #2b1a0f; margin: 0; }
  .rc-title { font-size: 1.05rem; font-weight: 700; letter-spacing: 0.14em; color: #5a3a1e; margin: 4px 0 0; }
  .rc-subtitle { font-size: 0.8rem; color: #748095; margin: 2px 0 0; }
  .rc-info { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 24px; margin-bottom: 1.1rem; font-size: 0.9rem; }
  .rc-info-row { display: flex; justify-content: space-between; border-bottom: 1px dotted #cbd5e1; padding: 3px 0; }
  .rc-info-label { color: #748095; font-weight: 600; }
  .rc-info-value { font-weight: 700; color: #1e2e40; }
  .rc-section-title { font-size: 0.78rem; letter-spacing: 0.12em; text-transform: uppercase; color: #5a3a1e; font-weight: 800; margin: 1.1rem 0 0.5rem; border-bottom: 1px solid #e5e7eb; padding-bottom: 3px; }
  table.rc-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; font-family: "Segoe UI", system-ui, sans-serif; }
  table.rc-table th { background: #2b1a0f; color: #f5eee2; text-align: left; padding: 6px 10px; font-weight: 700; font-size: 0.78rem; letter-spacing: 0.04em; }
  table.rc-table th.num, table.rc-table td.num { text-align: right; }
  table.rc-table th.ctr, table.rc-table td.ctr { text-align: center; }
  table.rc-table td { padding: 6px 10px; border-bottom: 1px solid #f1f5f9; }
  table.rc-table tr:nth-child(even) td { background: #f8fafc; }
  .rc-total-row td { background: #2b1a0f !important; color: #f5eee2 !important; font-weight: 800; }
  .rc-badge { display: inline-block; padding: 1px 10px; border-radius: 999px; font-size: 0.72rem; font-weight: 800; font-family: "Segoe UI", system-ui, sans-serif; }
  .rc-summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 0.7rem 0 0.4rem; }
  .rc-summary-cell { border: 1px solid #e5e7eb; border-radius: 8px; padding: 8px 10px; text-align: center; font-family: "Segoe UI", system-ui, sans-serif; }
  .rc-summary-label { font-size: 0.65rem; letter-spacing: 0.08em; text-transform: uppercase; color: #748095; font-weight: 700; }
  .rc-summary-value { font-size: 1.15rem; font-weight: 800; color: #1e2e40; line-height: 1.15; }
  .rc-list { margin: 0; padding-left: 1.2rem; font-size: 0.88rem; font-family: "Segoe UI", system-ui, sans-serif; }
  .rc-list li { margin-bottom: 2px; }
  .rc-comment { font-family: "Segoe UI", system-ui, sans-serif; font-size: 0.88rem; border: 1px solid #e5e7eb; border-radius: 8px; padding: 0.7rem 0.9rem; background: #f8fafc; min-height: 62px; line-height: 1.5; }
  .rc-sig { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top: 1.8rem; font-family: "Segoe UI", system-ui, sans-serif; font-size: 0.82rem; }
  .rc-sig-line { border-top: 1px solid #1e2e40; padding-top: 3px; margin-top: 34px; color: #748095; }
  .rc-footer { text-align: center; font-size: 0.68rem; color: #94a3b8; margin-top: 1rem; font-family: "Segoe UI", system-ui, sans-serif; }
`;

export default function ReportCardPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<StudentDeepAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    fetchStudentDeepAnalysis(id)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div style={{ padding: "3rem", textAlign: "center", color: "#94a3b8" }}>Preparing report card…</div>;
  if (error || !data) return <div style={{ padding: "2rem", color: "#991b1b" }}>Error: {error ?? "No data"}</div>;

  const s = data.summary;
  const today = new Date().toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });

  return (
    <>
      <style>{printStyles}</style>

      <div className="no-print" style={{ padding: "1rem 2rem", maxWidth: "820px", margin: "0 auto", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <button type="button" onClick={() => navigate(-1)} style={{ display: "inline-flex", alignItems: "center", gap: "6px", background: "transparent", border: "none", color: "#5a3a1e", fontWeight: 600, cursor: "pointer" }}>
          <ArrowLeft size={16} /> Back
        </button>
        <button type="button" onClick={() => window.print()} style={{ display: "inline-flex", alignItems: "center", gap: "6px", background: "#22b4f0", color: "#fff", border: "none", padding: "0.55rem 1.1rem", borderRadius: "10px", cursor: "pointer", fontWeight: 700, fontSize: "0.85rem" }}>
          <Printer size={16} /> Print
        </button>
      </div>

      <div className="report-card">
        <div className="rc-header">
          <h1 className="rc-school">QUEEN OF APOSTLES SEMINARY SENIOR SCHOOL</h1>
          <div className="rc-title">STUDENT ACADEMIC REPORT</div>
          <div className="rc-subtitle">Generated {today}</div>
        </div>

        <div className="rc-info">
          <div className="rc-info-row"><span className="rc-info-label">Student</span><span className="rc-info-value">{data.student.name}</span></div>
          <div className="rc-info-row"><span className="rc-info-label">Admission No</span><span className="rc-info-value">{data.student.admission_number}</span></div>
          <div className="rc-info-row"><span className="rc-info-label">Class</span><span className="rc-info-value">{data.teaching_group?.name ?? "—"}</span></div>
          <div className="rc-info-row"><span className="rc-info-label">Status</span><span className="rc-info-value">{data.student.status}</span></div>
        </div>

        <div className="rc-section-title">Subject Results</div>
        <table className="rc-table">
          <thead>
            <tr>
              <th>Subject</th><th className="num">Mean %</th><th className="num">Class</th><th className="num">Δ</th><th className="ctr">Grade</th><th className="ctr">Trend</th>
            </tr>
          </thead>
          <tbody>
            {data.subject_rows.map((r) => (
              <tr key={r.subject_id}>
                <td><strong>{r.subject_name}</strong> <span style={{ color: "#94a3b8" }}>({r.subject_code})</span></td>
                <td className="num"><strong>{r.mean}</strong></td>
                <td className="num" style={{ color: "#748095" }}>{r.class_mean ?? "—"}</td>
                <td className="num" style={{ color: r.vs_class === null ? "#94a3b8" : r.vs_class >= 0 ? "#10b981" : "#ef4444", fontWeight: 700 }}>{r.vs_class === null ? "—" : `${r.vs_class > 0 ? "+" : ""}${r.vs_class}`}</td>
                <td className="ctr"><span className="rc-badge" style={{ background: (GRADE_COLOR[r.grade] ?? "#94a3b8") + "22", color: GRADE_COLOR[r.grade] ?? "#64748b" }}>{r.grade}</span></td>
                <td className="ctr" style={{ fontSize: "0.78rem", color: r.trend === "improving" ? "#10b981" : r.trend === "declining" ? "#ef4444" : "#94a3b8" }}>{r.trend === "improving" ? `+${r.delta}` : r.trend === "declining" ? r.delta : "—"}</td>
              </tr>
            ))}
            <tr className="rc-total-row">
              <td>OVERALL</td>
              <td className="num">{s.overall_mean}%</td>
              <td className="num">{s.class_mean ?? "—"}</td>
              <td className="num">{s.vs_class_mean !== null ? `${s.vs_class_mean > 0 ? "+" : ""}${s.vs_class_mean}` : "—"}</td>
              <td className="ctr">{s.overall_grade}</td>
              <td className="ctr">—</td>
            </tr>
          </tbody>
        </table>

        <div className="rc-section-title">Overall Summary</div>
        <div className="rc-summary">
          <div className="rc-summary-cell"><div className="rc-summary-label">Mean</div><div className="rc-summary-value">{s.overall_mean}%</div></div>
          <div className="rc-summary-cell"><div className="rc-summary-label">Grade</div><div className="rc-summary-value">{s.overall_grade}</div></div>
          <div className="rc-summary-cell"><div className="rc-summary-label">Rank</div><div className="rc-summary-value">{s.rank ? `#${s.rank}` : "—"}</div></div>
          <div className="rc-summary-cell"><div className="rc-summary-label">Class Size</div><div className="rc-summary-value">{s.class_size ?? "—"}</div></div>
        </div>

        <div className="rc-section-title">Strengths</div>
        <ul className="rc-list" style={{ color: "#166534" }}>
          {data.strengths.map((x) => <li key={x}>{x}</li>)}
          {data.strengths.length === 0 && <li style={{ color: "#94a3b8", listStyle: "none", marginLeft: "-1.2rem" }}>—</li>}
        </ul>

        <div className="rc-section-title">Development Areas</div>
        <ul className="rc-list" style={{ color: "#991b1b" }}>
          {data.weaknesses.map((x) => <li key={x}>{x}</li>)}
          {data.weaknesses.length === 0 && <li style={{ color: "#94a3b8", listStyle: "none", marginLeft: "-1.2rem" }}>None flagged</li>}
        </ul>

        <div className="rc-section-title">Class Teacher's Comment</div>
        <div className="rc-comment">&nbsp;</div>

        <div className="rc-section-title">Principal's Comment</div>
        <div className="rc-comment">&nbsp;</div>

        <div className="rc-sig">
          <div><div className="rc-sig-line">Class Teacher's Signature</div></div>
          <div><div className="rc-sig-line">Principal's Signature</div></div>
        </div>

        <div className="rc-footer">Queen of Apostles Seminary Senior School · SmartSchoolPro · Report generated from live assessment data</div>
      </div>
    </>
  );
}