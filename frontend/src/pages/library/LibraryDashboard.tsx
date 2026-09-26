import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  BookOpen, Copy as CopyIcon, Users, AlertTriangle,
  BookMarked, CheckCircle2, Library, Loader2,
} from "lucide-react";
import * as lib from "../../services/library";
import LibraryTabs from "../../components/library/LibraryTabs";

export default function LibraryDashboard() {
  const [stats, setStats] = useState<lib.LibraryDashboard | null>(null);
  const [subjects, setSubjects] = useState<lib.SubjectSummaryRow[]>([]);
  const [subjectsLoading, setSubjectsLoading] = useState(true);
  const [error, setError] = useState("");

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
    { label: "Available", value: stats.available_copies, icon: CheckCircle2, colour:"#059669" },
    { label: "Issued", value: stats.issued_copies, icon: BookMarked, colour: "#7c3aed" },
    { label: "Active Loans", value: stats.active_loans, icon: BookMarked, colour: "#0284c7" },
    { label: "Overdue", value: stats.overdue_loans, icon: AlertTriangle, colour: "#dc2626" },
    { label: "Members", value: stats.active_members, icon: Users, colour: "#65a30d" },
  ] : [];

  const coveredSubjects = subjects.filter((s) => s.book_count > 0).length;
  const totalSubjects = subjects.length;

  // Icon lookup – backend doesn't yet expose icon/colour on subject-summary
  // but we added them to the Subject model, so we read them here with a
  // safe fallback: an emoji map + colour map used only when the API lacks it.
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

  return (
    <div className="lib-dash" style={{ padding: "1.5rem", position: "relative", overflow: "hidden" }}>
      {/* --- Shelf background (CSS only) --- */}
      <div className="lib-shelf-bg" aria-hidden="true" />

      <div style={{ position: "relative", zIndex: 2 }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "1rem" }}>
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

        <LibraryTabs />

        {error ? <div className="tt-error">{error}</div> : null}

        <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "1rem" }}>
          {cards.map((c) => {
            const Icon = c.icon;
            return (
              <div key={c.label} className="lib-stat-card"
                   style={{ background: "rgba(255,255,255,0.94)", border: "1px solid #e5e7eb",
                            borderRadius: "10px", padding: "1.25rem",
                            backdropFilter: "blur(2px)" }}>
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

        <section style={{ marginTop: "2rem" }}>
          <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: "0.9rem" }}>
            <div>
              <h2 style={{ margin: 0, fontSize: "1.15rem", color: "#111827",
                           display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Library size={18} style={{ color: "#1e3a8a" }} />
                Learning Categories
              </h2>
              <p style={{ color: "#748095", fontSize: "0.83rem", marginTop: "0.2rem" }}>
                Curriculum subjects supported by the library · {coveredSubjects} of {totalSubjects} covered
              </p>
            </div>
            <Link to="/library/catalogue" style={{ color: "#1e3a8a", fontSize: "0.83rem", fontWeight: 700 }}>
              Browse catalogue →
            </Link>
          </div>

          {subjectsLoading ? (
            <div style={{ padding: "1.5rem", color: "#64748b", display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <Loader2 size={16} className="spin" /> Loading subjects…
            </div>
          ) : subjects.length === 0 ? (
            <div style={{ padding: "1.5rem", background: "rgba(255,255,255,0.9)", borderRadius: "8px",
                          color: "#64748b", textAlign: "center" }}>
              No active subjects in the curriculum.
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: "0.75rem" }}>
              {subjects.map((s) => {
                const covered = s.book_count > 0;
                const anyS = s as any;
                const icon = anyS.icon || fallbackIcon(s.code);
                const colour = anyS.colour || fallbackColour(s.code);
                const thumb = anyS.thumbnail_url || "";
                return (
                  <Link
                    key={s.id}
                    to={`/library/catalogue?subject=${encodeURIComponent(s.code)}`}
                    className="lib-subject-card"
                    style={{
                      display: "block",
                      background: "rgba(255,255,255,0.94)",
                      border: `1px solid ${covered ? "#bbf7d0" : "#e5e7eb"}`,
                      borderRadius: "10px",
                      padding: "1rem",
                      textDecoration: "none",
                      color: "inherit",
                      position: "relative",
                      backdropFilter: "blur(2px)",
                      transition: "transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "flex-start", gap: "0.65rem" }}>
                      {/* Tile / thumbnail */}
                      <div className="lib-subject-tile"
                           style={{
                             width: 44, height: 44, borderRadius: 10,
                             display: "flex", alignItems: "center", justifyContent: "center",
                             background: thumb ? "#f1f5f9" : colour,
                             color: "#fff", fontSize: "1.35rem", flexShrink: 0,
                             overflow: "hidden",
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
                          }}>
                            {s.code}
                          </span>
                          <span style={{
                            width: 8, height: 8, borderRadius: "50%",
                            background: covered ? "#22c55e" : "#cbd5e1",
                            marginTop: 4,
                          }} />
                        </div>
                        <div style={{ fontWeight: 700, color: "#111827", marginTop: "0.4rem", fontSize: "0.9rem",
                                      overflow: "hidden", textOverflow: "ellipsis" }}>
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
        /* ============ Library shelf background ============ */
        .lib-shelf-bg {
          position: absolute;
          inset: 0;
          z-index: 0;
          pointer-events: none;
          background:
            /* three shelf rows */
            linear-gradient(180deg,
              transparent 0%,
              transparent 28%,
              rgba(120,53,15,0.18) 28%,
              rgba(120,53,15,0.28) 29%,
              transparent 30%,
              transparent 61%,
              rgba(120,53,15,0.18) 61%,
              rgba(120,53,15,0.28) 62%,
              transparent 63%,
              transparent 94%,
              rgba(120,53,15,0.18) 94%,
              rgba(120,53,15,0.28) 95%,
              transparent 96%),
            /* book spines: repeating stripes */
            repeating-linear-gradient(90deg,
              rgba(30,58,138,0.06)  0px,  rgba(30,58,138,0.06)  10px,
              rgba(14,116,144,0.08) 10px,  rgba(14,116,144,0.08) 22px,
              rgba(124,58,237,0.07) 22px,  rgba(124,58,237,0.07) 34px,
              rgba(180,83,9,0.07)   34px,  rgba(180,83,9,0.07)   48px,
              rgba(21,128,61,0.07)  48px,  rgba(21,128,61,0.07)  62px,
              rgba(190,24,93,0.06)  62px,  rgba(190,24,93,0.06)  74px),
            linear-gradient(180deg, #fbfaf7 0%, #f4f1ea 100%);
          background-size: 100% 100%, 100% 100%, 100% 100%;
          opacity: 0.85;
        }
        /* ensure the shelf fades toward the top so text stays readable */
        .lib-shelf-bg::after {
          content: "";
          position: absolute;
          inset: 0;
          background: linear-gradient(180deg,
            rgba(255,255,255,0.9) 0%,
            rgba(255,255,255,0.55) 30%,
            rgba(255,255,255,0.35) 60%,
            rgba(255,255,255,0.2) 100%);
        }

        /* ============ Motion effects ============ */
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
        .lib-stat-card {
          animation: ttFadeUp 260ms ease both;
        }
        .lib-subject-card {
          animation: ttFadeUp 340ms ease both;
        }
        .lib-subject-card .lib-subject-tile {
          animation: tilePulse 3.6s ease-in-out infinite;
          transition: transform 200ms ease;
        }
        .lib-subject-card:hover {
          transform: translateY(-3px);
          box-shadow: 0 10px 22px rgba(15,23,42,0.14);
          border-color: #93c5fd !important;
        }
        .lib-subject-card:hover .lib-subject-tile {
          animation: tileWiggle 400ms ease;
        }
        @media (prefers-reduced-motion: reduce) {
          .lib-subject-card, .lib-stat-card, .lib-subject-tile { animation: none !important; transition: none !important; }
        }
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
