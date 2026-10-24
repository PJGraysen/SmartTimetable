import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Search, BookOpen, Filter, X, Plus, ArrowLeft } from "lucide-react";
import { useAuth } from "../../auth/AuthContext";
import * as lib from "../../services/library";

const SUBJECT_COLOURS: Record<string, string> = {
  MAT:"#1e3a8a",EMCM:"#1e40af",BIO:"#15803d",BIOPRAC:"#166534",
  CHEM:"#0e7490",CHEMPRAC:"#155e75",PHY:"#0369a1",PHYPRAC:"#075985",
  INTSCI:"#0c4a6e",ENG:"#1d4ed8",KIS:"#b91c1c",LIT:"#991b1b",
  GEO:"#065f46",HIS:"#7c2d12",SST:"#0f766e",CRE:"#92400e",
  IRE:"#a16207",PPI:"#854d0e",CAS:"#9333ea",MUSD:"#7e22ce",
  ART:"#a21caf",BUS:"#4338ca",COMP:"#3730a3",CS:"#1e40af",
  ICT:"#0891b2",AGR:"#4d7c0f",PE:"#047857",
};
const BOOK_PALETTE = ["#1e3a8a","#0e7490","#166534","#a16207","#7e22ce","#991b1b","#3730a3","#4d7c0f"];
function bookColour(id: string): string {
  let h = 0;
  for (let i = 0; i < id.length; i++) h = ((h * 31) + id.charCodeAt(i)) >>> 0;
  return BOOK_PALETTE[h % BOOK_PALETTE.length];
}
const LIB_BG =
  "radial-gradient(1400px 600px at 85% -5%, rgba(122,78,42,0.07), transparent 60%)," +
  "radial-gradient(900px 500px at -5% 20%, rgba(30,64,175,0.05), transparent 55%)," +
  "linear-gradient(180deg, #f5ecd9 0%, #ecdfc8 100%)";

