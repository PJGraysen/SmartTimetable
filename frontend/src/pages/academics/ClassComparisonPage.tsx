import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart,
  Pie, PieChart, PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar,
  RadarChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import {
  AlertTriangle, ArrowLeft, Award, BarChart3, CheckCircle2, Crown,
  Info, Layers, Target, TrendingDown, TrendingUp, Trophy, Users,
} from "lucide-react";
import {
  fetchClassComparison, listAssessments,
  type Assessment, type ClassComparison, type Insight,
} from "../../services/analysis";
import "../../styles/analysis.css";

const BROWN = "#2b1a0f", BROWN2 = "#5a3a1e", SKY = "#22b4f0", CREAM = "#f5eee2";
const PALETTE = ["#22b4f0", "#f59e0b", "#10b981", "#8b5cf6", "#ef4444", "#ec4899", "#14b8a6", "#f97316", "#6366f1", "#84cc16"];
const GRADE_COLOR: Record<string, string> = {
  A: "#10b981", B: "#22b4f0", C: "#f59e0b", D: "#f97316", E: "#ef4444", "-": "#94a3b8",
};

const cardStyle: React.CSSProperties = {
  background: "#fff", border: "1px solid #e5e7eb", borderRadius: "14px",
  padding: "1.1rem 1.25rem", boxShadow: "0 4px 14px rgba(10,18,29,0.05)",
};

function round1(n: number) { return Math.round(n * 10) / 10; }

// Auto-pair: strip a trailing single letter, group by base, return the largest multi-class group
function autoSelectPairs(all: Array<{ group_id: string; group_name: string }>): string[] {
  const bases = new Map<string, Array<{ id: string; name: string }>>();
  for (const c of all) {
    const m = c.group_name.match(/^(.*\S)\s*([A-Z])$/);
    const base = m ? m[1] : c.group_name;
    if (!bases.has(base)) bases.set(base, []);
    bases.get(base)!.push({ id: c.group_id, name: c.group_name });
  }
  let best: Array<{ id: string; name: string }> = [];
  for (const [, group] of bases) {
    if (group.length >= 2 && group.length > best.length) best = group;
  }
  return best.map((x) => x.id);
}

function InsightCard({ insight }: { insight: Insight }) {
  const map: Record<string, { bg: string; fg: string; icon: React.ComponentType<{ size?: number; color?: string }> }> = {
    positive: { bg: "#dcfce7", fg: "#166534", icon: CheckCircle2 },
    info:     { bg: "#e0f2fe", fg: "#075985", icon: Info },
    warning:  { bg: "#fef3c7", fg: "#92400e", icon: AlertTriangle },
    danger:   { bg: "#fee2e2", fg: "#991b1b", icon: AlertTriangle },
  };
  const entry = map[insight?.severity] ?? map.info;
  const Icon = entry.icon;
  return (
    <div style={{ display: "flex", gap: "10px", padding: "0.75rem 0.85rem", background: entry.bg, borderRadius: "10px", marginBottom: "8px" }}>
      <Icon size={18} color={entry.fg} />
      <div>
        <div style={{ fontWeight: 700, color: entry.fg, fontSize: "0.88rem" }}>{insight?.title ?? ""}</div>
        <div style={{ color: entry.fg, fontSize: "0.8rem", opacity: 0.85 }}>{insight?.detail ?? ""}</div>
      </div>
    </div>
  );
}

function Kpi({ label, value, sub, icon: Icon, accent, delay = 0 }: {
  label: string; value: string | number; sub?: string;
  icon: React.ComponentType<{ size?: number; color?: string }>; accent: string; delay?: number;
}) {
  return (
    <div
      className="anim-rise"
      style={{ ...cardStyle, display: "flex", alignItems: "center", gap: "14px", animationDelay: `${delay}ms` }}
    >
      <div style={{
        width: "48px", height: "48px", borderRadius: "12px", flexShrink: 0,
        background: `linear-gradient(135deg, ${accent}, ${accent}bb)`,
        color: "#fff", display: "flex", alignItems: "center", justifyContent: "center",
        boxShadow: `0 6px 16px ${accent}44`,
      }}>
        <Icon size={22} color="#fff" />
      </div>
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: "0.72rem", letterSpacing: "0.08em", textTransform: "uppercase", color: "#748095", fontWeight: 700 }}>{label}</div>
        <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "#1e2e40", lineHeight: 1.15 }}>{value}</div>
        {sub && <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>{sub}</div>}
      </div>
    </div>
  );
}

