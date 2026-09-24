import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, FileStack, Printer } from "lucide-react";
import http from "../../services/http";
import "../../styles/report.css";
import { fetchBulkReportForms, listTeachingGroups } from "../../services/analysis";

const BROWN2 = "#5a3a1e";
const SKY = "#22b4f0";

export default function BulkReportsPage() {
  const navigate = useNavigate();
  const [groups, setGroups] = useState<Array<{ id: string; name: string }>>([]);
  const [selected, setSelected] = useState("");
  const [data, setData] = useState<Array<Record<string, unknown>> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listTeachingGroups()
      .then((rows) => {
        setGroups(rows);
        if (rows.length > 0) setSelected(rows[0].id);
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  async function generate() {
    if (!selected) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetchBulkReportForms(selected);
      setData(res.students);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ padding: "2rem", maxWidth: "1100px", margin: "0 auto" }}>
<div className="no-print">
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
          }}><FileStack size={26} /></div>
          <div>
            <h1 style={{ margin: 0, fontSize: "1.7rem", color: "#1e2e40", fontWeight: 800 }}>
              Bulk Report Forms
            </h1>
            <p style={{ margin: "2px 0 0", color: "#748095", fontSize: "0.9rem" }}>
              Generate all report forms for a class — one print run gives the whole PDF.
            </p>
          </div>
        </div>

        <div style={{
          display: "flex", gap: "12px", alignItems: "end", flexWrap: "wrap",
          background: "#fff", border: "1px solid #e5e7eb", borderRadius: "14px",
          padding: "1.1rem 1.25rem", marginBottom: "1.5rem",
          boxShadow: "0 4px 14px rgba(10,18,29,0.05)",
        }}>
          <div style={{ minWidth: "260px" }}>
            <label style={{ fontSize: "0.72rem", fontWeight: 700, color: "#748095", letterSpacing: "0.06em" }}>CLASS</label>
            <select value={selected} onChange={(e) => setSelected(e.target.value)}
              style={{
                width: "100%", padding: "0.55rem 0.9rem",
                border: `1px solid ${SKY}`, borderRadius: "10px",
                background: "#fff", fontWeight: 600, color: BROWN2,
              }}>
              {groups.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
            </select>
          </div>
          <button
            type="button"
            onClick={generate}
            disabled={loading || !selected}
            style={{
              background: SKY, color: "#fff", border: "none",
              padding: "0.6rem 1.2rem", borderRadius: "10px",
              cursor: loading ? "not-allowed" : "pointer",
              fontWeight: 700, fontSize: "0.85rem",
            }}
          >
            {loading ? "Generating…" : "Generate"}
          </button>
          {data && data.length > 0 && (
            <button
              type="button"
              onClick={() => window.print()}
              style={{
                display: "inline-flex", alignItems: "center", gap: "6px",
                background: "#10b981", color: "#fff", border: "none",
                padding: "0.6rem 1.2rem", borderRadius: "10px",
                cursor: "pointer", fontWeight: 700, fontSize: "0.85rem",
                marginLeft: "auto",
              }}
            >
              <Printer size={16} /> Print {data.length} forms
            </button>
          )}
        </div>

        {error && (
          <div style={{
            padding: "0.8rem 1rem", borderRadius: "10px",
            background: "#fee2e2", color: "#991b1b", marginBottom: "1rem",
          }}>{error}</div>
        )}
      </div>

      {data && data.length > 0 && (
        <div className="bulk-wrap">
          {data.map((form, idx) => (
            <BulkReportPage key={idx} form={form as any} index={idx + 1} total={data.length} />
          ))}
        </div>
      )}

      {data && data.length === 0 && (
        <div style={{ padding: "3rem", textAlign: "center", color: "#94a3b8" }}>
          No students in that class.
        </div>
      )}
    </div>
  );
}

function BulkReportPage({ form, index, total }: { form: any; index: number; total: number }) {
  if (!form || form.error) {
    return (
      <div className="bulk-report-page">
      <div className="rf-watermark">{student.admission_number} · OFFICIAL</div>
        <div style={{ padding: "2rem", textAlign: "center", color: "#991b1b" }}>
          Error generating report {index}: {form?.error ?? "unknown"}
        </div>
      </div>
    );
  }

  const { student, context, subjects, school } = form;
  const isKCSE = context.template === "kcse";

  return (
    <div className="bulk-report-page">
      <div className="rf-watermark">{student.admission_number} · OFFICIAL</div>
      <div style={{ textAlign: "center", fontSize: "10px", color: "#94a3b8", marginBottom: "4px" }}>
        Page {index} of {total}
      </div>

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
                <th colSpan={2}>EXAM 1</th>
                <th colSpan={2}>EXAM 2</th>
                <th colSpan={2}>EXAM 3</th>
                <th colSpan={3}>RESULT</th>
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
          {subjects.map((row: any) => {
            const cols = context.assessment_columns;
            const a0 = cols[0] ? row.marks[cols[0].assessment_id] : null;
            const a1 = cols[1] ? row.marks[cols[1].assessment_id] : null;
            const a2 = cols[2] ? row.marks[cols[2].assessment_id] : null;
            if (isKCSE) {
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
            {context.assessment_columns.map((c: any) => (
              isKCSE ? (
                <React.Fragment key={c.assessment_id}>
                  <td className="num">{c.total_mark.toFixed(0)}</td>
                  <td>{c.grade}</td>
                </React.Fragment>
              ) : (
                <React.Fragment key={c.assessment_id}>
                  <td className="num">{c.total_mark.toFixed(0)}</td>
                  <td>{c.grade}</td>
                  <td className="num">{c.points.toFixed(0)}</td>
                </React.Fragment>
              )
            ))}
            <td className="num">{context.total_avg_pct.toFixed(0)}</td>
            <td>{context.performance_level}</td>
            <td className="num">{context.total_avg_points.toFixed(0)}</td>
          </tr>
        </tbody>
      </table>

      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11.5px", marginTop: "8px" }}>
        <div><strong>Performance:</strong> <span className="rf-perf-badge">{context.performance_level}</span></div>
        <div><strong>Mean:</strong> {context.total_avg_pct}%</div>
        <div><strong>Rank:</strong> {context.rank ?? "—"} of {context.class_size ?? "—"}</div>
      </div>

      <div className="rf-comments">
        <div className="rf-comment-line">
          <span className="rf-comment-label">CONDUCT:</span>
          <span className="rf-comment-box">{form.comments?.conduct || ""}</span>
        </div>
        <div className="rf-comment-line">
          <span className="rf-comment-label">{isKCSE ? "FORM MASTER'S COMMENT:" : "CLASS TEACHER'S COMMENT:"}</span>
          <span className="rf-comment-box tall">{form.comments?.class_teacher_comment || ""}</span>
        </div>
        <div className="rf-comment-line">
          <span className="rf-comment-label">RECTOR'S COMMENT:</span>
          <span className="rf-comment-box tall">{form.comments?.rector_comment || ""}</span>
        </div>
        <div className="rf-comment-line">
          <span className="rf-comment-label">MISSION COMMENT &amp; STAMP:</span>
          <span className="rf-comment-box tall">{form.comments?.mission_comment || ""}</span>
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
  );
}

import React from "react";