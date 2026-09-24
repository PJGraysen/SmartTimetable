import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart,
  Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import {
  AlertTriangle, ArrowLeft, Award, BarChart3, CheckCircle2, Gauge,
  Info, Target, TrendingDown, TrendingUp, Users,
} from "lucide-react";
import {
  fetchStudentDeepAnalysis,
  type Insight, type StudentDeepAnalysis,
} from "../../services/analysis";

const BROWN = "#2b1a0f";
const BROWN2 = "#5a3a1e";
const SKY = "#22b4f0";
const CREAM = "#f5eee2";
const GRADE_COLOR: Record<string, string> = {
  A: "#10b981", B: "#22b4f0", C: "#f59e0b", D: "#f97316", E: "#ef4444", "-": "#94a3b8",
};

const cardStyle: React.CSSProperties = {
  background: "#fff", border: "1px solid #e5e7eb", borderRadius: "14px",
  padding: "1.1rem 1.25rem", boxShadow: "0 4px 14px rgba(10,18,29,0.05)",
};

function Kpi({ label, value, sub, icon: Icon, accent }: {
  label: string; value: string | number; sub?: string;
  icon: React.ComponentType<{ size?: number; color?: string }>; accent: string;
}) {
  return (
    <div style={{ ...cardStyle, display: "flex", alignItems: "center", gap: "14px" }}>
      <div style={{
        width: "48px", height: "48px", borderRadius: "12px", flexShrink: 0,
        background: `linear-gradient(135deg, ${accent}, ${accent}bb)`,
        color: "#fff", display: "flex", alignItems: "center", justifyContent: "center",
        boxShadow: `0 6px 16px ${accent}44`,
      }}>
        <Icon size={22} color="#fff" />
      </div>
      <div>
        <div style={{ fontSize: "0.72rem", letterSpacing: "0.08em", textTransform: "uppercase", color: "#748095", fontWeight: 700 }}>{label}</div>
        <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "#1e2e40", lineHeight: 1.15 }}>{value}</div>
        {sub && <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>{sub}</div>}
      </div>
    </div>
  );
}

function InsightCard({ insight }: { insight: Insight }) {
  const map: Record<Insight["severity"], { bg: string; fg: string; icon: React.ComponentType<{ size?: number; color?: string }> }> = {
    positive: { bg: "#dcfce7", fg: "#166534", icon: CheckCircle2 },
    info:     { bg: "#e0f2fe", fg: "#075985", icon: Info },
    warning:  { bg: "#fef3c7", fg: "#92400e", icon: AlertTriangle },
    danger:   { bg: "#fee2e2", fg: "#991b1b", icon: AlertTriangle },
  };
  const { bg, fg, icon: Icon } = map[insight.severity];
  return (
    <div style={{ display: "flex", gap: "10px", padding: "0.75rem 0.85rem", background: bg, borderRadius: "10px", marginBottom: "8px" }}>
      <Icon size={18} color={fg} />
      <div>
        <div style={{ fontWeight: 700, color: fg, fontSize: "0.88rem" }}>{insight.title}</div>
        <div style={{ color: fg, fontSize: "0.8rem", opacity: 0.85 }}>{insight.detail}</div>
      </div>
    </div>
  );
}

function TrendBadge({ trend, delta }: { trend: string; delta: number }) {
  if (trend === "improving") {
    return (
      <span style={{
        display: "inline-flex", alignItems: "center", gap: "3px",
        padding: "2px 8px", borderRadius: "999px", fontSize: "0.72rem", fontWeight: 700,
        background: "#dcfce7", color: "#166534",
      }}>
        <TrendingUp size={11} /> +{delta}
      </span>
    );
  }
  if (trend === "declining") {
    return (
      <span style={{
        display: "inline-flex", alignItems: "center", gap: "3px",
        padding: "2px 8px", borderRadius: "999px", fontSize: "0.72rem", fontWeight: 700,
        background: "#fee2e2", color: "#991b1b",
      }}>
        <TrendingDown size={11} /> {delta}
      </span>
    );
  }
  return <span style={{ fontSize: "0.72rem", color: "#94a3b8" }}>stable</span>;
}

