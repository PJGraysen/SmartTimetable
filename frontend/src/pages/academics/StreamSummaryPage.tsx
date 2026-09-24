import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart,
  PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import {
  ArrowLeft, BarChart3, Crown, FileText, LineChart as LineChartIcon,
  Minus, Printer, Target, TrendingDown, TrendingUp, Users,
} from "lucide-react";
import {
  listAssessments, fetchStreamSummary, fetchStreamTrend, fetchClassComparison,
  type Assessment, type ClassComparison, type StreamSummary, type StreamStudentSummary,
  type StreamSubjectSummary, type StreamTrend,
} from "../../services/analysis";
import { fetchMarksContext, type MarksContext } from "../../services/assessments";
import "../../styles/analysis.css";

const BROWN = "#2b1a0f", BROWN2 = "#5a3a1e", SKY = "#22b4f0", CREAM = "#f5eee2";
const GREEN = "#10b981", RED = "#ef4444", AMBER = "#f59e0b";
const PALETTE = ["#22b4f0","#f59e0b","#10b981","#8b5cf6","#ef4444","#ec4899","#14b8a6","#f97316"];
const GRADE_COLOR: Record<string,string> = { A:"#10b981", B:"#22b4f0", C:"#f59e0b", D:"#f97316", E:"#ef4444", "-":"#94a3b8" };

const cardStyle: React.CSSProperties = {
  background:"#fff", border:"1px solid #e5e7eb", borderRadius:"14px",
  padding:"1rem 1.15rem", boxShadow:"0 4px 14px rgba(10,18,29,0.05)",
};

const PRINT_CSS = `
  @media print {
    @page { size: A4 portrait; margin: 8mm; }

    html, body, #root {
      margin: 0 !important; padding: 0 !important;
      background: #fff !important;
    }

    /* Hide everything */
    body * { visibility: hidden !important; }

    /* Show only the printable report */
    #printable, #printable * { visibility: visible !important; }

    /* Elements we explicitly hide in print (toolbar, tabs, back button) */
    .no-print, .no-print * { display: none !important; visibility: hidden !important; }

    /* The wrapper that contains #printable should flatten in print */
    .stream-report-page {
      display: block !important;
      position: static !important;
      padding: 0 !important;
      margin: 0 !important;
      max-width: 100% !important;
      width: 100% !important;
      background: #fff !important;
      overflow: visible !important;
      height: auto !important;
    }

    #printable {
      display: block !important;
      position: static !important;
      width: 100% !important;
      max-width: 100% !important;
      max-height: none !important;
      overflow: visible !important;
      background: #fff !important;
    }

    .printable-section { display: none; }
    #printable[data-scope="current"]  .printable-section.is-active                                { display: block !important; }
    #printable[data-scope="class"]    .printable-section[data-section="class"]                    { display: block !important; }
    #printable[data-scope="students"] .printable-section[data-section="students"]                 { display: block !important; }
    #printable[data-scope="subjects"] .printable-section[data-section="subjects"]                 { display: block !important; }
    #printable[data-scope="leaderboards"] .printable-section[data-section="leaderboards"]         { display: block !important; }
    #printable[data-scope="full"]     .printable-section                                          { display: block !important; }

    .print-student-page {
      page-break-after: always; break-after: page;
      page-break-inside: avoid; break-inside: avoid;
    }
    .print-student-page:last-child { page-break-after: auto; break-after: auto; }

    .student-card, .subject-card, .class-card, .trend-card {
      page-break-inside: avoid; break-inside: avoid;
    }
  }

  /* Non-print (on-screen): only the active tab is visible */
  .printable-section { display: none; }
  .printable-section.is-active { display: block; }
`;

type TabKey = "class" | "students" | "subjects" | "leaderboards";
type PrintScope = "current" | "class" | "students" | "subjects" | "leaderboards" | "full";
type ChartType = "line" | "bar";

function RankBadge({ rank }: { rank: number }) {
  const top = rank <= 3;
  return (
    <span style={{
      display:"inline-flex", alignItems:"center", justifyContent:"center",
      minWidth:"28px", height:"28px", padding:"0 8px", borderRadius:"999px",
      background: top ? `linear-gradient(135deg, ${SKY}, #0b5d8c)` : "#f1f5f9",
      color: top ? "#fff" : "#64748b", fontWeight: 800, fontSize:"0.78rem",
    }}>#{rank}</span>
  );
}

function TrendPill({ trend, delta }: { trend: string; delta: number }) {
  if (trend === "improving") return <span style={{ color: GREEN, fontWeight: 700, fontSize:"0.8rem", display:"inline-flex", alignItems:"center", gap:"3px" }}><TrendingUp size={13}/> +{delta}</span>;
  if (trend === "declining") return <span style={{ color: RED, fontWeight: 700, fontSize:"0.8rem", display:"inline-flex", alignItems:"center", gap:"3px" }}><TrendingDown size={13}/> {delta}</span>;
  return <span style={{ color:"#94a3b8", fontSize:"0.8rem", display:"inline-flex", alignItems:"center", gap:"3px" }}><Minus size={13}/> stable</span>;
}

