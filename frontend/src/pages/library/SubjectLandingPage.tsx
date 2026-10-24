import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  BookOpen, FileText, GraduationCap, Layers, ArrowLeft,
  Scroll, FlaskConical, Briefcase,
} from "lucide-react";
import * as lib from "../../services/library";

const CLASS_GROUPS = [
  { label: "Junior School", items: [
    { code: "G7", label: "Grade 7" },
    { code: "G8", label: "Grade 8" },
    { code: "G9", label: "Grade 9" },
  ]},
  { label: "Senior School", items: [
    { code: "G10", label: "Grade 10" },
    { code: "G11", label: "Grade 11" },
    { code: "G12", label: "Grade 12" },
  ]},
  { label: "Form 3 / 4", items: [
    { code: "F3", label: "Form 3" },
    { code: "F4", label: "Form 4" },
  ]},
];

const RESOURCE_TYPES = [
  { id: "books",    label: "Textbooks",         icon: BookOpen,     to: "/library/catalogue" },
  { id: "resources", label: "Digital Resources", icon: FileText,     to: "/library/resources" },
  { id: "papers",   label: "Past Papers",        icon: Scroll,       to: "/library/resources?category=PAST_PAPER" },
  { id: "case",     label: "Case Studies",       icon: FlaskConical, to: "/library/resources?category=RESEARCH" },
  { id: "syllabus", label: "Syllabus",           icon: Layers,       to: "/library/resources?category=SYLLABUS" },
  { id: "careers",  label: "Careers",            icon: Briefcase,    to: "/library/resources?category=OTHER" },
];

// Class colour palette — each class gets its own distinct dark solid tone
const CLASS_COLOURS: Record<string, string> = {
  G7:  "#1e40af",  // blue
  G8:  "#0e7490",  // teal
  G9:  "#166534",  // green
  G10: "#a16207",  // amber
  G11: "#7e22ce",  // purple
  G12: "#991b1b",  // red
  F3:  "#3730a3",  // indigo
  F4:  "#1e3a8a",  // navy
};

// Group pill colours
const GROUP_COLOURS: Record<string, string> = {
  "Junior School": "#0e7490",
  "Senior School": "#7e22ce",
  "Form 3 / 4":    "#991b1b",
};

// Subject colour map (same as dashboard)
const SUBJECT_COLOURS: Record<string, string> = {
  MAT: "#1e3a8a", EMCM: "#1e40af",
  BIO: "#15803d", BIOPRAC: "#166534",
  CHEM: "#0e7490", CHEMPRAC: "#155e75",
  PHY: "#0369a1", PHYPRAC: "#075985",
  INTSCI: "#0c4a6e",
  ENG: "#1d4ed8", KIS: "#b91c1c", LIT: "#991b1b",
  GEO: "#065f46", HIS: "#7c2d12", SST: "#0f766e",
  CRE: "#92400e", IRE: "#a16207", PPI: "#854d0e",
  CAS: "#9333ea", MUSD: "#7e22ce", ART: "#a21caf",
  BUS: "#4338ca", COMP: "#3730a3", CS: "#1e40af", ICT: "#0891b2",
  AGR: "#4d7c0f", PE: "#047857",
};

const fallbackIcon = (code: string): string => {
  const map: Record<string, string> = {
    AGR:"🌾",BIO:"🧬",BIOPRAC:"🔬",BUS:"💼",CAS:"🎭",CHEM:"🧪",CHEMPRAC:"🧫",
    COMP:"💻",CS:"🖥️",CRE:"✝️",EMCM:"📐",ENG:"📖",GEO:"🌍",HIS:"🏛️",ICT:"🖥️",
    INTSCI:"🔬",IRE:"☪️",KIS:"📚",LIT:"📜",MAT:"🧮",MUSD:"🎼",PE:"🏃",PHY:"⚛️",
    PHYPRAC:"🔭",PPI:"🙏",SST:"🌐",ART:"🎨",
  };
  return map[code.toUpperCase()] || "📕";
};

