import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Printer } from "lucide-react";
import http from "../../services/http";
import "../../styles/report.css";

type AssessmentColumn = {
  assessment_id: string;
  name: string;
  total_mark: number;
  avg_pct: number;
  grade: string;
  points: number;
};

type SubjectRow = {
  code: string;
  name: string;
  marks: Record<string, { raw: number; pct: number; grade: string; points: number }>;
  average: { pct: number; grade: string; points: number };
};

type ReportForm = {
  student: {
    id: string;
    admission_number: string;
    name: string;
    kcpe_mark: number | null;
    class_name: string;
    class_level: string;
  };
  context: {
    template: "kcse" | "cbe_secondary" | "cbe_junior";
    term: string;
    year: string;
    assessment_columns: AssessmentColumn[];
    total_avg_pct: number;
    total_avg_points: number;
    performance_level: string;
    rank: number | null;
    class_size: number | null;
  };
  subjects: SubjectRow[];
  school: { name: string; address: string; email: string };
};

export default function ReportFormPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<ReportForm | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    http
      .get<ReportForm>(`/academics/analysis/report-form/${id}/`)
      .then((res) => setData(res.data))
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return <div style={{ padding: "3rem", textAlign: "center", color: "#94a3b8" }}>Loading report form…</div>;
  }
  if (error || !data) {
    return <div style={{ padding: "2rem", color: "#991b1b" }}>Error: {error ?? "No data"}</div>;
  }

  const { student, context, subjects, school } = data;
  const isKCSE = context.template === "kcse";

  return (
    <>
<div className="no-print" style={{ padding: "1rem 2rem", maxWidth: "900px", margin: "0 auto", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <button type="button" onClick={() => navigate(-1)} style={{ display: "inline-flex", alignItems: "center", gap: "6px", background: "transparent", border: "none", color: "#5a3a1e", fontWeight: 600, cursor: "pointer" }}>
          <ArrowLeft size={16} /> Back
        </button>
        <button type="button" onClick={() => window.print()} style={{ display: "inline-flex", alignItems: "center", gap: "6px", background: "#22b4f0", color: "#fff", border: "none", padding: "0.55rem 1.1rem", borderRadius: "10px", cursor: "pointer", fontWeight: 700, fontSize: "0.85rem" }}>
          <Printer size={16} /> Print
        </button>
      </div>

      <div className="report-form">
        <div className="rf-watermark">{student.admission_number} · OFFICIAL</div>
        <div className="rf-header">
          <div className="rf-school">{school.name}</div>
          <div className="rf-address">{school.address}</div>
          <div className="rf-address">{school.email}</div>
          <div className="rf-title">END OF TERM REPORT</div>
        </div>

        <div className="rf-student-info">
          <div className="rf-line"><span className="rf-label">NAME:</span><span className="rf-value">{student.name}</span></div>
          <div className="rf-line"><span className="rf-label">PARISH:</span><span className="rf-value" /></div>
          <div />
          <div className="rf-line"><span className="rf-label">{isKCSE ? "FORM:" : "GRADE:"}</span><span className="rf-value">{student.class_level}</span></div>
          <div className="rf-line"><span className="rf-label">ADM NO:</span><span className="rf-value">{student.admission_number}</span></div>
          <div className="rf-line"><span className="rf-label">TERM:</span><span className="rf-value">{context.term.replace("Term ", "")}</span></div>
          <div className="rf-line"><span className="rf-label">{isKCSE ? "KCPE:" : "ASSESSMENT NO:"}</span><span className="rf-value">{isKCSE ? (student.kcpe_mark ?? "") : ""}</span></div>
          <div className="rf-line"><span className="rf-label">YEAR:</span><span className="rf-value">{context.year}</span></div>
          <div className="rf-line"><span className="rf-label">NEMIS NO:</span><span className="rf-value" /></div>
        </div>

        <table className="rf-table">
          <thead>
            {isKCSE ? (
              <>
                <tr>
                  <th rowSpan={2}>SUBJECT</th>
                  <th colSpan={2}>EXAM 1 (100%)</th>
                  <th colSpan={2}>EXAM 2 (100%)</th>
                  <th colSpan={2}>EXAM 3 (100%)</th>
                  <th colSpan={3}>RESULT (100%)</th>
                </tr>
                <tr>
                  <th>MRKS</th><th>GRD</th>
                  <th>MRKS</th><th>GRD</th>
                  <th>MRKS</th><th>GRD</th>
                  <th>MRKS</th><th>GRD</th><th>PTS</th>
                </tr>
              </>
            ) : (
              <>
                <tr>
                  <th rowSpan={2}>LEARNING AREAS</th>
                  <th colSpan={3}>ASSESSMENT 1</th>
                  <th colSpan={3}>ASSESSMENT 2</th>
                  <th colSpan={3}>ASSESSMENT 3</th>
                  <th colSpan={3}>AVERAGE</th>
                </tr>
                <tr>
                  <th>MARKS</th><th>GRADE</th><th>PTS</th>
                  <th>MARKS</th><th>GRADE</th><th>PTS</th>
                  <th>MARKS</th><th>GRADE</th><th>PTS</th>
                  <th>MARKS</th><th>GRADE</th><th>PTS</th>
                </tr>
              </>
            )}
          </thead>
          <tbody>
            {subjects.map((row) => {
              if (isKCSE) {
                const a0 = context.assessment_columns[0] ? row.marks[context.assessment_columns[0].assessment_id] : null;
                const a1 = context.assessment_columns[1] ? row.marks[context.assessment_columns[1].assessment_id] : null;
                const a2 = context.assessment_columns[2] ? row.marks[context.assessment_columns[2].assessment_id] : null;
                return (
                  <tr key={row.code}>
                    <td className="subject">{row.code}</td>
                    <td className="num">{a0 ? a0.raw.toFixed(0) : ""}</td>
                    <td>{a0 ? a0.grade : ""}</td>
                    <td className="num">{a1 ? a1.raw.toFixed(0) : ""}</td>
                    <td>{a1 ? a1.grade : ""}</td>
                    <td className="num">{a2 ? a2.raw.toFixed(0) : ""}</td>
                    <td>{a2 ? a2.grade : ""}</td>
                    <td className="num">{row.average.pct.toFixed(0)}</td>
                    <td>{row.average.grade}</td>
                    <td className="num">{row.average.points.toFixed(0)}</td>
                  </tr>
                );
              }
              const a0 = context.assessment_columns[0] ? row.marks[context.assessment_columns[0].assessment_id] : null;
              const a1 = context.assessment_columns[1] ? row.marks[context.assessment_columns[1].assessment_id] : null;
              const a2 = context.assessment_columns[2] ? row.marks[context.assessment_columns[2].assessment_id] : null;
              return (
                <tr key={row.code}>
                  <td className="subject">{row.code}</td>
                  <td className="num">{a0 ? a0.raw.toFixed(0) : ""}</td>
                  <td>{a0 ? a0.grade : ""}</td>
                  <td className="num">{a0 ? a0.points.toFixed(0) : ""}</td>
                  <td className="num">{a1 ? a1.raw.toFixed(0) : ""}</td>
                  <td>{a1 ? a1.grade : ""}</td>
                  <td className="num">{a1 ? a1.points.toFixed(0) : ""}</td>
                  <td className="num">{a2 ? a2.raw.toFixed(0) : ""}</td>
                  <td>{a2 ? a2.grade : ""}</td>
                  <td className="num">{a2 ? a2.points.toFixed(0) : ""}</td>
                  <td className="num">{row.average.pct.toFixed(0)}</td>
                  <td>{row.average.grade}</td>
                  <td className="num">{row.average.points.toFixed(0)}</td>
                </tr>
              );
            })}
            <tr className="total-row">
              <td className="subject">TOTAL</td>
              {context.assessment_columns.map((c) => (
                isKCSE ? (
                  <CellFrag key={c.assessment_id} cols={2}>
                    <td className="num">{c.total_mark.toFixed(0)}</td>
                    <td>{c.grade}</td>
                  </CellFrag>
                ) : (
                  <CellFrag key={c.assessment_id} cols={3}>
                    <td className="num">{c.total_mark.toFixed(0)}</td>
                    <td>{c.grade}</td>
                    <td className="num">{c.points.toFixed(0)}</td>
                  </CellFrag>
                )
              ))}
              {isKCSE ? (
                <>
                  <td className="num">{context.total_avg_pct.toFixed(0)}</td>
                  <td>{context.performance_level}</td>
                  <td className="num">{context.total_avg_points.toFixed(0)}</td>
                </>
              ) : (
                <>
                  <td className="num">{context.total_avg_pct.toFixed(0)}</td>
                  <td>{context.performance_level}</td>
                  <td className="num">{context.total_avg_points.toFixed(0)}</td>
                </>
              )}
            </tr>
          </tbody>
        </table>

        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11.5px", marginTop: "8px" }}>
          <div><strong>Performance:</strong> <span className="rf-perf-badge">{context.performance_level}</span></div>
          <div><strong>Mean:</strong> {context.total_avg_pct}%</div>
          <div><strong>Rank:</strong> {context.rank ?? "—"} of {context.class_size ?? "—"}</div>
        </div>

        <table className="rf-trend">
          <thead>
            {isKCSE ? (
              <>
                <tr><th colSpan={4}></th><th colSpan={3}>FORM ONE</th><th colSpan={3}>FORM TWO</th></tr>
                <tr><th colSpan={4}>YEAR</th><th>T1</th><th>T2</th><th>T3</th><th>T1</th><th>T2</th><th>T3</th></tr>
              </>
            ) : context.template === "cbe_junior" ? (
              <>
                <tr><th colSpan={4}></th><th colSpan={3}>GRADE 7</th><th colSpan={3}>GRADE 8</th><th colSpan={3}>GRADE 9</th></tr>
                <tr><th colSpan={4}>YEAR</th><th>T1</th><th>T2</th><th>T3</th><th>T1</th><th>T2</th><th>T3</th><th>T1</th><th>T2</th><th>T3</th></tr>
              </>
            ) : (
              <>
                <tr><th colSpan={4}></th><th colSpan={3}>GRADE 10</th><th colSpan={3}>GRADE 11</th><th colSpan={3}>GRADE 12</th></tr>
                <tr><th colSpan={4}>YEAR</th><th>T1</th><th>T2</th><th>T3</th><th>T1</th><th>T2</th><th>T3</th><th>T1</th><th>T2</th><th>T3</th></tr>
              </>
            )}
          </thead>
          <tbody>
            <tr>
              <td colSpan={4} style={{ textAlign: "left", fontWeight: 700 }}>AVG POINTS</td>
              {Array.from({ length: isKCSE ? 6 : 9 }).map((_, i) => <td key={i} />)}
            </tr>
            <tr>
              <td colSpan={4} style={{ textAlign: "left", fontWeight: 700 }}>GRADE</td>
              {Array.from({ length: isKCSE ? 6 : 9 }).map((_, i) => <td key={i} />)}
            </tr>
          </tbody>
        </table>

        <div className="rf-comments">
          <div className="rf-comment-line">
            <span className="rf-comment-label">CONDUCT:</span>
            <span className="rf-comment-box">{data.comments?.conduct || ""}</span>
          </div>
          <div className="rf-comment-line">
            <span className="rf-comment-label">{isKCSE ? "FORM MASTER'S COMMENT:" : "CLASS TEACHER'S COMMENT:"}</span>
            <span className="rf-comment-box tall">{data.comments?.class_teacher_comment || ""}</span>
          </div>
          <div className="rf-comment-line">
            <span className="rf-comment-label">RECTOR'S COMMENT:</span>
            <span className="rf-comment-box tall">{data.comments?.rector_comment || ""}</span>
          </div>
          <div className="rf-comment-line">
            <span className="rf-comment-label">MISSION COMMENT &amp; STAMP:</span>
            <span className="rf-comment-box tall">{data.comments?.mission_comment || ""}</span>
          </div>
        </div>

        <div className="rf-bottom">
          <div className="rf-line"><span className="rf-label">Opening day next term:</span><span className="rf-value" /></div>
          <div className="rf-line"><span className="rf-label">Parent's signature:</span><span className="rf-value" /></div>
          <div className="rf-line"><span className="rf-label">Date:</span><span className="rf-value" /></div>
          <div />
        </div>
        <div className="rf-security">
          <strong>OFFICIAL DOCUMENT</strong> — Issued by Queen of Apostles Seminary Senior School. Any alteration, erasure, or unauthorized reproduction renders this report invalid.
          <span className="rf-security-code">VERIFY · {student.admission_number} · {new Date().toISOString().slice(0,10)} · QAS/SMARTPRO</span>
        </div>
      </div>
    </>
  );
}

function CellFrag({ cols, children }: { cols: number; children: React.ReactNode }) {
  void cols;
  return <>{children}</>;
}