import { useEffect, useMemo, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart,
  Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import {
  AlertTriangle, ArrowLeft, Award, BarChart3, CheckCircle2,
  Info, Target, TrendingDown, TrendingUp, Users,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import {
  fetchDashboard, listAssessments,
  type Assessment, type Dashboard, type Insight,
} from "../../services/analysis";

const BROWN = "#2b1a0f";
const BROWN2 = "#5a3a1e";
const SKY = "#22b4f0";
const CREAM = "#f5eee2";
const PALETTE = ["#22b4f0", "#f59e0b", "#10b981", "#ef4444", "#8b5cf6", "#ec4899", "#14b8a6", "#f97316"];
const GRADE_COLOR: Record<string, string> = {
  A: "#10b981", B: "#22b4f0", C: "#f59e0b", D: "#f97316", E: "#ef4444",
};

const cardStyle: React.CSSProperties = {
  background: "#fff",
  border: "1px solid #e5e7eb",
  borderRadius: "14px",
  padding: "1.1rem 1.25rem",
  boxShadow: "0 4px 14px rgba(10,18,29,0.05)",
};

function KpiCard({ label, value, sub, icon: Icon, accent }: {
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
        <div style={{ fontSize: "0.72rem", letterSpacing: "0.08em", textTransform: "uppercase", color: "#748095", fontWeight: 700 }}>
          {label}
        </div>
        <div style={{ fontSize: "1.55rem", fontWeight: 800, color: "#1e2e40", lineHeight: 1.15 }}>
          {value}
        </div>
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

export default function AnalysisDashboard() {
  const navigate = useNavigate();
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [data, setData] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listAssessments()
      .then((rows) => {
        setAssessments(rows);
        const latest = rows[rows.length - 1];
        if (latest) setSelected(latest.id);
      })
      .catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    if (!selected) return;
    setLoading(true);
    fetchDashboard(selected)
      .then(setData)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [selected]);

  const gradePie = useMemo(() => {
    if (!data) return [];
    return Object.entries(data.grade_distribution).map(([g, n]) => ({ name: g, value: n, fill: GRADE_COLOR[g] ?? "#94a3b8" }));
  }, [data]);

  const trendLine = useMemo(() => {
    if (!data) return [];
    return data.trend.map((t) => ({
      name: t.assessment_name.replace("Term 1 ", ""),
      mean: t.mean,
      pass_rate: t.pass_rate,
    }));
  }, [data]);

  if (error) {
    return <div style={{ padding: "2rem", color: "#991b1b" }}>Error: {error}</div>;
  }

  return (
    <div style={{ padding: "2rem", maxWidth: "1400px", margin: "0 auto" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "1rem", marginBottom: "1.5rem" }}>
        <div>
          <button type="button" onClick={() => navigate(-1)} style={{
            display: "inline-flex", alignItems: "center", gap: "6px",
            background: "transparent", border: "none", color: BROWN2,
            fontWeight: 600, cursor: "pointer", marginBottom: "6px",
          }}>
            <ArrowLeft size={16} /> Back
          </button>
          <h1 style={{ margin: 0, fontSize: "1.9rem", color: "#1e2e40", fontWeight: 800 }}>
            Academic Analysis
          </h1>
          <p style={{ margin: "4px 0 0", color: "#748095" }}>
            Statistical analysis &amp; insights across assessments, subjects and learners.
          </p>
        </div>
        <div>
          <label style={{ display: "block", fontSize: "0.72rem", letterSpacing: "0.08em", textTransform: "uppercase", color: "#748095", fontWeight: 700, marginBottom: "4px" }}>
            Assessment
          </label>
          <select
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            style={{
              padding: "0.55rem 0.9rem", border: `1px solid ${SKY}`,
              borderRadius: "10px", background: "#fff", fontWeight: 600,
              color: BROWN2, cursor: "pointer", minWidth: "220px",
            }}
          >
            {assessments.map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
        </div>
      </div>

      {data && (
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
            {data.assessment.name}
          </span>
          <span style={{ opacity: 0.5 }}>·</span>
          <span style={{ fontSize: "0.88rem", color: "#e8d9c2" }}>{data.assessment.date}</span>
          <span style={{ opacity: 0.5 }}>·</span>
          <span style={{ fontSize: "0.88rem", color: "#e8d9c2" }}>
            <strong style={{ color: "#6fcffb" }}>Whole school</strong> · {data.students} students · {data.subject_rows.length} subjects
          </span>
        </div>
      )}
      {loading || !data ? (
        <div style={{ padding: "3rem", textAlign: "center", color: "#94a3b8" }}>Loading analysis…</div>
      ) : (
        <>
          {/* KPI ROW */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1rem", marginBottom: "1.5rem" }}>
            <KpiCard label="Overall Mean" value={`${data.overall_mean}%`} sub={`Median ${data.overall_median}%`} icon={Target} accent={SKY} />
            <KpiCard label="Pass Rate" value={`${data.pass_rate}%`} sub="≥ 50%" icon={Award} accent="#10b981" />
            <KpiCard label="Students" value={data.students} sub={`${data.results} results`} icon={Users} accent="#8b5cf6" />
            <KpiCard label="Std Dev" value={data.overall_std_dev} sub={`High ${data.highest} · Low ${data.lowest}`} icon={BarChart3} accent="#f59e0b" />
          </div>

          {/* CHARTS ROW */}
          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "1rem", marginBottom: "1.5rem" }}>
            <div style={cardStyle}>
              <h3 style={{ margin: "0 0 0.75rem", color: BROWN2, fontSize: "0.95rem", fontWeight: 700, letterSpacing: "0.02em" }}>
                Subject Performance (mean %)
              </h3>
              <div style={{ width: "100%", height: 300 }}>
                <ResponsiveContainer>
                  <BarChart data={data.subject_rows} margin={{ top: 5, right: 15, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
                    <XAxis dataKey="subject_code" tick={{ fontSize: 12, fill: "#748095" }} />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 12, fill: "#748095" }} />
                    <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #e5e7eb" }} />
                    <Bar dataKey="mean" radius={[6, 6, 0, 0]}>
                      {data.subject_rows.map((row, i) => (
                        <Cell key={row.subject_id} fill={PALETTE[i % PALETTE.length]} />
                      ))}
                    </Bar>
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
                      {gradePie.map((entry) => (
                        <Cell key={entry.name} fill={entry.fill} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #e5e7eb" }} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* TREND + INSIGHTS */}
          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "1rem", marginBottom: "1.5rem" }}>
            <div style={cardStyle}>
              <h3 style={{ margin: "0 0 0.75rem", color: BROWN2, fontSize: "0.95rem", fontWeight: 700, letterSpacing: "0.02em" }}>
                Performance Trend
              </h3>
              <div style={{ width: "100%", height: 260 }}>
                <ResponsiveContainer>
                  <LineChart data={trendLine} margin={{ top: 5, right: 15, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
                    <XAxis dataKey="name" tick={{ fontSize: 12, fill: "#748095" }} />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 12, fill: "#748095" }} />
                    <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #e5e7eb" }} />
                    <Legend />
                    <Line type="monotone" dataKey="mean" stroke={SKY} strokeWidth={3} dot={{ r: 5 }} />
                    <Line type="monotone" dataKey="pass_rate" stroke="#10b981" strokeWidth={2} strokeDasharray="5 5" dot={{ r: 4 }} />
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
                {data.insights.length === 0 && (
                  <p style={{ color: "#94a3b8", fontSize: "0.85rem" }}>No insights generated.</p>
                )}
              </div>
            </div>
          </div>

          {/* SUBJECT TABLE */}
          <div style={{ ...cardStyle, marginBottom: "1.5rem", padding: 0, overflow: "hidden" }}>
            <div style={{ padding: "1rem 1.25rem", borderBottom: "1px solid #eef2f7" }}>
              <h3 style={{ margin: 0, color: BROWN2, fontSize: "0.95rem", fontWeight: 700, letterSpacing: "0.02em" }}>
                Subject Statistics
              </h3>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.86rem" }}>
                <thead>
                  <tr style={{ background: `linear-gradient(135deg, ${BROWN}, ${BROWN2})`, color: CREAM }}>
                    <th style={{ textAlign: "left", padding: "0.7rem 1rem", fontWeight: 700 }}>Subject</th>
                    <th style={{ textAlign: "right", padding: "0.7rem 1rem", fontWeight: 700 }}>Mean</th>
                    <th style={{ textAlign: "right", padding: "0.7rem 1rem", fontWeight: 700 }}>Median</th>
                    <th style={{ textAlign: "right", padding: "0.7rem 1rem", fontWeight: 700 }}>SD</th>
                    <th style={{ textAlign: "right", padding: "0.7rem 1rem", fontWeight: 700 }}>High</th>
                    <th style={{ textAlign: "right", padding: "0.7rem 1rem", fontWeight: 700 }}>Low</th>
                    <th style={{ textAlign: "right", padding: "0.7rem 1rem", fontWeight: 700 }}>Pass %</th>
                    <th style={{ textAlign: "left", padding: "0.7rem 1rem", fontWeight: 700 }}>Grades</th>
                  </tr>
                </thead>
                <tbody>
                  {data.subject_rows.map((row) => (
                    <tr key={row.subject_id} style={{ borderTop: "1px solid #f1f5f9" }}>
                      <td style={{ padding: "0.65rem 1rem", fontWeight: 600, color: "#1e2e40" }}>
                        {row.subject_name} <span style={{ color: "#94a3b8", fontWeight: 500 }}>({row.subject_code})</span>
                      </td>
                      <td style={{ padding: "0.65rem 1rem", textAlign: "right", fontWeight: 700, color: SKY }}>{row.mean}</td>
                      <td style={{ padding: "0.65rem 1rem", textAlign: "right" }}>{row.median}</td>
                      <td style={{ padding: "0.65rem 1rem", textAlign: "right", color: row.std_dev > 15 ? "#ef4444" : "#748095" }}>{row.std_dev}</td>
                      <td style={{ padding: "0.65rem 1rem", textAlign: "right", color: "#10b981" }}>{row.highest}</td>
                      <td style={{ padding: "0.65rem 1rem", textAlign: "right", color: "#ef4444" }}>{row.lowest}</td>
                      <td style={{ padding: "0.65rem 1rem", textAlign: "right" }}>
                        <span style={{
                          padding: "2px 10px", borderRadius: "999px", fontSize: "0.75rem", fontWeight: 700,
                          background: row.pass_rate >= 75 ? "#dcfce7" : row.pass_rate >= 50 ? "#fef3c7" : "#fee2e2",
                          color: row.pass_rate >= 75 ? "#166534" : row.pass_rate >= 50 ? "#92400e" : "#991b1b",
                        }}>{row.pass_rate}%</span>
                      </td>
                      <td style={{ padding: "0.65rem 1rem", fontSize: "0.78rem", color: "#748095" }}>
                        {Object.entries(row.grade_counts).map(([g, n]) => `${g}:${n}`).join(" ")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* RANKING */}
          <div style={{ ...cardStyle, padding: 0, overflow: "hidden" }}>
            <div style={{ padding: "1rem 1.25rem", borderBottom: "1px solid #eef2f7", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ margin: 0, color: BROWN2, fontSize: "0.95rem", fontWeight: 700, letterSpacing: "0.02em" }}>
                Class Ranking
              </h3>
              <span style={{ fontSize: "0.78rem", color: "#748095" }}>
                Competition ranking · ties share position
              </span>
            </div>
            <div style={{ overflowX: "auto", maxHeight: 480, overflowY: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.86rem" }}>
                <thead>
                  <tr style={{ background: "#f8fafc", color: "#748095", position: "sticky", top: 0 }}>
                    <th style={{ textAlign: "left", padding: "0.6rem 1rem", fontWeight: 700 }}>Rank</th>
                    <th style={{ textAlign: "left", padding: "0.6rem 1rem", fontWeight: 700 }}>Adm No</th>
                    <th style={{ textAlign: "left", padding: "0.6rem 1rem", fontWeight: 700 }}>Name</th>
                    <th style={{ textAlign: "right", padding: "0.6rem 1rem", fontWeight: 700 }}>Mean</th>
                    <th style={{ textAlign: "center", padding: "0.6rem 1rem", fontWeight: 700 }}>Grade</th>
                    <th style={{ textAlign: "center", padding: "0.6rem 1rem", fontWeight: 700 }}>Trend</th>
                  </tr>
                </thead>
                <tbody>
                  {data.ranking.map((r) => {
                    const top = r.rank <= 3;
                    return (
                      <tr key={r.student_id} style={{ borderTop: "1px solid #f1f5f9", background: top ? "#f0f9ff" : "transparent" }}>
                        <td style={{ padding: "0.55rem 1rem", fontWeight: 700, color: top ? SKY : "#1e2e40" }}>
                          {r.rank}
                        </td>
                        <td style={{ padding: "0.55rem 1rem", color: BROWN2, fontWeight: 600 }}>{r.admission_number}</td>
                        <td style={{ padding: "0.55rem 1rem" }}>{r.name}</td>
                        <td style={{ padding: "0.55rem 1rem", textAlign: "right", fontWeight: 700 }}>{r.mean}%</td>
                        <td style={{ padding: "0.55rem 1rem", textAlign: "center" }}>
                          <span style={{
                            padding: "2px 10px", borderRadius: "999px", fontSize: "0.75rem", fontWeight: 800,
                            background: (GRADE_COLOR[r.grade] ?? "#94a3b8") + "22",
                            color: GRADE_COLOR[r.grade] ?? "#64748b",
                          }}>{r.grade}</span>
                        </td>
                        <td style={{ padding: "0.55rem 1rem", textAlign: "center" }}>
                          {r.mean >= data.overall_mean ? (
                            <TrendingUp size={16} color="#10b981" />
                          ) : (
                            <TrendingDown size={16} color="#ef4444" />
                          )}
                        </td>
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