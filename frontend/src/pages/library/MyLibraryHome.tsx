import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Search, Loader2, BookOpen } from "lucide-react";
import * as lib from "../../services/library";
import { useAuth } from "../../contexts/AuthContext";

export default function MyLibraryHome() {
  const { me } = useAuth();
  const [portal, setPortal] = useState<Awaited<ReturnType<typeof lib.portalMe>> | null>(null);
  const [recs, setRecs] = useState<Awaited<ReturnType<typeof lib.portalRecommendations>>>([]);
  const [subjects, setSubjects] = useState<lib.SubjectSummaryRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");

  useEffect(() => {
    Promise.all([
      lib.portalMe().catch(() => null),
      lib.portalRecommendations().catch(() => []),
      lib.getSubjectSummary().catch(() => []),
    ]).then(([p, r, s]) => { setPortal(p); setRecs(r); setSubjects(s); })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div style={{ padding: "2rem", display: "flex", gap: "0.5rem", color: "#64748b" }}>
      <Loader2 size={18} className="spin" /> Loading your library…
    </div>
  );

  const active = portal?.active_loans ?? [];

  return (
    <div style={{ padding: "1.5rem" }}>
      <div style={{ marginBottom: "1rem" }}>
        <span style={{ fontSize: "0.75rem", letterSpacing: "0.08em", color: "#748095", fontWeight: 700 }}>
          MY LIBRARY{me?.role ? ` · ${me.role}` : ""}
        </span>
        <h1 style={{ marginTop: "0.35rem" }}>{me?.full_name ? `Welcome, ${me.full_name}` : "Library"}</h1>
        <p style={{ color: "#748095" }}>Browse by subject, request books, and track your loans.</p>
      </div>

      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1.25rem" }}>
        <div style={{ flex: 1, position: "relative" }}>
          <Search size={16} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "#94a3b8" }} />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search the catalogue…"
                 style={{ width: "100%", padding: "0.65rem 0.75rem 0.65rem 2.2rem", borderRadius: 6, border: "1px solid #d1d5db" }} />
        </div>
        <Link to={`/library/catalogue${q ? `?q=${encodeURIComponent(q)}` : ""}`} className="primary-button">Search</Link>
      </div>

      {active.length > 0 ? (
        <section style={{ marginBottom: "2rem" }}>
          <h2 style={{ fontSize: "1.1rem", marginBottom: "0.75rem" }}>Active loans</h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: "0.75rem" }}>
            {active.map((l) => (
              <div key={l.id} style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, padding: "1rem" }}>
                <div style={{ fontWeight: 700 }}>{l.book_title}</div>
                <div style={{ fontSize: "0.8rem", color: l.overdue_days > 0 ? "#b91c1c" : "#64748b", marginTop: "0.3rem" }}>
                  Due {new Date(l.due_at).toLocaleDateString()}{l.overdue_days > 0 ? ` · ${l.overdue_days}d overdue` : ""}
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <section style={{ marginBottom: "2rem" }}>
        <h2 style={{ fontSize: "1.1rem", marginBottom: "0.75rem" }}>Browse by subject</h2>
        {subjects.length === 0 ? (
          <div style={{ padding: "1rem", background: "#fff", borderRadius: 10, border: "1px solid #e5e7eb", color: "#64748b" }}>No subjects available.</div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: "0.6rem" }}>
            {subjects.slice(0, 24).map((s) => (
              <Link key={s.id} to={`/library/subject/${encodeURIComponent(s.code)}`}
                    style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, padding: "0.75rem", textDecoration: "none", color: "inherit" }}>
                <div style={{ fontSize: "0.72rem", fontWeight: 800, color: "#1e3a8a" }}>{s.code}</div>
                <div style={{ fontSize: "0.85rem", fontWeight: 700, marginTop: "0.15rem" }}>{s.name}</div>
                <div style={{ fontSize: "0.72rem", color: "#64748b", marginTop: "0.2rem" }}>
                  {s.book_count} titles{s.available_copies ? ` · ${s.available_copies} available` : ""}
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>

      {recs.length > 0 ? (
        <section>
          <h2 style={{ fontSize: "1.1rem", marginBottom: "0.75rem" }}>Recommended for you</h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "0.75rem" }}>
            {recs.slice(0, 8).map((r) => (
              <Link key={r.id} to={`/library/catalogue/${r.id}`}
                    style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, padding: "0.85rem", textDecoration: "none", color: "inherit" }}>
                <div style={{ fontWeight: 700, fontSize: "0.85rem" }}>{r.title}</div>
                <div style={{ fontSize: "0.7rem", color: "#64748b", marginTop: "0.2rem" }}>{r.subjects.slice(0, 3).join(" · ")}</div>
              </Link>
            ))}
          </div>
        </section>
      ) : null}

      <style>{`.spin { animation: spin 1s linear infinite; } @keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
