import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { BookOpen, FileText, GraduationCap, Layers, ArrowLeft, Scroll, FlaskConical, Briefcase } from "lucide-react";
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
  { id: "books", label: "Textbooks", icon: BookOpen, to: "/library/catalogue" },
  { id: "resources", label: "Digital Resources", icon: FileText, to: "/library/resources" },
  { id: "papers", label: "Past Papers", icon: Scroll, to: "/library/resources?category=PAST_PAPER" },
  { id: "case", label: "Case Studies", icon: FlaskConical, to: "/library/resources?category=RESEARCH" },
  { id: "syllabus", label: "Syllabus", icon: Layers, to: "/library/resources?category=SYLLABUS" },
  { id: "careers", label: "Careers", icon: Briefcase, to: "/library/resources?category=OTHER" },
];

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

  return (
    <div style={{ padding: "1.5rem" }}>
      <Link to="/library" style={{ display: "inline-flex", alignItems: "center", gap: "0.35rem",
                                    color: "#1e3a8a", marginBottom: "1rem", fontSize: "0.85rem" }}>
        <ArrowLeft size={15} /> Back to dashboard
      </Link>

      <div style={{ display: "flex", alignItems: "center", gap: "0.85rem", marginBottom: "1.5rem" }}>
        <div style={{
          width: 56, height: 56, borderRadius: 12, background: subject?.colour || "#1e3a8a",
          color: "#fff", fontSize: "1.6rem", display: "flex", alignItems: "center",
          justifyContent: "center", boxShadow: "0 2px 8px rgba(15,23,42,0.2)",
        }}>
          {subject?.icon || "📕"}
        </div>
        <div>
          <div style={{ fontSize: "0.72rem", letterSpacing: "0.08em", color: "#748095", fontWeight: 700 }}>
            {code.toUpperCase()}
          </div>
          <h1 style={{ margin: 0, fontSize: "1.5rem" }}>{subject?.name || code}</h1>
          <p style={{ color: "#748095", margin: "0.2rem 0 0" }}>Choose class level and resource type.</p>
        </div>
      </div>

      {CLASS_GROUPS.map((group) => (
        <section key={group.label} style={{ marginBottom: "1.75rem" }}>
          <h2 style={{ fontSize: "1rem", color: "#1e3a8a", display: "flex", alignItems: "center",
                        gap: "0.5rem", marginBottom: "0.75rem" }}>
            <GraduationCap size={17} /> {group.label}
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: "0.75rem" }}>
            {group.items.map((cl) => (
              <div key={cl.code} style={{
                background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, padding: "0.9rem",
              }}>
                <div style={{ fontWeight: 700, color: "#111827", marginBottom: "0.6rem" }}>{cl.label}</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem" }}>
                  {RESOURCE_TYPES.map((rt) => {
                    const Icon = rt.icon;
                    return (
                      <Link key={rt.id} to={buildLink(rt.to, cl.code)}
                            style={{
                              display: "inline-flex", alignItems: "center", gap: "0.3rem",
                              fontSize: "0.72rem", padding: "0.28rem 0.55rem", borderRadius: 5,
                              background: "#f1f5f9", color: "#1e3a8a", fontWeight: 700,
                              textDecoration: "none", border: "1px solid #cbd5e1",
                            }}>
                        <Icon size={11} /> {rt.label}
                      </Link>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