export default function StudentAnalysisPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<StudentDeepAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    fetchStudentDeepAnalysis(id)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [id]);

  const gradePie = useMemo(() => {
    if (!data) return [];
    return Object.entries(data.grade_distribution).map(([g, n]) => ({
      name: g, value: n, fill: GRADE_COLOR[g] ?? "#94a3b8",
    }));
  }, [data]);

  const subjectBar = useMemo(() => {
    if (!data) return [];
    return data.subject_rows.map((r) => ({
      subject: r.subject_code,
      student: r.mean,
      class: r.class_mean ?? 0,
    }));
  }, [data]);

  const historyLine = useMemo(() => {
    if (!data) return [];
    return data.history.map((h) => ({
      name: h.assessment_name.replace("Term 1 ", ""),
      mean_pct: h.mean_pct,
      total: h.total,
    }));
  }, [data]);

  if (loading) {
    return <div style={{ padding: "3rem", textAlign: "center", color: "#94a3b8" }}>Loading student analysis…</div>;
  }
  if (error || !data) {
    return <div style={{ padding: "2rem", color: "#991b1b" }}>Error: {error ?? "No data"}</div>;
  }

  const s = data.summary;

  return (
    <div style={{ padding: "2rem", maxWidth: "1400px", margin: "0 auto" }}>
      <button
        type="button"
        onClick={() => navigate("/academics/students")}
        style={{
          display: "inline-flex", alignItems: "center", gap: "6px",
          background: "transparent", border: "none", color: BROWN2,
          fontWeight: 600, cursor: "pointer", marginBottom: "1rem",
        }}
      >
        <ArrowLeft size={16} /> Back to students
      </button>

      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: "16px", marginBottom: "1.5rem" }}>
        <div style={{
          width: "64px", height: "64px", borderRadius: "16px",
          background: `linear-gradient(135deg, ${BROWN}, ${BROWN2})`,
          color: CREAM, display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: "1.35rem", fontWeight: 800, boxShadow: "0 8px 20px rgba(43,26,15,0.35)",
        }}>
          {data.student.name.split(" ").slice(0, 2).map((p) => p[0]).join("")}
        </div>
        <div>
          <h1 style={{ margin: 0, fontSize: "1.85rem", color: "#1e2e40", fontWeight: 800 }}>
            {data.student.name}
          </h1>
          <div style={{ color: "#748095", fontSize: "0.9rem", display: "flex", gap: "14px", flexWrap: "wrap" }}>
            <span><strong style={{ color: BROWN2 }}>{data.student.admission_number}</strong></span>
            {data.teaching_group && <span>{data.teaching_group.name}</span>}
            <span style={{
              padding: "2px 10px", borderRadius: "999px", fontSize: "0.72rem", fontWeight: 700,
              background: data.student.status === "ACTIVE" ? "#dcfce7" : "#f1f5f9",
              color: data.student.status === "ACTIVE" ? "#166534" : "#64748b",
            }}>{data.student.status}</span>
          </div>
        </div>
      </div>

      <div style={{
        background: "linear-gradient(135deg, #2b1a0f, #5a3a1e)",
        color: "#f5eee2",
        borderRadius: "12px",
        padding: "0.85rem 1.25rem",
        marginBottom: "1.25rem",
        display: "flex",
        alignItems: "center",
        gap: "0.9rem",
        flexWrap: "wrap",
        boxShadow: "0 4px 14px rgba(43,26,15,0.25)",
      }}>
        <span style={{ fontSize: "0.68rem", letterSpacing: "0.14em", textTransform: "uppercase", color: "#6fcffb", fontWeight: 800 }}>
          NOW VIEWING
        </span>
        <span style={{ fontSize: "1.02rem", fontWeight: 700 }}>
          {data.student.name}
        </span>
        <span style={{ opacity: 0.5 }}>·</span>
        <span style={{ fontSize: "0.88rem", color: "#e8d9c2" }}>{data.student.admission_number}</span>
        {data.teaching_group && (
          <>
            <span style={{ opacity: 0.5 }}>·</span>
            <span style={{ fontSize: "0.88rem", color: "#e8d9c2" }}>
              <strong style={{ color: "#6fcffb" }}>{data.teaching_group.name}</strong>
            </span>
          </>
        )}
        <span style={{ opacity: 0.5 }}>·</span>
        <span style={{ fontSize: "0.88rem", color: "#e8d9c2" }}>
          {s.subjects_count} subjects · {s.assessments_count} assessments
        </span>
      </div>
      {/* KPI row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1rem", marginBottom: "1.5rem" }}>
        <Kpi label="Mean" value={`${s.overall_mean}%`} sub={`Median ${s.overall_median}%`} icon={Target} accent={SKY} />
        <Kpi label="Overall Grade" value={s.overall_grade} sub={`${s.overall_points} points avg`} icon={Award} accent="#10b981" />
        <Kpi label="Class Rank" value={s.rank ? `#${s.rank}` : "—"} sub={s.class_size ? `of ${s.class_size} · ${s.percentile}%ile` : ""} icon={Users} accent="#8b5cf6" />
        <Kpi label="Std Dev" value={s.overall_std_dev} sub={`Consistency`} icon={BarChart3} accent="#f59e0b" />
        <Kpi label="Subjects" value={s.subjects_count} sub={`${s.assessments_count} assessments`} icon={Gauge} accent="#ec4899" />
        <Kpi
          label="vs Class Mean"
          value={s.vs_class_mean !== null ? `${s.vs_class_mean > 0 ? "+" : ""}${s.vs_class_mean}` : "—"}
          sub={s.class_mean !== null ? `Class ${s.class_mean}%` : ""}
          icon={TrendingUp}
          accent="#14b8a6"
        />
      </div>

      {/* Charts row 1 */}
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "1rem", marginBottom: "1.5rem" }}>
        <div style={cardStyle}>
          <h3 style={{ margin: "0 0 0.75rem", color: BROWN2, fontSize: "0.95rem", fontWeight: 700, letterSpacing: "0.02em" }}>
            Subject Performance — Student vs Class
          </h3>
          <div style={{ width: "100%", height: 300 }}>
            <ResponsiveContainer>
              <BarChart data={subjectBar} margin={{ top: 5, right: 15, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
                <XAxis dataKey="subject" tick={{ fontSize: 12, fill: "#748095" }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 12, fill: "#748095" }} />
                <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #e5e7eb" }} />
                <Legend />
                <Bar dataKey="student" fill={SKY} radius={[6, 6, 0, 0]} name="Student" />
                <Bar dataKey="class" fill="#cbd5e1" radius={[6, 6, 0, 0]} name="Class mean" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div style={cardStyle}>
          <h3 style={{ margin: "0 0 0.75rem", color: BROWN2, fontSize: "0.95rem", fontWeight: 700, letterSpacing: "0.02em" }}>
            Grade Distribution
          </h3>
          <div style={{ width: "100%", height: 300 }}>
            <ResponsiveContainer>
              <PieChart>
                <Pie data={gradePie} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={55} outerRadius={95} paddingAngle={2}>
                  {gradePie.map((entry) => <Cell key={entry.name} fill={entry.fill} />)}
                </Pie>
                <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #e5e7eb" }} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Trend + Insights */}
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "1rem", marginBottom: "1.5rem" }}>
        <div style={cardStyle}>
          <h3 style={{ margin: "0 0 0.75rem", color: BROWN2, fontSize: "0.95rem", fontWeight: 700, letterSpacing: "0.02em" }}>
            Performance History
          </h3>
          <div style={{ width: "100%", height: 260 }}>
            <ResponsiveContainer>
              <LineChart data={historyLine} margin={{ top: 5, right: 15, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
                <XAxis dataKey="name" tick={{ fontSize: 12, fill: "#748095" }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 12, fill: "#748095" }} />
                <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #e5e7eb" }} />
                <Legend />
                <Line type="monotone" dataKey="mean_pct" stroke={SKY} strokeWidth={3} dot={{ r: 5 }} name="Mean %" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div style={cardStyle}>
          <h3 style={{ margin: "0 0 0.75rem", color: BROWN2, fontSize: "0.95rem", fontWeight: 700, letterSpacing: "0.02em" }}>
            Automated Insights
          </h3>
          <div style={{ maxHeight: 260, overflowY: "auto" }}>
            {data.insights.map((ins, i) => <InsightCard key={i} insight={ins} />)}
          </div>
        </div>
      </div>

      {/* Strengths / Weaknesses */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.5rem" }}>
        <div style={{ ...cardStyle, background: "linear-gradient(135deg, #f0fdf4, #fff)" }}>
          <h3 style={{ margin: "0 0 0.5rem", color: "#166534", fontSize: "0.95rem", fontWeight: 700 }}>
            ✓ Strengths
          </h3>
          <ul style={{ margin: 0, paddingLeft: "1.1rem", color: "#166534" }}>
            {data.strengths.map((x) => <li key={x} style={{ fontSize: "0.9rem" }}>{x}</li>)}
            {data.strengths.length === 0 && <li style={{ color: "#94a3b8", listStyle: "none", marginLeft: "-1.1rem" }}>Not enough data</li>}
          </ul>
        </div>
        <div style={{ ...cardStyle, background: "linear-gradient(135deg, #fef2f2, #fff)" }}>
          <h3 style={{ margin: "0 0 0.5rem", color: "#991b1b", fontSize: "0.95rem", fontWeight: 700 }}>
            ⚠ Development Areas
          </h3>
          <ul style={{ margin: 0, paddingLeft: "1.1rem", color: "#991b1b" }}>
            {data.weaknesses.map((x) => <li key={x} style={{ fontSize: "0.9rem" }}>{x}</li>)}
            {data.weaknesses.length === 0 && <li style={{ color: "#94a3b8", listStyle: "none", marginLeft: "-1.1rem" }}>None flagged</li>}
          </ul>
        </div>
      </div>

      {/* Subject table */}
      <div style={{ ...cardStyle, padding: 0, overflow: "hidden", marginBottom: "1.5rem" }}>
        <div style={{ padding: "1rem 1.25rem", borderBottom: "1px solid #eef2f7" }}>
          <h3 style={{ margin: 0, color: BROWN2, fontSize: "0.95rem", fontWeight: 700, letterSpacing: "0.02em" }}>
            Subject Breakdown
          </h3>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.86rem" }}>
            <thead>
              <tr style={{ background: `linear-gradient(135deg, ${BROWN}, ${BROWN2})`, color: CREAM }}>
                <th style={{ textAlign: "left", padding: "0.7rem 1rem" }}>Subject</th>
                <th style={{ textAlign: "right", padding: "0.7rem 1rem" }}>Mean</th>
                <th style={{ textAlign: "right", padding: "0.7rem 1rem" }}>Class</th>
                <th style={{ textAlign: "right", padding: "0.7rem 1rem" }}>Δ</th>
                <th style={{ textAlign: "right", padding: "0.7rem 1rem" }}>SD</th>
                <th style={{ textAlign: "right", padding: "0.7rem 1rem" }}>High</th>
                <th style={{ textAlign: "right", padding: "0.7rem 1rem" }}>Low</th>
                <th style={{ textAlign: "center", padding: "0.7rem 1rem" }}>Grade</th>
                <th style={{ textAlign: "center", padding: "0.7rem 1rem" }}>Trend</th>
              </tr>
            </thead>
            <tbody>
              {data.subject_rows.map((r) => (
                <tr key={r.subject_id} style={{ borderTop: "1px solid #f1f5f9" }}>
                  <td style={{ padding: "0.65rem 1rem", fontWeight: 600, color: "#1e2e40" }}>
                    {r.subject_name} <span style={{ color: "#94a3b8", fontWeight: 500 }}>({r.subject_code})</span>
                  </td>
                  <td style={{ padding: "0.65rem 1rem", textAlign: "right", fontWeight: 700, color: SKY }}>{r.mean}</td>
                  <td style={{ padding: "0.65rem 1rem", textAlign: "right", color: "#748095" }}>{r.class_mean ?? "—"}</td>
                  <td style={{ padding: "0.65rem 1rem", textAlign: "right", fontWeight: 700, color: r.vs_class === null ? "#94a3b8" : r.vs_class >= 0 ? "#10b981" : "#ef4444" }}>
                    {r.vs_class === null ? "—" : `${r.vs_class > 0 ? "+" : ""}${r.vs_class}`}
                  </td>
                  <td style={{ padding: "0.65rem 1rem", textAlign: "right", color: r.std_dev > 15 ? "#ef4444" : "#748095" }}>{r.std_dev}</td>
                  <td style={{ padding: "0.65rem 1rem", textAlign: "right", color: "#10b981" }}>{r.highest}</td>
                  <td style={{ padding: "0.65rem 1rem", textAlign: "right", color: "#ef4444" }}>{r.lowest}</td>
                  <td style={{ padding: "0.65rem 1rem", textAlign: "center" }}>
                    <span style={{
                      padding: "2px 10px", borderRadius: "999px", fontSize: "0.75rem", fontWeight: 800,
                      background: (GRADE_COLOR[r.grade] ?? "#94a3b8") + "22",
                      color: GRADE_COLOR[r.grade] ?? "#64748b",
                    }}>{r.grade}</span>
                  </td>
                  <td style={{ padding: "0.65rem 1rem", textAlign: "center" }}>
                    <TrendBadge trend={r.trend} delta={r.delta} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* History table */}
      <div style={{ ...cardStyle, padding: 0, overflow: "hidden" }}>
        <div style={{ padding: "1rem 1.25rem", borderBottom: "1px solid #eef2f7" }}>
          <h3 style={{ margin: 0, color: BROWN2, fontSize: "0.95rem", fontWeight: 700, letterSpacing: "0.02em" }}>
            Assessment History
          </h3>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.86rem" }}>
            <thead>
              <tr style={{ background: "#f8fafc", color: "#748095" }}>
                <th style={{ textAlign: "left", padding: "0.7rem 1rem" }}>Assessment</th>
                <th style={{ textAlign: "left", padding: "0.7rem 1rem" }}>Date</th>
                <th style={{ textAlign: "right", padding: "0.7rem 1rem" }}>Total</th>
                <th style={{ textAlign: "right", padding: "0.7rem 1rem" }}>Mean %</th>
                <th style={{ textAlign: "center", padding: "0.7rem 1rem" }}>Grade</th>
                <th style={{ textAlign: "right", padding: "0.7rem 1rem" }}>Subjects</th>
              </tr>
            </thead>
            <tbody>
              {data.history.map((h) => (
                <tr key={h.assessment_id} style={{ borderTop: "1px solid #f1f5f9" }}>
                  <td style={{ padding: "0.65rem 1rem", fontWeight: 600 }}>{h.assessment_name}</td>
                  <td style={{ padding: "0.65rem 1rem", color: "#748095" }}>{h.date}</td>
                  <td style={{ padding: "0.65rem 1rem", textAlign: "right" }}>{h.total} / {h.total_max}</td>
                  <td style={{ padding: "0.65rem 1rem", textAlign: "right", fontWeight: 700, color: SKY }}>{h.mean_pct}%</td>
                  <td style={{ padding: "0.65rem 1rem", textAlign: "center" }}>
                    <span style={{
                      padding: "2px 10px", borderRadius: "999px", fontSize: "0.75rem", fontWeight: 800,
                      background: (GRADE_COLOR[h.grade] ?? "#94a3b8") + "22",
                      color: GRADE_COLOR[h.grade] ?? "#64748b",
                    }}>{h.grade}</span>
                  </td>
                  <td style={{ padding: "0.65rem 1rem", textAlign: "right", color: "#748095" }}>{h.subjects_sat}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}