import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Search, BookOpen, Filter, X } from "lucide-react";
import { useAuth } from "../../auth/AuthContext";
import * as lib from "../../services/library";

export default function CataloguePage() {
  const { role } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  const [q, setQ] = useState(searchParams.get("q") || "");
  const [subject, setSubject] = useState(searchParams.get("subject") || "");
  const [author, setAuthor] = useState(searchParams.get("author") || "");
  const [yearFrom, setYearFrom] = useState(searchParams.get("year_from") || "");
  const [yearTo, setYearTo] = useState(searchParams.get("year_to") || "");
  const [availability, setAvailability] = useState(searchParams.get("availability") || "");
  const [showFilters, setShowFilters] = useState(false);

  const [subjects, setSubjects] = useState<lib.Subject[]>([]);
  const [rows, setRows] = useState<lib.CatalogueSearchRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    lib.getSubjects().then(setSubjects).catch(() => setSubjects([]));
  }, []);

  // Debounced search whenever params change
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    const t = setTimeout(() => {
      lib.catalogueSearch({
        q: q || undefined,
        subject: subject || undefined,
        author: author || undefined,
        year_from: yearFrom || undefined,
        year_to: yearTo || undefined,
        availability: (availability as "available" | "") || undefined,
      })
        .then((r) => { if (!cancelled) setRows(r.results); })
        .catch((e) => { if (!cancelled) setError(e?.response?.data?.detail || "Search failed."); })
        .finally(() => { if (!cancelled) setLoading(false); });

      // Reflect in URL
      const next: Record<string, string> = {};
      if (q) next.q = q;
      if (subject) next.subject = subject;
      if (author) next.author = author;
      if (yearFrom) next.year_from = yearFrom;
      if (yearTo) next.year_to = yearTo;
      if (availability) next.availability = availability;
      setSearchParams(next, { replace: true });
    }, 300);
    return () => { cancelled = true; clearTimeout(t); };
  }, [q, subject, author, yearFrom, yearTo, availability, setSearchParams]);

  const activeFilterCount = useMemo(() => {
    let n = 0;
    if (subject) n++;
    if (author) n++;
    if (yearFrom || yearTo) n++;
    if (availability) n++;
    return n;
  }, [subject, author, yearFrom, yearTo, availability]);

  function clearFilters() {
    setSubject(""); setAuthor(""); setYearFrom(""); setYearTo(""); setAvailability("");
  }

  return (
    <div style={{ padding: "1.5rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "1rem" }}>
        <div>
          <span style={{ fontSize: "0.75rem", letterSpacing: "0.08em", color: "#748095", fontWeight: 700 }}>
            LIBRARY MANAGEMENT
          </span>
          <h1 style={{ marginTop: "0.35rem" }}>Catalogue</h1>
          {searchParams.get("class") ? (
            <span style={{
              display: "inline-block", marginTop: "0.35rem",
              fontSize: "0.72rem", fontWeight: 800, padding: "0.15rem 0.55rem",
              background: "#e0e7ff", color: "#3730a3", borderRadius: 4,
            }}>Class: {searchParams.get("class")}</span>
          ) : null}
          <p style={{ color: "#748095" }}>Search and browse the collection.</p>
        </div>
        {role !== "STUDENT" && (<Link to="/library/catalogue/new" className="primary-button">Add Book</Link>)}
      </div>


      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem", flexWrap: "wrap" }}>
        <div style={{ flex: "1 1 320px", position: "relative" }}>
          <Search size={16} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "#94a3b8" }} />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search title, author, ISBN, publisher…"
            style={{ width: "100%", padding: "0.65rem 0.75rem 0.65rem 2.2rem", borderRadius: "6px", border: "1px solid #d1d5db", fontSize: "0.95rem" }}
          />
        </div>
        <button
          type="button"
          onClick={() => setShowFilters((v) => !v)}
          style={{
            display: "inline-flex", alignItems: "center", gap: "0.4rem",
            padding: "0.65rem 0.9rem", borderRadius: "6px",
            background: showFilters ? "#1e3a8a" : "#fff",
            color: showFilters ? "#fff" : "#1e3a8a",
            border: "1px solid #1e3a8a", fontWeight: 700, cursor: "pointer",
          }}
        >
          <Filter size={15} /> Filters{activeFilterCount > 0 ? ` (${activeFilterCount})` : ""}
        </button>
      </div>

      {showFilters ? (
        <div style={{ background: "#f8fafc", border: "1px solid #e5e7eb", borderRadius: "8px", padding: "1rem", marginBottom: "1rem" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "0.75rem" }}>
            <div>
              <label style={lbl}>Subject</label>
              <select value={subject} onChange={(e) => setSubject(e.target.value)} style={inp}>
                <option value="">All subjects</option>
                {subjects.map((s) => <option key={s.id} value={s.code}>{s.code} — {s.name}</option>)}
              </select>
            </div>
            <div>
              <label style={lbl}>Author</label>
              <input value={author} onChange={(e) => setAuthor(e.target.value)} style={inp} placeholder="e.g. Bloch" />
            </div>
            <div>
              <label style={lbl}>Year from</label>
              <input value={yearFrom} onChange={(e) => setYearFrom(e.target.value)} style={inp} placeholder="1990" />
            </div>
            <div>
              <label style={lbl}>Year to</label>
              <input value={yearTo} onChange={(e) => setYearTo(e.target.value)} style={inp} placeholder="2026" />
            </div>
            <div>
              <label style={lbl}>Availability</label>
              <select value={availability} onChange={(e) => setAvailability(e.target.value)} style={inp}>
                <option value="">Any</option>
                <option value="available">Available copies only</option>
              </select>
            </div>
          </div>
          {activeFilterCount > 0 ? (
            <button type="button" onClick={clearFilters} style={{ marginTop: "0.75rem", display: "inline-flex", alignItems: "center", gap: "0.35rem", background: "transparent", border: "none", color: "#b91c1c", fontWeight: 700, cursor: "pointer", fontSize: "0.85rem" }}>
              <X size={14} /> Clear filters
            </button>
          ) : null}
        </div>
      ) : null}

      {error ? <div className="tt-error">{error}</div> : null}

      {loading ? (
        <div style={{ padding: "2rem", textAlign: "center", color: "#64748b" }}>Loading…</div>
      ) : rows.length === 0 ? (
        <div style={{ padding: "2rem", background: "#f8fafc", borderRadius: "10px", textAlign: "center", color: "#64748b" }}>
          <BookOpen size={28} style={{ color: "#94a3b8", marginBottom: "0.5rem" }} />
          <div>No books match those filters.</div>
        </div>
      ) : (
        <>
          <div style={{ fontSize: "0.8rem", color: "#64748b", marginBottom: "0.6rem" }}>{rows.length} result{rows.length === 1 ? "" : "s"}</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "1rem" }}>
            {rows.map((b) => (
              <Link key={b.id} to={`/library/catalogue/${b.id}`} style={{
                display: "block", background: "#fff", border: "1px solid #e5e7eb",
                borderRadius: "10px", padding: "1rem", textDecoration: "none", color: "inherit",
              }}>
                <div style={{ display: "flex", gap: "0.85rem" }}>
                  {b.cover_url ? (
                    <img src={b.cover_url} alt="" style={{ width: 56, height: 78, objectFit: "cover", borderRadius: 4, border: "1px solid #e5e7eb" }} />
                  ) : (
                    <div style={{ width: 56, height: 78, background: "#f1f5f9", borderRadius: 4, display: "flex", alignItems: "center", justifyContent: "center" }}>
                      <BookOpen size={20} style={{ color: "#94a3b8" }} />
                    </div>
                  )}
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div style={{ fontWeight: 700, color: "#111827", fontSize: "0.95rem", overflow: "hidden", textOverflow: "ellipsis", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}>
                      {b.title}
                    </div>
                    {b.authors.length ? (
                      <div style={{ color: "#64748b", fontSize: "0.8rem", marginTop: "0.2rem" }}>
                        {b.authors.map((a) => a.name).join(", ")}
                      </div>
                    ) : null}
                    <div style={{ fontSize: "0.72rem", color: "#94a3b8", marginTop: "0.35rem" }}>
                      {b.published_year || "—"}{b.publisher ? ` · ${b.publisher}` : ""}
                    </div>
                    <div style={{ display: "flex", gap: "0.35rem", marginTop: "0.5rem", flexWrap: "wrap" }}>
                      {b.subjects.slice(0, 3).map((s) => (
                        <span key={s.id} style={{ fontSize: "0.68rem", background: "#e0e7ff", color: "#3730a3", padding: "0.1rem 0.4rem", borderRadius: 4, fontWeight: 700 }}>
                          {s.code}
                        </span>
                      ))}
                      <span style={{ fontSize: "0.68rem", marginLeft: "auto", color: b.available_copy_count > 0 ? "#166534" : "#b91c1c", fontWeight: 700 }}>
                        {b.available_copy_count}/{b.copy_count} avail
                      </span>
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

const lbl: React.CSSProperties = { display: "block", fontSize: "0.72rem", fontWeight: 700, color: "#748095", marginBottom: "0.25rem" };
const inp: React.CSSProperties = { width: "100%", padding: "0.5rem 0.6rem", borderRadius: "6px", border: "1px solid #d1d5db", fontSize: "0.9rem" };