export default function CataloguePage() {
  const { role } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialSubject = searchParams.get("subject") || "";
  const initialClass = searchParams.get("class") || "";

  const [q, setQ] = useState(searchParams.get("q") || "");
  const [subject, setSubject] = useState(initialSubject);
  const [author, setAuthor] = useState(searchParams.get("author") || "");
  const [yearFrom, setYearFrom] = useState(searchParams.get("year_from") || "");
  const [yearTo, setYearTo] = useState(searchParams.get("year_to") || "");
  const [availability, setAvailability] = useState(searchParams.get("availability") || "");
  const [showFilters, setShowFilters] = useState(false);

  const [subjects, setSubjects] = useState<lib.Subject[]>([]);
  const [rows, setRows] = useState<lib.CatalogueSearchRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => { lib.getSubjects().then(setSubjects).catch(() => setSubjects([])); }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    const t = setTimeout(() => {
      lib.catalogueSearch({
        q: q || undefined, subject: subject || undefined, author: author || undefined,
        year_from: yearFrom || undefined, year_to: yearTo || undefined,
        availability: (availability as "available" | "") || undefined,
      })
        .then((r) => { if (!cancelled) setRows(r.results); })
        .catch((e) => { if (!cancelled) setError(e?.response?.data?.detail || "Search failed."); })
        .finally(() => { if (!cancelled) setLoading(false); });
      const next: Record<string, string> = {};
      if (q) next.q = q;
      if (subject) next.subject = subject;
      if (author) next.author = author;
      if (yearFrom) next.year_from = yearFrom;
      if (yearTo) next.year_to = yearTo;
      if (availability) next.availability = availability;
      if (initialClass) next.class = initialClass;
      setSearchParams(next, { replace: true });
    }, 300);
    return () => { cancelled = true; clearTimeout(t); };
  }, [q, subject, author, yearFrom, yearTo, availability, initialClass, setSearchParams]);

  const activeFilterCount = useMemo(() => {
    let n = 0;
    if (subject) n++;
    if (author) n++;
    if (yearFrom || yearTo) n++;
    if (availability) n++;
    return n;
  }, [subject, author, yearFrom, yearTo, availability]);

  function clearFilters() { setSubject(""); setAuthor(""); setYearFrom(""); setYearTo(""); setAvailability(""); }

  const contextSubject = useMemo(() => {
    if (!initialSubject) return null;
    const s = subjects.find((x) => x.code.toUpperCase() === initialSubject.toUpperCase());
    return s ? { code: s.code, name: s.name } : { code: initialSubject, name: initialSubject };
  }, [subjects, initialSubject]);

  const subjectColour = initialSubject ? (SUBJECT_COLOURS[initialSubject.toUpperCase()] || "#1e3a8a") : "#1e3a8a";
  const showEmptyState = !loading && !error && rows.length === 0;
  const hasContext = !!initialSubject;

  return (
    <div style={{ padding: "1.5rem", minHeight: "100vh", background: LIB_BG }}>
      {hasContext ? <Link to="/library" style={backBtn}><ArrowLeft size={15} /> Back</Link> : null}

      <div style={hasContext ? { ...contextHeader, borderLeftColor: subjectColour } : plainHeader}>
        <div>
          <span style={kicker}>{hasContext ? "LIBRARY · TEXTBOOKS" : "LIBRARY CATALOGUE"}</span>
          <h1 style={{ color: "#111827", fontSize: "1.6rem", fontWeight: 800, margin: "0.35rem 0 0" }}>
            {contextSubject ? `Textbooks · ${contextSubject.code}` : "Catalogue"}
          </h1>
          {initialClass ? <span style={{ ...classChip, background: subjectColour }}>Class: {initialClass}</span> : null}
          <p style={{ color: "#748095", marginTop: "0.5rem", marginBottom: 0 }}>
            {contextSubject?.name
              ? `${contextSubject.name} · ${rows.length} title${rows.length === 1 ? "" : "s"}`
              : "Search and browse the collection."}
          </p>
        </div>
        {role !== "STUDENT" && (
          <Link to="/library/catalogue/new" className="primary-button"
                style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem", alignSelf: "flex-start" }}>
            <Plus size={15} /> Add Book
          </Link>
        )}
      </div>

      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem", flexWrap: "wrap" }}>
        <div style={{ flex: "1 1 320px", position: "relative" }}>
          <Search size={16} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "#94a3b8" }} />
          <input value={q} onChange={(e) => setQ(e.target.value)}
                 placeholder="Search title, author, ISBN, publisher…"
                 style={{ width: "100%", padding: "0.65rem 0.75rem 0.65rem 2.2rem", borderRadius: 8,
                          border: "1px solid #d1d5db", fontSize: "0.95rem", background: "#fff", fontFamily: "inherit" }} />
        </div>
        <button type="button" onClick={() => setShowFilters((v) => !v)}
                style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem",
                         padding: "0.65rem 0.9rem", borderRadius: 8,
                         background: showFilters ? "#1e3a8a" : "#fff",
                         color: showFilters ? "#fff" : "#1e3a8a",
                         border: "1px solid #1e3a8a", fontWeight: 700, cursor: "pointer",
                         fontFamily: "inherit", fontSize: "0.9rem" }}>
          <Filter size={15} /> Filters{activeFilterCount > 0 ? ` (${activeFilterCount})` : ""}
        </button>
      </div>

      {showFilters ? (
        <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, padding: "1rem", marginBottom: "1rem" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "0.75rem" }}>
            <div><label style={lbl}>Subject</label>
              <select value={subject} onChange={(e) => setSubject(e.target.value)} style={inp}>
                <option value="">All subjects</option>
                {subjects.map((s) => <option key={s.id} value={s.code}>{s.code} — {s.name}</option>)}
              </select>
            </div>
            <div><label style={lbl}>Author</label>
              <input value={author} onChange={(e) => setAuthor(e.target.value)} style={inp} placeholder="e.g. Bloch" />
            </div>
            <div><label style={lbl}>Year from</label>
              <input value={yearFrom} onChange={(e) => setYearFrom(e.target.value)} style={inp} placeholder="1990" />
            </div>
            <div><label style={lbl}>Year to</label>
              <input value={yearTo} onChange={(e) => setYearTo(e.target.value)} style={inp} placeholder="2026" />
            </div>
            <div><label style={lbl}>Availability</label>
              <select value={availability} onChange={(e) => setAvailability(e.target.value)} style={inp}>
                <option value="">Any</option>
                <option value="available">Available copies only</option>
              </select>
            </div>
          </div>
          {activeFilterCount > 0 ? (
            <button type="button" onClick={clearFilters}
                    style={{ marginTop: "0.75rem", display: "inline-flex", alignItems: "center", gap: "0.35rem",
                             background: "transparent", border: "none", color: "#b91c1c", fontWeight: 700,
                             cursor: "pointer", fontSize: "0.85rem", fontFamily: "inherit" }}>
              <X size={14} /> Clear filters
            </button>
          ) : null}
        </div>
      ) : null}

      {error ? <div className="tt-error">{error}</div> : null}

      {loading ? (
        <div style={{ padding: "2rem", textAlign: "center", color: "#64748b" }}>Loading…</div>
      ) : showEmptyState ? (
        <div style={emptyStateCard}>
          <div style={{ ...emptyIcon, background: subjectColour }}><BookOpen size={34} /></div>
          <h3 style={emptyTitle}>
            {contextSubject ? `No textbooks yet for ${contextSubject.code}` : "No books match those filters"}
          </h3>
          <p style={emptySub}>
            {contextSubject
              ? `${contextSubject.name} has no textbooks in the catalogue yet. Add one, or browse the rest of the collection.`
              : "Try clearing filters, or browse the whole catalogue."}
          </p>
          <div style={{ display: "flex", gap: "0.6rem", justifyContent: "center", marginTop: "1.25rem", flexWrap: "wrap" }}>
            <Link to="/library/catalogue" className="primary-button"
                  style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem" }}>
              <BookOpen size={15} /> Browse full catalogue
            </Link>
            {role !== "STUDENT" && (
              <Link to="/library/catalogue/new" className="secondary-button"
                    style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem" }}>
                <Plus size={15} /> Add Book
              </Link>
            )}
          </div>
        </div>
      ) : (
        <>
          <div style={{ fontSize: "0.85rem", color: "#5b6b82", marginBottom: "0.75rem", fontWeight: 600 }}>
            {rows.length} result{rows.length === 1 ? "" : "s"}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "1rem" }}>
            {rows.map((b, i) => {
              const colour = bookColour(b.id);
              return (
                <Link key={b.id} to={`/library/catalogue/${b.id}`} className="cat-card"
                      style={{ display: "block", background: colour, border: `2px solid ${colour}`,
                               borderRadius: 14, padding: "1.25rem", textDecoration: "none", color: "#fff",
                               position: "relative", overflow: "hidden",
                               boxShadow: "0 6px 16px rgba(15,23,42,0.14), inset 0 1px 0 rgba(255,255,255,0.12)",
                               animationDelay: `${Math.min(i * 40, 400)}ms` }}>
                  <div style={{ display: "flex", gap: "0.9rem" }}>
                    <div style={{ width: 64, height: 88, borderRadius: 8,
                                  background: "rgba(255,255,255,0.2)",
                                  border: "1px solid rgba(255,255,255,0.3)",
                                  overflow: "hidden", flexShrink: 0,
                                  display: "flex", alignItems: "center", justifyContent: "center" }}>
                      {b.cover_url
                        ? <img src={b.cover_url} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                        : <BookOpen size={26} style={{ color: "rgba(255,255,255,0.8)" }} />}
                    </div>
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div style={{ fontWeight: 800, color: "#fff", fontSize: "1rem", lineHeight: 1.3,
                                    marginBottom: "0.35rem", overflow: "hidden", display: "-webkit-box",
                                    WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}>
                        {b.title}
                      </div>
                      {b.authors.length ? (
                        <div style={{ color: "rgba(255,255,255,0.82)", fontSize: "0.8rem" }}>
                          {b.authors.map((a) => a.name).join(", ")}
                        </div>
                      ) : null}
                      <div style={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.7)", marginTop: "0.35rem" }}>
                        {b.published_year || "—"}{b.publisher ? ` · ${b.publisher}` : ""}
                      </div>
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: "0.35rem", marginTop: "0.85rem", flexWrap: "wrap", alignItems: "center" }}>
                    {b.subjects.slice(0, 3).map((s) => (
                      <span key={s.id} style={{ fontSize: "0.68rem", background: "rgba(255,255,255,0.2)",
                                                color: "#fff", padding: "0.15rem 0.5rem",
                                                borderRadius: 4, fontWeight: 800,
                                                border: "1px solid rgba(255,255,255,0.28)" }}>
                        {s.code}
                      </span>
                    ))}
                    <span style={{ fontSize: "0.72rem", marginLeft: "auto",
                                   color: b.available_copy_count > 0 ? "#4ade80" : "#fca5a5", fontWeight: 800 }}>
                      {b.available_copy_count}/{b.copy_count} avail
                    </span>
                  </div>
                </Link>
              );
            })}
          </div>
        </>
      )}

      <style>{`
        @keyframes catFadeUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
        .cat-card { animation: catFadeUp 340ms ease both;
                    transition: transform 240ms cubic-bezier(0.34, 1.56, 0.64, 1),
                                box-shadow 240ms ease, filter 240ms ease;
                    will-change: transform, filter; }
        .cat-card:hover { transform: translateY(-6px) scale(1.02);
                          box-shadow: 0 20px 40px rgba(15,23,42,0.28);
                          filter: brightness(1.12) saturate(1.08); }
        .cat-card:active { transform: translateY(-1px) scale(0.99); transition-duration: 80ms; }
        @media (prefers-reduced-motion: reduce) {
          .cat-card { animation: none !important; transition: none !important; transform: none !important; filter: none !important; }
        }
      `}</style>
    </div>
  );
}

