import { useEffect, useMemo, useState } from "react";
import {
  Activity, AlertTriangle, Award, BarChart3, BookOpen, ChevronDown,
  GraduationCap, Layers, LineChart as LineIcon, PieChart,
  Sparkles, Target, TrendingDown, TrendingUp, Users,
} from "lucide-react";
import http from "../services/http";
import { useAuth } from "../auth/AuthContext";
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  LineChart as RLineChart, Line, BarChart as RBarChart, Bar, Cell,
  PieChart as RPieChart, Pie,
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from "recharts";
import "./TeacherAnalyticsPage.css";

type Exam = { assessment_id: string; name: string; date: string; pct: number; grade: string };
type Subject = {
  subject_id: string; code: string; name: string;
  mean: number; grade: string;
  trend: "improving" | "stable" | "declining";
  consistency: string; consistency_sd: number;
  school_mean: number | null; delta: number | null;
  exam_count: number; student_count: number; exams: Exam[];
};
type Student = { id: string; name: string; mean: number };
type StudentRef = {
  id: string; name: string; admission_number: string; mean: number;
};

type SubjectMeanDetail = {
  code: string; name: string;
  mean: number; std_dev: number; highest: number; lowest: number;
  in_scope: boolean;
};

type ClassRow = {
  group_id: string; group_name: string;
  student_count: number; mean: number; subject_count: number;
  top: Student[]; focus: Student[];
  // ClassRow-compatible drilldown fields (from backend)
  students?: number;
  overall_mean?: number;
  overall_median?: number;
  overall_std_dev?: number;
  overall_pass_rate?: number;
  best_student?: StudentRef | null;
  worst_student?: StudentRef | null;
  subject_means?: Record<string, number>;
  subject_full?: SubjectMeanDetail[];
  leading_subject?: { code: string; name: string; mean: number } | null;
  trailing_subject?: { code: string; name: string; mean: number } | null;
  rank?: number;
  stream_name?: string | null;
  stream_code?: string | null;
};
type Overall = {
  mean: number; school_mean: number | null; delta: number | null;
  std_dev: number; subject_count: number; class_count: number;
  student_count: number; exam_count: number;
};
type RecentExam = { name: string; date: string; mean: number; subject_count: number };

type SchoolFilters = {
  classes: { id: string; name: string }[];
  streams: { id: string; name: string }[];
  subjects: { id: string; name: string; code: string }[];
  teachers: { id: string; name: string; code: string }[];
  terms: { id: string; name: string }[];
  students: { id: string; name: string; admission: string }[];
};

type SchoolRow = {
  mean: number;
  deviation: number | null;
  rank?: number;
  exam_count?: number;
  student_count?: number;
};

type SchoolClassRow = SchoolRow & { group_id: string; group_name: string };
type SchoolSubjectRow = SchoolRow & { subject_id: string; code: string; name: string };
type SchoolTeacherRow = SchoolRow & { teacher_id: string; name: string; code: string; subject_count: number };
type SchoolTermRow = SchoolRow & { term_id: string; name: string };
type SchoolStreamRow = SchoolRow & { stream_id: string; stream_name: string; class_count: number };

type SchoolData = {
  filters: Record<string, string | null>;
  overall: {
    mean: number;
    student_count: number;
    subject_count: number;
    class_count: number;
    teacher_count: number;
    exam_count: number;
  };
  by_class: SchoolClassRow[];
  by_stream: SchoolStreamRow[];
  by_subject: SchoolSubjectRow[];
  by_teacher: SchoolTeacherRow[];
  by_term: SchoolTermRow[];
  recent_exams: { assessment_id: string; name: string; date: string; mean: number; subject_count: number }[];
};

type StudentSubjectExam = {
  assessment_id: string;
  name: string;
  date: string;
  pct: number;
  grade: string;
};

type StudentSubjectRow = {
  subject_id: string;
  code: string;
  name: string;
  mean: number;
  grade: string;
  sd: number;
  trend: "improving" | "stable" | "declining";
  exam_count: number;
  in_scope: boolean;
  exams: StudentSubjectExam[];
};

type StudentDrill = {
  student: {
    id: string;
    name: string;
    admission: string;
    class_id: string | null;
    class_name: string | null;
  };
  scope: "mine" | "whole";
  overall: { mean: number; subject_count: number; exam_count: number };
  subjects: StudentSubjectRow[];
};

type Tab = "overview" | "subjects" | "classes" | "students" | "trends" | "school";
type ChartKind = "bar" | "line" | "pie";

const PALETTE = ["#0ea5e9", "#10b981", "#f59e0b", "#a855f7", "#ef4444", "#14b8a6", "#eab308", "#6366f1"];

const GRADE_ORDER = ["Grade 8", "Grade 9", "Grade 10", "Grade 11", "Form 3", "Form 4"];

const TOOLTIP_STYLE: React.CSSProperties = {
  background: "#ffffff",
  backgroundColor: "#ffffff",
  border: "1px solid #94a3b8",
  borderRadius: 8,
  boxShadow: "0 10px 30px rgba(15,23,42,0.30)",
  padding: "10px 14px",
  fontSize: "0.82rem",
  color: "#0f172a",
  opacity: 1,
  zIndex: 99999,
  pointerEvents: "none",
};

const TOOLTIP_ITEM_STYLE: React.CSSProperties = {
  color: "#0f172a",
  fontWeight: 700,
};

const TOOLTIP_LABEL_STYLE: React.CSSProperties = {
  color: "#334155",
  fontWeight: 800,
  marginBottom: 4,
};

const TERM_COLORS: Record<number, string> = {
  1: "#0ea5e9", // sky
  2: "#10b981", // emerald
  3: "#f59e0b", // amber
  4: "#a855f7", // violet (safety)
};

function termFromName(name: string): number {
  const m = name.match(/Term\s+(\d+)/i);
  return m ? parseInt(m[1], 10) : 0;
}

function termColor(name: string): string {
  return TERM_COLORS[termFromName(name)] ?? "#64748b";
}

// Stable class-color assignment by group_id (so class color is consistent)
const CLASS_COLOR_CACHE: Record<string, string> = {};
function classColor(groupId: string, fallbackIndex = 0): string {
  if (!CLASS_COLOR_CACHE[groupId]) {
    const hash = Array.from(groupId).reduce((a, c) => a + c.charCodeAt(0), 0);
    CLASS_COLOR_CACHE[groupId] = PALETTE[(hash + fallbackIndex) % PALETTE.length];
  }
  return CLASS_COLOR_CACHE[groupId];
}

function gradeKeyFromClass(name: string): string | null {
  // "Grade 10E" -> "Grade 10" | "Form 4W" -> "Form 4" | "G11E" -> "Grade 11"
  const gradeMatch = name.match(/^Grade\s+(\d+)/i);
  if (gradeMatch) return "Grade " + gradeMatch[1];
  const formMatch = name.match(/^Form\s+(\d+)/i);
  if (formMatch) return "Form " + formMatch[1];
  const gMatch = name.match(/^G(\d+)/i);
  if (gMatch) return "Grade " + gMatch[1];
  return null;
}

const TABS: { id: Tab; label: string; Icon: any }[] = [
  { id: "overview", label: "Overview", Icon: BarChart3 },
  { id: "subjects", label: "Subjects", Icon: BookOpen },
  { id: "classes",  label: "Classes",  Icon: Layers },
  { id: "students", label: "Students", Icon: Users },
  { id: "trends",   label: "Trends",   Icon: LineIcon },
];