export default function SubjectLandingPage() {
  const { code = "" } = useParams();
  const [subject, setSubject] = useState<lib.Subject | null>(null);

  useEffect(() => {
    lib.getSubjects()
      .then((rows) => setSubject(rows.find((s) => s.code.toUpperCase() === code.toUpperCase()) || null))
      .catch(() => setSubject(null));
  }, [code]);

  function buildLink(baseTo: string, classCode: string): string {
    const sep = baseTo.includes("?") ? "&" : "?";
    return `${baseTo}${sep}subject=${encodeURIComponent(code)}&class=${encodeURIComponent(classCode)}`;
  }

  const subjectColour = SUBJECT_COLOURS[code.toUpperCase()] || subject?.colour || "#1e3a8a";
  const subjectIcon = subject?.icon || fallbackIcon(code);

  return (
    <div
      className="lib-subject-page"
      style={{
        padding: "1.5rem",
        minHeight: "100vh",
        background:
          "radial-gradient(1400px 600px at 85% -5%, rgba(122,78,42,0.07), transparent 60%)," +
          "radial-gradient(900px 500px at -5% 20%, rgba(30,64,175,0.05), transparent 55%)," +
          "linear-gradient(180deg, #f5ecd9 0%, #ecdfc8 100%)",
      }}
    >
      <Link to="/library" className="lib-back-link">
        <ArrowLeft size={15} /> Back to dashboard
      </Link>

      {/* Subject header */}
      <div className="lib-subject-header" style={{ borderLeftColor: subjectColour }}>
        <div className="lib-subject-header-tile" style={{ background: subjectColour }}>
          {subjectIcon}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            fontSize: "0.72rem",
            letterSpacing: "0.1em",
            color: subjectColour,
            fontWeight: 800,
            textTransform: "uppercase",
          }}>
            {code.toUpperCase()}
          </div>
          <h1 style={{ margin: "0.2rem 0 0", fontSize: "1.75rem", color: "#111827", fontWeight: 800 }}>
            {subject?.name || code}
          </h1>
          <p style={{ color: "#64748b", margin: "0.35rem 0 0", fontSize: "0.95rem" }}>
            Choose a class level and resource type to explore.
          </p>
        </div>
      </div>

      {/* Class groups */}
      {CLASS_GROUPS.map((group, gi) => {
        const groupColour = GROUP_COLOURS[group.label] || "#1e3a8a";
        return (
          <section key={group.label} style={{ marginBottom: "2.25rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "1rem" }}>
              <span className="lib-group-pill" style={{ background: groupColour }}>
                <GraduationCap size={15} /> {group.label}
              </span>
              <span style={{ color: "#748095", fontSize: "0.82rem", fontWeight: 600 }}>
                {group.items.length} class{group.items.length === 1 ? "" : "es"}
              </span>
            </div>

            <div style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
              gap: "1.25rem",
            }}>
              {group.items.map((cl, i) => {
                const classColour = CLASS_COLOURS[cl.code] || "#1e3a8a";
                const delay = `${Math.min((gi * 3 + i) * 50, 500)}ms`;
                return (
                  <div
                    key={cl.code}
                    className="lib-class-card"
                    style={{
                      background: classColour,
                      border: `2px solid ${classColour}`,
                      animationDelay: delay,
                    }}
                  >
                    <div style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "flex-start",
                      marginBottom: "1rem",
                    }}>
                      <div>
                        <div style={{
                          fontSize: "1.35rem",
                          fontWeight: 800,
                          color: "#fff",
                          letterSpacing: "-0.01em",
                        }}>
                          {cl.label}
                        </div>
                        <div style={{
                          fontSize: "0.7rem",
                          fontWeight: 800,
                          letterSpacing: "0.1em",
                          color: "rgba(255,255,255,0.7)",
                          marginTop: "0.15rem",
                        }}>
                          {cl.code}
                        </div>
                      </div>
                      <div className="lib-class-icon" style={{
                        width: 44,
                        height: 44,
                        borderRadius: 12,
                        background: "rgba(255,255,255,0.2)",
                        border: "1px solid rgba(255,255,255,0.3)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}>
                        <GraduationCap size={22} style={{ color: "#fff" }} />
                      </div>
                    </div>

                    <div style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))",
                      gap: "0.45rem",
                    }}>
                      {RESOURCE_TYPES.map((rt) => {
                        const Icon = rt.icon;
                        return (
                          <Link key={rt.id} to={buildLink(rt.to, cl.code)} className="lib-rt-chip">
                            <Icon size={13} style={{ flexShrink: 0 }} />
                            <span style={{
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              whiteSpace: "nowrap",
                            }}>
                              {rt.label}
                            </span>
                          </Link>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        );
      })}

      <style>{`
        @keyframes ttFadeUp {
          from { opacity: 0; transform: translateY(8px); }
          to   { opacity: 1; transform: translateY(0); }
        }

        .lib-back-link {
          display: inline-flex;
          align-items: center;
          gap: 0.35rem;
          padding: 0.5rem 0.9rem;
          border-radius: 8px;
          background: rgba(255,255,255,0.9);
          border: 1px solid #cbd5e1;
          color: #1e3a8a;
          margin-bottom: 1.25rem;
          font-size: 0.85rem;
          font-weight: 700;
          text-decoration: none;
          transition: transform 200ms ease, border-color 200ms ease, background 200ms ease;
        }
        .lib-back-link:hover {
          transform: translateX(-3px);
          border-color: #93c5fd;
          background: #eff6ff;
        }

        .lib-subject-header {
          display: flex;
          align-items: center;
          gap: 1rem;
          margin-bottom: 2rem;
          padding: 1.5rem;
          background: rgba(255,255,255,0.94);
          border-radius: 16px;
          border-left: 6px solid #1e3a8a;
          box-shadow: 0 6px 18px rgba(15,23,42,0.08);
        }
        .lib-subject-header-tile {
          width: 72px;
          height: 72px;
          border-radius: 16px;
          color: #fff;
          font-size: 2.1rem;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 6px 16px rgba(15,23,42,0.25);
          flex-shrink: 0;
        }

        .lib-group-pill {
          display: inline-flex;
          align-items: center;
          gap: 0.4rem;
          padding: 0.45rem 0.9rem;
          border-radius: 999px;
          color: #fff;
          font-weight: 800;
          font-size: 0.82rem;
          letter-spacing: 0.03em;
          box-shadow: 0 3px 10px rgba(15,23,42,0.18);
        }

        .lib-class-card {
          border-radius: 16px;
          padding: 1.4rem 1.5rem;
          color: #fff;
          position: relative;
          overflow: hidden;
          box-shadow: 0 6px 16px rgba(15,23,42,0.14), inset 0 1px 0 rgba(255,255,255,0.12);
          animation: ttFadeUp 380ms ease both;
          transition: transform 260ms cubic-bezier(0.34, 1.56, 0.64, 1),
                      box-shadow 260ms ease,
                      filter 260ms ease;
          will-change: transform, filter;
        }
        .lib-class-card:hover {
          transform: translateY(-4px);
          box-shadow: 0 20px 40px rgba(15,23,42,0.28);
          filter: brightness(1.06) saturate(1.05);
        }
        .lib-class-card:hover .lib-class-icon {
          transform: scale(1.1) rotate(-6deg);
        }
        .lib-class-icon {
          transition: transform 260ms cubic-bezier(0.34, 1.56, 0.64, 1);
        }

        .lib-rt-chip {
          display: inline-flex;
          align-items: center;
          gap: 0.35rem;
          padding: 0.5rem 0.65rem;
          border-radius: 8px;
          background: rgba(255,255,255,0.15);
          border: 1px solid rgba(255,255,255,0.28);
          color: #fff;
          font-size: 0.76rem;
          font-weight: 700;
          text-decoration: none;
          transition: background 180ms ease, transform 180ms ease, border-color 180ms ease;
        }
        .lib-rt-chip:hover {
          background: rgba(255,255,255,0.32);
          transform: translateY(-1px);
          border-color: rgba(255,255,255,0.55);
        }
        .lib-rt-chip:active {
          transform: translateY(0);
          transition-duration: 60ms;
        }

        @media (prefers-reduced-motion: reduce) {
          .lib-class-card, .lib-rt-chip, .lib-back-link, .lib-class-icon {
            animation: none !important;
            transition: none !important;
            transform: none !important;
            filter: none !important;
          }
        }
      `}</style>
    </div>
  );
}