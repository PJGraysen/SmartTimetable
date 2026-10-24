import { useState, type FormEvent } from "react";
import { useNavigate, Link } from "react-router-dom";
import {
  ArrowLeft, Download, Loader2, Library, BookOpen,
  User, Building2, Hash, FileText, BookMarked,
} from "lucide-react";
import * as lib from "../../services/library";

const LIB_BG =
  "radial-gradient(1400px 600px at 85% -5%, rgba(122,78,42,0.07), transparent 60%)," +
  "radial-gradient(900px 500px at -5% 20%, rgba(30,64,175,0.05), transparent 55%)," +
  "linear-gradient(180deg, #f5ecd9 0%, #ecdfc8 100%)";

export default function BookFormPage() {
  const navigate = useNavigate();

  const [title, setTitle] = useState("");
  const [subtitle, setSubtitle] = useState("");
  const [isbn, setIsbn] = useState("");
  const [edition, setEdition] = useState("");
  const [language, setLanguage] = useState("English");
  const [publishedYear, setPublishedYear] = useState("");
  const [description, setDescription] = useState("");

  const [authorsText, setAuthorsText] = useState("");
  const [publisherName, setPublisherName] = useState("");
  const [coverUrl, setCoverUrl] = useState("");
  const [pageCount, setPageCount] = useState("");
  const [ddc, setDdc] = useState("");
  const [lcc, setLcc] = useState("");
  const [toc, setToc] = useState("");
  const [source, setSource] = useState("");
  const [sourceId, setSourceId] = useState("");
  const [marc21, setMarc21] = useState<Record<string, unknown> | null>(null);

  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [fetching, setFetching] = useState<"rest" | "marc" | null>(null);
  const [fetchNotice, setFetchNotice] = useState<string>("");

  function applyResult(r: lib.MarcLookupResult) {
    if (r.title) setTitle(r.title);
    if (r.subtitle) setSubtitle(r.subtitle);
    if (r.authors && r.authors.length) setAuthorsText(r.authors.join(", "));
    if (r.publisher) setPublisherName(r.publisher);
    if (r.published_year) setPublishedYear(String(r.published_year));
    if (r.edition) setEdition(r.edition);
    if (r.language) setLanguage(r.language);
    if (r.description) setDescription(r.description);
    if (r.cover_url) setCoverUrl(r.cover_url);
    if (r.page_count) setPageCount(String(r.page_count));
    if (r.ddc) setDdc(r.ddc);
    if (r.lcc) setLcc(r.lcc);
    if (r.toc) setToc(r.toc);
    if (r.source) setSource(r.source);
    if (r.source_id) setSourceId(r.source_id);
    if ((r as any).marc21) setMarc21((r as any).marc21);
  }

  async function fetchMetadata(kind: "rest" | "marc") {
    const cleaned = isbn.replace(/[^0-9Xx]/g, "").toUpperCase();
    if (cleaned.length !== 10 && cleaned.length !== 13) {
      setFetchNotice("ISBN must be 10 or 13 digits.");
      return;
    }
    setFetching(kind);
    setFetchNotice("");
    setError("");
    try {
      const r = kind === "marc"
        ? await lib.lookupMarcByIsbn(cleaned)
        : await lib.lookupBookByIsbn(cleaned);
      if (!r.found) {
        setFetchNotice(kind === "marc"
          ? "No MARC record found on LoC SRU for that ISBN."
          : "No metadata found for that ISBN.");
        return;
      }
      applyResult(r as lib.MarcLookupResult);
      setFetchNotice(kind === "marc"
        ? "Fetched from LoC SRU (MARC21) — review and save."
        : `Fetched from ${r.source || "remote"} — review and save.`);
    } catch (err: any) {
      setFetchNotice("");
      setError(err?.response?.data?.error || "Lookup failed.");
    } finally {
      setFetching(null);
    }
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const authors = authorsText.split(",").map((s) => s.trim()).filter(Boolean);
      const payload: Record<string, unknown> = {
        title, subtitle, isbn, edition, language, description,
        published_year: publishedYear ? Number(publishedYear) : null,
        cover_url: coverUrl,
        page_count: pageCount ? Number(pageCount) : null,
        ddc, lcc, toc,
        source: source || "MANUAL",
        source_id: sourceId,
        authors_text: authors.join(", "),
        publisher_name: publisherName,
      };
      if (marc21) payload.marc21 = marc21;
      const created = await lib.createBook(payload as any);
      navigate(`/library/catalogue/${created.id}`);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Could not create book.");
    } finally {
      setSubmitting(false);
    }
  }

  const busy = fetching !== null;

  return (
    <div className="book-form-page"
         style={{ padding: "1.5rem", maxWidth: 920, margin: "0 auto", minHeight: "100vh", background: LIB_BG }}>
      <Link to="/library/catalogue" style={backBtn}>
        <ArrowLeft size={16} /> Back to catalogue
      </Link>

      <div style={pageHeader}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.9rem" }}>
          <div style={{
            width: 56, height: 56, borderRadius: 14,
            background: "#1e3a8a", color: "#fff",
            display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 6px 16px rgba(30,58,138,0.35)",
          }}>
            <BookOpen size={26} />
          </div>
          <div>
            <span style={kicker}>LIBRARY · CATALOGUE</span>
            <h1 style={{ margin: "0.35rem 0 0", color: "#111827", fontSize: "1.6rem", fontWeight: 800 }}>
              Add Book
            </h1>
            <p style={{ margin: "0.25rem 0 0", color: "#748095", fontSize: "0.92rem" }}>
              Enter details manually, or fetch metadata from ISBN.
            </p>
          </div>
        </div>
      </div>

      <form onSubmit={submit}>

        {/* ISBN Quick-fill */}
        <div style={isbnBar}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.7rem" }}>
            <div style={{
              width: 32, height: 32, borderRadius: 8, background: "#1e3a8a", color: "#fff",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <Hash size={16} />
            </div>
            <div>
              <div style={{ fontSize: "0.8rem", fontWeight: 800, color: "#1e3a8a", letterSpacing: "0.05em" }}>
                ISBN QUICK-FILL
              </div>
              <div style={{ fontSize: "0.72rem", color: "#64748b" }}>
                Auto-populate title, authors, publisher, cover, and classification.
              </div>
            </div>
          </div>

          <div style={{ display: "flex", gap: "0.55rem", flexWrap: "wrap" }}>
            <input
              value={isbn}
              onChange={(e) => setIsbn(e.target.value)}
              placeholder="9780134685991"
              style={{ ...isbnInp, flex: "1 1 260px" }}
            />
            <button type="button" onClick={() => void fetchMetadata("rest")}
                    disabled={busy || !isbn} className="isbn-btn isbn-btn-blue">
              {fetching === "rest" ? <Loader2 size={14} className="spin" /> : <Download size={14} />}
              {fetching === "rest" ? "Fetching…" : "REST · OpenLibrary"}
            </button>
            <button type="button" onClick={() => void fetchMetadata("marc")}
                    disabled={busy || !isbn} className="isbn-btn isbn-btn-green">
              {fetching === "marc" ? <Loader2 size={14} className="spin" /> : <Library size={14} />}
              {fetching === "marc" ? "Fetching…" : "MARC · LoC SRU"}
            </button>
          </div>

          {fetchNotice ? (
            <div style={{
              marginTop: "0.7rem", padding: "0.5rem 0.75rem",
              background: "#ecfdf5", border: "1px solid #86efac",
              borderRadius: 6, fontSize: "0.82rem", color: "#065f46",
              display: "inline-block", fontWeight: 600,
            }}>{fetchNotice}</div>
          ) : null}
        </div>

        {/* Section: Book identity */}
        <Section title="Book Identity" colour="#1e3a8a" Icon={BookOpen}>
          <Field label="Title *">
            <input required value={title} onChange={(e) => setTitle(e.target.value)} style={inp} />
          </Field>
          <Field label="Subtitle">
            <input value={subtitle} onChange={(e) => setSubtitle(e.target.value)} style={inp} />
          </Field>
          <Field label="Authors (comma-separated)" Icon={User}>
            <input value={authorsText} onChange={(e) => setAuthorsText(e.target.value)}
                   style={inp} placeholder="Joshua Bloch, Brian Goetz" />
          </Field>
          <Field label="ISBN" Icon={Hash}>
            <input value={isbn} onChange={(e) => setIsbn(e.target.value)} style={inp} />
          </Field>
          <div style={row3}>
            <Field label="Edition">
              <input value={edition} onChange={(e) => setEdition(e.target.value)} style={inp} />
            </Field>
            <Field label="Language">
              <input value={language} onChange={(e) => setLanguage(e.target.value)} style={inp} />
            </Field>
            <Field label="Published year">
              <input type="number" value={publishedYear}
                     onChange={(e) => setPublishedYear(e.target.value)} style={inp} />
            </Field>
          </div>
        </Section>

        {/* Section: Publication */}
        <Section title="Publication" colour="#0e7490" Icon={Building2}>
          <Field label="Publisher">
            <input value={publisherName} onChange={(e) => setPublisherName(e.target.value)} style={inp} />
          </Field>
          <div style={row3}>
            <Field label="Pages">
              <input type="number" value={pageCount}
                     onChange={(e) => setPageCount(e.target.value)} style={inp} />
            </Field>
            <Field label="Cover URL">
              <input value={coverUrl} onChange={(e) => setCoverUrl(e.target.value)}
                     style={inp} placeholder="https://…" />
            </Field>
            <div />
          </div>
          {coverUrl ? (
            <div style={{ display: "flex", gap: "1rem", alignItems: "flex-start", marginTop: "0.5rem" }}>
              <div style={coverPreview}>
                <img src={coverUrl} alt="cover"
                     style={{ width: "100%", height: "100%", objectFit: "cover" }} />
              </div>
              <div style={{ fontSize: "0.8rem", color: "#64748b", alignSelf: "center", lineHeight: 1.5 }}>
                <b style={{ color: "#0e7490" }}>Cover preview</b><br />
                This is how the book will appear in catalogue cards.
              </div>
            </div>
          ) : null}
        </Section>

        {/* Section: Classification */}
        <Section title="Classification" colour="#7e22ce" Icon={BookMarked}>
          <div style={row2}>
            <Field label="DDC (Dewey Decimal)">
              <input value={ddc} onChange={(e) => setDdc(e.target.value)}
                     style={inp} placeholder="005.133" />
            </Field>
            <Field label="LCC (Library of Congress)">
              <input value={lcc} onChange={(e) => setLcc(e.target.value)}
                     style={inp} placeholder="QA76.73.J38" />
            </Field>
          </div>
        </Section>

        {/* Section: Content */}
        <Section title="Content" colour="#a16207" Icon={FileText}>
          <Field label="Description">
            <textarea value={description} onChange={(e) => setDescription(e.target.value)}
                      rows={4} style={{ ...inp, resize: "vertical" }} />
          </Field>
          <Field label="Table of Contents">
            <textarea value={toc} onChange={(e) => setToc(e.target.value)}
                      rows={3} style={{ ...inp, resize: "vertical" }} />
          </Field>
        </Section>

        {source ? (
          <div style={{
            fontSize: "0.78rem", color: "#475569", marginBottom: "1rem",
            padding: "0.6rem 0.9rem", background: "rgba(255,255,255,0.7)",
            border: "1px solid #cbd5e1", borderRadius: 8,
          }}>
            <b style={{ color: "#1e3a8a" }}>Source:</b> {source}
            {sourceId ? ` · ${sourceId}` : ""}
            {marc21 ? " · MARC21 record attached" : ""}
          </div>
        ) : null}

        {error ? (
          <div style={{
            background: "#fef2f2", border: "1px solid #fecaca",
            color: "#7f1d1d", padding: "0.75rem 1rem",
            borderRadius: 8, marginBottom: "1rem", fontSize: "0.88rem", fontWeight: 600,
          }}>{error}</div>
        ) : null}

        <div style={{ display: "flex", gap: "0.75rem", marginTop: "0.5rem", flexWrap: "wrap" }}>
          <button type="submit" disabled={submitting} className="save-btn">
            {submitting ? <Loader2 size={16} className="spin" /> : <BookOpen size={16} />}
            {submitting ? "Saving…" : "Save Book"}
          </button>
          <Link to="/library/catalogue" className="cancel-btn">Cancel</Link>
        </div>
      </form>

      <style>{`
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }

        .isbn-btn {
          display: inline-flex; align-items: center; gap: 0.4rem;
          padding: 0.65rem 1rem; border-radius: 8px; border: none;
          color: #fff; font-weight: 800; font-size: 0.82rem;
          cursor: pointer; transition: transform 200ms ease, box-shadow 200ms ease, filter 200ms ease;
          font-family: inherit;
        }
        .isbn-btn:disabled { opacity: 0.55; cursor: not-allowed; }
        .isbn-btn-blue  { background: #1e3a8a; }
        .isbn-btn-green { background: #065f46; }
        .isbn-btn:hover:not(:disabled) {
          transform: translateY(-2px) scale(1.02);
          box-shadow: 0 8px 20px rgba(15,23,42,0.25);
          filter: brightness(1.08);
        }
        .isbn-btn:active:not(:disabled) { transform: translateY(0) scale(0.99); }

        .save-btn {
          display: inline-flex; align-items: center; gap: 0.5rem;
          padding: 0.85rem 1.75rem; border-radius: 10px; border: 2px solid #1e3a8a;
          background: #1e3a8a; color: #fff; font-weight: 800; font-size: 0.95rem;
          cursor: pointer; font-family: inherit;
          transition: transform 240ms cubic-bezier(0.34, 1.56, 0.64, 1),
                      box-shadow 240ms ease, filter 240ms ease;
          box-shadow: 0 6px 16px rgba(30,58,138,0.25);
        }
        .save-btn:hover:not(:disabled) {
          transform: translateY(-4px) scale(1.03);
          box-shadow: 0 18px 36px rgba(30,58,138,0.35);
          filter: brightness(1.12) saturate(1.08);
        }
        .save-btn:active:not(:disabled) { transform: translateY(-1px) scale(0.99); }
        .save-btn:disabled { opacity: 0.6; cursor: wait; }

        .cancel-btn {
          display: inline-flex; align-items: center; gap: 0.5rem;
          padding: 0.85rem 1.5rem; border-radius: 10px;
          background: rgba(255,255,255,0.9); border: 2px solid #cbd5e1;
          color: #475569; font-weight: 800; font-size: 0.95rem;
          text-decoration: none; font-family: inherit;
          transition: transform 200ms ease, border-color 200ms ease, background 200ms ease;
        }
        .cancel-btn:hover {
          transform: translateY(-2px);
          border-color: #94a3b8;
          background: #fff;
          color: #1e293b;
        }

        @media (prefers-reduced-motion: reduce) {
          .isbn-btn, .save-btn, .cancel-btn { transition: none !important; transform: none !important; }
        }
      `}</style>
    </div>
  );
}

const backBtn: React.CSSProperties = {
  display: "inline-flex", alignItems: "center", gap: "0.35rem",
  padding: "0.5rem 0.9rem", borderRadius: 8,
  background: "rgba(255,255,255,0.9)", border: "1px solid #cbd5e1",
  color: "#1e3a8a", marginBottom: "1.25rem", fontSize: "0.85rem",
  fontWeight: 700, textDecoration: "none",
};
const pageHeader: React.CSSProperties = {
  marginBottom: "1.5rem", padding: "1.5rem",
  background: "rgba(255,255,255,0.94)", borderRadius: 16,
  borderLeft: "6px solid #1e3a8a",
  boxShadow: "0 6px 18px rgba(15,23,42,0.08)",
};
const kicker: React.CSSProperties = {
  fontSize: "0.75rem", letterSpacing: "0.08em", color: "#748095", fontWeight: 700,
};
const isbnBar: React.CSSProperties = {
  padding: "1.1rem 1.25rem", borderRadius: 14, marginBottom: "1.25rem",
  background: "rgba(255,255,255,0.94)",
  border: "2px solid #93c5fd",
  boxShadow: "0 4px 14px rgba(30,58,138,0.08)",
};
const isbnInp: React.CSSProperties = {
  padding: "0.65rem 0.85rem", borderRadius: 8,
  border: "2px solid #cbd5e1", fontSize: "0.95rem",
  background: "#fff", fontFamily: "monospace",
  transition: "border-color 180ms ease, box-shadow 180ms ease",
};
const inp: React.CSSProperties = {
  width: "100%", padding: "0.6rem 0.8rem", borderRadius: 8,
  border: "1px solid #cbd5e1", fontSize: "0.92rem",
  background: "#fdfbf7", fontFamily: "inherit",
  transition: "border-color 180ms ease, box-shadow 180ms ease, background 180ms ease",
};
const row2: React.CSSProperties = { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" };
const row3: React.CSSProperties = { display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem" };
const coverPreview: React.CSSProperties = {
  width: 72, height: 100, borderRadius: 8, overflow: "hidden",
  background: "rgba(15,23,42,0.06)", border: "1px solid #cbd5e1",
  boxShadow: "0 4px 12px rgba(15,23,42,0.15)",
  flexShrink: 0,
};

function Section({ title, colour, Icon, children }: {
  title: string; colour: string; Icon: any; children: React.ReactNode;
}) {
  return (
    <div style={{
      background: "rgba(255,255,255,0.94)", borderRadius: 14,
      padding: "1.25rem 1.5rem", marginBottom: "1.25rem",
      boxShadow: "0 4px 14px rgba(15,23,42,0.06)",
      borderLeft: `6px solid ${colour}`,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: "0.55rem", marginBottom: "1rem" }}>
        <div style={{
          width: 32, height: 32, borderRadius: 8, background: colour, color: "#fff",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <Icon size={16} />
        </div>
        <h2 style={{ margin: 0, fontSize: "1rem", fontWeight: 800, color: "#111827" }}>{title}</h2>
      </div>
      {children}
    </div>
  );
}

function Field({ label, Icon, children }: {
  label: string; Icon?: any; children: React.ReactNode;
}) {
  return (
    <div style={{ marginBottom: "1rem" }}>
      <label style={{
        display: "flex", alignItems: "center", gap: "0.35rem",
        fontSize: "0.72rem", fontWeight: 800, color: "#475569",
        letterSpacing: "0.04em", textTransform: "uppercase", marginBottom: "0.3rem",
      }}>
        {Icon ? <Icon size={12} /> : null}
        {label}
      </label>
      {children}
    </div>
  );
}