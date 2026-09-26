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

  return (
    <div style={{ padding: "1.5rem" }}>
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
            <div key={c.label} style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: "10px", padding: "1.25rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ color: "#748095", fontSize: "0.8rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em" }}>{c.label}</span>
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
            <h2 style={{ margin: 0, fontSize: "1.15rem", color: "#111827", display: "flex", alignItems: "center", gap: "0.5rem" }}>
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
          <div style={{ padding: "1.5rem", background: "#f8fafc", borderRadius: "8px", color: "#64748b", textAlign: "center" }}>
            No active subjects in the curriculum.
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: "0.75rem" }}>
            {subjects.map((s) => {
              const covered = s.book_count > 0;
              return (
                <Link
                  key={s.id}
                  to={`/library/catalogue?subject=${encodeURIComponent(s.code)}`}
                  style={{
                    display: "block",
                    background: "#fff",
                    border: `1px solid ${covered ? "#bbf7d0" : "#e5e7eb"}`,
                    borderRadius: "10px",
                    padding: "1rem",
                    textDecoration: "none",
                    color: "inherit",
                    position: "relative",
                    transition: "box-shadow 150ms ease",
                  }}
                >
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
                  <div style={{ fontWeight: 700, color: "#111827", marginTop: "0.55rem", fontSize: "0.92rem" }}>
                    {s.name}
                  </div>
                  <div style={{ color: "#64748b", fontSize: "0.78rem", marginTop: "0.35rem" }}>
                    {s.book_count} {s.book_count === 1 ? "title" : "titles"}
                    {s.available_copies > 0 ? ` · ${s.available_copies} available` : ""}
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </section>

      <section style={{ marginTop: "2rem", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "1rem" }}>
        <QuickLink to="/library/catalogue" icon={BookOpen} title="Catalogue" text="Browse and search the book collection." />
        <QuickLink to="/library/members" icon={Users} title="Members" text="Students, teachers, and staff who borrow." />
        <QuickLink to="/library/loans" icon={BookMarked} title="Loans" text="Active, overdue, and returned loans." />
        <QuickLink to="/library/reports" icon={AlertTriangle} title="Reports" text="Circulation, inventory, top borrowers." />
      </section>

      <style>{`
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}

function QuickLink({ to, icon: Icon, title, text }: { to: string; icon: any; title: string; text: string }) {
  return (
    <Link to={to} style={{
      display: "block", background: "#fff", border: "1px solid #e5e7eb",
      borderRadius: "10px", padding: "1.25rem", textDecoration: "none", color: "inherit",
    }}>
      <Icon size={22} style={{ color: "#1e3a8a" }} />
      <div style={{ fontWeight: 700, marginTop: "0.5rem", color: "#111827" }}>{title}</div>
      <div style={{ color: "#748095", fontSize: "0.85rem", marginTop: "0.25rem" }}>{text}</div>
    </Link>
  );
}
