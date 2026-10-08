import { useEffect, useMemo, useState } from "react";
import {
  Activity, BookOpen, GraduationCap, Layers, TrendingDown, TrendingUp, Users,
} from "lucide-react";
import http from "../services/http";
import "./TeacherAnalyticsPage.css";

// ---------------- types ----------------
type Filters = {
  classes: { id: string; name: string }[];
  streams: { id: string; name: string }[];
  subjects: { id: string; name: string; code: string }[];
  teachers: { id: string; name: string; code: string }[];
  terms: { id: string; name: string }[];
  students: { id: string; name: string; admission: string }[];
};

type Row = {
  mean: number;
  deviation: number | null;
  rank?: number;
  student_count?: number;
  exam_count?: number;
};
type ClassRow = Row & { group_id: string; group_name: string };
type SubjectRow = Row & { subject_id: string; code: string; name: string };
type TeacherRow = Row & { teacher_id: string; name: string; code: string; subject_count: number };
type TermRow = Row & { term_id: string; name: string };
type StreamRow = Row & { stream_id: string; stream_name: string; class_count: number };
type RecentExam = { assessment_id: string; name: string; date: string; mean: number; subject_count: number };

type SchoolData = {
  filters: Record<string, string | null>;
  overall: {
    mean: number; student_count: number; subject_count: number;
    class_count: number; teacher_count: number; exam_count: number;
  };
  by_class: ClassRow[];
  by_stream: StreamRow[];
  by_subject: SubjectRow[];
  by_teacher: TeacherRow[];
  by_term: TermRow[];
  recent_exams: RecentExam[];
};

// ---------------- deviation badge ----------------
function DeviationBadge({ value }: { value: number | null | undefined }) {
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
      {up ? "▲ +" : "▼ "}{abs}
    </span>
  );
}

