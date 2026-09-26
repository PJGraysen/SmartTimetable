import { useState, type FormEvent } from "react";
import { useNavigate, Link } from "react-router-dom";
import { ArrowLeft, Download, Loader2, Library } from "lucide-react";
import * as lib from "../../services/library";

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
    <div style={{ padding: "1.5rem", maxWidth: "820px" }}>
      <Link to="/library/catalogue" style={{ display: "inline-flex", alignItems: "center", gap: "0.35rem", color: "#1e3a8a", marginBottom: "1rem" }}>
        <ArrowLeft size={16} /> Back to catalogue
      </Link>
      <h1 style={{ marginBottom: "1.5rem" }}>Add Book</h1>

      <form onSubmit={submit} style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: "10px", padding: "1.5rem" }}>
        <div style={{ background: "#f0f7ff", border: "1px solid #b6d3f5", borderRadius: "8px", padding: "0.9rem 1rem", marginBottom: "1.25rem" }}>
          <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#1e3a8a", letterSpacing: "0.04em", marginBottom: "0.4rem" }}>
            ISBN QUICK-FILL · choose source
          </div>
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", flexWrap: "wrap" }}>
            <input
              value={isbn}
              onChange={(e) => setIsbn(e.target.value)}
              placeholder="9780134685991"
              style={{ ...inp, flex: "1 1 220px", fontFamily: "monospace" }}
            />
            <button
              type="button"
              onClick={() => void fetchMetadata("rest")}
              disabled={busy || !isbn}
              style={{
                display: "inline-flex", alignItems: "center", gap: "0.4rem",
                padding: "0.55rem 0.9rem", borderRadius: "6px",
                background: "#1e3a8a", color: "#fff", border: "none",
                fontWeight: 700, cursor: busy ? "wait" : "pointer",
                opacity: busy || !isbn ? 0.6 : 1,
              }}>
              {fetching === "rest" ? <Loader2 size={14} className="spin" /> : <Download size={14} />}
              {fetching === "rest" ? "Fetching…" : "REST (OpenLibrary)"}
            </button>
            <button
              type="button"
              onClick={() => void fetchMetadata("marc")}
              disabled={busy || !isbn}
              style={{
                display: "inline-flex", alignItems: "center", gap: "0.4rem",
                padding: "0.55rem 0.9rem", borderRadius: "6px",
                background: "#065f46", color: "#fff", border: "none",
                fontWeight: 700, cursor: busy ? "wait" : "pointer",
                opacity: busy || !isbn ? 0.6 : 1,
              }}>
              {fetching === "marc" ? <Loader2 size={14} className="spin" /> : <Library size={14} />}
              {fetching === "marc" ? "Fetching…" : "MARC (LoC SRU)"}
            </button>
          </div>
          {fetchNotice ? (
            <div style={{ marginTop: "0.5rem", fontSize: "0.8rem", color: "#0f766e" }}>{fetchNotice}</div>
          ) : null}
        </div>

        <Row label="Title *">
          <input required value={title} onChange={(e) => setTitle(e.target.value)} style={inp} />
        </Row>
        <Row label="Subtitle">
          <input value={subtitle} onChange={(e) => setSubtitle(e.target.value)} style={inp} />
        </Row>
        <Row label="Authors (comma-separated)">
          <input value={authorsText} onChange={(e) => setAuthorsText(e.target.value)} style={inp} placeholder="Joshua Bloch" />
        </Row>
        <Row label="Publisher">
          <input value={publisherName} onChange={(e) => setPublisherName(e.target.value)} style={inp} />
        </Row>
        <Row label="ISBN">
          <input value={isbn} onChange={(e) => setIsbn(e.target.value)} style={inp} />
        </Row>
        <Row label="Edition">
          <input value={edition} onChange={(e) => setEdition(e.target.value)} style={inp} />
        </Row>
        <Row label="Language">
          <input value={language} onChange={(e) => setLanguage(e.target.value)} style={inp} />
        </Row>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem" }}>
          <Row label="Published year">
            <input type="number" value={publishedYear} onChange={(e) => setPublishedYear(e.target.value)} style={inp} />
          </Row>
          <Row label="Pages">
            <input type="number" value={pageCount} onChange={(e) => setPageCount(e.target.value)} style={inp} />
          </Row>
          <Row label="DDC">
            <input value={ddc} onChange={(e) => setDdc(e.target.value)} style={inp} placeholder="005.133" />
          </Row>
        </div>

        <Row label="LCC">
          <input value={lcc} onChange={(e) => setLcc(e.target.value)} style={inp} placeholder="QA76.73.J38" />
        </Row>
        <Row label="Cover URL">
          <input value={coverUrl} onChange={(e) => setCoverUrl(e.target.value)} style={inp} />
        </Row>
        {coverUrl ? (
          <div style={{ marginBottom: "1rem" }}>
            <img src={coverUrl} alt="cover" style={{ maxHeight: "160px", borderRadius: "6px", border: "1px solid #e5e7eb" }} />
          </div>
        ) : null}
        <Row label="Description">
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={4} style={{ ...inp, resize: "vertical" }} />
        </Row>
        <Row label="Table of Contents">
          <textarea value={toc} onChange={(e) => setToc(e.target.value)} rows={3} style={{ ...inp, resize: "vertical" }} />
        </Row>

        {source ? (
          <div style={{ fontSize: "0.72rem", color: "#64748b", marginBottom: "1rem" }}>
            Source: <strong>{source}</strong>{sourceId ? ` · ${sourceId}` : ""}
            {marc21 ? " · MARC21 record attached" : ""}
          </div>
        ) : null}

        {error ? <div style={{ color: "#b91c1c", marginBottom: "1rem" }}>{error}</div> : null}

        <button type="submit" disabled={submitting} className="primary-button">
          {submitting ? "Saving…" : "Save Book"}
        </button>
      </form>

      <style>{`
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}

const inp: React.CSSProperties = { width: "100%", padding: "0.55rem 0.7rem", borderRadius: "6px", border: "1px solid #d1d5db", fontSize: "0.95rem" };

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: "1rem" }}>
      <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color:"#748095", marginBottom: "0.3rem" }}>{label}</label>
      {children}
    </div>
  );
}
