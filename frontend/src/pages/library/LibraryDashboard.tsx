import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  BookOpen, Copy as CopyIcon, Users, AlertTriangle,
  BookMarked, CheckCircle2, Library, Loader2,
  Layers, LayoutGrid, GraduationCap, ChevronLeft,
} from "lucide-react";
import * as lib from "../../services/library";

type CategoryKey =
  | "math" | "sciences" | "languages" | "humanities"
  | "religious" | "creative" | "technology" | "applied";

const CATEGORIES: Record<CategoryKey, { label: string; icon: string; colour: string; codes: string[] }> = {
  math:       { label: "Mathematics",           icon: "🔢", colour: "#1e40af", codes: ["MAT", "EMCM"] },
  sciences:   { label: "Sciences",              icon: "🔬", colour: "#0e7490", codes: ["BIO","BIOPRAC","CHEM","CHEMPRAC","PHY","PHYPRAC","INTSCI"] },
  languages:  { label: "Languages",             icon: "📚", colour: "#991b1b", codes: ["ENG","KIS","LIT"] },
  humanities: { label: "Humanities",            icon: "🌍", colour: "#166534", codes: ["GEO","HIS","SST"] },
  religious:  { label: "Religious Studies",     icon: "🙏", colour: "#a16207", codes: ["CRE","IRE","PPI"] },
  creative:   { label: "Creative Arts",         icon: "🎨", colour: "#7e22ce", codes: ["CAS","MUSD","ART"] },
  technology: { label: "Business & Technology", icon: "💻", colour: "#3730a3", codes: ["BUS","COMP","CS","ICT"] },
  applied:    { label: "Applied & Vocational",  icon: "🌾", colour: "#4d7c0f", codes: ["AGR","PE"] },
};

const CATEGORY_ORDER: CategoryKey[] = [
  "math","sciences","languages","humanities","religious","creative","technology","applied",
];

/* Per-subject solid colour — each one distinct, dark enough for white text */
const SUBJECT_COLOURS: Record<string, string> = {
  // Mathematics
  MAT: "#1e3a8a", EMCM: "#1e40af",
  // Sciences
  BIO: "#15803d", BIOPRAC: "#166534",
  CHEM: "#0e7490", CHEMPRAC: "#155e75",
  PHY: "#0369a1", PHYPRAC: "#075985",
  INTSCI: "#0c4a6e",
  // Languages
  ENG: "#1d4ed8", KIS: "#b91c1c", LIT: "#991b1b",
  // Humanities
  GEO: "#065f46", HIS: "#7c2d12", SST: "#0f766e",
  // Religious
  CRE: "#92400e", IRE: "#a16207", PPI: "#854d0e",
  // Creative
  CAS: "#9333ea", MUSD: "#7e22ce", ART: "#a21caf",
  // Business & Technology
  BUS: "#4338ca", COMP: "#3730a3", CS: "#1e40af", ICT: "#0891b2",
  // Applied
  AGR: "#4d7c0f", PE: "#047857",
};

type ViewMode = "categories" | "subjects" | "classes";

