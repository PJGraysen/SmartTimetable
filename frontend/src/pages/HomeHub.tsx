import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  BookOpen, CalendarDays, GraduationCap, LayoutGrid,
  Package, Bot, ArrowUpRight, Sparkles,
} from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import CalendarWidget from "../components/CalendarWidget";
import http from "../services/http";
import "./HomeHub.css";

type Tile = {
  to: string;
  label: string;
  desc: string;
  icon: React.ComponentType<{ size?: number }>;
  hue: string;
  module: string;
};

const HUB_TILES: Tile[] = [
  { to: "/academics",     label: "Academics",  desc: "Students, marks, analysis, reports",     icon: GraduationCap, hue: "amber",  module: "academics" },
  { to: "/timetables",    label: "Timetable",  desc: "Master and per-class timetables",        icon: CalendarDays,  hue: "sky",    module: "scheduling" },
  { to: "/library",       label: "Library",    desc: "Catalogue, loans, resources",            icon: BookOpen,      hue: "emerald",module: "library" },
  { to: "/inventory/dashboard", label: "Inventory", desc: "Assets, stock, movements",         icon: Package,       hue: "rose",   module: "inventory" },
  { to: "/scheduling",    label: "Scheduling", desc: "Generate and validate timetables",       icon: LayoutGrid,    hue: "violet", module: "scheduling" },
  { to: "/ai",            label: "AI Assistant", desc: "Ask questions about your data",        icon: Bot,           hue: "cyan",   module: "aichat" },
];

// Student-specific tiles
const STUDENT_TILES: Tile[] = [
  { to: "/academics",           label: "My Academics", desc: "Your subjects, marks, and rank",   icon: GraduationCap, hue: "amber",  module: "academics" },
  { to: "/timetables",          label: "My Timetable", desc: "This week's classes",              icon: CalendarDays,  hue: "sky",    module: "scheduling" },
  { to: "/library/catalogue",   label: "Library",      desc: "Browse and borrow books",          icon: BookOpen,      hue: "emerald",module: "library" },
  { to: "/ai",                  label: "AI Assistant", desc: "Get help with your studies",       icon: Bot,           hue: "cyan",   module: "aichat" },
];

export default function HomeHub() {
  const { user, modules, role } = useAuth();
  const navigate = useNavigate();
  const [clock, setClock] = useState(new Date());

  useEffect(() => {
    const t = window.setInterval(() => setClock(new Date()), 1000);
    return () => window.clearInterval(t);
  }, []);

  const isStudent = role === "STUDENT";
  const u = user as any;
  const firstLast = [u?.first_name, u?.last_name].filter(Boolean).join(" ").trim();
  const rawName =
    u?.display_name ||
    u?.full_name ||
    firstLast ||
    u?.username ||
    "there";
  const displayName = String(rawName)
    .replace(/^[A-Za-z]+\d+\s*[-\u2013\u2014]\s*/, "")
    .trim();
  const isSuper = modules.includes("*");

  const tiles = (isStudent ? STUDENT_TILES : HUB_TILES).filter(
    (t) => isSuper || modules.includes(t.module),
  );

  const greeting = (() => {
    const h = clock.getHours();
    if (h < 12) return "Good morning";
    if (h < 17) return "Good afternoon";
    return "Good evening";
  })();

  return (
    <div className="hh-page">
      {/* Greeting bar */}
      <header className="hh-hero">
        <div className="hh-hero-left">
          <span className="hh-eyebrow">
            <Sparkles size={13} /> SmartTimetable Pro
          </span>
          <h1 className="hh-greeting">
            {greeting}, <b>{(() => {
      const parts = displayName.split(/\s+/).filter(Boolean);
      // skip title prefixes like Mr., Mrs., Ms., Fr., Dr., Madam, Sis.
      const titles = new Set(["mr.", "mrs.", "ms.", "fr.", "dr.", "madam", "sis.", "mr", "mrs", "ms", "fr", "dr"]);
      const withoutTitle = parts.filter((p) => !titles.has(p.toLowerCase()));
      return withoutTitle[0] || parts[0] || "there";
    })()}</b>
          </h1>
          <p className="hh-date">
            {clock.toLocaleDateString(undefined, {
              weekday: "long", day: "numeric", month: "long", year: "numeric",
            })}
          </p>
        </div>
        <div className="hh-hero-right">
          <div className="hh-clock">
            <span>{clock.toLocaleTimeString()}</span>
          </div>
        </div>
      </header>

      <div className="hh-layout">
        {/* Tiles grid */}
        <section className="hh-grid">
          {tiles.map((t, i) => {
            const Icon = t.icon;
            return (
              <button
                key={t.to}
                className={`hh-tile hh-tile-${t.hue}`}
                style={{ animationDelay: `${i * 45}ms` }}
                onClick={() => navigate(t.to)}
              >
                <div className="hh-tile-icon">
                  <Icon size={22} />
                </div>
                <div className="hh-tile-body">
                  <div className="hh-tile-label">{t.label}</div>
                  <div className="hh-tile-desc">{t.desc}</div>
                </div>
                <ArrowUpRight size={16} className="hh-tile-arrow" />
              </button>
            );
          })}
        </section>

        {/* Student exam summary below tiles */}
        {isStudent && <ExamSummaryWidget />}

        {/* Side panel: calendar */}
        <aside className="hh-aside">
          <div className="hh-calendar-frame">
            <div className="hh-cal-header">
              <h3>Calendar</h3>
              <div className="hh-cal-header-dots">
                <span /><span /><span />
              </div>
            </div>
            <CalendarWidget />
          </div>
        </aside>
      </div>
    </div>
  );
}


// ============================================================
// Exam summary widget — student's last 3 exams at a glance
// ============================================================
import { Award, TrendingUp as TrendIcon } from "lucide-react";
import { useEffect as _useEffect, useState as _useState } from "react";

function ExamSummaryWidget() {
  const [_loading, _setLoading] = _useState(true);
  const [_exams, _setExams] = _useState<Array<{
    name: string; date: string; mean: number; rank?: number;
  }>>([]);

  _useEffect(() => {
    http.get("/academics/analysis/me/")
      .then((r) => {
        const d = r.data || {};
        const ex = Array.isArray(d.recent_exams) ? d.recent_exams : [];
        _setExams(ex.slice(0, 3));
      })
      .catch(() => _setExams([]))
      .finally(() => _setLoading(false));
  }, []);

  if (_loading) return null;
  if (_exams.length === 0) return null;

  return (
    <section className="hh-exam-summary">
      <header className="hh-exam-head">
        <Award size={16} />
        <h2>Last {_exams.length} exam{_exams.length === 1 ? "" : "s"}</h2>
      </header>
      <div className="hh-exam-list">
        {_exams.map((e, i) => {
          const prev = _exams[i + 1];
          const delta = prev ? Number(e.mean || 0) - Number(prev.mean || 0) : null;
          const cls = delta == null ? "" : delta >= 0 ? "hh-delta-up" : "hh-delta-down";
          return (
            <div key={i} className="hh-exam-row">
              <div className="hh-exam-name">{e.name}</div>
              <div className="hh-exam-date">{e.date ? new Date(e.date).toLocaleDateString() : "—"}</div>
              <div className="hh-exam-mean">
                <b>{Number(e.mean || 0).toFixed(1)}%</b>
                {delta != null && (
                  <span className={"hh-delta " + cls}>
                    {delta >= 0 ? "▲" : "▼"} {Math.abs(delta).toFixed(1)}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