const kicker: React.CSSProperties = { fontSize: "0.75rem", letterSpacing: "0.08em", color: "#748095", fontWeight: 700 };
const backBtn: React.CSSProperties = {
  display: "inline-flex", alignItems: "center", gap: "0.35rem",
  padding: "0.5rem 0.9rem", borderRadius: 8,
  background: "rgba(255,255,255,0.9)", border: "1px solid #cbd5e1",
  color: "#1e3a8a", marginBottom: "1.25rem", fontSize: "0.85rem", fontWeight: 700, textDecoration: "none",
};
const contextHeader: React.CSSProperties = {
  marginBottom: "1.5rem", padding: "1.5rem",
  background: "rgba(255,255,255,0.94)", borderRadius: 16, borderLeft: "6px solid #1e3a8a",
  boxShadow: "0 6px 18px rgba(15,23,42,0.08)",
  display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: "1rem",
};
const plainHeader: React.CSSProperties = {
  marginBottom: "1.5rem",
  display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: "1rem",
};
const classChip: React.CSSProperties = {
  display: "inline-block", marginTop: "0.5rem", fontSize: "0.72rem", fontWeight: 800,
  padding: "0.2rem 0.6rem", color: "#fff", borderRadius: 6,
};
const emptyStateCard: React.CSSProperties = {
  padding: "3rem 2rem", textAlign: "center",
  background: "rgba(255,255,255,0.94)", borderRadius: 16, border: "2px dashed #cbd5e1",
};
const emptyIcon: React.CSSProperties = {
  width: 72, height: 72, borderRadius: "50%", color: "#fff",
  display: "inline-flex", alignItems: "center", justifyContent: "center",
  marginBottom: "1rem", boxShadow: "0 8px 20px rgba(15,23,42,0.25)",
};
const emptyTitle: React.CSSProperties = { margin: 0, color: "#0f172a", fontSize: "1.25rem", fontWeight: 800 };
const emptySub: React.CSSProperties = {
  color: "#64748b", fontSize: "0.95rem", marginTop: "0.5rem",
  maxWidth: 480, margin: "0.5rem auto 0", lineHeight: 1.5,
};
const lbl: React.CSSProperties = { display: "block", fontSize: "0.72rem", fontWeight: 700, color: "#748095", marginBottom: "0.25rem" };
const inp: React.CSSProperties = {
  width: "100%", padding: "0.5rem 0.6rem", borderRadius: 6,
  border: "1px solid #d1d5db", fontSize: "0.9rem", background: "#fff", fontFamily: "inherit",
};