type TabKey = "overview" | "by-class" | "leaderboards";

export default function ClassComparisonPage() {
  const navigate = useNavigate();
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [data, setData] = useState<ClassComparison | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedClasses, setSelectedClasses] = useState<string[]>([]);
  const [tab, setTab] = useState<TabKey>("overview");

  useEffect(() => {
    listAssessments()
      .then((rows) => {
        setAssessments(rows);
        const latest = rows[rows.length - 1];
        if (latest) setSelected(latest.id);
        else setLoading(false);
      })
      .catch((e) => { setError(e instanceof Error ? e.message : String(e)); setLoading(false); });
  }, []);

  useEffect(() => {
    if (!selected) return;
    setLoading(true); setError(null);
    fetchClassComparison(selected)
      .then((res) => {
        setData(res);
        // Auto-select pairs on first load
        if (res.classes.length > 0 && selectedClasses.length === 0) {
          const auto = autoSelectPairs(res.classes);
          setSelectedClasses(auto.length > 0 ? auto : res.classes.map((c) => c.group_id));
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected]);

  const visibleClasses = useMemo(() => {
    if (!data) return [];
    if (selectedClasses.length === 0) return data.classes;
    return data.classes.filter((c) => selectedClasses.includes(c.group_id));
  }, [data, selectedClasses]);

  const chartData = useMemo(() => {
    if (!data) return [];
    return data.subjects.map((code) => {
      const row: Record<string, string | number> = { subject: code };
      for (const c of visibleClasses) {
        const v = c.subject_means?.[code];
        row[c.group_name] = typeof v === "number" ? v : 0;
      }
      return row;
    });
  }, [data, visibleClasses]);

  const gradeAggregate = useMemo(() => {
    if (!data) return [];
    const agg: Record<string, number> = {};
    for (const c of visibleClasses) {
      for (const sub of c.subject_full) {
        for (const [g, n] of Object.entries(sub.grade_counts ?? {})) {
          agg[g] = (agg[g] ?? 0) + n;
        }
      }
    }
    return Object.entries(agg).map(([g, n]) => ({ name: g, value: n, fill: GRADE_COLOR[g] ?? "#94a3b8" }));
  }, [data, visibleClasses]);

  function toggleClass(id: string) {
    setSelectedClasses((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  }

  if (error) return <div style={{ padding: "2rem", color: "#991b1b" }}>Error: {error}</div>;

  const classes = data?.classes ?? [];
  const subjects = data?.subjects ?? [];
  const subjectGaps = data?.subject_gaps ?? [];
  const insights = data?.insights ?? [];
  const leaderboard = data?.leaderboards?.per_subject ?? [];
  const leading = classes[0];
  const trailing = classes.length > 1 ? classes[classes.length - 1] : null;
  const span = leading && trailing ? round1(leading.overall_mean - trailing.overall_mean) : null;
  const biggestGap = subjectGaps[0];

  return (
    <div style={{ padding: "2rem", maxWidth: "1500px", margin: "0 auto" }}>
      <button type="button" onClick={() => navigate(-1)} style={{
        display: "inline-flex", alignItems: "center", gap: "6px",
        background: "transparent", border: "none", color: BROWN2,
        fontWeight: 600, cursor: "pointer", marginBottom: "1rem",
      }}><ArrowLeft size={16} /> Back</button>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "1rem", marginBottom: "1.25rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <div style={{
            width: "52px", height: "52px", borderRadius: "14px",
            background: `linear-gradient(135deg, ${SKY}, #0b5d8c)`,
            color: "#fff", display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 6px 18px rgba(34,180,240,0.35)",
          }}><Layers size={26} /></div>
          <div>
            <h1 style={{ margin: 0, fontSize: "1.7rem", color: "#1e2e40", fontWeight: 800 }}>
              Class &amp; Stream Comparison
            </h1>
            <p style={{ margin: "2px 0 0", color: "#748095", fontSize: "0.9rem" }}>
              Auto-paired streams, per-class detail, and per-subject leaderboards.
            </p>
          </div>
        </div>

        <select value={selected} onChange={(e) => setSelected(e.target.value)}
          style={{
            padding: "0.55rem 0.9rem", border: `1px solid ${SKY}`,
            borderRadius: "10px", background: "#fff", fontWeight: 600,
            color: BROWN2, cursor: "pointer", minWidth: "220px",
          }}>
          {assessments.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
        </select>
      </div>

      {/* NOW VIEWING banner */}
      {data && (
        <div className="anim-rise" style={{
          background: `linear-gradient(135deg, ${BROWN}, ${BROWN2})`,
          color: CREAM, borderRadius: "12px",
          padding: "0.85rem 1.25rem", marginBottom: "1.25rem",
          display: "flex", alignItems: "center", gap: "0.9rem",
          flexWrap: "wrap", boxShadow: "0 4px 14px rgba(43,26,15,0.25)",
        }}>
          <span style={{ fontSize: "0.68rem", letterSpacing: "0.14em", textTransform: "uppercase", color: "#6fcffb", fontWeight: 800 }}>
            NOW VIEWING
          </span>
          <span style={{ fontSize: "1.02rem", fontWeight: 700 }}>{data.assessment.name}</span>
          <span style={{ opacity: 0.5 }}>·</span>
          <span style={{ fontSize: "0.88rem", color: "#e8d9c2" }}>{data.assessment.date}</span>
          <span style={{ opacity: 0.5 }}>·</span>
          <span style={{ fontSize: "0.88rem", color: "#e8d9c2" }}>
            <strong style={{ color: "#6fcffb" }}>{visibleClasses.length} of {classes.length} classes</strong> selected · {subjects.length} subjects
          </span>
        </div>
      )}

      {error && <div style={{ padding: "0.8rem 1rem", borderRadius: "10px", background: "#fee2e2", color: "#991b1b", marginBottom: "1rem" }}>{error}</div>}

      {loading ? (
        <div style={{ padding: "3rem", textAlign: "center", color: "#94a3b8" }}>Loading…</div>
      ) : classes.length === 0 ? (
        <div style={{ padding: "3rem", textAlign: "center", color: "#94a3b8" }}>No data for this assessment yet.</div>
      ) : (
        <>
          {/* Class selector chips */}
          <div className="anim-rise" style={{
            ...cardStyle, marginBottom: "1.25rem",
            display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap",
          }}>
            <span style={{ fontSize: "0.72rem", letterSpacing: "0.08em", textTransform: "uppercase", color: "#748095", fontWeight: 700, marginRight: "4px" }}>
              Compare:
            </span>
            {classes.map((c, i) => {
              const on = selectedClasses.includes(c.group_id);
              return (
                <button
                  key={c.group_id}
                  type="button"
                  onClick={() => toggleClass(c.group_id)}
                  style={{
                    padding: "5px 12px", borderRadius: "999px",
                    border: on ? `1px solid ${PALETTE[i % PALETTE.length]}` : "1px solid #e5e7eb",
                    background: on ? `${PALETTE[i % PALETTE.length]}18` : "#fff",
                    color: on ? PALETTE[i % PALETTE.length] : "#64748b",
                    fontSize: "0.82rem", fontWeight: 700, cursor: "pointer",
                  }}
                >
                  {c.group_name}
                  <span style={{ fontWeight: 500, color: "#94a3b8", marginLeft: "6px" }}>{c.overall_mean}%</span>
                </button>
              );
            })}
            <button
              type="button"
              onClick={() => setSelectedClasses(classes.map((c) => c.group_id))}
              style={{
                marginLeft: "auto", padding: "5px 12px", borderRadius: "8px",
                border: "1px solid #cbd5e1", background: "#fff",
                color: "#475569", fontSize: "0.8rem", fontWeight: 600, cursor: "pointer",
              }}
            >
              All
            </button>
            <button
              type="button"
              onClick={() => {
                const auto = autoSelectPairs(classes);
                setSelectedClasses(auto.length > 0 ? auto : classes.map((c) => c.group_id));
              }}
              style={{
                padding: "5px 12px", borderRadius: "8px",
                border: `1px solid ${SKY}`, background: "#f0f9ff",
                color: SKY, fontSize: "0.8rem", fontWeight: 600, cursor: "pointer",
              }}
            >
              Auto-pair
            </button>
          </div>

          {/* Tabs */}
          <div className="anim-rise" style={{ display: "flex", gap: "6px", marginBottom: "1.25rem" }}>
            {([
              ["overview", "Overview", BarChart3],
              ["by-class", "By Class", Users],
              ["leaderboards", "Leaderboards", Trophy],
            ] as Array<[TabKey, string, React.ComponentType<{ size?: number }>]>).map(([k, label, Icon]) => {
              const on = tab === k;
              return (
                <button
                  key={k}
                  type="button"
                  onClick={() => setTab(k)}
                  style={{
                    display: "inline-flex", alignItems: "center", gap: "6px",
                    background: on ? BROWN2 : "#fff",
                    color: on ? CREAM : "#64748b",
                    border: on ? `1px solid ${BROWN2}` : "1px solid #e5e7eb",
                    padding: "0.6rem 1.1rem", borderRadius: "10px",
                    cursor: "pointer", fontWeight: 700, fontSize: "0.85rem",
                    transition: "all 200ms ease",
                  }}
                >
                  <Icon size={15} /> {label}
                </button>
              );
            })}
          </div>

          {/* ============ OVERVIEW ============ */}
          {tab === "overview" && (
            <>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1rem", marginBottom: "1.5rem" }}>
                <Kpi delay={0} label="Classes shown" value={visibleClasses.length} sub={`of ${classes.length}`} icon={Layers} accent={SKY} />
                <Kpi delay={60} label="Leading class" value={visibleClasses[0]?.group_name ?? "—"} sub={visibleClasses[0] ? `${visibleClasses[0].overall_mean}% · ${visibleClasses[0].overall_pass_rate}% pass` : ""} icon={Crown} accent="#10b981" />
                <Kpi delay={120} label="Largest gap" value={biggestGap ? `${biggestGap.gap} pts` : "—"} sub={biggestGap?.subject_code ?? ""} icon={Target} accent="#f59e0b" />
                <Kpi delay={180} label="Span (top→bottom)" value={span !== null ? `${span} pts` : "—"} sub="overall mean" icon={TrendingUp} accent="#8b5cf6" />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "1rem", marginBottom: "1.5rem" }}>
                <div className="anim-rise" style={cardStyle}>
                  <h3 style={{ margin: "0 0 0.75rem", color: BROWN2, fontSize: "0.95rem", fontWeight: 700, letterSpacing: "0.02em" }}>
                    Subject means by class
                  </h3>
                  <div style={{ width: "100%", height: 360 }}>
                    <ResponsiveContainer>
                      <BarChart data={chartData} margin={{ top: 5, right: 15, left: 0, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
                        <XAxis dataKey="subject" tick={{ fontSize: 12, fill: "#748095" }} />
                        <YAxis domain={[0, 100]} tick={{ fontSize: 12, fill: "#748095" }} />
                        <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #e5e7eb" }} />
                        <Legend />
                        {visibleClasses.map((c, i) => (
                          <Bar key={c.group_id} dataKey={c.group_name} fill={PALETTE[i % PALETTE.length]} radius={[6, 6, 0, 0]} />
                        ))}
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div className="anim-rise" style={{ ...cardStyle, animationDelay: "120ms" }}>
                  <h3 style={{ margin: "0 0 0.75rem", color: BROWN2, fontSize: "0.95rem", fontWeight: 700, letterSpacing: "0.02em" }}>
                    Grade distribution (all shown)
                  </h3>
                  <div style={{ width: "100%", height: 260 }}>
                    <ResponsiveContainer>
                      <PieChart>
                        <Pie data={gradeAggregate} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={50} outerRadius={90} paddingAngle={2}>
                          {gradeAggregate.map((entry) => <Cell key={entry.name} fill={entry.fill} />)}
                        </Pie>
                        <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #e5e7eb" }} />
                        <Legend />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div style={{ maxHeight: 130, overflowY: "auto", marginTop: "0.5rem" }}>
                    {insights.slice(0, 4).map((ins, i) => <InsightCard key={i} insight={ins} />)}
                  </div>
                </div>
              </div>

              <div className="anim-rise" style={{ ...cardStyle, padding: 0, overflow: "hidden", marginBottom: "1.5rem" }}>
                <div style={{ padding: "1rem 1.25rem", borderBottom: "1px solid #eef2f7" }}>
                  <h3 style={{ margin: 0, color: BROWN2, fontSize: "0.95rem", fontWeight: 700, letterSpacing: "0.02em" }}>
                    Class × Subject matrix
                  </h3>
                </div>
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.86rem" }}>
                    <thead>
                      <tr style={{ background: `linear-gradient(135deg, ${BROWN}, ${BROWN2})`, color: CREAM }}>
                        <th style={{ textAlign: "left", padding: "0.7rem 1rem" }}>Subject</th>
                        {visibleClasses.map((c) => (
                          <th key={c.group_id} style={{ textAlign: "right", padding: "0.7rem 1rem" }}>{c.group_name}</th>
                        ))}
                        <th style={{ textAlign: "right", padding: "0.7rem 1rem" }}>Gap</th>
                      </tr>
                    </thead>
                    <tbody>
                      {subjects.map((code) => {
                        const means = visibleClasses.map((c) => {
                          const v = c.subject_means?.[code];
                          return typeof v === "number" ? v : null;
                        });
                        const valid = means.filter((v): v is number => v !== null);
                        const best = valid.length ? Math.max(...valid) : null;
                        const worst = valid.length ? Math.min(...valid) : null;
                        const gap = best !== null && worst !== null ? round1(best - worst) : null;
                        return (
                          <tr key={code} style={{ borderTop: "1px solid #f1f5f9" }}>
                            <td style={{ padding: "0.65rem 1rem", fontWeight: 600, color: "#1e2e40" }}>{code}</td>
                            {means.map((v, i) => (
                              <td key={i} style={{
                                padding: "0.65rem 1rem", textAlign: "right",
                                fontWeight: v === best ? 800 : 500,
                                color: v === best ? "#10b981" : (v === worst && best !== worst) ? "#ef4444" : "#1e2e40",
                              }}>{v === null ? "—" : v}</td>
                            ))}
                            <td style={{ padding: "0.65rem 1rem", textAlign: "right", color: "#748095" }}>{gap === null ? "—" : gap}</td>
                          </tr>
                        );
                      })}
                      <tr style={{ background: "#f8fafc", borderTop: "2px solid #cbd5e1" }}>
                        <td style={{ padding: "0.7rem 1rem", fontWeight: 800, color: BROWN2 }}>OVERALL</td>
                        {visibleClasses.map((c) => (
                          <td key={c.group_id} style={{ padding: "0.7rem 1rem", textAlign: "right", fontWeight: 800, color: SKY }}>{c.overall_mean}</td>
                        ))}
                        <td style={{ padding: "0.7rem 1rem", textAlign: "right", color: "#748095", fontWeight: 700 }}>{span ?? "—"}</td>
                      </tr>
                      <tr>
                        <td style={{ padding: "0.7rem 1rem", fontWeight: 700, color: BROWN2 }}>Pass rate</td>
                        {visibleClasses.map((c) => (
                          <td key={c.group_id} style={{ padding: "0.7rem 1rem", textAlign: "right" }}>{c.overall_pass_rate}%</td>
                        ))}
                        <td />
                      </tr>
                      <tr>
                        <td style={{ padding: "0.7rem 1rem", fontWeight: 700, color: BROWN2 }}>Students</td>
                        {visibleClasses.map((c) => (
                          <td key={c.group_id} style={{ padding: "0.7rem 1rem", textAlign: "right" }}>{c.students}</td>
                        ))}
                        <td />
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Subject gaps */}
              <div className="anim-rise" style={{ ...cardStyle, padding: 0, overflow: "hidden" }}>
                <div style={{ padding: "1rem 1.25rem", borderBottom: "1px solid #eef2f7" }}>
                  <h3 style={{ margin: 0, color: BROWN2, fontSize: "0.95rem", fontWeight: 700, letterSpacing: "0.02em" }}>
                    Subject gaps — where classes diverge most
                  </h3>
                </div>
                <div style={{ overflowX: "auto" }}>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.86rem" }}>
                    <thead>
                      <tr style={{ background: "#f8fafc", color: "#748095" }}>
                        <th style={{ textAlign: "left", padding: "0.7rem 1rem" }}>Subject</th>
                        <th style={{ textAlign: "left", padding: "0.7rem 1rem" }}>Best</th>
                        <th style={{ textAlign: "right", padding: "0.7rem 1rem" }}>Best mean</th>
                        <th style={{ textAlign: "left", padding: "0.7rem 1rem" }}>Worst</th>
                        <th style={{ textAlign: "right", padding: "0.7rem 1rem" }}>Worst mean</th>
                        <th style={{ textAlign: "right", padding: "0.7rem 1rem" }}>Gap</th>
                      </tr>
                    </thead>
                    <tbody>
                      {subjectGaps.filter((g) => visibleClasses.some((c) => c.group_name === g.best_class) || visibleClasses.some((c) => c.group_name === g.worst_class)).map((g) => (
                        <tr key={g.subject_code} style={{ borderTop: "1px solid #f1f5f9" }}>
                          <td style={{ padding: "0.65rem 1rem", fontWeight: 600 }}>{g.subject_code}</td>
                          <td style={{ padding: "0.65rem 1rem", color: "#10b981" }}>{g.best_class}</td>
                          <td style={{ padding: "0.65rem 1rem", textAlign: "right", color: "#10b981", fontWeight: 700 }}>{g.best_mean}</td>
                          <td style={{ padding: "0.65rem 1rem", color: "#ef4444" }}>{g.worst_class}</td>
                          <td style={{ padding: "0.65rem 1rem", textAlign: "right", color: "#ef4444" }}>{g.worst_mean}</td>
                          <td style={{ padding: "0.65rem 1rem", textAlign: "right", fontWeight: 700 }}>{g.gap}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}

          {/* ============ BY CLASS ============ */}
          {tab === "by-class" && (
            <div style={{ display: "grid", gap: "1rem" }}>
              {visibleClasses.map((c, idx) => {
                const radarData = c.subject_full.map((s) => ({ subject: s.code, mean: s.mean, fullMark: 100 }));
                return (
                  <div key={c.group_id} className="anim-rise" style={{ ...cardStyle, animationDelay: `${idx * 60}ms` }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "0.8rem", flexWrap: "wrap" }}>
                      <div style={{
                        width: "42px", height: "42px", borderRadius: "10px",
                        background: `${PALETTE[idx % PALETTE.length]}22`,
                        color: PALETTE[idx % PALETTE.length],
                        display: "flex", alignItems: "center", justifyContent: "center",
                        fontWeight: 800, fontSize: "1.05rem",
                      }}>
                        #{c.rank}
                      </div>
                      <div style={{ flex: 1 }}>
                        <h3 style={{ margin: 0, color: "#1e2e40", fontSize: "1.1rem", fontWeight: 800 }}>{c.group_name}</h3>
                        <div style={{ fontSize: "0.82rem", color: "#748095" }}>
                          {c.students} students · mean {c.overall_mean}% · median {c.overall_median}% · SD {c.overall_std_dev} · pass {c.overall_pass_rate}%
                        </div>
                      </div>
                      {c.leading_subject && (
                        <span style={{
                          padding: "4px 12px", borderRadius: "999px",
                          background: "#dcfce7", color: "#166534",
                          fontSize: "0.78rem", fontWeight: 700,
                        }}>
                          🏆 Leading: {c.leading_subject.code} {c.leading_subject.mean}%
                        </span>
                      )}
                      {c.trailing_subject && c.leading_subject?.code !== c.trailing_subject.code && (
                        <span style={{
                          padding: "4px 12px", borderRadius: "999px",
                          background: "#fee2e2", color: "#991b1b",
                          fontSize: "0.78rem", fontWeight: 700,
                        }}>
                          ⚠ Needs work: {c.trailing_subject.code} {c.trailing_subject.mean}%
                        </span>
                      )}
                    </div>

                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1.2fr", gap: "1rem", marginBottom: "0.9rem" }}>
                      <div>
                        <div style={{ fontSize: "0.72rem", letterSpacing: "0.08em", textTransform: "uppercase", color: "#748095", fontWeight: 700, marginBottom: "4px" }}>
                          Subject profile
                        </div>
                        <div style={{ width: "100%", height: 240 }}>
                          <ResponsiveContainer>
                            <RadarChart data={radarData}>
                              <PolarGrid stroke="#e5e7eb" />
                              <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11, fill: "#748095" }} />
                              <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 9, fill: "#cbd5e1" }} />
                              <Radar dataKey="mean" stroke={PALETTE[idx % PALETTE.length]} fill={PALETTE[idx % PALETTE.length]} fillOpacity={0.35} />
                              <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #e5e7eb" }} />
                            </RadarChart>
                          </ResponsiveContainer>
                        </div>
                      </div>

                      <div>
                        <div style={{ fontSize: "0.72rem", letterSpacing: "0.08em", textTransform: "uppercase", color: "#748095", fontWeight: 700, marginBottom: "4px" }}>
                          Subject breakdown
                        </div>
                        <div style={{ overflowX: "auto", maxHeight: 240, overflowY: "auto" }}>
                          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem" }}>
                            <thead>
                              <tr style={{ background: "#f8fafc", color: "#748095", position: "sticky", top: 0 }}>
                                <th style={{ textAlign: "left", padding: "5px 8px" }}>Subj</th>
                                <th style={{ textAlign: "right", padding: "5px 8px" }}>Mean</th>
                                <th style={{ textAlign: "right", padding: "5px 8px" }}>SD</th>
                                <th style={{ textAlign: "right", padding: "5px 8px" }}>Hi</th>
                                <th style={{ textAlign: "right", padding: "5px 8px" }}>Lo</th>
                              </tr>
                            </thead>
                            <tbody>
                              {c.subject_full.map((s) => (
                                <tr key={s.code} style={{ borderTop: "1px solid #f1f5f9" }}>
                                  <td style={{ padding: "4px 8px", fontWeight: 700 }}>{s.code}</td>
                                  <td style={{ padding: "4px 8px", textAlign: "right", fontWeight: 700, color: SKY }}>{s.mean}</td>
                                  <td style={{ padding: "4px 8px", textAlign: "right", color: s.std_dev > 15 ? "#ef4444" : "#748095" }}>{s.std_dev}</td>
                                  <td style={{ padding: "4px 8px", textAlign: "right", color: "#10b981" }}>{s.highest}</td>
                                  <td style={{ padding: "4px 8px", textAlign: "right", color: "#ef4444" }}>{s.lowest}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </div>

                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
                      {c.best_student && (
                        <div style={{ padding: "8px 12px", borderRadius: "10px", background: "#f0fdf4", border: "1px solid #bbf7d0" }}>
                          <div style={{ fontSize: "0.68rem", fontWeight: 700, color: "#166534", letterSpacing: "0.06em", textTransform: "uppercase" }}>Top student</div>
                          <div style={{ fontWeight: 700, color: "#166534", fontSize: "0.9rem" }}>{c.best_student.name}</div>
                          <div style={{ fontSize: "0.75rem", color: "#16a34a" }}>{c.best_student.admission_number} · {c.best_student.mean}%</div>
                        </div>
                      )}
                      {c.worst_student && (
                        <div style={{ padding: "8px 12px", borderRadius: "10px", background: "#fef2f2", border: "1px solid #fecaca" }}>
                          <div style={{ fontSize: "0.68rem", fontWeight: 700, color: "#991b1b", letterSpacing: "0.06em", textTransform: "uppercase" }}>Needs intervention</div>
                          <div style={{ fontWeight: 700, color: "#991b1b", fontSize: "0.9rem" }}>{c.worst_student.name}</div>
                          <div style={{ fontSize: "0.75rem", color: "#dc2626" }}>{c.worst_student.admission_number} · {c.worst_student.mean}%</div>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* ============ LEADERBOARDS ============ */}
          {tab === "leaderboards" && (
            <div style={{ display: "grid", gap: "1rem" }}>
              {leaderboard.length === 0 ? (
                <div style={{ padding: "2rem", textAlign: "center", color: "#94a3b8" }}>No leaderboard data.</div>
              ) : leaderboard.map((row, i) => {
                const visibleByClass = row.by_class.filter((b) => visibleClasses.some((c) => c.group_id === b.group_id));
                if (visibleByClass.length === 0) return null;
                return (
                  <div key={row.subject_code} className="anim-rise" style={{ ...cardStyle, animationDelay: `${i * 40}ms`, padding: 0, overflow: "hidden" }}>
                    <div style={{ padding: "0.8rem 1.25rem", borderBottom: "1px solid #eef2f7", display: "flex", alignItems: "center", gap: "10px" }}>
                      <Award size={18} color={SKY} />
                      <h3 style={{ margin: 0, color: BROWN2, fontSize: "0.95rem", fontWeight: 800, letterSpacing: "0.02em" }}>
                        {row.subject_name} <span style={{ color: "#94a3b8", fontWeight: 500 }}>({row.subject_code})</span>
                      </h3>
                    </div>
                    <div style={{ overflowX: "auto" }}>
                      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.84rem" }}>
                        <thead>
                          <tr style={{ background: "#f8fafc", color: "#748095" }}>
                            <th style={{ textAlign: "left", padding: "0.6rem 1rem" }}>Class</th>
                            <th style={{ textAlign: "left", padding: "0.6rem 1rem" }}>🥇 Best</th>
                            <th style={{ textAlign: "left", padding: "0.6rem 1rem" }}>📈 Most improved</th>
                            <th style={{ textAlign: "left", padding: "0.6rem 1rem" }}>📉 Most declined</th>
                            <th style={{ textAlign: "left", padding: "0.6rem 1rem" }}>⚠ Worst</th>
                          </tr>
                        </thead>
                        <tbody>
                          {visibleByClass.map((b) => (
                            <tr key={b.group_id} style={{ borderTop: "1px solid #f1f5f9" }}>
                              <td style={{ padding: "0.6rem 1rem", fontWeight: 700, color: BROWN2 }}>{b.group_name}</td>
                              <td style={{ padding: "0.6rem 1rem" }}>
                                {b.best ? (
                                  <div>
                                    <div style={{ fontWeight: 700, color: "#166534" }}>{b.best.name}</div>
                                    <div style={{ fontSize: "0.72rem", color: "#16a34a" }}>{b.best.admission_number} · {b.best.pct}%</div>
                                  </div>
                                ) : <span style={{ color: "#cbd5e1" }}>—</span>}
                              </td>
                              <td style={{ padding: "0.6rem 1rem" }}>
                                {b.most_improved ? (
                                  <div>
                                    <div style={{ fontWeight: 700, color: "#075985" }}>{b.most_improved.name}</div>
                                    <div style={{ fontSize: "0.72rem", color: "#0284c7" }}>
                                      {b.most_improved.admission_number} · +{b.most_improved.delta} pts
                                    </div>
                                  </div>
                                ) : <span style={{ color: "#cbd5e1" }}>—</span>}
                              </td>
                              <td style={{ padding: "0.6rem 1rem" }}>
                                {b.most_declined ? (
                                  <div>
                                    <div style={{ fontWeight: 700, color: "#991b1b" }}>{b.most_declined.name}</div>
                                    <div style={{ fontSize: "0.72rem", color: "#dc2626" }}>
                                      {b.most_declined.admission_number} · {b.most_declined.delta} pts
                                    </div>
                                  </div>
                                ) : <span style={{ color: "#cbd5e1" }}>—</span>}
                              </td>
                              <td style={{ padding: "0.6rem 1rem" }}>
                                {b.worst ? (
                                  <div>
                                    <div style={{ fontWeight: 700, color: "#991b1b" }}>{b.worst.name}</div>
                                    <div style={{ fontSize: "0.72rem", color: "#dc2626" }}>{b.worst.admission_number} · {b.worst.pct}%</div>
                                  </div>
                                ) : <span style={{ color: "#cbd5e1" }}>—</span>}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}