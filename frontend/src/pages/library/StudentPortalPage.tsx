import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BookOpen, AlertTriangle, Loader2 } from "lucide-react";
import * as lib from "../../services/library";

export default function StudentPortalPage() {
  const [data, setData] = useState<Awaited<ReturnType<typeof lib.portalMe>> | null>(null);
  const [recs, setRecs] = useState<Awaited<ReturnType<typeof lib.portalRecommendations>>>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([lib.portalMe(), lib.portalRecommendations().catch(() => [])])
      .then(([me, r]) => { setData(me); setRecs(r); })
      .catch(() => setData({ linked: false }))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div style={{ padding: "2rem", display: "flex", alignItems: "center", gap: "0.5rem", color: "#64748b" }}>
      <Loader2 size={18} className="spin" /> Loading portal…
    </div>
  );

  if (!data?.linked) return (
    <div style={{ padding: "1.5rem", maxWidth: 720 }}>
      <div style={{ background: "#fef3c7", border: "1px solid #fde68a", borderRadius: 10,
                    padding: "1.25rem", display: "flex", gap: "0.6rem", color: "#78350f" }}>
        <AlertTriangle size={20} />
        <div>
          <div style={{ fontWeight: 700 }}>Not linked to a library membership</div>
          <div style={{ fontSize: "0.85rem" }}>{data?.message || "Ask the librarian to link your account."}</div>
        </div>
      </div>
    </div>
  );

  return (
    <div style={{ padding: "1.5rem", maxWidth: 1100 }}>
      <div style={{ marginBottom: "1rem" }}>
        <span style={{ fontSize: "0.75rem", letterSpacing: "0.08em", color: "#748095", fontWeight: 700 }}>
          MY LIBRARY
        </span>
        <h1 style={{ marginTop: "0.35rem" }}>{data.member?.full_name}</h1>
        <p style={{ color: "#748095" }}>{data.member?.member_number} · {data.member?.member_type}</p>
      </div>

      <section style={{ marginBottom: "2rem" }}>
        <h2 style={{ fontSize: "1.1rem" }}>Active loans</h2>
        {(data.active_loans?.length ?? 0) === 0 ? (
          <div style={{ padding: "1.25rem", background: "#fff", borderRadius: 10,
                        border: "1px solid #e5e7eb", color: "#64748b" }}>No active loans.</div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "0.75rem" }}>
            {data.active_loans?.map((l) => (
              <div key={l.id} style={{ background: "#fff", border: "1px solid #e5e7eb",
                                       borderRadius: 10, padding: "1rem" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  <BookOpen size={16} style={{ color: "#1e3a8a" }} />
                  <span style={{ fontWeight: 700 }}>{l.book_title}</span>
                </div>
                <div style={{ fontSize: "0.8rem", color: "#64748b", marginTop: "0.35rem" }}>
                  Due {new Date(l.due_at).toLocaleDateString()}
                  {l.overdue_days > 0 ? ` · ${l.overdue_days} days overdue` : ""}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section style={{ marginBottom: "2rem" }}>
        <h2 style={{ fontSize: "1.1rem" }}>Recommended for you</h2>
        {recs.length === 0 ? (
          <div style={{ padding: "1.25rem", background: "#fff", borderRadius: 10,
                        border: "1px solid #e5e7eb", color: "#64748b" }}>No recommendations yet.</div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "0.75rem" }}>
            {recs.map((r) => (
              <Link key={r.id} to={`/library/catalogue/${r.id}`}
                    style={{ display: "block", background: "#fff", border: "1px solid #e5e7eb",
                             borderRadius: 10, padding: "0.85rem", textDecoration: "none", color: "inherit" }}>
                <div style={{ display: "flex", gap: "0.6rem" }}>
                  {r.cover_url ? <img src={r.cover_url} alt="" style={{ width: 44, height: 60, borderRadius: 4, objectFit: "cover" }} />
                    : <div style={{ width: 44, height: 60, background: "#f1f5f9", borderRadius: 4 }} />}
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontWeight: 700, fontSize: "0.85rem" }}>{r.title}</div>
                    <div style={{ fontSize: "0.7rem", color: "#64748b", marginTop: "0.2rem" }}>
                      {r.subjects.slice(0, 3).join(" · ")}
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 style={{ fontSize: "1.1rem" }}>Reading history</h2>
        {(data.history?.length ?? 0) === 0 ? (
          <div style={{ padding: "1.25rem", background: "#fff", borderRadius: 10,
                        border: "1px solid #e5e7eb", color: "#64748b" }}>No history yet.</div>
        ) : (
          <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, overflow: "hidden" }}>
            {data.history?.map((h) => (
              <div key={h.id} style={{ padding: "0.6rem 0.85rem", borderBottom: "1px solid #f1f5f9",
                                        fontSize: "0.85rem", display: "flex", justifyContent: "space-between" }}>
                <span>{h.book_title}</span>
                <span style={{ color: "#64748b" }}>{h.returned_at ? new Date(h.returned_at).toLocaleDateString() : h.status}</span>
              </div>
            ))}
          </div>
        )}
      </section>

      <style>{`
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
