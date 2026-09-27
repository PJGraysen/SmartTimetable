import { useEffect, useState } from "react";
import { Search, BookOpen, Loader2 } from "lucide-react";
import * as lib from "../../services/library";

export default function PublicCataloguePage() {
  const [q, setQ] = useState("");
  const [rows, setRows] = useState<lib.CatalogueSearchRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const t = setTimeout(() => {
      lib.catalogueSearch({ q: q || undefined })
        .then((r) => { if (!cancelled) setRows(r.results); })
        .catch(() => { if (!cancelled) setRows([]); })
        .finally(() => { if (!cancelled) setLoading(false); });
    }, 300);
    return () => { cancelled = true; clearTimeout(t); };
  }, [q]);

  return (
    <div style={{ padding: "1.5rem" }}>
      <div style={{ marginBottom: "1rem" }}>
        <span style={{ fontSize: "0.75rem", letterSpacing: "0.08em", color: "#748095", fontWeight: 700 }}>PUBLIC CATALOGUE</span>
        <h1 style={{ marginTop: "0.35rem" }}>Library — Public Browse</h1>
        <p style={{ color: "#748095" }}>Read-only catalogue. Sign in to borrow or reserve.</p>
      </div>
      <div style={{ position: "relative", marginBottom: "1rem" }}>
        <Search size={16} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "#94a3b8" }} />
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search title, author, ISBN…"
               style={{ width: "100%", padding: "0.65rem 0.75rem 0.65rem 2.2rem", borderRadius: 6, border: "1px solid #d1d5db" }} />
      </div>
      {loading ? (
        <div style={{ padding: "2rem", textAlign: "center", color: "#64748b", display: "flex", justifyContent: "center", gap: "0.5rem" }}>
          <Loader2 size={18} className="spin" /> Loading…
        </div>
      ) : rows.length === 0 ? (
        <div style={{ padding: "2rem", background: "#f8fafc", borderRadius: 10, textAlign: "center", color: "#64748b" }}>
          <BookOpen size={28} style={{ color: "#94a3b8" }} />
          <div style={{ marginTop: "0.5rem" }}>No titles found.</div>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "1rem" }}>
          {rows.map((b) => (
            <div key={b.id} style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, padding: "1rem" }}>
              <div style={{ fontWeight: 700 }}>{b.title}</div>
              {b.authors.length ? <div style={{ fontSize: "0.8rem", color: "#64748b", marginTop: "0.2rem" }}>{b.authors.map((a) => a.name).join(", ")}</div> : null}
              <div style={{ fontSize: "0.72rem", color: "#94a3b8", marginTop: "0.35rem" }}>
                {b.published_year || "—"}{b.publisher ? ` · ${b.publisher}` : ""}
              </div>
              <div style={{ fontSize: "0.75rem", color: b.available_copy_count > 0 ? "#166534" : "#b91c1c", fontWeight: 700, marginTop: "0.5rem" }}>
                {b.available_copy_count}/{b.copy_count} available
              </div>
            </div>
          ))}
        </div>
      )}
      <style>{`.spin { animation: spin 1s linear infinite; } @keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