const ADMIN_TAB: { id: Tab; label: string; Icon: any } = {
  id: "school", label: "School", Icon: GraduationCap,
};

export default function TeacherAnalyticsPage() {
  const { role: authRole } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [teacher, setTeacher] = useState<any>(null);
  const [overall, setOverall] = useState<Overall | null>(null);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [classes, setClasses] = useState<ClassRow[]>([]);
  const [strengths, setStrengths] = useState<Subject[]>([]);
  const [focus, setFocus] = useState<Subject[]>([]);
  const [recent, setRecent] = useState<RecentExam[]>([]);

  const [tab, setTab] = useState<Tab>("overview");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [trendChartType, setTrendChartType] = useState<ChartKind>("bar");
  const [classScope, setClassScope] = useState<"mine" | "whole">("mine");
  const [classStream, setClassStream] = useState<string>("all");
  const [expandedClass, setExpandedClass] = useState<string | null>(null);
  const [studentScope, setStudentScope] = useState<"mine" | "whole">("mine");
  const [expandedStudent, setExpandedStudent] = useState<string | null>(null);
  const [studentRange, setStudentRange] = useState<3 | 6>(3);
  const [studentDrill, setStudentDrill] = useState<StudentDrill | null>(null);
  const [studentDrillLoading, setStudentDrillLoading] = useState(false);
  const [studentDrillError, setStudentDrillError] = useState("");
  const [studentChartType, setStudentChartType] = useState<"bar" | "line" | "pie">("line");
  const [schoolData, setSchoolData] = useState<SchoolData | null>(null);
  const [schoolFilters, setSchoolFilters] = useState<SchoolFilters | null>(null);
  const [schoolLoading, setSchoolLoading] = useState(false);
  const [schoolError, setSchoolError] = useState("");
  const [schoolFilterValues, setSchoolFilterValues] = useState<{ [k: string]: string }>({
    class: "", stream: "", student: "", subject: "", teacher: "", term: "",
  });
  const [perSubjectChartType, setPerSubjectChartType] = useState<ChartKind>("bar");

  // School tab: load filters once when tab is opened
  useEffect(() => {
    if (tab !== "school" || schoolFilters) return;
    http.get("/academics/analysis/school/filters/")
      .then((r) => setSchoolFilters(r.data))
      .catch(() => setSchoolFilters(null));
  }, [tab, schoolFilters]);

  // School tab: refetch data whenever filters change
  useEffect(() => {
    if (tab !== "school") return;
    setSchoolLoading(true);
    setSchoolError("");
    const params = new URLSearchParams();
    Object.entries(schoolFilterValues).forEach(([k, v]) => {
      if (v) params.append(k, v);
    });
    const qs = params.toString();
    http.get("/academics/analysis/school/" + (qs ? "?" + qs : ""))
      .then((r) => setSchoolData(r.data))
      .catch((e) => {
        setSchoolError(e?.response?.data?.detail || "Could not load school analytics.");
        setSchoolData(null);
      })
      .finally(() => setSchoolLoading(false));
  }, [tab, schoolFilterValues]);

  useEffect(() => {
    if (!expandedStudent) {
      setStudentDrill(null);
      return;
    }
    setStudentDrillLoading(true);
    setStudentDrillError("");
    http.get(`/academics/analysis/teacher/me/student/${expandedStudent}/?scope=${studentScope}`)
      .then((r) => setStudentDrill(r.data))
      .catch((e) => {
        setStudentDrill(null);
        setStudentDrillError(
          e?.response?.data?.detail || `Could not load student details (${e?.response?.status ?? "network"}).`
        );
      })
      .finally(() => setStudentDrillLoading(false));
  }, [expandedStudent, studentScope]);

  useEffect(() => {
    http.get("/academics/analysis/teacher/me/")
      .then((r) => {
        const d = r.data || {};
        setTeacher(d.teacher || null);
        setOverall(d.overall || null);
        setSubjects(Array.isArray(d.subjects) ? d.subjects : []);
        setClasses(Array.isArray(d.classes) ? d.classes : []);
        setStrengths(Array.isArray(d.strengths) ? d.strengths : []);
        setFocus(Array.isArray(d.focus) ? d.focus : []);
        setRecent(Array.isArray(d.recent_exams) ? d.recent_exams : []);
      })
      .catch((e) => setError(e?.response?.data?.detail || "Could not load teaching data."))
      .finally(() => setLoading(false));
  }, []);

  const notableStudents = useMemo(() => {
    const seen = new Map<string, { id: string; name: string; mean: number; group: string; kind: "top" | "focus" }>();
    classes.forEach((c) => {
      c.top.forEach((s) => seen.set(s.id, { id: s.id, name: s.name, mean: s.mean, group: c.group_name, kind: "top" }));
      c.focus.forEach((s) => {
        if (!seen.has(s.id)) seen.set(s.id, { id: s.id, name: s.name, mean: s.mean, group: c.group_name, kind: "focus" });
      });
    });
    return Array.from(seen.values()).sort((a, b) => b.mean - a.mean);
  }, [classes]);

  const fmtDelta = (d: number | null) => (d == null ? "—" : (d >= 0 ? "+" : "") + d.toFixed(1));

  if (loading) return <div className="ta-page"><div className="ta-empty">Loading your teaching analytics…</div></div>;
  if (error) return <div className="ta-page"><div className="ta-error">{error}</div></div>;

  return (
    <div className="ta-page">
      <style>{`
        .recharts-tooltip-wrapper { z-index: 99999 !important; outline: none !important; }
        .recharts-default-tooltip {
          background: #ffffff !important;
          background-color: #ffffff !important;
          border: 1px solid #94a3b8 !important;
          border-radius: 8px !important;
          box-shadow: 0 10px 30px rgba(15,23,42,0.30) !important;
          padding: 10px 14px !important;
          font-size: 0.82rem !important;
          color: #0f172a !important;
          opacity: 1 !important;
        }
        .recharts-tooltip-item { color: #0f172a !important; font-weight: 700 !important; }
        .recharts-tooltip-item-name,
        .recharts-tooltip-item-value,
        .recharts-tooltip-item-separator { color: #0f172a !important; }
        .recharts-tooltip-label { color: #334155 !important; font-weight: 800 !important; margin-bottom: 4px !important; }
      `}</style>
      <header className="ta-hero">
        <div className="ta-hero-left">
          <span className="ta-hero-eyebrow"><Sparkles size={13} /> My Teaching</span>
          <h1>{teacher?.name || "Teacher"}</h1>
          <p className="ta-hero-sub">
            {teacher?.code ? teacher.code + " · " : ""}
            {overall?.class_count ?? 0} classes · {overall?.subject_count ?? 0} subjects · {overall?.student_count ?? 0} students
          </p>
        </div>
        {overall && (
          <div className="ta-hero-right">
            <div className="ta-hero-stat">
              <div>
                <span className="ta-hero-stat-label">Overall mean</span>
                <span className="ta-hero-stat-value" style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                  {overall.mean.toFixed(1)}%
                  <DeviationBadge value={(overall as any).deviation} />
                </span>
              </div>
            </div>
            {overall.school_mean != null && (
              <div className="ta-hero-stat">
                <Target size={14} />
                <div>
                  <span className="ta-hero-stat-label">vs School</span>
                  <span className="ta-hero-stat-value" style={{ color: (overall.delta ?? 0) >= 0 ? "#6ee7b7" : "#fca5a5" }}>
                    {fmtDelta(overall.delta)}
                  </span>
                </div>
              </div>
            )}
          </div>
        )}
      </header>

      <nav className="ta-tabs">
        {[...TABS, ...(authRole === "PRINCIPAL" || authRole === "ADMIN" || authRole === "SUPER_ADMIN" || authRole === "SECRETARY" ? [ADMIN_TAB] : [])].map((t) => (
          <button
            key={t.id}
            type="button"
            className={"ta-tab" + (tab === t.id ? " active" : "")}
            onClick={() => setTab(t.id)}
          >
            <t.Icon size={14} /> {t.label}
          </button>
        ))}
      </nav>

      {tab === "overview" && overall && (
        <div className="ta-tab-body">
          <section className="ta-kpi-strip">
            <div className="ta-kpi ta-kpi-sky">
              <div className="ta-kpi-icon"><Users size={18} /></div>
              <div><span className="ta-kpi-label">Students</span><span className="ta-kpi-value">{overall.student_count}</span></div>
            </div>
            <div className="ta-kpi ta-kpi-violet">
              <div className="ta-kpi-icon"><Layers size={18} /></div>
              <div><span className="ta-kpi-label">Classes</span><span className="ta-kpi-value">{overall.class_count}</span></div>
            </div>
            <div className="ta-kpi ta-kpi-emerald">
              <div className="ta-kpi-icon"><BookOpen size={18} /></div>
              <div><span className="ta-kpi-label">Subjects</span><span className="ta-kpi-value">{overall.subject_count}</span></div>
            </div>
            <div className="ta-kpi ta-kpi-amber">
              <div className="ta-kpi-icon"><Activity size={18} /></div>
              <div><span className="ta-kpi-label">Consistency (σ)</span><span className="ta-kpi-value">{overall.std_dev.toFixed(1)}</span></div>
            </div>
          </section>

          <div className="ta-grid-2">
            <section className="ta-card">
              <header className="ta-card-head">
                <BarChart3 size={16} />
                <h2>Subject means</h2>
              </header>
              {subjects.length === 0 ? (
                <div className="ta-empty-mini">No subject data yet</div>
              ) : (
                <BarChart data={subjects.map((s) => ({ label: s.code, value: s.mean }))} height={240} />
              )}
            </section>
            <section className="ta-card">
              <header className="ta-card-head">
                <Users size={16} />
                <h2>Students by class</h2>
              </header>
              {classes.length === 0 ? (
                <div className="ta-empty-mini">No class data yet</div>
              ) : (
                <DonutChart
                  data={classes.map((c, i) => ({ label: c.group_name, value: c.student_count, color: PALETTE[i % PALETTE.length] }))}
                  size={200}
                />
              )}
            </section>
          </div>

          <div className="ta-grid-2">
            <section className="ta-card ta-card-strength">
              <header className="ta-card-head">
                <Award size={16} />
                <h2>Strongest subjects</h2>
              </header>
              {strengths.length === 0 ? (
                <div className="ta-empty-mini">More data needed.</div>
              ) : (
                <ul className="ta-list">
                  {strengths.map((s) => (
                    <li key={s.subject_id}>
                      <b>{s.code}</b>
                      <span>{s.mean.toFixed(1)}%</span>
                      {s.delta != null && (
                        <span className={"ta-delta " + (s.delta >= 0 ? "ta-pos" : "ta-neg")}>{fmtDelta(s.delta)}</span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </section>
            <section className="ta-card ta-card-focus">
              <header className="ta-card-head">
                <AlertTriangle size={16} />
                <h2>Need attention</h2>
              </header>
              {focus.length === 0 ? (
                <div className="ta-empty-mini">Nothing to flag yet.</div>
              ) : (
                <ul className="ta-list">
                  {focus.map((s) => (
                    <li key={s.subject_id}>
                      <b>{s.code}</b>
                      <span>{s.mean.toFixed(1)}%</span>
                      {s.delta != null && (
                        <span className={"ta-delta " + (s.delta >= 0 ? "ta-pos" : "ta-neg")}>{fmtDelta(s.delta)}</span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        </div>
      )}

      {tab === "subjects" && (
        <div className="ta-tab-body">
          {subjects.length === 0 ? (
            <div className="ta-empty">No subjects yet.</div>
          ) : (
            <div className="ta-grid-3">
              {subjects.map((s) => {
                const isOpen = expanded === s.subject_id;
                return (
                  <article key={s.subject_id} className="ta-card ta-subject-card">
                    <header className="ta-card-head">
                      <div>
                        <div className="ta-subject-code">{s.code}</div>
                        <div className="ta-subject-name">{s.name}</div>
                      </div>
                      <span className={"ta-trend ta-trend-" + s.trend} style={{ marginLeft: "auto" }}>
                        {s.trend === "improving" ? <TrendingUp size={14} /> : s.trend === "declining" ? <TrendingDown size={14} /> : null}
                        {s.trend}
                      </span>
                    </header>
                    <div className="ta-subject-main">
                      <div className="ta-subject-big">
                        <b>{s.mean.toFixed(1)}%</b>
                        <span>class mean</span>
                      </div>
                      <span style={{ marginLeft: 8 }}>
                        <DeviationBadge value={(s as any).deviation} />
                      </span>
                      <span className="ta-grade" style={{ marginLeft: "auto" }}>{s.grade || "—"}</span>
                    </div>
                    <div className="ta-subject-metrics">
                      <div><span>School</span><b>{s.school_mean != null ? s.school_mean.toFixed(1) + "%" : "—"}</b></div>
                      <div><span>Delta</span><b className={(s.delta ?? 0) >= 0 ? "ta-pos" : "ta-neg"}>{fmtDelta(s.delta)}</b></div>
                      <div><span>Students</span><b>{s.student_count}</b></div>
                      <div><span>σ</span><b>{s.consistency_sd.toFixed(1)}</b></div>
                    </div>
                    <div className="ta-subject-tags">
                      <span className="ta-tag">{s.consistency}</span>
                      <span className="ta-tag">{s.exam_count} exam{s.exam_count === 1 ? "" : "s"}</span>
                    </div>
                    {s.exams.length > 0 && (
                      <button
                        type="button"
                        className="ta-expand"
                        onClick={() => setExpanded(isOpen ? null : s.subject_id)}
                      >
                        <ChevronDown
                          size={13}
                          style={{ transform: isOpen ? "rotate(180deg)" : "none", transition: "transform 200ms" }}
                        />
                        {isOpen ? "Hide exam history" : "Show exam history"}
                      </button>
                    )}
                    {isOpen && s.exams.length > 0 && (
                      <div className="ta-subject-detail">
                        <h4 style={{ marginBottom: 6 }}>Performance chart</h4>
                        <div style={{ width: "100%", height: 180, marginBottom: 12 }}>
                          <ResponsiveContainer>
                            <RLineChart
                              data={s.exams.map((e) => ({
                                name: e.name.replace(/^Term \d+\s*/i, ""),
                                fullName: e.name,
                                pct: e.pct,
                              }))}
                              margin={{ top: 8, right: 12, left: -10, bottom: 0 }}
                            >
                              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                              <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#748095" }} />
                              <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "#748095" }} />
                              <Tooltip
                                contentStyle={TOOLTIP_STYLE}
                                itemStyle={TOOLTIP_ITEM_STYLE}
                                labelStyle={TOOLTIP_LABEL_STYLE}
                                wrapperStyle={{ zIndex: 99999 }}
                                allowEscapeViewBox={{ x: true, y: true }}
                                labelFormatter={(label, payload) => payload?.[0]?.payload?.fullName ?? label}
                              />
                              <Line
                                type="monotone"
                                dataKey="pct"
                                stroke="#94a3b8"
                                strokeWidth={1.5}
                                dot={(props: any) => {
                                  const { cx, cy, payload, index } = props;
                                  const t = termFromName(payload?.fullName ?? "");
                                  return (
                                    <circle
                                      key={`dot-${index}`}
                                      cx={cx}
                                      cy={cy}
                                      r={4}
                                      fill={TERM_COLORS[t] ?? "#64748b"}
                                      stroke="#fff"
                                      strokeWidth={1.5}
                                    />
                                  );
                                }}
                                activeDot={{ r: 6 }}
                              />
                            </RLineChart>
                          </ResponsiveContainer>
                        </div>
                        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", fontSize: "0.7rem", color: "#64748b", marginBottom: 10 }}>
                          {[1, 2, 3].map((t) => (
                            <span key={t} style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                              <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: "50%", background: TERM_COLORS[t] }} />
                              Term {t}
                            </span>
                          ))}
                        </div>
                        <h4>Exam history</h4>
                        {s.exams.map((e, i) => (
                          <div
                            key={i}
                            style={{
                              display: "grid",
                              gridTemplateColumns: "1fr auto auto auto",
                              gap: 10,
                              padding: "6px 0",
                              borderTop: i === 0 ? "none" : "1px solid #f1f5f9",
                              fontSize: "0.8rem",
                              alignItems: "center",
                            }}
                          >
                            <span>{e.name}</span>
                            <span style={{ color: "#64748b", fontSize: "0.72rem" }}>
                              {e.date ? new Date(e.date).toLocaleDateString() : "—"}
                            </span>
                            <span style={{ fontWeight: 800 }}>{e.pct.toFixed(1)}%</span>
                            <span className="ta-tag">{e.grade}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </article>
                );
              })}
            </div>
          )}
        </div>
      )}

      {tab === "classes" && (
        <div className="ta-tab-body">
          {/* ---------- Filter bar ---------- */}
          <div className="ta-filter-row" style={{ marginBottom: "0.75rem" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.68rem", fontWeight: 800, letterSpacing: "0.05em", textTransform: "uppercase", color: "#64748b", marginBottom: 4 }}>Scope</label>
              <div className="ta-switch">
                <button
                  type="button"
                  className={"ta-switch-btn" + (classScope === "mine" ? " active" : "")}
                  onClick={() => setClassScope("mine")}
                >My subjects</button>
                <button
                  type="button"
                  className={"ta-switch-btn" + (classScope === "whole" ? " active" : "")}
                  onClick={() => setClassScope("whole")}
                >Whole class</button>
              </div>
            </div>
            <div>
              <label htmlFor="class-stream" style={{ display: "block", fontSize: "0.68rem", fontWeight: 800, letterSpacing: "0.05em", textTransform: "uppercase", color: "#64748b", marginBottom: 4 }}>Stream / Grade</label>
              <select
                id="class-stream"
                value={classStream}
                onChange={(e) => setClassStream(e.target.value)}
                style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #e2e8f0", background: "#fff", fontSize: "0.85rem", minWidth: 180 }}
              >
                <option value="all">All</option>
                {Array.from(new Set(
                  classes
                    .map((c) => gradeKeyFromClass(c.group_name))
                    .filter((g): g is string => !!g)
                ))
                  .sort((a, b) => GRADE_ORDER.indexOf(a) - GRADE_ORDER.indexOf(b))
                  .map((g) => (
                    <option key={g} value={g}>{g}</option>
                  ))}
              </select>
            </div>
          </div>

          {classes.length === 0 ? (
            <div className="ta-empty">No classes yet.</div>
          ) : (
            <div className="ta-grid-3">
              {classes
                .filter((c) => classStream === "all" || gradeKeyFromClass(c.group_name) === classStream)
                .map((c) => {
                  const isOpen = expandedClass === c.group_id;
                  const subjectFull = c.subject_full ?? [];
                  const visibleSubjects = classScope === "mine"
                    ? subjectFull.filter((s) => s.in_scope)
                    : subjectFull;
                  const radarData = visibleSubjects
                    .filter((s) => s.mean > 0)
                    .map((s) => ({ subject: s.code, mean: s.mean, fullMark: 100 }));

                  // Leading/trailing badges based on current scope
                  const scoped = visibleSubjects.filter((s) => s.mean > 0);
                  const lead = scoped.length ? scoped.reduce((a, b) => (a.mean >= b.mean ? a : b)) : null;
                  const trail = scoped.length ? scoped.reduce((a, b) => (a.mean <= b.mean ? a : b)) : null;

                  return (
                    <article
                      key={c.group_id}
                      className="ta-card ta-class-card"
                      style={{ cursor: "pointer" }}
                      onClick={() => setExpandedClass(isOpen ? null : c.group_id)}
                    >
                      <header className="ta-card-head">
                        {typeof c.rank === "number" && (
                          <span style={{
                            display: "inline-flex", alignItems: "center", justifyContent: "center",
                            minWidth: 34, height: 34, borderRadius: 8,
                            background: classColor(c.group_id) + "22",
                            color: classColor(c.group_id),
                            fontWeight: 800, fontSize: "0.9rem",
                          }}>#{c.rank}</span>
                        )}
                        <div style={{ flex: 1 }}>
                          <div className="ta-subject-code">{c.group_name}</div>
                          <div className="ta-subject-name">
                            {c.students ?? c.student_count} students
                            {typeof c.overall_mean === "number" ? ` · mean ${c.overall_mean}%` : ""}
                            {typeof c.overall_median === "number" ? ` · median ${c.overall_median}%` : ""}
                            {typeof c.overall_std_dev === "number" ? ` · SD ${c.overall_std_dev}` : ""}
                            {typeof c.overall_pass_rate === "number" ? ` · pass ${c.overall_pass_rate}%` : ""}
                          </div>
                        </div>
                        <GraduationCap size={18} style={{ color: "#244b72" }} />
                      </header>

                      {lead && trail && lead.code !== trail.code && (
                        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 6 }}>
                          <span className="ta-tag" style={{ background: "#dcfce7", color: "#166534", borderColor: "transparent" }}>
                            🏆 Leading: {lead.code} {lead.mean}%
                          </span>
                          <span className="ta-tag" style={{ background: "#fee2e2", color: "#991b1b", borderColor: "transparent" }}>
                            ⚠ Needs work: {trail.code} {trail.mean}%
                          </span>
                        </div>
                      )}

                      {/* Legacy top/focus list for compact view */}
                      {!isOpen && c.top.length > 0 && (
                        <div className="ta-class-list">
                          <div className="ta-class-list-head" style={{ color: "#065f46" }}>Top performers</div>
                          {c.top.slice(0, 3).map((s) => (
                            <div key={s.id} className="ta-class-row">
                              <span>{s.name}</span>
                              <b>{s.mean.toFixed(1)}%</b>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* ---------- Drill-down ---------- */}
                      {isOpen && (
                        <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px dashed #e2e8f0" }}>
                          <div style={{
                            display: "grid",
                            gridTemplateColumns: "minmax(180px, 1fr) minmax(220px, 1.2fr)",
                            gap: "1rem",
                            marginBottom: "0.9rem",
                          }}>
                            <div>
                              <div style={{
                                fontSize: "0.68rem", letterSpacing: "0.08em",
                                textTransform: "uppercase", color: "#748095",
                                fontWeight: 700, marginBottom: 4,
                              }}>
                                Subject profile ({classScope === "mine" ? "my subjects" : "whole class"})
                              </div>
                              <div style={{ width: "100%", height: 240 }}>
                                {radarData.length > 0 ? (
                                  <ResponsiveContainer>
                                    <RadarChart data={radarData}>
                                      <PolarGrid stroke="#e5e7eb" />
                                      <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11, fill: "#748095" }} />
                                      <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 9, fill: "#cbd5e1" }} />
                                      <Radar
                                        dataKey="mean"
                                        stroke={classColor(c.group_id)}
                                        fill={classColor(c.group_id)}
                                        fillOpacity={0.35}
                                      />
                                      <Tooltip contentStyle={TOOLTIP_STYLE} itemStyle={TOOLTIP_ITEM_STYLE} labelStyle={TOOLTIP_LABEL_STYLE} wrapperStyle={{ zIndex: 99999 }} allowEscapeViewBox={{ x: true, y: true }} />
                                    </RadarChart>
                                  </ResponsiveContainer>
                                ) : (
                                  <div className="ta-empty-mini">No subject data in scope</div>
                                )}
                              </div>
                            </div>

                            <div>
                              <div style={{
                                fontSize: "0.68rem", letterSpacing: "0.08em",
                                textTransform: "uppercase", color: "#748095",
                                fontWeight: 700, marginBottom: 4,
                              }}>
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
                                    {visibleSubjects.map((s) => (
                                      <tr key={s.code} style={{ borderTop: "1px solid #f1f5f9" }}>
                                        <td style={{ padding: "4px 8px", fontWeight: 700 }}>
                                          {s.code}
                                          {!s.in_scope && classScope === "whole" && (
                                            <span style={{ color: "#94a3b8", fontWeight: 400, marginLeft: 4 }}>·</span>
                                          )}
                                        </td>
                                        <td style={{ padding: "4px 8px", textAlign: "right", fontWeight: 700, color: "#0369a1" }}>{s.mean}</td>
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

                          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                            {c.best_student && (
                              <div style={{ padding: "8px 12px", borderRadius: 10, background: "#f0fdf4", border: "1px solid #bbf7d0" }}>
                                <div style={{ fontSize: "0.68rem", fontWeight: 700, color: "#166534", letterSpacing: "0.06em", textTransform: "uppercase" }}>Top student</div>
                                <div style={{ fontWeight: 700, color: "#166534", fontSize: "0.9rem" }}>{c.best_student.name}</div>
                                <div style={{ fontSize: "0.75rem", color: "#16a34a" }}>{c.best_student.admission_number} · {c.best_student.mean}%</div>
                              </div>
                            )}
                            {c.worst_student && (
                              <div style={{ padding: "8px 12px", borderRadius: 10, background: "#fef2f2", border: "1px solid #fecaca" }}>
                                <div style={{ fontSize: "0.68rem", fontWeight: 700, color: "#991b1b", letterSpacing: "0.06em", textTransform: "uppercase" }}>Needs intervention</div>
                                <div style={{ fontWeight: 700, color: "#991b1b", fontSize: "0.9rem" }}>{c.worst_student.name}</div>
                                <div style={{ fontSize: "0.75rem", color: "#dc2626" }}>{c.worst_student.admission_number} · {c.worst_student.mean}%</div>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </article>
                  );
                })}
            </div>
          )}
        </div>
      )}

      {tab === "students" && (
        <div className="ta-tab-body">
          {/* ---------- Filter bar ---------- */}
          <div className="ta-filter-row" style={{ marginBottom: "0.75rem" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.68rem", fontWeight: 800, letterSpacing: "0.05em", textTransform: "uppercase", color: "#64748b", marginBottom: 4 }}>Scope</label>
              <div className="ta-switch">
                <button
                  type="button"
                  className={"ta-switch-btn" + (studentScope === "mine" ? " active" : "")}
                  onClick={() => setStudentScope("mine")}
                >My subjects</button>
                <button
                  type="button"
                  className={"ta-switch-btn" + (studentScope === "whole" ? " active" : "")}
                  onClick={() => setStudentScope("whole")}
                >Whole class</button>
              </div>
            </div>
          </div>

          {notableStudents.length === 0 ? (
            <div className="ta-empty">No student data yet.</div>
          ) : (
            <div style={{ display: "grid", gap: 8 }}>
              {notableStudents.map((s) => {
                const isOpen = expandedStudent === s.id;
                const drill = isOpen ? studentDrill : null;
                return (
                  <article
                    key={s.id}
                    className="ta-card"
                    style={{ cursor: "pointer", padding: "12px 16px" }}
                    onClick={() => {
                      if (isOpen) {
                        setExpandedStudent(null);
                      } else {
                        setExpandedStudent(s.id);
                      }
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 800, color: "#0f172a" }}>{s.name}</div>
                        <div style={{ fontSize: "0.75rem", color: "#64748b", display: "flex", alignItems: "center", gap: 6 }}>
                          <span>{s.group} · {s.mean.toFixed(1)}%</span>
                          <DeviationBadge value={(s as any).deviation} />
                          <span
                            className="ta-tag"
                            style={{
                              marginLeft: 8,
                              background: s.kind === "top" ? "#d1fae5" : "#fef3c7",
                              color: s.kind === "top" ? "#065f46" : "#92400e",
                              borderColor: "transparent",
                            }}
                          >{s.kind === "top" ? "Top" : "Focus"}</span>
                        </div>
                      </div>
                      <ChevronDown
                        size={16}
                        style={{ transform: isOpen ? "rotate(180deg)" : "none", transition: "transform 200ms", color: "#64748b" }}
                      />
                    </div>

                    {isOpen && (
                      <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px dashed #e2e8f0" }}>
                        {/* Controls row: exam range + chart type */}
                        <div style={{ display: "flex", gap: 16, marginBottom: 10, flexWrap: "wrap", alignItems: "center" }}>
                          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                            <span style={{ fontSize: "0.7rem", fontWeight: 800, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em" }}>Exams:</span>
                            <div className="ta-switch">
                              <button
                                type="button"
                                className={"ta-switch-btn" + (studentRange === 3 ? " active" : "")}
                                onClick={(e) => { e.stopPropagation(); setStudentRange(3); }}
                              >Last 3</button>
                              <button
                                type="button"
                                className={"ta-switch-btn" + (studentRange === 6 ? " active" : "")}
                                onClick={(e) => { e.stopPropagation(); setStudentRange(6); }}
                              >Last 6</button>
                            </div>
                          </div>
                          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                            <span style={{ fontSize: "0.7rem", fontWeight: 800, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em" }}>Chart:</span>
                            <div className="ta-switch">
                              <button
                                type="button"
                                className={"ta-switch-btn" + (studentChartType === "bar" ? " active" : "")}
                                onClick={(e) => { e.stopPropagation(); setStudentChartType("bar"); }}
                              >Bar</button>
                              <button
                                type="button"
                                className={"ta-switch-btn" + (studentChartType === "line" ? " active" : "")}
                                onClick={(e) => { e.stopPropagation(); setStudentChartType("line"); }}
                              >Line</button>
                              <button
                                type="button"
                                className={"ta-switch-btn" + (studentChartType === "pie" ? " active" : "")}
                                onClick={(e) => { e.stopPropagation(); setStudentChartType("pie"); }}
                              >Pie</button>
                            </div>
                          </div>
                        </div>

                        {studentDrillLoading && !drill && (
                          <div className="ta-empty-mini">Loading…</div>
                        )}
                        {!studentDrillLoading && studentDrillError && (
                          <div className="ta-empty-mini" style={{ color: "#991b1b", borderColor: "#fecaca", background: "#fef2f2" }}>
                            {studentDrillError}
                          </div>
                        )}

                        {drill && (
                          <div style={{ display: "grid", gap: 12 }}>
                            {drill.subjects.map((sub) => {
                              const exams = sub.exams.slice(-studentRange);
                              const data = exams.map((e) => ({
                                name: e.name.replace(/^Term \d+\s*/i, ""),
                                fullName: e.name,
                                pct: e.pct,
                              }));
                              return (
                                <div key={sub.subject_id} style={{ padding: 10, border: "1px solid #e2e8f0", borderRadius: 10 }}>
                                  <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 6 }}>
                                    <span style={{ fontWeight: 800 }}>{sub.code}</span>
                                    <span style={{ fontSize: "0.75rem", color: "#64748b" }}>{sub.name}</span>
                                    {!sub.in_scope && (
                                      <span style={{ fontSize: "0.65rem", color: "#94a3b8", marginLeft: "auto" }}>other teacher</span>
                                    )}
                                    <span
                                      className={"ta-trend ta-trend-" + sub.trend}
                                      style={{ marginLeft: sub.in_scope ? "auto" : 0, fontSize: "0.7rem" }}
                                    >{sub.trend}</span>
                                  </div>
                                  <div style={{ display: "flex", gap: 12, fontSize: "0.75rem", color: "#64748b", marginBottom: 6 }}>
                                    <span>mean <b style={{ color: "#0f172a" }}>{sub.mean}%</b></span>
                                    <span>grade <b style={{ color: "#0f172a" }}>{sub.grade}</b></span>
                                    <span>σ <b style={{ color: "#0f172a" }}>{sub.sd}</b></span>
                                    <span>{sub.exam_count} exam{sub.exam_count === 1 ? "" : "s"}</span>
                                  </div>
                                  <div style={{ width: "100%", height: 150 }}>
                                    {studentChartType === "line" ? (
                                      <ResponsiveContainer>
                                        <RLineChart data={data} margin={{ top: 6, right: 12, left: -14, bottom: 0 }}>
                                          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                                          <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#748095" }} />
                                          <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "#748095" }} />
                                          <Tooltip
                                            contentStyle={TOOLTIP_STYLE}
                                            itemStyle={TOOLTIP_ITEM_STYLE}
                                            labelStyle={TOOLTIP_LABEL_STYLE}
                                            wrapperStyle={{ zIndex: 99999 }}
                                            allowEscapeViewBox={{ x: true, y: true }}
                                            labelFormatter={(label, payload) => payload?.[0]?.payload?.fullName ?? label}
                                          />
                                          <Line
                                            type="monotone"
                                            dataKey="pct"
                                            stroke="#94a3b8"
                                            strokeWidth={1.5}
                                            dot={(props: any) => {
                                              const { cx, cy, payload, index } = props;
                                              const t = termFromName(payload?.fullName ?? "");
                                              return (
                                                <circle key={`sd-${index}`} cx={cx} cy={cy} r={4}
                                                  fill={TERM_COLORS[t] ?? "#64748b"} stroke="#fff" strokeWidth={1.5} />
                                              );
                                            }}
                                            activeDot={{ r: 6 }}
                                          />
                                        </RLineChart>
                                      </ResponsiveContainer>
                                    ) : studentChartType === "bar" ? (
                                      <ResponsiveContainer>
                                        <RBarChart data={data} margin={{ top: 6, right: 12, left: -14, bottom: 0 }}>
                                          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                                          <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#748095" }} />
                                          <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: "#748095" }} />
                                          <Tooltip
                                            contentStyle={TOOLTIP_STYLE}
                                            itemStyle={TOOLTIP_ITEM_STYLE}
                                            labelStyle={TOOLTIP_LABEL_STYLE}
                                            wrapperStyle={{ zIndex: 99999 }}
                                            allowEscapeViewBox={{ x: true, y: true }}
                                            labelFormatter={(label, payload) => payload?.[0]?.payload?.fullName ?? label}
                                          />
                                          <Bar dataKey="pct" radius={[4, 4, 0, 0]}>
                                            {data.map((entry, i) => {
                                              const t = termFromName(entry.fullName ?? "");
                                              return <Cell key={i} fill={TERM_COLORS[t] ?? "#64748b"} />;
                                            })}
                                          </Bar>
                                        </RBarChart>
                                      </ResponsiveContainer>
                                    ) : (
                                      <ResponsiveContainer>
                                        <RPieChart>
                                          <Tooltip
                                            contentStyle={TOOLTIP_STYLE}
                                            itemStyle={TOOLTIP_ITEM_STYLE}
                                            labelStyle={TOOLTIP_LABEL_STYLE}
                                            wrapperStyle={{ zIndex: 99999 }}
                                            allowEscapeViewBox={{ x: true, y: true }}
                                          />
                                          <Pie
                                            data={data}
                                            dataKey="pct"
                                            nameKey="fullName"
                                            innerRadius="45%"
                                            outerRadius="75%"
                                            paddingAngle={2}
                                          >
                                            {data.map((entry, i) => {
                                              const t = termFromName(entry.fullName ?? "");
                                              return <Cell key={i} fill={TERM_COLORS[t] ?? "#64748b"} />;
                                            })}
                                          </Pie>
                                        </RPieChart>
                                      </ResponsiveContainer>
                                    )}
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    )}
                  </article>
                );
              })}
            </div>
          )}
        </div>
      )}

      {tab === "trends" && (
        <div className="ta-tab-body">
          <section className="ta-card">
            <header className="ta-card-head">
              <LineIcon size={16} />
              <h2>Overall trend (last 8 exams)</h2>
              <ChartTypeSwitch value={trendChartType} onChange={setTrendChartType} />
            </header>
            {recent.length === 0 ? (
              <div className="ta-empty-mini">No exam data</div>
            ) : trendChartType === "bar" ? (
              <BarChart
                data={recent.slice().reverse().map((e) => ({ label: e.name, value: e.mean }))}
                height={240}
                colorFor={(label) => termColor(label)}
              />
            ) : trendChartType === "line" ? (
              <LineChart data={recent.slice().reverse().map((e) => ({ label: e.name, value: e.mean }))} height={240} />
            ) : (
              <DonutChart
                data={recent.slice().reverse().map((e, i) => ({
                  label: e.name,
                  value: Math.round(e.mean),
                  color: PALETTE[i % PALETTE.length],
                }))}
                size={220}
              />
            )}
          </section>

          <div className="ta-chart-type-bar">
            <h3>Per-subject trends</h3>
            <ChartTypeSwitch value={perSubjectChartType} onChange={setPerSubjectChartType} />
          </div>
          <div className="ta-grid-2">
            {subjects.length === 0 ? (
              <div className="ta-empty-mini">No subject data yet</div>
            ) : (
              subjects.map((s) => (
                <section key={s.subject_id} className="ta-card">
                  <header className="ta-card-head">
                    <BarChart3 size={16} />
                    <h2>{s.code} — {s.name}</h2>
                  </header>
                  {s.exams.length === 0 ? (
                    <div className="ta-empty-mini">No exam data yet</div>
                  ) : perSubjectChartType === "bar" ? (
                    <BarChart
                      data={s.exams.map((p) => ({ label: p.name, value: p.pct }))}
                      height={180}
                      colorFor={(label) => termColor(label)}
                    />
                  ) : perSubjectChartType === "line" ? (
                    <LineChart data={s.exams.map((p) => ({ label: p.name, value: p.pct }))} height={180} />
                  ) : (
                    <DonutChart
                      data={s.exams.map((p, i) => ({
                        label: p.name,
                        value: Math.round(p.pct),
                        color: PALETTE[i % PALETTE.length],
                      }))}
                      size={180}
                    />
                  )}
                </section>
              ))
            )}
          </div>
        </div>
      )}

      {tab === "school" && (
        <div className="ta-tab-body">
          <div className="ta-filter-row" style={{ marginBottom: "1rem", flexWrap: "wrap" }}>
            {(["class", "stream", "student", "subject", "teacher", "term"] as const).map((key) => {
              const opts = schoolFilters ? (schoolFilters[key + "s" as keyof SchoolFilters] || []) as any[] : [];
              return (
                <div key={key}>
                  <label style={{ display: "block", fontSize: "0.68rem", fontWeight: 800, letterSpacing: "0.05em", textTransform: "uppercase", color: "#64748b", marginBottom: 4 }}>
                    {key.charAt(0).toUpperCase() + key.slice(1)}
                  </label>
                  <select
                    value={schoolFilterValues[key] || ""}
                    onChange={(e) => setSchoolFilterValues({ ...schoolFilterValues, [key]: e.target.value })}
                    style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #e2e8f0", background: "#fff", fontSize: "0.82rem", minWidth: 160 }}
                  >
                    <option value="">All</option>
                    {opts.map((o: any) => (
                      <option key={o.id} value={o.id}>{o.name || o.code}</option>
                    ))}
                  </select>
                </div>
              );
            })}
            <div style={{ alignSelf: "flex-end" }}>
              <button
                type="button"
                className="ta-switch-btn active"
                style={{ padding: "8px 14px", borderRadius: 8 }}
                onClick={() => { /* auto-fetch on change; no-op */ }}
              >Apply</button>
            </div>
          </div>

          {schoolLoading && <div className="ta-empty-mini">Loading school analytics…</div>}
          {schoolError && <div className="ta-error">{schoolError}</div>}

          {schoolData && (
            <>
              <section className="ta-kpi-strip" style={{ marginBottom: "1rem" }}>
                <div className="ta-kpi ta-kpi-sky">
                  <div className="ta-kpi-icon"><Activity size={18} /></div>
                  <div>
                    <span className="ta-kpi-label">Overall mean</span>
                    <span className="ta-kpi-value">{schoolData.overall.mean}%</span>
                  </div>
                </div>
                <div className="ta-kpi ta-kpi-violet">
                  <div className="ta-kpi-icon"><Users size={18} /></div>
                  <div><span className="ta-kpi-label">Students</span><span className="ta-kpi-value">{schoolData.overall.student_count}</span></div>
                </div>
                <div className="ta-kpi ta-kpi-emerald">
                  <div className="ta-kpi-icon"><BookOpen size={18} /></div>
                  <div><span className="ta-kpi-label">Subjects</span><span className="ta-kpi-value">{schoolData.overall.subject_count}</span></div>
                </div>
                <div className="ta-kpi ta-kpi-amber">
                  <div className="ta-kpi-icon"><GraduationCap size={18} /></div>
                  <div><span className="ta-kpi-label">Teachers</span><span className="ta-kpi-value">{schoolData.overall.teacher_count}</span></div>
                </div>
              </section>

              {/* By Class */}
              <section className="ta-card" style={{ marginBottom: "1rem" }}>
                <header className="ta-card-head"><Layers size={16} /><h2>By class</h2></header>
                <div className="ta-table-wrap">
                  <table className="ta-table">
                    <thead><tr><th>#</th><th>Class</th><th>Mean</th><th>Deviation</th><th>Students</th></tr></thead>
                    <tbody>
                      {schoolData.by_class.map((r, i) => (
                        <tr key={r.group_id}>
                          <td>{r.rank ?? i + 1}</td>
                          <td><b>{r.group_name}</b></td>
                          <td>{r.mean}%</td>
                          <td><DeviationBadge value={r.deviation} /></td>
                          <td>{r.student_count ?? 0}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              {/* By Subject */}
              <section className="ta-card" style={{ marginBottom: "1rem" }}>
                <header className="ta-card-head"><BookOpen size={16} /><h2>By subject</h2></header>
                <div className="ta-table-wrap">
                  <table className="ta-table">
                    <thead><tr><th>#</th><th>Code</th><th>Subject</th><th>Mean</th><th>Deviation</th><th>Students</th></tr></thead>
                    <tbody>
                      {schoolData.by_subject.map((r, i) => (
                        <tr key={r.subject_id}>
                          <td>{r.rank ?? i + 1}</td>
                          <td><b>{r.code}</b></td>
                          <td>{r.name}</td>
                          <td>{r.mean}%</td>
                          <td><DeviationBadge value={r.deviation} /></td>
                          <td>{r.student_count ?? 0}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              {/* By Teacher */}
              <section className="ta-card" style={{ marginBottom: "1rem" }}>
                <header className="ta-card-head"><GraduationCap size={16} /><h2>By teacher</h2></header>
                <div className="ta-table-wrap">
                  <table className="ta-table">
                    <thead><tr><th>#</th><th>Teacher</th><th>Mean</th><th>Deviation</th><th>Subjects</th><th>Students</th></tr></thead>
                    <tbody>
                      {schoolData.by_teacher.map((r, i) => (
                        <tr key={r.teacher_id}>
                          <td>{r.rank ?? i + 1}</td>
                          <td><b>{r.name}</b> <span style={{ color: "#94a3b8", fontSize: "0.75rem" }}>{r.code}</span></td>
                          <td>{r.mean}%</td>
                          <td><DeviationBadge value={r.deviation} /></td>
                          <td>{r.subject_count}</td>
                          <td>{r.student_count ?? 0}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              {/* By Term */}
              <section className="ta-card" style={{ marginBottom: "1rem" }}>
                <header className="ta-card-head"><LineIcon size={16} /><h2>By term</h2></header>
                <div className="ta-table-wrap">
                  <table className="ta-table">
                    <thead><tr><th>Term</th><th>Mean</th><th>Deviation</th><th>Exams</th></tr></thead>
                    <tbody>
                      {schoolData.by_term.map((r) => (
                        <tr key={r.term_id}>
                          <td><b>{r.name}</b></td>
                          <td>{r.mean}%</td>
                          <td><DeviationBadge value={r.deviation} /></td>
                          <td>{r.exam_count ?? 0}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              {/* By Stream */}
              {schoolData.by_stream.length > 0 && (
                <section className="ta-card" style={{ marginBottom: "1rem" }}>
                  <header className="ta-card-head"><Users size={16} /><h2>By stream</h2></header>
                  <div className="ta-table-wrap">
                    <table className="ta-table">
                      <thead><tr><th>Stream</th><th>Mean</th><th>Classes</th><th>Students</th></tr></thead>
                      <tbody>
                        {schoolData.by_stream.map((r) => (
                          <tr key={r.stream_id}>
                            <td><b>{r.stream_name}</b></td>
                            <td>{r.mean}%</td>
                            <td>{r.class_count}</td>
                            <td>{r.student_count ?? 0}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

// ----------------------------------------------------------------
// Inline chart components — no external chart library
// ----------------------------------------------------------------
function BarChart({ data, height = 240, colorFor }: { data: { label: string; value: number }[]; height?: number; colorFor?: (label: string) => string }) {
  if (!data.length) return <div className="ta-empty-mini">No data</div>;
  const max = Math.max(...data.map((d) => d.value), 1);
  return (
    <div className="ta-chart" style={{ height: height + 30 }}>
      <div className="ta-chart-bar" style={{ height, alignItems: "stretch" }}>
        {data.map((d, i) => (
          <div
            key={i}
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "flex-end",
              gap: 6,
            }}
          >
            <div
              className="ta-bar"
              style={{
                width: "60%",
                maxWidth: 32,
                height: Math.max((d.value / max) * 100, 2) + "%",
                position: "relative",
                background: colorFor
                  ? `linear-gradient(180deg, ${colorFor(d.label)}, ${colorFor(d.label)}cc)`
                  : "linear-gradient(180deg,#38bdf8,#0369a1)",
                borderRadius: "4px 4px 0 0",
              }}
            >
              <span className="ta-bar-value">{d.value.toFixed(0)}</span>
            </div>
            <span className="ta-bar-label">{d.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function LineChart({ data, height = 240 }: { data: { label: string; value: number }[]; height?: number }) {
  if (!data.length) return <div className="ta-empty-mini">No data</div>;
  const w = 600;
  const h = height;
  const padX = 30;
  const padY = 20;
  const values = data.map((d) => d.value);
  const max = Math.max(...values, 100);
  const min = Math.min(...values, 0);
  const range = max - min || 1;
  const step = data.length > 1 ? (w - padX * 2) / (data.length - 1) : 0;
  const pts = data.map((d, i) => ({
    x: padX + i * step,
    y: h - padY - ((d.value - min) / range) * (h - padY * 2),
  }));
  const line = pts.map((p, i) => (i === 0 ? "M" : "L") + p.x.toFixed(1) + "," + p.y.toFixed(1)).join(" ");
  const area = line + " L" + pts[pts.length - 1].x.toFixed(1) + "," + (h - padY) + " L" + pts[0].x.toFixed(1) + "," + (h - padY) + " Z";
  return (
    <div className="ta-chart-line" style={{ height: h + 30 }}>
      <svg
        viewBox={"0 0 " + w + " " + h}
        preserveAspectRatio="none"
        style={{ width: "100%", height: h, display: "block" }}
      >
        <defs>
          <linearGradient id="ta-line-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#38bdf8" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={area} fill="url(#ta-line-grad)" />
        <path d={line} fill="none" stroke="#0369a1" strokeWidth={2} vectorEffect="non-scaling-stroke" />
      </svg>
      <div className="ta-line-labels">
        {data.map((d, i) => <span key={i}>{d.label}</span>)}
      </div>
    </div>
  );
}

function DonutChart({ data, size = 200 }: { data: { label: string; value: number; color: string }[]; size?: number }) {
  if (!data.length) return <div className="ta-empty-mini">No data</div>;
  const total = data.reduce((s, d) => s + d.value, 0) || 1;
  const r = size / 2 - 12;
  const ir = r * 0.6;
  const cx = size / 2;
  const cy = size / 2;
  let acc = 0;
  const arcs = data.map((d, i) => {
    const start = (acc / total) * Math.PI * 2 - Math.PI / 2;
    acc += d.value;
    const end = (acc / total) * Math.PI * 2 - Math.PI / 2;
    const x1 = cx + r * Math.cos(start);
    const y1 = cy + r * Math.sin(start);
    const x2 = cx + r * Math.cos(end);
    const y2 = cy + r * Math.sin(end);
    const xi2 = cx + ir * Math.cos(end);
    const yi2 = cy + ir * Math.sin(end);
    const xi1 = cx + ir * Math.cos(start);
    const yi1 = cy + ir * Math.sin(start);
    const large = end - start > Math.PI ? 1 : 0;
    const path = "M " + x1 + " " + y1 + " A " + r + " " + r + " 0 " + large + " 1 " + x2 + " " + y2 +
                 " L " + xi2 + " " + yi2 + " A " + ir + " " + ir + " 0 " + large + " 0 " + xi1 + " " + yi1 + " Z";
    return { path, color: d.color, key: i };
  });
  return (
    <div className="ta-chart-donut" style={{ width: size, margin: "0 auto" }}>
      <svg viewBox={"0 0 " + size + " " + size} width={size} height={size} style={{ display: "block", margin: "0 auto" }}>
        {arcs.map((a) => <path key={a.key} d={a.path} fill={a.color} />)}
      </svg>
      <div className="ta-donut-legend">
        {data.map((d, i) => (
          <span key={i} className="ta-donut-legend-row">
            <span className="ta-donut-dot" style={{ background: d.color }} />
            <span className="ta-donut-label">{d.label}</span>
            <span className="ta-donut-val">{d.value}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

// ----------------------------------------------------------------
// Chart type switcher (Bar / Line / Pie) — bar is default
// ----------------------------------------------------------------
function DeviationBadge({ value, compact }: { value: number | null | undefined; compact?: boolean }) {
  if (value == null || isNaN(value)) {
    return (
      <span className="ta-tag" style={{ background: "#f1f5f9", color: "#94a3b8", borderColor: "transparent", fontSize: "0.68rem" }}>
        ● n/a
      </span>
    );
  }
  const v = Math.round(value * 10) / 10;
  const abs = Math.abs(v).toFixed(1);
  if (Math.abs(v) < 2) {
    return (
      <span className="ta-tag" style={{ background: "#f1f5f9", color: "#64748b", borderColor: "transparent", fontSize: "0.68rem", fontWeight: 800 }}>
        ● {abs}
      </span>
    );
  }
  const up = v > 0;
  return (
    <span className="ta-tag" style={{
      background: up ? "#dcfce7" : "#fee2e2",
      color: up ? "#166534" : "#991b1b",
      borderColor: "transparent",
      fontSize: "0.68rem",
      fontWeight: 800,
    }}>
      {up ? "▲" : "▼"} {up ? "+" : ""}{abs}{compact ? "" : ""}
    </span>
  );
}


function ChartTypeSwitch({
  value, onChange,
}: { value: ChartKind; onChange: (v: ChartKind) => void }) {
  const opts: [ChartKind, string, any][] = [
    ["bar", "Bar", BarChart3],
    ["line", "Line", LineIcon],
    ["pie", "Pie", PieChart],
  ];
  return (
    <div className="ta-switch">
      {opts.map(([id, label, Icon]) => (
        <button
          key={id}
          type="button"
          className={"ta-switch-btn" + (value === id ? " active" : "")}
          onClick={() => onChange(id)}
          title={label + " chart"}
        >
          <Icon size={13} /> {label}
        </button>
      ))}
    </div>
  );
}