const VIEW_TABS: { key: ViewMode; label: string; Icon: any }[] = [
  { key: "categories", label: "Learning Categories", Icon: Layers },
  { key: "subjects",   label: "All Subjects",        Icon: LayoutGrid },
  { key: "classes",    label: "Classes",             Icon: GraduationCap },
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
  const [viewMode, setViewMode] = useState<ViewMode>("categories");
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

  useEffect(() => {
    setSelectedCategory(null);
  }, [viewMode]);

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

  const showCategoriesOnly    = viewMode === "categories" && !selectedCategory;
  const showCategoryDrilldown = viewMode === "categories" && !!selectedCategory;
  const showAllSubjects       = viewMode === "subjects";
  const showClasses           = viewMode === "classes";

  return (
    <div
      className="lib-dash"
      style={{
        padding: "1.5rem",
        position: "relative",
        overflow: "hidden",
        background:
          "radial-gradient(1400px 600px at 85% -5%, rgba(122,78,42,0.07), transparent 60%)," +
          "radial-gradient(900px 500px at -5% 20%, rgba(30,64,175,0.05), transparent 55%)," +
          "linear-gradient(180deg, #f5ecd9 0%, #ecdfc8 100%)",
      }}
    >
      <div style={{ position: "relative", zIndex: 2 }}>
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

        <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "1rem" }}>
          {cards.map((c) => {
            const Icon = c.icon;
            return (
              <div key={c.label} className="lib-stat-card"
                   style={{ background: "rgba(255,255,255,0.96)", border: "1px solid #e5e7eb",
                            borderRadius: "10px", padding: "1.25rem" }}>
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

        <section style={{
          marginTop: "1.75rem",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
          gap: "1.25rem",
        }}>
          <QuickLink to="/library/catalogue" Icon={BookOpen}      title="Catalogue" text="Browse and search the book collection."    colour="#1e40af" bg="#eef2ff" border="#c7d2fe" />
          <QuickLink to="/library/members"   Icon={Users}         title="Members"   text="Students, teachers, and staff who borrow."  colour="#0e7490" bg="#ecfeff" border="#a5f3fc" />
          <QuickLink to="/library/loans"     Icon={BookMarked}    title="Loans"     text="Active, overdue, and returned loans."        colour="#7e22ce" bg="#f5f3ff" border="#ddd6fe" />
          <QuickLink to="/library/reports"   Icon={AlertTriangle} title="Reports"   text="Circulation, inventory, top borrowers."     colour="#991b1b" bg="#fef2f2" border="#fecaca" />
        </section>

        <section style={{ marginTop: "2.5rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center",
                        flexWrap: "wrap", gap: "1rem", marginBottom: "1.25rem" }}>
            <div>
              <h2 style={{ margin: 0, fontSize: "1.35rem", color: "#111827",
                           display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Library size={20} style={{ color: "#1e3a8a" }} />
                Learning Library
              </h2>
              <p style={{ color: "#748095", fontSize: "0.85rem", marginTop: "0.25rem" }}>
                {viewMode === "categories" && !selectedCategory && `${CATEGORY_ORDER.length} categories covering ${totalSubjects} subjects · ${coveredSubjects} covered`}
                {viewMode === "categories" && selectedCategory && `${CATEGORIES[selectedCategory].label} · ${filteredSubjects.length} subject${filteredSubjects.length === 1 ? "" : "s"}`}
                {viewMode === "subjects" && `All ${totalSubjects} subjects · ${coveredSubjects} covered`}
                {viewMode === "classes" && "Class-section views"}
              </p>
            </div>

            <div className="lib-view-tabs">
              {VIEW_TABS.map(({ key, label, Icon }) => (
                <button
                  key={key}
                  onClick={() => setViewMode(key)}
                  className={"lib-view-tab" + (viewMode === key ? " active" : "")}
                >
                  <Icon size={16} /> {label}
                </button>
              ))}
            </div>
          </div>

          {subjectsLoading ? (
            <div style={{ padding: "2rem", color: "#64748b", display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <Loader2 size={16} className="spin" /> Loading subjects…
            </div>
          ) : (
            <>
              {showCategoriesOnly && (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "1.25rem" }}>
                  {CATEGORY_ORDER.map((key) => {
                    const cat = CATEGORIES[key];
                    const stat = categoryStats[key];
                    return (
                      <button
                        key={key}
                        onClick={() => setSelectedCategory(key)}
                        className="lib-cat-card"
                        style={{
                          background: cat.colour,
                          border: `2px solid ${cat.colour}`,
                          borderRadius: "14px",
                          padding: "1.5rem 1.6rem",
                          textAlign: "left",
                          cursor: "pointer",
                          position: "relative",
                          overflow: "hidden",
                          boxShadow: "0 6px 16px rgba(15,23,42,0.14), inset 0 1px 0 rgba(255,255,255,0.12)",
                        }}
                      >
                        <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginBottom: "0.9rem" }}>
                          <div style={{
                            width: 60, height: 60, borderRadius: 14,
                            background: "rgba(255,255,255,0.18)", color: "#fff",
                            display: "flex", alignItems: "center", justifyContent: "center",
                            fontSize: "1.75rem", flexShrink: 0,
                            border: "1px solid rgba(255,255,255,0.28)",
                          }}>{cat.icon}</div>
                          <div style={{ minWidth: 0 }}>
                            <div style={{ fontWeight: 800, color: "#fff", fontSize: "1.15rem",
                                          whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                              {cat.label}
                            </div>
                            <div style={{ color: "rgba(255,255,255,0.78)", fontSize: "0.85rem", marginTop: "0.15rem" }}>
                              {stat.subjects} subject{stat.subjects === 1 ? "" : "s"}
                            </div>
                          </div>
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.85rem" }}>
                          <span style={{ color: "rgba(255,255,255,0.92)", fontWeight: 700 }}>
                            {stat.books} {stat.books === 1 ? "title" : "titles"}
                          </span>
                          <span style={{
                            padding: "0.25rem 0.6rem", borderRadius: "999px",
                            background: "rgba(255,255,255,0.2)", color: "#fff",
                            border: "1px solid rgba(255,255,255,0.3)",
                            fontWeight: 800, fontSize: "0.75rem",
                          }}>
                            {stat.covered}/{stat.subjects} covered
                          </span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}

              {showCategoryDrilldown && selectedCategory && (
                <>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1rem" }}>
                    <button
                      onClick={() => setSelectedCategory(null)}
                      className="lib-back-btn"
                    >
                      <ChevronLeft size={16} /> All categories
                    </button>
                    <span style={{
                      padding: "0.4rem 0.9rem", borderRadius: "999px",
                      background: CATEGORIES[selectedCategory].colour, color: "#fff",
                      fontWeight: 800, fontSize: "0.85rem",
                      boxShadow: "0 3px 10px rgba(15,23,42,0.2)",
                    }}>
                      {CATEGORIES[selectedCategory].icon} {CATEGORIES[selectedCategory].label}
                    </span>
                  </div>
                  {filteredSubjects.length === 0 ? (
                    <div style={{ padding: "1.5rem", background: "rgba(255,255,255,0.9)", borderRadius: "8px",
                                  color: "#64748b", textAlign: "center" }}>
                      No subjects yet in {CATEGORIES[selectedCategory].label}.
                    </div>
                  ) : (
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1rem" }}>
                      {filteredSubjects.map((s, i) => <SubjectCard key={s.id} subject={s} index={i} />)}
                    </div>
                  )}
                </>
              )}

              {showAllSubjects && (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1rem" }}>
                  {filteredSubjects.map((s, i) => <SubjectCard key={s.id} subject={s} index={i} />)}
                </div>
              )}

              {showClasses && (
                <div style={{
                  padding: "3rem 2rem",
                  background: "linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%)",
                  border: "2px dashed #c4b5fd",
                  borderRadius: "16px",
                  textAlign: "center",
                  boxShadow: "0 6px 16px rgba(15,23,42,0.06)",
                }}>
                  <div style={{
                    width: 72, height: 72, borderRadius: "50%",
                    background: "#7e22ce", color: "#fff",
                    display: "inline-flex", alignItems: "center", justifyContent: "center",
                    marginBottom: "1rem",
                    boxShadow: "0 8px 20px rgba(126,34,206,0.35)",
                  }}>
                    <GraduationCap size={36} />
                  </div>
                  <h3 style={{ margin: 0, color: "#0f172a", fontSize: "1.25rem", fontWeight: 800 }}>
                    Class-section view coming soon
                  </h3>
                  <p style={{ color: "#5b21b6", fontSize: "0.95rem", marginTop: "0.5rem", maxWidth: 480, margin: "0.5rem auto 0", lineHeight: 1.5 }}>
                    This view will group the library collection by class (Form 4E, 10W, G11E, etc.) so you can see
                    which books are assigned to each section.
                  </p>
                </div>
              )}
            </>
          )}
        </section>
      </div>

      <style>{`
        @keyframes ttFadeUp {
          from { opacity: 0; transform: translateY(6px); }
          to   { opacity: 1; transform: translateY(0); }
        }

        .lib-stat-card { animation: ttFadeUp 260ms ease both; }

        /* Subject cards — dark solid, heavy motion */
        .lib-subject-card {
          transition: transform 240ms cubic-bezier(0.34, 1.56, 0.64, 1),
                      box-shadow 240ms ease,
                      filter 240ms ease;
          will-change: transform, filter;
          animation: ttFadeUp 340ms ease both;
        }
        .lib-subject-card:hover {
          transform: translateY(-6px) scale(1.02);
          box-shadow: 0 20px 40px rgba(15,23,42,0.28);
          filter: brightness(1.12) saturate(1.08);
        }
        .lib-subject-card:active {
          transform: translateY(-1px) scale(0.99);
          transition-duration: 80ms;
        }
        .lib-subject-icon {
          transition: transform 260ms cubic-bezier(0.34, 1.56, 0.64, 1);
        }
        .lib-subject-card:hover .lib-subject-icon {
          transform: scale(1.15) rotate(-6deg);
        }

        /* Category cards — dark solid, brighter hover */
        .lib-cat-card {
          transition: transform 240ms cubic-bezier(0.34, 1.56, 0.64, 1),
                      box-shadow 240ms ease,
                      filter 240ms ease;
          will-change: transform, filter;
        }
        .lib-cat-card:hover {
          transform: translateY(-6px) scale(1.02);
          box-shadow: 0 20px 40px rgba(15,23,42,0.28);
          filter: brightness(1.12) saturate(1.08);
        }
        .lib-cat-card:active {
          transform: translateY(-1px) scale(0.99);
          transition-duration: 80ms;
        }

        /* QuickLink cards — soft tints */
        .lib-quicklink {
          position: relative; overflow: hidden;
          transition: transform 260ms cubic-bezier(0.34, 1.56, 0.64, 1),
                      box-shadow 260ms ease,
                      filter 260ms ease;
          will-change: transform;
        }
        .lib-quicklink:hover {
          transform: translateY(-8px) scale(1.03);
          box-shadow: 0 20px 45px rgba(15,23,42,0.18);
          filter: brightness(1.02);
        }
        .lib-quicklink:active {
          transform: translateY(-2px) scale(0.98);
          transition-duration: 80ms;
        }
        .ql-icon {
          transition: transform 260ms cubic-bezier(0.34, 1.56, 0.64, 1),
                      box-shadow 260ms ease;
          display: inline-flex; align-items: center; justify-content: center;
          width: 56px; height: 56px; border-radius: 14px;
          background: #fff;
          box-shadow: 0 2px 8px rgba(15,23,42,0.10);
        }
        .lib-quicklink:hover .ql-icon {
          transform: scale(1.15) rotate(-6deg);
          box-shadow: 0 10px 22px rgba(15,23,42,0.22);
        }

        .lib-view-tabs {
          display: inline-flex; gap: 0.35rem;
          background: rgba(255,255,255,0.9);
          padding: 0.35rem;
          border-radius: 999px;
          border: 1px solid #e5e7eb;
        }
        .lib-view-tab {
          display: inline-flex; align-items: center; gap: 0.4rem;
          padding: 0.55rem 1rem;
          border-radius: 999px;
          border: none;
          background: transparent;
          color: #475569;
          font-weight: 700;
          font-size: 0.85rem;
          cursor: pointer;
          transition: background 200ms ease, color 200ms ease;
        }
        .lib-view-tab:hover { background: #eff6ff; color: #1e3a8a; }
        .lib-view-tab.active {
          background: #1e3a8a;
          color: #fff;
          box-shadow: 0 4px 12px rgba(30,58,138,0.3);
        }

        .lib-back-btn {
          display: inline-flex; align-items: center; gap: 0.35rem;
          padding: 0.5rem 0.9rem;
          border-radius: 8px;
          border: 1px solid #cbd5e1;
          background: rgba(255,255,255,0.9);
          color: #334155;
          font-weight: 700;
          font-size: 0.85rem;
          cursor: pointer;
          transition: transform 200ms ease, border-color 200ms ease, background 200ms ease;
        }
        .lib-back-btn:hover {
          transform: translateX(-3px);
          border-color: #93c5fd;
          background: #eff6ff;
          color: #1e3a8a;
        }

        @media (prefers-reduced-motion: reduce) {
          .lib-subject-card, .lib-stat-card, .lib-subject-icon,
          .lib-quicklink, .lib-cat-card, .ql-icon, .lib-back-btn, .lib-view-tab {
            animation: none !important;
            transition: none !important;
            transform: none !important;
            filter: none !important;
          }
        }
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}

function QuickLink({ to, Icon, title, text, colour, bg, border }: {
  to: string; Icon: any; title: string; text: string; colour: string; bg: string; border: string;
}) {
  return (
    <Link
      to={to}
      className="lib-quicklink"
      style={{
        display: "block",
        background: bg,
        border: `2px solid ${border}`,
        borderRadius: "14px",
        padding: "1.5rem 1.6rem",
        textDecoration: "none",
        color: "inherit",
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div className="ql-icon" style={{ color: colour }}>
        <Icon size={26} />
      </div>
      <div style={{ fontWeight: 800, marginTop: "0.9rem", color: "#0f172a", fontSize: "1.15rem" }}>
        {title}
      </div>
      <div style={{ color: "#5b6b82", fontSize: "0.9rem", marginTop: "0.35rem", lineHeight: 1.4 }}>
        {text}
      </div>
    </Link>
  );
}

function SubjectCard({ subject: s, index }: { subject: lib.SubjectSummaryRow; index: number }) {
  const covered = s.book_count > 0;
  const anyS = s as any;
  const icon = anyS.icon || fallbackIcon(s.code);
  const colour = SUBJECT_COLOURS[(s.code || "").toUpperCase()] || anyS.colour || fallbackColour(s.code);
  const thumb = anyS.thumbnail_url || "";
  return (
    <Link
      to={`/library/subject/${encodeURIComponent(s.code)}`}
      className="lib-subject-card"
      style={{
        display: "block",
        background: colour,
        border: `2px solid ${colour}`,
        borderRadius: "14px",
        padding: "1.4rem 1.5rem",
        textDecoration: "none",
        color: "#fff",
        position: "relative",
        overflow: "hidden",
        boxShadow: "0 6px 16px rgba(15,23,42,0.14), inset 0 1px 0 rgba(255,255,255,0.12)",
        animationDelay: `${Math.min(index * 40, 400)}ms`,
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "0.85rem" }}>
        <div className="lib-subject-icon" style={{
          width: 56, height: 56, borderRadius: 14,
          background: "rgba(255,255,255,0.2)",
          border: "1px solid rgba(255,255,255,0.3)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: "1.65rem", overflow: "hidden",
        }}>
          {thumb ? (
            <img src={thumb} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          ) : (
            <span>{icon}</span>
          )}
        </div>
        <span style={{
          width: 10, height: 10, borderRadius: "50%",
          background: covered ? "#4ade80" : "rgba(255,255,255,0.4)",
          boxShadow: covered ? "0 0 8px rgba(74,222,128,0.7)" : "none",
          marginTop: 6,
          flexShrink: 0,
        }} />
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", marginBottom: "0.45rem" }}>
        <span style={{
          fontSize: "0.68rem", fontWeight: 800, letterSpacing: "0.08em",
          color: "#fff",
          background: "rgba(255,255,255,0.2)",
          border: "1px solid rgba(255,255,255,0.3)",
          padding: "0.15rem 0.5rem", borderRadius: "4px",
        }}>{s.code}</span>
        {covered && <CheckCircle2 size={14} style={{ color: "#4ade80", flexShrink: 0 }} />}
      </div>
      <div style={{
        fontWeight: 800, color: "#fff", fontSize: "1.05rem",
        lineHeight: 1.25, marginBottom: "0.4rem",
        minHeight: "2.6rem",
        overflow: "hidden",
      }}>
        {s.name}
      </div>
      <div style={{ color: "rgba(255,255,255,0.82)", fontSize: "0.82rem", fontWeight: 600 }}>
        {s.book_count} {s.book_count === 1 ? "title" : "titles"}
        {s.available_copies > 0 ? ` · ${s.available_copies} available` : ""}
      </div>
    </Link>
  );
}