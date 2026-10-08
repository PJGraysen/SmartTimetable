import { useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { ArrowLeft, BookOpen, Plus } from "lucide-react";
import * as lib from "../../services/library";

export default function BookDetailPage() {
  const { id = "" } = useParams();
  const [book, setBook] = useState<lib.Book | null>(null);
  const [copies, setCopies] = useState<lib.Copy[]>([]);
  const [error, setError] = useState("");

  const { role } = useAuth();
  const [requestBusy, setRequestBusy] = useState(false);
  const [requestMsg, setRequestMsg] = useState("");
  const [showAddCopy, setShowAddCopy] = useState(false);
  const [barcode, setBarcode] = useState("");
  const [accession, setAccession] = useState("");
  const [shelf, setShelf] = useState("");
  const [shelves, setShelves] = useState<lib.Shelf[]>([]);

  useEffect(() => {
    if (!id) return;
    Promise.all([lib.getBook(id), lib.listBookCopies(id), lib.listShelves()])
      .then(([b, c, s]) => { setBook(b); setCopies(c); setShelves(s); })
      .catch((e) => setError(e?.response?.data?.detail || "Failed to load book."));
  }, [id]);

  async function submitRequest() {
    if (!book) return;
    setRequestBusy(true);
    setRequestMsg("");
    try {
      await lib.requestBook(book.id);
      setRequestMsg("Request submitted — awaiting teacher approval.");
    } catch (e: any) {
      const status = e?.response?.status;
      const detail =
        e?.response?.data?.detail ||
        e?.response?.data?.error ||
        e?.message ||
        "Unknown error";
      setRequestMsg(
        status ? `[${status}] ${detail}` : `Network error: ${detail}`
      );
    } finally {
      setRequestBusy(false);
    }
  }

  async function submitCopy(e: FormEvent) {
    e.preventDefault();
    try {
      const created = await lib.createCopy(id, {
        barcode, accession_number: accession, shelf: shelf || null,
        status: "AVAILABLE", condition: "GOOD",
      } as Partial<lib.Copy>);
      setCopies((prev) => [...prev, created]);
      setBarcode(""); setAccession(""); setShelf("");
      setShowAddCopy(false);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Could not add copy.");
    }
  }

  if (!book) {
    return <div style={{ padding: "1.5rem" }}>{error || "Loading…"}</div>;
  }

  return (
    <div style={{ padding: "1.5rem" }}>
      <Link to="/library/catalogue" style={{ display: "inline-flex", alignItems: "center", gap: "0.35rem", color: "#1e3a8a", marginBottom: "1rem" }}>
        <ArrowLeft size={16} /> Back to catalogue
      </Link>

      <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: "10px", padding: "1.5rem", marginBottom: "1.5rem" }}>
        <h1 style={{ margin: 0 }}>{book.title}</h1>
        <div style={{ marginTop: "0.5rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
          {role === "STUDENT" ? (
            <button
              type="button"
              onClick={submitRequest}
              disabled={requestBusy}
              style={{
                padding: "0.55rem 1rem", borderRadius: 6,
                background: "#059669", color: "#fff",
                fontWeight: 700, border: "none", cursor: "pointer",
                display: "inline-flex", alignItems: "center", gap: "0.4rem",
              }}
            >
              <BookOpen size={15} /> {requestBusy ? "Requesting…" : "Request this book"}
            </button>
          ) : null}
          {book.read_asset ? (
            <Link to={`/library/read/${book.id}`}
                  style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem",
                           padding: "0.55rem 1rem", borderRadius: 6, background: "#1e3a8a",
                           color: "#fff", fontWeight: 700, textDecoration: "none" }}>
              <BookOpen size={15} /> Read online
            </Link>
          ) : null}
        </div>
        {book.subtitle ? <p style={{ color: "#748095", marginTop: "0.35rem" }}>{book.subtitle}</p> : null}
        {requestMsg ? (
          <div style={{ marginTop: "0.75rem", padding: "0.55rem 0.85rem",
                        background: "#ecfdf5", border: "1px solid #a7f3d0",
                        borderRadius: 6, color: "#065f46", fontSize: "0.85rem" }}>
            {requestMsg}
          </div>
        ) : null}

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem", marginTop: "1rem" }}>
          <Field label="Authors" value={book.authors.map((a) => a.name).join(", ") || "—"} />
          <Field label="Publisher" value={book.publisher?.name || "—"} />
          <Field label="ISBN" value={book.isbn || "—"} />
          <Field label="Year" value={book.published_year ? String(book.published_year) : "—"} />
          <Field label="Language" value={book.language || "—"} />
          <Field label="Edition" value={book.edition || "—"} />
        </div>
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
        <h2 style={{ margin: 0 }}>Copies ({copies.length})</h2>
        <button type="button" className="primary-button" onClick={() => setShowAddCopy((s) => !s)}>
          <Plus size={16} /> Add Copy
        </button>
      </div>

      {showAddCopy ? (
        <form onSubmit={submitCopy} style={{ background: "#f9fafb", border: "1px solid #e5e7eb", borderRadius: "8px", padding: "1rem", marginBottom: "1rem", display: "grid", gridTemplateColumns: "1fr 1fr 1fr auto", gap: "0.75rem", alignItems: "end" }}>
          <Input label="Barcode" value={barcode} onChange={setBarcode} required />
          <Input label="Accession #" value={accession} onChange={setAccession} required />
          <div>
            <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "#748095", marginBottom: "0.25rem" }}>Shelf</label>
            <select value={shelf} onChange={(e) => setShelf(e.target.value)} style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid #d1d5db" }}>
              <option value="">—</option>
              {shelves.map((s) => <option key={s.id} value={s.id}>{s.code} — {s.name}</option>)}
            </select>
          </div>
          <button type="submit" className="primary-button">Save</button>
        </form>
      ) : null}

      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr><th>Barcode</th><th>Accession</th><th>Status</th><th>Condition</th></tr>
          </thead>
          <tbody>
            {copies.length === 0 ? (
              <tr><td colSpan={4} style={{ textAlign: "center", color: "#748095", padding: "1rem" }}>No copies yet.</td></tr>
            ) : copies.map((c) => (
              <tr key={c.id}>
                <td><code>{c.barcode}</code></td>
                <td>{c.accession_number}</td>
                <td><StatusPill status={c.status} /></td>
                <td>{c.condition}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={{ fontSize: "0.7rem", color: "#748095", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</div>
      <div style={{ marginTop: "0.2rem", color: "#111827" }}>{value}</div>
    </div>
  );
}

function Input({ label, value, onChange, required }: { label: string; value: string; onChange: (v: string) => void; required?: boolean }) {
  return (
    <div>
      <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "#748095", marginBottom: "0.25rem" }}>{label}</label>
      <input required={required} value={value} onChange={(e) => onChange(e.target.value)} style={{ width: "100%", padding: "0.5rem", borderRadius: "6px", border: "1px solid #d1d5db" }} />
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const colour: Record<string, string> = {
    AVAILABLE: "#059669", ISSUED: "#7c3aed", RESERVED: "#0284c7",
    LOST: "#dc2626", DAMAGED: "#ea580c", REPAIR: "#6b7280",
  };
  return (
    <span style={{ background: (colour[status] || "#6b7280") + "22", color: colour[status] || "#6b7280", padding: "0.2rem 0.5rem", borderRadius: "4px", fontSize: "0.75rem", fontWeight: 700 }}>
      {status}
    </span>
  );
}
