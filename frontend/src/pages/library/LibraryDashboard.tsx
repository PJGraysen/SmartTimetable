import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  BookOpen, Copy as CopyIcon, Users, AlertTriangle,
  BookMarked, CheckCircle2, Library, Loader2, X,
} from "lucide-react";
import * as lib from "../../services/library";

/* ===== Category map: groups the 27 curriculum subjects into 8 faculties ===== */
type CategoryKey =
  | "math" | "sciences" | "languages" | "humanities"
  | "religious" | "creative" | "technology" | "applied";

const CATEGORIES: Record<CategoryKey, { label: string; icon: string; colour: string; codes: string[] }> = {
  math:       { label: "Mathematics",           icon: "🔢", colour: "#1e3a8a", codes: ["MAT", "EMCM"] },
  sciences:   { label: "Sciences",              icon: "🔬", colour: "#0e7490", codes: ["BIO","BIOPRAC","CHEM","CHEMPRAC","PHY","PHYPRAC","INTSCI"] },
  languages:  { label: "Languages",             icon: "📚", colour: "#b91c1c", codes: ["ENG","KIS","LIT"] },
  humanities: { label: "Humanities",            icon: "🌍", colour: "#065f46", codes: ["GEO","HIS","SST"] },
  religious:  { label: "Religious Studies",     icon: "🙏", colour: "#7c2d12", codes: ["CRE","IRE","PPI"] },
  creative:   { label: "Creative Arts",         icon: "🎨", colour: "#7e22ce", codes: ["CAS","MUSD","ART"] },
  technology: { label: "Business & Technology", icon: "💻", colour: "#0f766e", codes: ["BUS","COMP","CS","ICT"] },
  applied:    { label: "Applied & Vocational",  icon: "🌾", colour: "#92400e", codes: ["AGR","PE"] },
};

const CATEGORY_ORDER: CategoryKey[] = [
  "math","sciences","languages","humanities","religious","creative","technology","applied",
];

const fallbackIcon = (code: string): string => {
  const map: Record<string, string> = {
    AGR:"🌾",BIO:"🧬",BIOPRAC:"🔬",BUS:"💼",CAS:"🎭",CHEM:"🧪",CHEMPRAC:"🧫",
    COMP:"💻",CS:"🖥️",CRE:"✝️",EMCM:"📐",ENG:"📖",GEO:"🌍",HIS:"🏛️",ICT:"🖥️",
    INTSCI:"🔬",IRE:"☪️",KIS:"📚",LIT:"📜",MAT:"🧮",MUSD:"🎼",PE:"🏃",PHY:"⚛️",
    PHYPRAC:"🔭",PPI:"🙏",SST:"🌐",ART:"🎨",
  };
  return map[code.toUpperCase()] || "📕";
};
const fallbackColour = (code: string): string => {
  const map: Record<string, string> = {
    MAT:"#1e3a8a",ENG:"#1d4ed8",KIS:"#b91c1c",BIO:"#15803d",CHEM:"#0e7490",
    PHY:"#0e7490",GEO:"#065f46",HIS:"#7c2d12",CRE:"#7c2d12",AGR:"#92400e",
    BUS:"#1e40af",COMP:"#1e3a8a",ICT:"#0f766e",MUSD:"#7e22ce",ART:"#a21caf",
  };
  return map[code.toUpperCase()] || "#475569";
};

