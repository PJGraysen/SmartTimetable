import { useEffect, useState } from "react";
import {
  Award, TrendingUp, TrendingDown, Target, Activity,
  BookOpen, AlertTriangle, Sparkles, Users, ChevronDown,
} from "lucide-react";
import http from "../services/http";
import "./StudentAcademicsPage.css";

type Exam = {
  assessment_id: string;
  name: string;
  date: string;
  pct: number;
  grade: string;
};

type Subject = {
  subject_id: string;
  code: string;
  name: string;
  mean: number;
  grade: string;
  trend: "improving" | "stable" | "declining";
  consistency: string;
  consistency_sd: number;
  class_mean: number | null;
  class_median: number | null;
  delta_class: number | null;
  percentile: number | null;
  exam_count: number;
  best: Exam | null;
  worst: Exam | null;
  exams: Exam[];
};

type Overall = {
  mean: number;
  class_mean: number | null;
  delta: number | null;
  class_rank: number | null;
  class_size: number | null;
  percentile: number | null;
  std_dev: number;
  subject_count: number;
  exam_count: number;
};

type RecentExam = { name: string; date: string; mean: number; subject_count: number };

export default function StudentAcademicsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [student, setStudent] = useState<any>(null);
  const [overall, setOverall] = useState<Overall | null>(null);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [strengths, setStrengths] = useState<Subject[]>([]);
  const [focus, setFocus] = useState<Subject[]>([]);
  const [recent, setRecent] = useState<RecentExam[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    http.get("/academics/analysis/me/")
      .then((r) => {
        const d = r.data || {};
        setStudent(d.student || null);
        setOverall(d.overall || null);
        setSubjects(Array.isArray(d.subjects) ? d.subjects : []);
        setStrengths(Array.isArray(d.strengths) ? d.strengths : []);
        setFocus(Array.isArray(d.focus) ? d.focus : []);
        setRecent(Array.isArray(d.recent_exams) ? d.recent_exams : []);
      })
      .catch((e) => setError(
        e?.response?.data?.detail || "Could not load your academic data.",
      ))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="sa-page"><div className="sa-empty">Loading your academics…</div></div>;
  if (error) return <div className="sa-page"><div className="sa-error">{error}</div></div>;

  const fmtDelta = (d: number | null) => {
    if (d == null) return "—";
    const sign = d >= 0 ? "+" : "";
    return `${sign}${d.toFixed(1)}`;
  };

  return (
    <div className="sa-page">
      <header className="sa-hero">
        <div className="sa-hero-left">
          <span className="sa-hero-eyebrow">
            <Sparkles size={13} /> My Performance
          </span>
          <h1>{student?.name || "Student"}</h1>
          <p className="sa-hero-sub">
            {student?.admission}{student?.klass ? ` · ${student.klass}` : ""}
          </p>
        </div>
        {overall && (
          <div className="sa-hero-right">
            <div className="sa-hero-stat">
              <div>
                <span className="sa-hero-stat-label">Overall mean</span>
                <span className="sa-hero-stat-value">{overall.mean.toFixed(1)}%</span>
              </div>
            </div>
            {overall.class_rank != null && (
              <div className="sa-hero-stat">
                <Users size={14} />
                <div>
                  <span className="sa-hero-stat-label">Class rank</span>
                  <span className="sa-hero-stat-value">
                    #{overall.class_rank}<small>/{overall.class_size}</small>
                  </span>
                </div>
              </div>
            )}
            {overall.percentile != null && (
              <div className="sa-hero-stat">
                <Award size={14} />
                <div>
                  <span className="sa-hero-stat-label">Percentile</span>
                  <span className="sa-hero-stat-value">Top {100 - overall.percentile}%</span>
                </div>
              </div>
            )}
          </div>
        )}
      </header>

      {overall && (
        <section className="sa-strip">
          <div className="sa-strip-card">
            <Target size={16} />
            <div>
              <span>vs Class</span>
              <b className={(overall.delta ?? 0) >= 0 ? "sa-pos" : "sa-neg"}>
                {fmtDelta(overall.delta)}
              </b>
            </div>
          </div>
          <div className="sa-strip-card">
            <Activity size={16} />
            <div>
              <span>Consistency (σ)</span>
              <b>{overall.std_dev.toFixed(1)}</b>
            </div>
          </div>
          <div className="sa-strip-card">
            <BookOpen size={16} />
            <div>
              <span>Subjects</span>
              <b>{overall.subject_count}</b>
            </div>
          </div>
          <div className="sa-strip-card">
            <TrendingUp size={16} />
            <div>
              <span>Exams</span>
              <b>{overall.exam_count}</b>
            </div>
          </div>
        </section>
      )}

      <div className="sa-split">
        <section className="sa-side sa-side-strength">
          <header><Award size={16} /> <h2>Strengths</h2></header>
          {strengths.length === 0
            ? <p className="sa-side-empty">More data needed.</p>
            : <ul>
                {strengths.map((s) => (
                  <li key={s.subject_id}>
                    <b>{s.code}</b>
                    <span className="sa-side-metric">{s.mean.toFixed(1)}%</span>
                    {s.delta_class != null && (
                      <span className={"sa-delta " + ((s.delta_class ?? 0) >= 0 ? "sa-pos" : "sa-neg")}>
                        {fmtDelta(s.delta_class)}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
          }
        </section>

        <section className="sa-side sa-side-focus">
          <header><AlertTriangle size={16} /> <h2>Focus areas</h2></header>
          {focus.length === 0
            ? <p className="sa-side-empty">Nothing to flag yet.</p>
            : <ul>
                {focus.map((s) => (
                  <li key={s.subject_id}>
                    <b>{s.code}</b>
                    <span className="sa-side-metric">{s.mean.toFixed(1)}%</span>
                    {s.delta_class != null && (
                      <span className={"sa-delta " + ((s.delta_class ?? 0) >= 0 ? "sa-pos" : "sa-neg")}>
                        {fmtDelta(s.delta_class)}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
          }
        </section>
      </div>

      {recent.length > 0 && (
        <section className="sa-recent">
          <header><TrendingUp size={16} /> <h2>Recent exams</h2></header>
          <div className="sa-recent-row">
            {recent.map((e, i) => {
              const prev = recent[i + 1];
              const delta = prev ? e.mean - prev.mean : null;
              return (
                <div key={i} className="sa-recent-card">
                  <div className="sa-recent-name">{e.name}</div>
                  <div className="sa-recent-date">
                    {e.date ? new Date(e.date).toLocaleDateString() : "—"}
                  </div>
                  <div className="sa-recent-mean">
                    {e.mean.toFixed(1)}%
                    {delta != null && (
                      <span className={"sa-recent-delta " + (delta >= 0 ? "sa-pos" : "sa-neg")}>
                        {delta >= 0 ? "▲" : "▼"} {Math.abs(delta).toFixed(1)}
                      </span>
                    )}
                  </div>
                  <div className="sa-recent-sub">{e.subject_count} subject{e.subject_count === 1 ? "" : "s"}</div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      <section className="sa-subjects">
        <header className="sa-subjects-head">
          <h2>All subjects</h2>
          <span className="sa-subjects-hint">Click a subject to expand exam history</span>
        </header>
        <div className="sa-grid">
          {subjects.map((s) => {
            const isOpen = expanded === s.subject_id;
            return (
              <article
                key={s.subject_id}
                className={"sa-card" + (isOpen ? " open" : "")}
                onClick={() => setExpanded(isOpen ? null : s.subject_id)}
              >
                <header className="sa-card-head">
                  <div>
                    <div className="sa-card-code">{s.code}</div>
                    <div className="sa-card-name">{s.name}</div>
                  </div>
                  <span className={"sa-trend sa-trend-" + s.trend}>
                    {s.trend === "improving" ? <TrendingUp size={14} /> : s.trend === "declining" ? <TrendingDown size={14} /> : null}
                    {s.trend}
                  </span>
                </header>

                <div className="sa-card-main">
                  <div className="sa-card-big">
                    <b>{s.mean.toFixed(1)}%</b>
                    <span>my mean</span>
                  </div>
                  <span className={"sa-grade sa-grade-" + (s.grade || "x")}>{s.grade}</span>
                </div>

                <div className="sa-card-metrics">
                  <div className="sa-metric">
                    <span>Class</span>
                    <b>{s.class_mean != null ? s.class_mean.toFixed(1) + "%" : "—"}</b>
                  </div>
                  <div className="sa-metric">
                    <span>Delta</span>
                    <b className={(s.delta_class ?? 0) >= 0 ? "sa-pos" : "sa-neg"}>
                      {fmtDelta(s.delta_class)}
                    </b>
                  </div>
                  <div className="sa-metric">
                    <span>Percentile</span>
                    <b>{s.percentile != null ? s.percentile + "th" : "—"}</b>
                  </div>
                  <div className="sa-metric">
                    <span>σ</span>
                    <b>{s.consistency_sd.toFixed(1)}</b>
                  </div>
                </div>

                <div className="sa-card-tags">
                  <span className="sa-tag">{s.consistency}</span>
                  <span className="sa-tag">{s.exam_count} exam{s.exam_count === 1 ? "" : "s"}</span>
                </div>

                {isOpen && s.exams.length > 0 && (
                  <div className="sa-exam-history">
                    <div className="sa-exam-history-head">
                      Exam history <ChevronDown size={11} />
                    </div>
                    {s.exams.map((e, i) => (
                      <div key={i} className="sa-exam-row">
                        <span className="sa-exam-row-name">{e.name}</span>
                        <span className="sa-exam-row-date">
                          {e.date ? new Date(e.date).toLocaleDateString() : "—"}
                        </span>
                        <span className="sa-exam-row-pct">{e.pct.toFixed(1)}%</span>
                        <span className="sa-exam-row-grade">{e.grade}</span>
                      </div>
                    ))}
                  </div>
                )}
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
}