function ChartTypeToggle({ value, onChange }: { value: ChartType; onChange: (v: ChartType) => void }) {
  return (
    <div className="no-print" style={{ display:"inline-flex", gap:"4px", background:"#f1f5f9", borderRadius:"8px", padding:"3px" }}>
      {(["line","bar"] as ChartType[]).map((t) => {
        const on = value === t;
        return (
          <button key={t} type="button" onClick={() => onChange(t)} style={{
            display:"inline-flex", alignItems:"center", gap:"4px",
            background: on ? "#fff" : "transparent",
            color: on ? BROWN2 : "#64748b",
            border:"none", padding:"4px 10px", borderRadius:"6px",
            cursor:"pointer", fontWeight:700, fontSize:"0.72rem",
            boxShadow: on ? "0 1px 3px rgba(0,0,0,0.08)" : "none",
          }}>
            {t === "line" ? <LineChartIcon size={12}/> : <BarChart3 size={12}/>} {t === "line" ? "Line" : "Bar"}
          </button>
        );
      })}
    </div>
  );
}

type SeriesSpec = { key: string; color: string; name: string; dashed?: boolean };

function TrendChart({
  data, series, type, height = 240,
}: { data: Array<Record<string, number | string>>; series: SeriesSpec[]; type: ChartType; height?: number }) {
  if (!data || data.length < 2) {
    return <div style={{ fontSize:"0.75rem", color:"#cbd5e1", padding:"0.5rem" }}>needs ≥ 2 exams</div>;
  }
  return (
    <div style={{ width:"100%", height }}>
      <ResponsiveContainer>
        {type === "line" ? (
          <LineChart data={data} margin={{ top: 5, right: 15, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
            <XAxis dataKey="name" tick={{ fontSize: 11, fill:"#748095" }} />
            <YAxis domain={[0,100]} tick={{ fontSize: 11, fill:"#748095" }} />
            <Tooltip contentStyle={{ borderRadius: 8, border:"1px solid #e5e7eb" }} />
            <Legend />
            {series.map((s) => (
              <Line key={s.key} type="monotone" dataKey={s.key} stroke={s.color} strokeWidth={2} dot={{ r: 3 }} name={s.name} strokeDasharray={s.dashed ? "5 5" : undefined} />
            ))}
          </LineChart>
        ) : (
          <BarChart data={data} margin={{ top: 5, right: 15, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
            <XAxis dataKey="name" tick={{ fontSize: 11, fill:"#748095" }} />
            <YAxis domain={[0,100]} tick={{ fontSize: 11, fill:"#748095" }} />
            <Tooltip contentStyle={{ borderRadius: 8, border:"1px solid #e5e7eb" }} />
            <Legend />
            {series.map((s) => (
              <Bar key={s.key} dataKey={s.key} fill={s.color} name={s.name} radius={[4,4,0,0]} />
            ))}
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}

function StudentTrendChart({ points, type }: { points: Array<{ name: string; mean: number }>; type: ChartType }) {
  if (!points || points.length < 2) return <div style={{ fontSize:"0.7rem", color:"#cbd5e1" }}>needs ≥2 exams</div>;
  return (
    <div style={{ width:"100%", height: 90 }}>
      <ResponsiveContainer>
        {type === "line" ? (
          <LineChart data={points} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
            <XAxis dataKey="name" tick={{ fontSize: 8, fill:"#94a3b8" }} interval={0}/>
            <YAxis domain={[0,100]} tick={{ fontSize: 8, fill:"#cbd5e1" }} />
            <Tooltip contentStyle={{ fontSize: 10, borderRadius: 4 }} />
            <Line type="monotone" dataKey="mean" stroke={SKY} strokeWidth={2} dot={{ r: 3 }} />
          </LineChart>
        ) : (
          <BarChart data={points} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
            <XAxis dataKey="name" tick={{ fontSize: 8, fill:"#94a3b8" }} interval={0}/>
            <YAxis domain={[0,100]} tick={{ fontSize: 8, fill:"#cbd5e1" }} />
            <Tooltip contentStyle={{ fontSize: 10, borderRadius: 4 }} />
            <Bar dataKey="mean" fill={SKY} radius={[3,3,0,0]} />
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}

function StudentCard({ s, streamName, trend, chartType }: {
  s: StreamStudentSummary; streamName: string; chartType: ChartType;
  trend?: { points: Array<{ name: string; mean: number }>; delta: number; trend: string };
}) {
  return (
    <div className="student-card print-student-page" style={{ ...cardStyle }}>
      <div style={{ display:"flex", alignItems:"center", gap:"10px", marginBottom:"0.6rem" }}>
        <RankBadge rank={s.rank} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 800, color:"#1e2e40", fontSize:"1rem" }}>{s.name}</div>
          <div style={{ fontSize:"0.75rem", color:"#748095" }}>{s.admission_number} · {streamName}</div>
        </div>
        <span style={{
          padding:"2px 10px", borderRadius:"999px", fontSize:"0.72rem", fontWeight:800,
          background:(GRADE_COLOR[s.grade] ?? "#94a3b8") + "22",
          color: GRADE_COLOR[s.grade] ?? "#64748b",
        }}>{s.grade}</span>
      </div>

      <div style={{ display:"flex", gap:"14px", fontSize:"0.78rem", color:"#475569", flexWrap:"wrap", marginBottom:"0.5rem" }}>
        <span>Mean <strong style={{ color: BROWN2 }}>{s.mean}%</strong></span>
        <span>SD <strong style={{ color: BROWN2 }}>{s.std}</strong></span>
        <span>Subjects <strong style={{ color: BROWN2 }}>{s.subjects_count}</strong></span>
        {trend && <TrendPill trend={trend.trend} delta={trend.delta} />}
      </div>

      <div style={{ display:"grid", gridTemplateColumns:"1fr 1.2fr", gap:"0.8rem" }}>
        <div>
          <div style={{ fontSize:"0.66rem", fontWeight:800, color:"#94a3b8", letterSpacing:"0.08em", marginBottom:"2px" }}>SUBJECT PROFILE (vs class)</div>
          <div style={{ width:"100%", height: 200 }}>
            <ResponsiveContainer>
              <RadarChart data={s.radar ?? []}>
                <PolarGrid stroke="#e5e7eb" />
                <PolarAngleAxis dataKey="subject" tick={{ fontSize: 9, fill:"#748095" }} />
                <PolarRadiusAxis domain={[0,100]} tick={{ fontSize: 8, fill:"#cbd5e1" }} />
                <Radar dataKey="student" stroke={SKY} fill={SKY} fillOpacity={0.4} />
                <Radar dataKey="class" stroke="#cbd5e1" fill="#cbd5e1" fillOpacity={0.15} />
                <Tooltip contentStyle={{ borderRadius: 6, border:"1px solid #e5e7eb", fontSize: 11 }} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div>
          <div style={{ fontSize:"0.66rem", fontWeight:800, color:"#94a3b8", letterSpacing:"0.08em", marginBottom:"2px" }}>SUBJECT BREAKDOWN</div>
          <table style={{ width:"100%", borderCollapse:"collapse", fontSize:"0.78rem" }}>
            <thead>
              <tr style={{ color:"#748095", fontSize:"0.7rem" }}>
                <th style={{ textAlign:"left", padding:"2px 4px" }}>Subj</th>
                <th style={{ textAlign:"right", padding:"2px 4px" }}>Me</th>
                <th style={{ textAlign:"right", padding:"2px 4px" }}>Class</th>
                <th style={{ textAlign:"center", padding:"2px 4px" }}>Gr</th>
              </tr>
            </thead>
            <tbody>
              {(s.subjects ?? []).map((r) => (
                <tr key={r.code} style={{ borderTop:"1px solid #f1f5f9" }}>
                  <td style={{ padding:"2px 4px", fontWeight:700 }}>{r.code}</td>
                  <td style={{ padding:"2px 4px", textAlign:"right", fontWeight:700, color: SKY }}>{r.pct}</td>
                  <td style={{ padding:"2px 4px", textAlign:"right", color:"#94a3b8" }}>{r.class_mean ?? "—"}</td>
                  <td style={{ padding:"2px 4px", textAlign:"center" }}>
                    <span style={{
                      padding:"0 6px", borderRadius:"999px", fontSize:"0.66rem", fontWeight:800,
                      background:(GRADE_COLOR[r.grade] ?? "#94a3b8") + "22",
                      color: GRADE_COLOR[r.grade] ?? "#64748b",
                    }}>{r.grade}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {trend && (
            <>
              <div style={{ fontSize:"0.66rem", fontWeight:800, color:"#94a3b8", letterSpacing:"0.08em", marginTop:"6px", marginBottom:"2px" }}>TREND (last {trend.points.length})</div>
              <StudentTrendChart points={trend.points} type={chartType} />
            </>
          )}
        </div>
      </div>

      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:"8px", marginTop:"0.6rem" }}>
        <div style={{ padding:"6px 10px", borderRadius:"8px", background:"#f0fdf4", border:"1px solid #bbf7d0" }}>
          <div style={{ fontSize:"0.62rem", fontWeight:800, color:"#166534", letterSpacing:"0.06em", textTransform:"uppercase" }}>Strengths</div>
          <div style={{ fontSize:"0.78rem", color:"#166534" }}>{(s.strengths ?? []).join(" · ") || "—"}</div>
        </div>
        <div style={{ padding:"6px 10px", borderRadius:"8px", background:"#fef2f2", border:"1px solid #fecaca" }}>
          <div style={{ fontSize:"0.62rem", fontWeight:800, color:"#991b1b", letterSpacing:"0.06em", textTransform:"uppercase" }}>Development</div>
          <div style={{ fontSize:"0.78rem", color:"#991b1b" }}>{(s.weaknesses ?? []).join(" · ") || "—"}</div>
        </div>
      </div>
    </div>
  );
}

export default function StreamSummaryPage() {
  const navigate = useNavigate();
  const [ctx, setCtx] = useState<MarksContext | null>(null);
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [assessmentId, setAssessmentId] = useState("");
  const [streamId, setStreamId] = useState("");
  const [data, setData] = useState<StreamSummary | null>(null);
  const [trend, setTrend] = useState<StreamTrend | null>(null);
  const [classCmp, setClassCmp] = useState<ClassComparison | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<TabKey>("class");
  const [printScope, setPrintScope] = useState<PrintScope>("current");
  const [trendChart, setTrendChart] = useState<ChartType>("line");

  useEffect(() => {
    Promise.all([fetchMarksContext(), listAssessments()])
      .then(([c, a]) => {
        setCtx(c); setAssessments(a);
        if (a.length && !assessmentId) setAssessmentId(a[a.length - 1].id);
        if (c.classes.length && !streamId) setStreamId(c.classes[0].id);
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!assessmentId || !streamId) return;
    setLoading(true); setError(null);
    Promise.all([
      fetchStreamSummary(assessmentId, streamId),
      fetchStreamTrend(streamId, 3).catch(() => null),
      fetchClassComparison(assessmentId).catch(() => null),
    ])
      .then(([s, tr, cmp]) => { setData(s); setTrend(tr); setClassCmp(cmp); })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [assessmentId, streamId]);

  const subjectBar = useMemo(() => {
    if (!data) return [];
    return (data.subjects ?? []).map((s) => ({ code: s.code, mean: s.mean }));
  }, [data]);

  const classTrendData = useMemo(() => {
    if (!trend || !trend.class_trend) return [];
    return trend.class_trend.map((p) => ({ name: p.name.replace("Term 1 ", ""), mean: p.mean, pass_rate: p.pass_rate ?? 0 }));
  }, [trend]);

  const subjectTrendSeries = useMemo(() => {
    if (!trend || !trend.subject_trends) return [];
    const codes = Object.keys(trend.subject_trends);
    const names = trend.assessments.map((a) => a.name.replace("Term 1 ", ""));
    return names.map((n, i) => {
      const row: Record<string, string | number> = { name: n };
      codes.forEach((code) => {
        const pt = trend.subject_trends[code].points[i];
        row[code] = pt ? pt.mean : 0;
      });
      return row;
    });
  }, [trend]);

  const subjectTrendCodes = useMemo(() => trend ? Object.keys(trend.subject_trends) : [], [trend]);

  const tabBtn = (key: TabKey, label: string, Icon: React.ComponentType<{ size?: number }>) => {
    const on = tab === key;
    return (
      <button type="button" onClick={() => setTab(key)} className="no-print" style={{
        display:"inline-flex", alignItems:"center", gap:"6px",
        background: on ? BROWN2 : "#fff",
        color: on ? CREAM : "#64748b",
        border: on ? `1px solid ${BROWN2}` : "1px solid #e5e7eb",
        padding:"0.55rem 1rem", borderRadius:"10px",
        cursor:"pointer", fontWeight:700, fontSize:"0.85rem",
      }}>
        <Icon size={14}/> {label}
      </button>
    );
  };

  return (
    <>
      <style>{PRINT_CSS}</style>
      <div className="stream-report-page" style={{ padding:"2rem", maxWidth:"1400px", margin:"0 auto" }}>
        <button type="button" onClick={() => navigate(-1)} className="no-print" style={{
          display:"inline-flex", alignItems:"center", gap:"6px",
          background:"transparent", border:"none", color:BROWN2,
          fontWeight:600, cursor:"pointer", marginBottom:"1rem",
        }}><ArrowLeft size={16}/> Back</button>

        <div className="no-print" style={{ display:"flex", alignItems:"center", justifyContent:"space-between", flexWrap:"wrap", gap:"1rem", marginBottom:"1.25rem" }}>
          <div style={{ display:"flex", alignItems:"center", gap:"14px" }}>
            <div style={{
              width:"52px", height:"52px", borderRadius:"14px",
              background:`linear-gradient(135deg, ${SKY}, #0b5d8c)`, color:"#fff",
              display:"flex", alignItems:"center", justifyContent:"center",
              boxShadow:"0 6px 18px rgba(34,180,240,0.35)",
            }}><FileText size={26}/></div>
            <div>
              <h1 style={{ margin:0, fontSize:"1.7rem", color:"#1e2e40", fontWeight:800 }}>
                Class &amp; Stream Report
              </h1>
              <p style={{ margin:"2px 0 0", color:"#748095", fontSize:"0.9rem" }}>
                A4 report with trends, per-student cards, subject insights, and printable scope selector.
              </p>
            </div>
          </div>

          <div style={{ display:"flex", gap:"8px", flexWrap:"wrap", alignItems:"center" }}>
            <select value={assessmentId} onChange={(e) => setAssessmentId(e.target.value)}
              style={{ padding:"0.5rem 0.8rem", border:`1px solid ${SKY}`, borderRadius:"9px", fontWeight:600, color:BROWN2, background:"#fff", minWidth:"150px" }}>
              {assessments.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
            <select value={streamId} onChange={(e) => setStreamId(e.target.value)}
              style={{ padding:"0.5rem 0.8rem", border:`1px solid ${SKY}`, borderRadius:"9px", fontWeight:600, color:BROWN2, background:"#fff", minWidth:"150px" }}>
              {(ctx?.classes ?? []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <select value={printScope} onChange={(e) => setPrintScope(e.target.value as PrintScope)}
              style={{ padding:"0.5rem 0.8rem", border:`1px solid ${BROWN2}`, borderRadius:"9px", fontWeight:600, color:BROWN2, background:"#fff" }}>
              <option value="current">Print: Current tab</option>
              <option value="class">Print: Class overview</option>
              <option value="students">Print: All students</option>
              <option value="subjects">Print: All subjects</option>
              <option value="leaderboards">Print: Leaderboards</option>
              <option value="full">Print: Full packet</option>
            </select>
            <button type="button" onClick={() => window.print()} style={{
              display:"inline-flex", alignItems:"center", gap:"6px",
              background:SKY, color:"#fff", border:"none",
              padding:"0.55rem 1rem", borderRadius:"10px",
              cursor:"pointer", fontWeight:700, fontSize:"0.85rem",
            }}><Printer size={15}/> Print</button>
          </div>
        </div>

        <div className="no-print" style={{ display:"flex", gap:"6px", marginBottom:"1.25rem", flexWrap:"wrap" }}>
          {tabBtn("class", "Class Overview", BarChart3)}
          {tabBtn("students", "Students", Users)}
          {tabBtn("subjects", "Subjects", Target)}
          {tabBtn("leaderboards", "Leaderboards", Crown)}
        </div>

        {error && <div className="no-print" style={{ padding:"0.7rem 1rem", borderRadius:"10px", background:"#fee2e2", color:"#991b1b", marginBottom:"1rem" }}>{error}</div>}
        {loading && <div className="no-print" style={{ padding:"2rem", textAlign:"center", color:"#94a3b8" }}>Loading…</div>}

        {!loading && data && (
          <div id="printable" data-scope={printScope}>
            <div style={{ textAlign:"center", borderBottom:`3px double ${BROWN}`, paddingBottom:"0.5rem", marginBottom:"0.9rem" }}>
              <div style={{ fontSize:"1.15rem", fontWeight:800, letterSpacing:"0.06em", color:BROWN }}>QUEEN OF APOSTLES SEMINARY SENIOR SCHOOL</div>
              <div style={{ fontSize:"0.8rem", color:BROWN2, fontWeight:700, marginTop:"2px" }}>
                {data.stream?.name ?? "Stream"} · {data.assessment.name} · {data.assessment.date}
              </div>
            </div>

            {/* ========== CLASS OVERVIEW ========== */}
            <div className={`printable-section ${tab === "class" ? "is-active" : ""}`} data-section="class">
              <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit, minmax(160px, 1fr))", gap:"0.7rem", marginBottom:"1rem" }}>
                {[
                  { label:"Mean", value:`${data.class_stats?.mean ?? "—"}%` },
                  { label:"Median", value:`${data.class_stats?.median ?? "—"}%` },
                  { label:"Std Dev", value:data.class_stats?.std_dev ?? "—" },
                  { label:"Pass Rate", value:`${data.class_stats?.pass_rate ?? "—"}%` },
                  { label:"Highest", value:`${data.class_stats?.highest ?? "—"}%` },
                  { label:"Lowest", value:`${data.class_stats?.lowest ?? "—"}%` },
                  { label:"Students", value:data.class_stats?.student_count ?? 0 },
                  { label:"Results", value:data.class_stats?.count ?? 0 },
                ].map((k) => (
                  <div key={k.label} className="class-card" style={{ ...cardStyle }}>
                    <div style={{ fontSize:"0.66rem", letterSpacing:"0.08em", textTransform:"uppercase", color:"#748095", fontWeight:800 }}>{k.label}</div>
                    <div style={{ fontSize:"1.35rem", fontWeight:800, color:"#1e2e40" }}>{k.value}</div>
                  </div>
                ))}
              </div>

              <div className="trend-card" style={cardStyle}>
                <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"0.5rem" }}>
                  <h3 style={{ margin:0, color:BROWN2, fontSize:"0.95rem", fontWeight:800 }}>
                    <LineChartIcon size={14} style={{ marginRight: 6, verticalAlign:"middle" }}/> Class mean trend (last {classTrendData.length} exams)
                  </h3>
                  <ChartTypeToggle value={trendChart} onChange={setTrendChart} />
                </div>
                <TrendChart
                  data={classTrendData}
                  series={[
                    { key: "mean", color: SKY, name: "Mean %" },
                    { key: "pass_rate", color: GREEN, name: "Pass %", dashed: true },
                  ]}
                  type={trendChart}
                />
              </div>

              <div style={{ ...cardStyle, marginTop:"0.9rem" }}>
                <h3 style={{ margin:"0 0 0.5rem", color:BROWN2, fontSize:"0.95rem", fontWeight:800 }}>Subject means (current assessment)</h3>
                <div style={{ width:"100%", height: 240 }}>
                  <ResponsiveContainer>
                    <BarChart data={subjectBar}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
                      <XAxis dataKey="code" tick={{ fontSize: 11, fill:"#748095" }} />
                      <YAxis domain={[0,100]} tick={{ fontSize: 11, fill:"#748095" }} />
                      <Tooltip contentStyle={{ borderRadius: 8, border:"1px solid #e5e7eb" }} />
                      <Bar dataKey="mean" radius={[6,6,0,0]}>
                        {subjectBar.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {classCmp && (classCmp.classes ?? []).length > 1 && (
                <div style={{ ...cardStyle, marginTop:"0.9rem" }}>
                  <h3 style={{ margin:"0 0 0.5rem", color:BROWN2, fontSize:"0.95rem", fontWeight:800 }}>Cross-stream comparison</h3>
                  <table style={{ width:"100%", borderCollapse:"collapse", fontSize:"0.82rem" }}>
                    <thead>
                      <tr style={{ background:`linear-gradient(135deg, ${BROWN}, ${BROWN2})`, color:CREAM }}>
                        <th style={{ textAlign:"left", padding:"5px 8px" }}>Class</th>
                        <th style={{ textAlign:"right", padding:"5px 8px" }}>Mean</th>
                        <th style={{ textAlign:"right", padding:"5px 8px" }}>Pass %</th>
                        <th style={{ textAlign:"right", padding:"5px 8px" }}>Students</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(classCmp.classes ?? []).map((c) => (
                        <tr key={c.group_id} style={{ borderTop:"1px solid #f1f5f9", background: c.group_id === streamId ? "#f0f9ff" : "transparent" }}>
                          <td style={{ padding:"5px 8px", fontWeight:700, color:BROWN2 }}>{c.group_name}</td>
                          <td style={{ padding:"5px 8px", textAlign:"right", fontWeight:700, color:SKY }}>{c.overall_mean}</td>
                          <td style={{ padding:"5px 8px", textAlign:"right" }}>{c.overall_pass_rate}%</td>
                          <td style={{ padding:"5px 8px", textAlign:"right" }}>{c.students}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* ========== STUDENTS ========== */}
            <div className={`printable-section ${tab === "students" ? "is-active" : ""}`} data-section="students">
              <div className="no-print" style={{ display:"flex", justifyContent:"flex-end", marginBottom:"0.6rem" }}>
                <ChartTypeToggle value={trendChart} onChange={setTrendChart} />
              </div>
              <div style={{ display:"grid", gap:"0.9rem" }}>
                {(data.students ?? []).map((s) => (
                  <StudentCard key={s.id} s={s} streamName={data.stream?.name ?? ""} trend={trend?.student_trends[s.id]} chartType={trendChart} />
                ))}
              </div>
            </div>

            {/* ========== SUBJECTS ========== */}
            <div className={`printable-section ${tab === "subjects" ? "is-active" : ""}`} data-section="subjects">
              <div className="trend-card" style={{ ...cardStyle, marginBottom:"0.9rem" }}>
                <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"0.5rem" }}>
                  <h3 style={{ margin:0, color:BROWN2, fontSize:"0.95rem", fontWeight:800 }}>
                    <LineChartIcon size={14} style={{ marginRight: 6, verticalAlign:"middle" }}/> Subject trends (last {subjectTrendSeries.length} exams)
                  </h3>
                  <ChartTypeToggle value={trendChart} onChange={setTrendChart} />
                </div>
                <TrendChart
                  data={subjectTrendSeries}
                  series={subjectTrendCodes.map((code, i) => ({ key: code, color: PALETTE[i % PALETTE.length], name: code }))}
                  type={trendChart}
                  height={260}
                />
              </div>

              <div style={{ display:"grid", gap:"0.8rem" }}>
                {(data.subjects ?? []).map((s: StreamSubjectSummary) => {
                  const tr = trend?.subject_trends[s.code];
                  return (
                    <div key={s.code} className="subject-card" style={{ ...cardStyle }}>
                      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"0.4rem", flexWrap:"wrap", gap:"8px" }}>
                        <div>
                          <h3 style={{ margin:0, fontSize:"0.98rem", fontWeight:800, color:"#1e2e40" }}>
                            {s.name} <span style={{ color:"#94a3b8", fontWeight:500 }}>({s.code})</span>
                          </h3>
                          <div style={{ fontSize:"0.74rem", color:"#748095" }}>
                            {s.candidates} candidates · pass {s.pass_rate}%
                            {tr && <span style={{ marginLeft:"8px" }}><TrendPill trend={tr.trend} delta={tr.delta}/></span>}
                          </div>
                        </div>
                        <div style={{ display:"flex", gap:"12px", fontSize:"0.78rem", color:"#475569" }}>
                          <span>Mean <strong style={{ color:SKY }}>{s.mean}%</strong></span>
                          <span>SD <strong>{s.std_dev}</strong></span>
                          <span>Hi <strong style={{ color:GREEN }}>{s.highest}</strong></span>
                          <span>Lo <strong style={{ color:RED }}>{s.lowest}</strong></span>
                        </div>
                      </div>

                      {tr && tr.points.length >= 2 && (
                        <div style={{ marginBottom:"0.4rem" }}>
                          <StudentTrendChart points={tr.points} type={trendChart} />
                        </div>
                      )}

                      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit, minmax(180px, 1fr))", gap:"8px" }}>
                        {s.top_student && (
                          <div style={{ padding:"6px 10px", borderRadius:"8px", background:"#f0fdf4", border:"1px solid #bbf7d0" }}>
                            <div style={{ fontSize:"0.62rem", fontWeight:800, color:"#166534", textTransform:"uppercase", letterSpacing:"0.06em" }}>Leading</div>
                            <div style={{ fontSize:"0.82rem", fontWeight:700, color:"#166534" }}>{s.top_student.name}</div>
                            <div style={{ fontSize:"0.7rem", color:"#16a34a" }}>{s.top_student.admission_number} · {s.top_student.pct}%</div>
                          </div>
                        )}
                        {s.most_improved && (
                          <div style={{ padding:"6px 10px", borderRadius:"8px", background:"#e0f2fe", border:"1px solid #bae6fd" }}>
                            <div style={{ fontSize:"0.62rem", fontWeight:800, color:"#075985", textTransform:"uppercase", letterSpacing:"0.06em" }}>Best improved</div>
                            <div style={{ fontSize:"0.82rem", fontWeight:700, color:"#075985" }}>{s.most_improved.name}</div>
                            <div style={{ fontSize:"0.7rem", color:"#0284c7" }}>+{s.most_improved.delta} pts</div>
                          </div>
                        )}
                        {s.most_declined && (
                          <div style={{ padding:"6px 10px", borderRadius:"8px", background:"#fef2f2", border:"1px solid #fecaca" }}>
                            <div style={{ fontSize:"0.62rem", fontWeight:800, color:"#991b1b", textTransform:"uppercase", letterSpacing:"0.06em" }}>Worst declined</div>
                            <div style={{ fontSize:"0.82rem", fontWeight:700, color:"#991b1b" }}>{s.most_declined.name}</div>
                            <div style={{ fontSize:"0.7rem", color:"#dc2626" }}>{s.most_declined.delta} pts</div>
                          </div>
                        )}
                        {s.most_stable && (
                          <div style={{ padding:"6px 10px", borderRadius:"8px", background:"#f8fafc", border:"1px solid #e5e7eb" }}>
                            <div style={{ fontSize:"0.62rem", fontWeight:800, color:"#475569", textTransform:"uppercase", letterSpacing:"0.06em" }}>Most consistent</div>
                            <div style={{ fontSize:"0.82rem", fontWeight:700, color:"#475569" }}>{s.most_stable.name}</div>
                            <div style={{ fontSize:"0.7rem", color:"#64748b" }}>SD {s.most_stable.std}</div>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* ========== LEADERBOARDS ========== */}
            <div className={`printable-section ${tab === "leaderboards" ? "is-active" : ""}`} data-section="leaderboards">
              {data.leaderboards ? (
                <>
                  <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:"0.9rem" }}>
                    <div className="class-card" style={{ ...cardStyle, border:"2px solid #10b981" }}>
                      <div style={{ display:"flex", alignItems:"center", gap:"8px", marginBottom:"0.5rem" }}>
                        <Crown size={18} color="#b45309" />
                        <h3 style={{ margin:0, color:"#166534", fontSize:"0.95rem", fontWeight:800 }}>Best overall</h3>
                      </div>
                      {(data.leaderboards.best_overall ?? []).map((s, i) => (
                        <div key={s.id} style={{ display:"flex", justifyContent:"space-between", padding:"4px 0", borderTop: i ? "1px solid #f1f5f9" : "none" }}>
                          <span style={{ fontWeight:700, color:"#166534" }}>#{i+1} {s.name}</span>
                          <span style={{ color:"#16a34a", fontWeight:700 }}>{s.mean}% ({s.grade})</span>
                        </div>
                      ))}
                    </div>

                    <div className="class-card" style={{ ...cardStyle, border:"2px solid #10b981" }}>
                      <div style={{ display:"flex", alignItems:"center", gap:"8px", marginBottom:"0.5rem" }}>
                        <TrendingUp size={18} color="#075985" />
                        <h3 style={{ margin:0, color:"#075985", fontSize:"0.95rem", fontWeight:800 }}>Most improved</h3>
                      </div>
                      {(data.leaderboards.most_improved ?? []).length === 0
                        ? <div style={{ color:"#94a3b8", fontSize:"0.82rem" }}>None flagged</div>
                        : (data.leaderboards.most_improved ?? []).map((s, i) => (
                          <div key={s.id} style={{ display:"flex", justifyContent:"space-between", padding:"4px 0", borderTop: i ? "1px solid #f1f5f9" : "none" }}>
                            <span style={{ fontWeight:700, color:"#075985" }}>{s.name}</span>
                            <span style={{ color:"#0284c7", fontWeight:700 }}>+{s.delta} pts</span>
                          </div>
                        ))}
                    </div>

                    <div className="class-card" style={{ ...cardStyle, border:"2px solid #ef4444" }}>
                      <div style={{ display:"flex", alignItems:"center", gap:"8px", marginBottom:"0.5rem" }}>
                        <TrendingDown size={18} color="#991b1b" />
                        <h3 style={{ margin:0, color:"#991b1b", fontSize:"0.95rem", fontWeight:800 }}>Most declined</h3>
                      </div>
                      {(data.leaderboards.most_declined ?? []).length === 0
                        ? <div style={{ color:"#94a3b8", fontSize:"0.82rem" }}>None flagged</div>
                        : (data.leaderboards.most_declined ?? []).map((s, i) => (
                          <div key={s.id} style={{ display:"flex", justifyContent:"space-between", padding:"4px 0", borderTop: i ? "1px solid #f1f5f9" : "none" }}>
                            <span style={{ fontWeight:700, color:"#991b1b" }}>{s.name}</span>
                            <span style={{ color:"#dc2626", fontWeight:700 }}>{s.delta} pts</span>
                          </div>
                        ))}
                    </div>

                    <div className="class-card" style={{ ...cardStyle, border:"2px solid #64748b" }}>
                      <div style={{ display:"flex", alignItems:"center", gap:"8px", marginBottom:"0.5rem" }}>
                        <Minus size={18} color="#475569" />
                        <h3 style={{ margin:0, color:"#475569", fontSize:"0.95rem", fontWeight:800 }}>Most consistent</h3>
                      </div>
                      {(data.leaderboards.most_consistent ?? []).length === 0
                        ? <div style={{ color:"#94a3b8", fontSize:"0.82rem" }}>Not enough data</div>
                        : (data.leaderboards.most_consistent ?? []).map((s, i) => (
                          <div key={s.id} style={{ display:"flex", justifyContent:"space-between", padding:"4px 0", borderTop: i ? "1px solid #f1f5f9" : "none" }}>
                            <span style={{ fontWeight:700, color:"#475569" }}>{s.name}</span>
                            <span style={{ color:"#64748b", fontWeight:700 }}>SD {s.std}</span>
                          </div>
                        ))}
                    </div>
                  </div>

                  <div className="class-card" style={{ ...cardStyle, marginTop:"0.9rem" }}>
                    <h3 style={{ margin:"0 0 0.5rem", color:BROWN2, fontSize:"0.95rem", fontWeight:800 }}>Best student per subject</h3>
                    <table style={{ width:"100%", borderCollapse:"collapse", fontSize:"0.82rem" }}>
                      <thead>
                        <tr style={{ background:`linear-gradient(135deg, ${BROWN}, ${BROWN2})`, color:CREAM }}>
                          <th style={{ textAlign:"left", padding:"5px 8px" }}>Subject</th>
                          <th style={{ textAlign:"left", padding:"5px 8px" }}>Top student</th>
                          <th style={{ textAlign:"right", padding:"5px 8px" }}>Score</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(data.leaderboards.best_per_subject ?? []).map((row) => (
                          <tr key={row.subject} style={{ borderTop:"1px solid #f1f5f9" }}>
                            <td style={{ padding:"5px 8px", fontWeight:700, color:BROWN2 }}>{row.subject}</td>
                            <td style={{ padding:"5px 8px" }}>{row.student?.name ?? "—"} <span style={{ color:"#94a3b8" }}>({row.student?.admission_number})</span></td>
                            <td style={{ padding:"5px 8px", textAlign:"right", fontWeight:700, color:SKY }}>{row.student?.pct ?? "—"}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </>
              ) : (
                <div style={{ padding:"2rem", textAlign:"center", color:"#94a3b8" }}>No leaderboard data for this stream.</div>
              )}
            </div>
          </div>
        )}
      </div>
    </>
  );
}