export default function LibraryDashboard() {
  const [stats, setStats] = useState<lib.LibraryDashboard | null>(null);
  const [subjects, setSubjects] = useState<lib.SubjectSummaryRow[]>([]);
  const [subjectsLoading, setSubjectsLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<CategoryKey | null>(null);

  useEffect(() => {
    lib.getDashboard()
      .then(setStats)
      .catch((e) => setError(e?.response?.data?.detail || "Unable to load dashboard."));
    lib.getSubjectSummary()
      .then(setSubjects)
      .catch(() => setSubjects([]))
      .finally(() => setSubjectsLoading(false));
  }, []);

  const cards = stats ? [
    { label: "Books", value: stats.total_books, icon: BookOpen, colour: "#1e3a8a" },
    { label: "Copies", value: stats.total_copies, icon: CopyIcon, colour: "#0e7490" },
    { label: "Available", value: stats.available_copies, icon: CheckCircle2, colour: "#059669" },
    { label: "Issued", value: stats.issued_copies, icon: BookMarked, colour: "#7c3aed" },
    { label: "Active Loans", value: stats.active_loans, icon: BookMarked, colour: "#0284c7" },
    { label: "Overdue", value: stats.overdue_loans, icon: AlertTriangle, colour: "#dc2626" },
    { label: "Members", value: stats.active_members, icon: Users, colour: "#65a30d" },
  ] : [];

  const coveredSubjects = subjects.filter((s) => s.book_count > 0).length;
  const totalSubjects = subjects.length;

  /* Per-category aggregates */
  const categoryStats = useMemo(() => {
    const map: Record<CategoryKey, { subjects: number; covered: number; books: number; available: number }> =
      {} as any;
    for (const key of CATEGORY_ORDER) map[key] = { subjects: 0, covered: 0, books: 0, available: 0 };
    for (const s of subjects) {
      const code = (s.code || "").toUpperCase();
      for (const key of CATEGORY_ORDER) {
        if (CATEGORIES[key].codes.includes(code)) {
          map[key].subjects += 1;
          if (s.book_count > 0) map[key].covered += 1;
          map[key].books += s.book_count;
          map[key].available += s.available_copies;
          break;
        }
      }
    }
    return map;
  }, [subjects]);

  const filteredSubjects = useMemo(() => {
    if (!selectedCategory) return subjects;
    const codes = CATEGORIES[selectedCategory].codes;
    return subjects.filter((s) => codes.includes((s.code || "").toUpperCase()));
  }, [subjects, selectedCategory]);

  const toggleCategory = (key: CategoryKey) =>
    setSelectedCategory((prev) => (prev === key ? null : key));

  return (
    <div className="lib-dash" style={{ padding: "1.5rem", position: "relative", overflow: "hidden" }}>
      <div className="lib-shelf-bg" aria-hidden="true" />

      <div style={{ position: "relative", zIndex: 2 }}>
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "1rem", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <span style={{ fontSize: "0.75rem", letterSpacing: "0.08em", color: "#748095", fontWeight: 700 }}>
              LIBRARY MANAGEMENT
            </span>
            <h1 style={{ marginTop: "0.35rem" }}>Dashboard</h1>
            <p style={{ color: "#748095" }}>Catalogue, circulation, and inventory overview.</p>
          </div>
          <div style={{ display: "flex", gap: "0.5rem", alignSelf: "flex-start" }}>
            <Link to="/library/circulation" className="primary-button">Circulation Desk</Link>
            <Link to="/library/catalogue/new" className="secondary-button">Add Book</Link>
          </div>
        </div>

        {error ? <div className="tt-error">{error}</div> : null}

        {/* Stats */}
        <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "1rem" }}>
          {cards.map((c) => {
            const Icon = c.icon;
            return (
              <div key={c.label} className="lib-stat-card"
                   style={{ background: "rgba(255,255,255,0.94)", border: "1px solid #e5e7eb",
                            borderRadius: "10px", padding: "1.25rem", backdropFilter: "blur(2px)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ color: "#748095", fontSize: "0.8rem", fontWeight: 700,
                                 textTransform: "uppercase", letterSpacing: "0.05em" }}>{c.label}</span>
                  <Icon size={20} style={{ color: c.colour }} />
                </div>
                <div style={{ fontSize: "1.85rem", fontWeight: 700, color: "#111827", marginTop: "0.5rem" }}>{c.value}</div>
              </div>
            );
          })}
        </section>

        {/* Quick Actions — promoted to top */}
        <section style={{
          marginTop: "1.5rem",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "1rem",
        }}>
          <QuickLink to="/library/catalogue" icon={BookOpen} title="Catalogue"
                     text="Browse and search the book collection." colour="#1e3a8a" />
          <QuickLink to="/library/members" icon={Users} title="Members"
                     text="Students, teachers, and staff who borrow." colour="#0e7490" />
          <QuickLink to="/library/loans" icon={BookMarked} title="Loans"
                     text="Active, overdue, and returned loans." colour="#7c3aed" />
          <QuickLink to="/library/reports" icon={AlertTriangle} title="Reports"
                     text="Circulation, inventory, top borrowers." colour="#dc2626" />
        </section>

        {/* Learning Categories */}
        <section style={{ marginTop: "2rem" }}>
          <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: "0.9rem", flexWrap: "wrap", gap: "0.5rem" }}>
            <div>
              <h2 style={{ margin: 0, fontSize: "1.15rem", color: "#111827",
                           display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Library size={18} style={{ color: "#1e3a8a" }} />
                Learning Categories
              </h2>
              <p style={{ color: "#748095", fontSize: "0.83rem", marginTop: "0.2rem" }}>
                {coveredSubjects} of {totalSubjects} subjects covered
                {selectedCategory ? ` · filtered to ${CATEGORIES[selectedCategory].label}` : ""}
              </p>
            </div>
            {selectedCategory ? (
              <button onClick={() => setSelectedCategory(null)}
                      style={{ display: "inline-flex", alignItems: "center", gap: "0.35rem",
                               padding: "0.35rem 0.75rem", borderRadius: "999px",
                               border: "1px solid #93c5fd", background: "#eff6ff",
                               color: "#1e3a8a", fontWeight: 700, fontSize: "0.78rem",
                               cursor: "pointer" }}>
                <X size={12} /> Clear filter
              </button>
            ) : (
              <Link to="/library/catalogue" style={{ color: "#1e3a8a", fontSize: "0.83rem", fontWeight: 700 }}>
                Browse catalogue →
              </Link>
            )}
          </div>

          {/* Category cards */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "0.75rem", marginBottom: "1.5rem" }}>
            {CATEGORY_ORDER.map((key) => {
              const cat = CATEGORIES[key];
              const stat = categoryStats[key];
              const isActive = selectedCategory === key;
              return (
                <button
                  key={key}
                  onClick={() => toggleCategory(key)}
                  className={"lib-cat-card" + (isActive ? " active" : "")}
                  style={{
                    background: "rgba(255,255,255,0.96)",
                    border: `2px solid ${isActive ? "#1e3a8a" : "#e5e7eb"}`,
                    borderRadius: "12px",
                    padding: "1rem",
                    textAlign: "left",
                    cursor: "pointer",
                    position: "relative",
                    backdropFilter: "blur(2px)",
                    overflow: "hidden",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "0.65rem", marginBottom: "0.55rem" }}>
                    <div style={{
                      width: 44, height: 44, borderRadius: 10,
                      background: cat.colour, color: "#fff",
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: "1.35rem", flexShrink: 0,
                      boxShadow: "0 2px 6px rgba(15,23,42,0.18)",
                    }}>{cat.icon}</div>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontWeight: 800, color: "#111827", fontSize: "0.95rem",
                                    whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                        {cat.label}
                      </div>
                      <div style={{ color: "#64748b", fontSize: "0.75rem" }}>
                        {stat.subjects} subject{stat.subjects === 1 ? "" : "s"}
                      </div>
                    </div>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.78rem" }}>
                    <span style={{ color: "#475569", fontWeight: 700 }}>
                      {stat.books} {stat.books === 1 ? "title" : "titles"}
                    </span>
                    <span style={{
                      padding: "0.15rem 0.5rem", borderRadius: "999px",
                      background: stat.covered > 0 ? "#dcfce7" : "#f1f5f9",
                      color: stat.covered > 0 ? "#166534" : "#64748b",
                      fontWeight: 800, fontSize: "0.68rem",
                    }}>
                      {stat.covered}/{stat.subjects}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Subject grid (filtered) */}
          {subjectsLoading ? (
            <div style={{ padding: "1.5rem", color: "#64748b", display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <Loader2 size={16} className="spin" /> Loading subjects…
            </div>
          ) : filteredSubjects.length === 0 ? (
            <div style={{ padding: "1.5rem", background: "rgba(255,255,255,0.9)", borderRadius: "8px",
                          color: "#64748b", textAlign: "center" }}>
              {selectedCategory
                ? `No subjects yet in ${CATEGORIES[selectedCategory].label}.`
                : "No active subjects in the curriculum."}
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: "0.75rem" }}>
              {filteredSubjects.map((s) => {
                const covered = s.book_count > 0;
                const anyS = s as any;
                const icon = anyS.icon || fallbackIcon(s.code);
                const colour = anyS.colour || fallbackColour(s.code);
                const thumb = anyS.thumbnail_url || "";
                return (
                  <Link
                    key={s.id}
                    to={`/library/subject/${encodeURIComponent(s.code)}`}
                    className="lib-subject-card"
                    style={{
                      display: "block", background: "rgba(255,255,255,0.94)",
                      border: `1px solid ${covered ? "#bbf7d0" : "#e5e7eb"}`,
                      borderRadius: "10px", padding: "1rem", textDecoration: "none",
                      color: "inherit", position: "relative", backdropFilter: "blur(2px)",
                      transition: "transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "flex-start", gap: "0.65rem" }}>
                      <div className="lib-subject-tile"
                           style={{
                             width: 44, height: 44, borderRadius: 10,
                             display: "flex", alignItems: "center", justifyContent: "center",
                             background: thumb ? "#f1f5f9" : colour, color: "#fff",
                             fontSize: "1.35rem", flexShrink: 0, overflow: "hidden",
                             boxShadow: "0 2px 6px rgba(15,23,42,0.15)",
                           }}>
                        {thumb ? (
                          <img src={thumb} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                        ) : (
                          <span>{icon}</span>
                        )}
                      </div>
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                          <span style={{
                            fontSize: "0.7rem", fontWeight: 800, letterSpacing: "0.06em",
                            color: covered ? "#166534" : "#64748b",
                            background: covered ? "#dcfce7" : "#f1f5f9",
                            padding: "0.15rem 0.45rem", borderRadius: "4px",
                          }}>{s.code}</span>
                          <span style={{
                            width: 8, height: 8, borderRadius: "50%",
                            background: covered ? "#22c55e" : "#cbd5e1", marginTop: 4,
                          }} />
                        </div>
                        <div style={{ fontWeight: 700, color: "#111827", marginTop: "0.4rem",
                                      fontSize: "0.9rem", overflow: "hidden", textOverflow: "ellipsis" }}>
                          {s.name}
                        </div>
                        <div style={{ color: "#64748b", fontSize: "0.75rem", marginTop: "0.25rem" }}>
                          {s.book_count} {s.book_count === 1 ? "title" : "titles"}
                          {s.available_copies > 0 ? ` · ${s.available_copies} avail` : ""}
                        </div>
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </section>
      </div>

      <style>{`
        .lib-shelf-bg {
          position: absolute; inset: 0; z-index: 0; pointer-events: none;
          background:
            linear-gradient(180deg,
              transparent 0%, transparent 28%,
              rgba(120,53,15,0.18) 28%, rgba(120,53,15,0.28) 29%,
              transparent 30%, transparent 61%,
              rgba(120,53,15,0.18) 61%, rgba(120,53,15,0.28) 62%,
              transparent 63%, transparent 94%,
              rgba(120,53,15,0.18) 94%, rgba(120,53,15,0.28) 95%,
              transparent 96%),
            repeating-linear-gradient(90deg,
              rgba(30,58,138,0.06)  0px,  rgba(30,58,138,0.06)  10px,
              rgba(14,116,144,0.08) 10px,  rgba(14,116,144,0.08) 22px,
              rgba(124,58,237,0.07) 22px,  rgba(124,58,237,0.07) 34px,
              rgba(180,83,9,0.07)   34px,  rgba(180,83,9,0.07)   48px,
              rgba(21,128,61,0.07)  48px,  rgba(21,128,61,0.07)  62px,
              rgba(190,24,93,0.06)  62px,  rgba(190,24,93,0.06)  74px),
            linear-gradient(180deg, #fbfaf7 0%, #f4f1ea 100%);
          opacity: 0.85;
        }
        .lib-shelf-bg::after {
          content: ""; position: absolute; inset: 0;
          background: linear-gradient(180deg,
            rgba(255,255,255,0.9) 0%,
            rgba(255,255,255,0.55) 30%,
            rgba(255,255,255,0.35) 60%,
            rgba(255,255,255,0.2) 100%);
        }

        @keyframes ttFadeUp {
          from { opacity: 0; transform: translateY(6px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes tilePulse {
          0%, 100% { box-shadow: 0 2px 6px rgba(15,23,42,0.15); }
          50%      { box-shadow: 0 4px 12px rgba(15,23,42,0.28); }
        }
        @keyframes tileWiggle {
          0%, 100% { transform: rotate(0deg) scale(1); }
          40%      { transform: rotate(-6deg) scale(1.08); }
          60%      { transform: rotate(5deg)  scale(1.08); }
        }

        .lib-stat-card { animation: ttFadeUp 260ms ease both; }
        .lib-subject-card { animation: ttFadeUp 340ms ease both; }
        .lib-subject-card .lib-subject-tile {
          animation: tilePulse 3.6s ease-in-out infinite;
          transition: transform 200ms ease;
        }
        .lib-subject-card:hover {
          transform: translateY(-3px);
          box-shadow: 0 10px 22px rgba(15,23,42,0.14);
          border-color: #93c5fd !important;
        }
        .lib-subject-card:hover .lib-subject-tile { animation: tileWiggle 400ms ease; }

        /* Category card motion */
        .lib-cat-card {
          transition: transform 220ms cubic-bezier(0.34, 1.56, 0.64, 1),
                      box-shadow 220ms ease,
                      border-color 220ms ease;
          will-change: transform;
        }
        .lib-cat-card:hover {
          transform: translateY(-4px);
          box-shadow: 0 12px 26px rgba(15,23,42,0.16);
        }
        .lib-cat-card.active {
          box-shadow: 0 0 0 3px rgba(30,58,138,0.18), 0 10px 24px rgba(30,58,138,0.22);
        }

        /* Quick action cards — heavy motion */
        .lib-quicklink {
          position: relative; overflow: hidden;
          transition: transform 260ms cubic-bezier(0.34, 1.56, 0.64, 1),
                      box-shadow 260ms ease,
                      border-color 260ms ease;
          will-change: transform;
        }
        .lib-quicklink::before {
          content: "";
          position: absolute; inset: 0;
          background: linear-gradient(135deg, transparent 0%, rgba(30,58,138,0.10) 100%);
          opacity: 0;
          transition: opacity 260ms ease;
          pointer-events: none;
        }
        .lib-quicklink:hover {
          transform: translateY(-8px) scale(1.03);
          box-shadow: 0 20px 45px rgba(30,58,138,0.28),
                      0 0 0 2px #93c5fd;
          border-color: #93c5fd !important;
        }
        .lib-quicklink:hover::before { opacity: 1; }
        .lib-quicklink:active {
          transform: translateY(-2px) scale(0.98);
          transition-duration: 80ms;
        }
        .ql-icon {
          transition: transform 260ms cubic-bezier(0.34, 1.56, 0.64, 1),
                      background 260ms ease,
                      color 260ms ease,
                      box-shadow 260ms ease;
          display: inline-flex; align-items: center; justify-content: center;
          width: 48px; height: 48px; border-radius: 12px;
          background: #eff6ff;
        }
        .lib-quicklink:hover .ql-icon {
          transform: scale(1.18) rotate(-8deg);
          background: #1e3a8a;
          color: #fff !important;
          box-shadow: 0 8px 18px rgba(30,58,138,0.35);
        }

        @media (prefers-reduced-motion: reduce) {
          .lib-subject-card, .lib-stat-card, .lib-subject-tile,
          .lib-quicklink, .lib-cat-card, .ql-icon {
            animation: none !important;
            transition: none !important;
            transform: none !important;
          }
        }
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}

function QuickLink({ to, icon: Icon, title, text, colour }: {
  to: string; icon: any; title: string; text: string; colour: string;
}) {
  return (
    <Link
      to={to}
      className="lib-quicklink"
      style={{
        display: "block",
        background: "rgba(255,255,255,0.94)",
        border: "1px solid #e5e7eb",
        borderRadius: "12px",
        padding: "1.1rem 1.25rem",
        textDecoration: "none",
        color: "inherit",
        backdropFilter: "blur(2px)",
      }}
    >
      <div className="ql-icon" style={{ color: colour }}>
        <Icon size={22} />
      </div>
      <div style={{ fontWeight: 800, marginTop: "0.7rem", color: "#111827", fontSize: "1rem" }}>
        {title}
      </div>
      <div style={{ color: "#748095", fontSize: "0.85rem", marginTop: "0.25rem" }}>
        {text}
      </div>
    </Link>
  );
}