export default function SchoolAnalyticsPage() {
  const [data, setData] = useState<SchoolData | null>(null);
  const [filters, setFilters] = useState<Filters | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [values, setValues] = useState<Record<string, string>>({
    class: "", stream: "", student: "", subject: "", teacher: "", term: "",
  });

  // Load filters once
  useEffect(() => {
    http.get("/academics/analysis/school/filters/")
      .then((r) => setFilters(r.data))
      .catch(() => setFilters(null));
  }, []);

  // Load data on filter change
  useEffect(() => {
    setLoading(true);
    setError("");
    const params = new URLSearchParams();
    Object.entries(values).forEach(([k, v]) => { if (v) params.append(k, v); });
    const qs = params.toString();
    http.get("/academics/analysis/school/" + (qs ? "?" + qs : ""))
      .then((r) => setData(r.data))
      .catch((e) => {
        setError(e?.response?.data?.detail || "Could not load school analytics.");
        setData(null);
      })
      .finally(() => setLoading(false));
  }, [values]);

  const reset = () => setValues({ class: "", stream: "", student: "", subject: "", teacher: "", term: "" });

  const activeFilterCount = useMemo(
    () => Object.values(values).filter(Boolean).length,
    [values],
  );

  return (
    <div className="ta-page">
      {/* ---------- HERO ---------- */}
      <header className="ta-hero">
        <div className="ta-hero-left">
          <span className="ta-hero-eyebrow"><Activity size={13} /> School Analytics</span>
          <h1>Whole-School Performance</h1>
          <p className="ta-hero-sub">
            {data?.overall.student_count ?? 0} students · {data?.overall.class_count ?? 0} classes ·{" "}
            {data?.overall.subject_count ?? 0} subjects · {data?.overall.teacher_count ?? 0} teachers
          </p>
        </div>
        {data && (
          <div className="ta-hero-right">
            <div className="ta-hero-stat">
              <div>
                <span className="ta-hero-stat-label">Overall mean</span>
                <span className="ta-hero-stat-value" style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                  {data.overall.mean}%
                </span>
              </div>
            </div>
            <div className="ta-hero-stat">
              <div>
                <span className="ta-hero-stat-label">Filters active</span>
                <span className="ta-hero-stat-value">{activeFilterCount}</span>
              </div>
            </div>
          </div>
        )}
      </header>

      {/* ---------- FILTER BAR ---------- */}
      <div className="ta-filter-row" style={{ marginBottom: "1rem", flexWrap: "wrap", gap: "0.75rem" }}>
        {(["class", "stream", "subject", "teacher", "term", "student"] as const).map((key) => {
          const listKey = (key === "class" ? "classes"
            : key === "stream" ? "streams"
            : key === "subject" ? "subjects"
            : key === "teacher" ? "teachers"
            : key === "term" ? "terms"
            : "students") as keyof Filters;
          const opts = (filters?.[listKey] ?? []) as any[];
          return (
            <div key={key}>
              <label style={{ display: "block", fontSize: "0.68rem", fontWeight: 800, letterSpacing: "0.05em", textTransform: "uppercase", color: "#64748b", marginBottom: 4 }}>
                {key.charAt(0).toUpperCase() + key.slice(1)}
              </label>
              <select
                value={values[key] || ""}
                onChange={(e) => setValues({ ...values, [key]: e.target.value })}
                style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #e2e8f0", background: "#fff", fontSize: "0.82rem", minWidth: 170 }}
              >
                <option value="">All</option>
                {opts.map((o: any) => (
                  <option key={o.id} value={o.id}>
                    {o.name || o.code}{o.admission ? ` · ${o.admission}` : ""}
                  </option>
                ))}
              </select>
            </div>
          );
        })}
        <div style={{ alignSelf: "flex-end" }}>
          <button
            type="button"
            onClick={reset}
            className="ta-switch-btn"
            style={{ padding: "8px 14px", borderRadius: 8 }}
          >Reset</button>
        </div>
      </div>

      {loading && <div className="ta-empty-mini">Loading school analytics…</div>}
      {error && <div className="ta-error">{error}</div>}

      {data && !loading && (
        <>
          {/* ---------- KPI STRIP ---------- */}
          <section className="ta-kpi-strip" style={{ marginBottom: "1rem" }}>
            <div className="ta-kpi ta-kpi-sky">
              <div className="ta-kpi-icon"><Activity size={18} /></div>
              <div>
                <span className="ta-kpi-label">Overall mean</span>
                <span className="ta-kpi-value">{data.overall.mean}%</span>
              </div>
            </div>
            <div className="ta-kpi ta-kpi-violet">
              <div className="ta-kpi-icon"><Users size={18} /></div>
              <div><span className="ta-kpi-label">Students</span><span className="ta-kpi-value">{data.overall.student_count}</span></div>
            </div>
            <div className="ta-kpi ta-kpi-emerald">
              <div className="ta-kpi-icon"><BookOpen size={18} /></div>
              <div><span className="ta-kpi-label">Subjects</span><span className="ta-kpi-value">{data.overall.subject_count}</span></div>
            </div>
            <div className="ta-kpi ta-kpi-amber">
              <div className="ta-kpi-icon"><GraduationCap size={18} /></div>
              <div><span className="ta-kpi-label">Teachers</span><span className="ta-kpi-value">{data.overall.teacher_count}</span></div>
            </div>
          </section>

          {/* ---------- RECENT EXAMS CHART ---------- */}
          {data.recent_exams.length > 0 && (
            <section className="ta-card" style={{ marginBottom: "1rem" }}>
              <header className="ta-card-head">
                <TrendingUp size={16} />
                <h2>Recent exams — school mean</h2>
              </header>
              <div style={{ display: "flex", gap: 8, alignItems: "flex-end", height: 220, padding: "0.5rem 0" }}>
                {data.recent_exams.slice().reverse().map((e, i) => {
                  const max = Math.max(...data.recent_exams.map((x) => x.mean), 1);
                  const h = (e.mean / max) * 100;
                  return (
                    <div key={e.assessment_id} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4, height: "100%", justifyContent: "flex-end" }}>
                      <span style={{ fontSize: "0.7rem", fontWeight: 800, color: "#334155" }}>{e.mean.toFixed(1)}</span>
                      <div style={{
                        width: "70%",
                        maxWidth: 36,
                        height: `${Math.max(h, 4)}%`,
                        background: `linear-gradient(180deg, ${["#0ea5e9", "#10b981", "#f59e0b"][i % 3]}, ${["#0369a1", "#047857", "#b45309"][i % 3]})`,
                        borderRadius: "6px 6px 0 0",
                      }} />
                      <span style={{ fontSize: "0.62rem", color: "#64748b", textAlign: "center", fontWeight: 700 }}>
                        {e.name.replace(/^Term \d+\s*/i, "")}
                      </span>
                    </div>
                  );
                })}
              </div>
            </section>
          )}

          {/* ---------- BY CLASS ---------- */}
          <section className="ta-card" style={{ marginBottom: "1rem" }}>
            <header className="ta-card-head"><Layers size={16} /><h2>By class</h2></header>
            <div className="ta-table-wrap">
              <table className="ta-table">
                <thead><tr><th>#</th><th>Class</th><th>Mean</th><th>Deviation</th><th>Students</th></tr></thead>
                <tbody>
                  {data.by_class.map((r, i) => (
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

          {/* ---------- BY SUBJECT ---------- */}
          <section className="ta-card" style={{ marginBottom: "1rem" }}>
            <header className="ta-card-head"><BookOpen size={16} /><h2>By subject</h2></header>
            <div className="ta-table-wrap">
              <table className="ta-table">
                <thead><tr><th>#</th><th>Code</th><th>Subject</th><th>Mean</th><th>Deviation</th><th>Students</th></tr></thead>
                <tbody>
                  {data.by_subject.map((r, i) => (
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

          {/* ---------- BY TEACHER ---------- */}
          <section className="ta-card" style={{ marginBottom: "1rem" }}>
            <header className="ta-card-head"><GraduationCap size={16} /><h2>By teacher</h2></header>
            <div className="ta-table-wrap">
              <table className="ta-table">
                <thead><tr><th>#</th><th>Teacher</th><th>Mean</th><th>Deviation</th><th>Subjects</th><th>Students</th></tr></thead>
                <tbody>
                  {data.by_teacher.map((r, i) => (
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

          {/* ---------- BY TERM ---------- */}
          <section className="ta-card" style={{ marginBottom: "1rem" }}>
            <header className="ta-card-head"><TrendingDown size={16} /><h2>By term</h2></header>
            <div className="ta-table-wrap">
              <table className="ta-table">
                <thead><tr><th>Term</th><th>Mean</th><th>Deviation</th><th>Exams</th></tr></thead>
                <tbody>
                  {data.by_term.map((r) => (
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

          {/* ---------- BY STREAM ---------- */}
          {data.by_stream.length > 0 && (
            <section className="ta-card" style={{ marginBottom: "1rem" }}>
              <header className="ta-card-head"><Users size={16} /><h2>By stream</h2></header>
              <div className="ta-table-wrap">
                <table className="ta-table">
                  <thead><tr><th>Stream</th><th>Mean</th><th>Classes</th><th>Students</th></tr></thead>
                  <tbody>
                    {data.by_stream.map((r) => (
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
  );
}
