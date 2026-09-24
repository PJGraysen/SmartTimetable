import { useState, type FormEvent } from "react";
import { useNavigate, Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
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
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true); setError("");
    try {
      const created = await lib.createBook({
        title, subtitle, isbn, edition, language, description,
        published_year: publishedYear ? Number(publishedYear) : null,
      } as any);
      navigate(`/library/catalogue/${created.id}`);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Could not create book.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={{ padding: "1.5rem", maxWidth: "720px" }}>
      <Link to="/library/catalogue" style={{ display: "inline-flex", alignItems: "center", gap: "0.35rem", color: "#1e3a8a", marginBottom: "1rem" }}>
        <ArrowLeft size={16} /> Back to catalogue
      </Link>
      <h1 style={{ marginBottom: "1.5rem" }}>Add Book</h1>

      <form onSubmit={submit} style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: "10px", padding: "1.5rem" }}>
        <Row label="Title *"><input required value={title} onChange={(e) => setTitle(e.target.value)} style={inp} /></Row>
        <Row label="Subtitle"><input value={subtitle} onChange={(e) => setSubtitle(e.target.value)} style={inp} /></Row>
        <Row label="ISBN"><input value={isbn} onChange={(e) => setIsbn(e.target.value)} style={inp} /></Row>
        <Row label="Edition"><input value={edition} onChange={(e) => setEdition(e.target.value)} style={inp} /></Row>
        <Row label="Language"><input value={language} onChange={(e) => setLanguage(e.target.value)} style={inp} /></Row>
        <Row label="Published year"><input type="number" value={publishedYear} onChange={(e) => setPublishedYear(e.target.value)} style={inp} /></Row>
        <Row label="Description"><textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={4} style={{ ...inp, resize: "vertical" }} /></Row>

        {error ? <div style={{ color: "#b91c1c", marginBottom: "1rem" }}>{error}</div> : null}

        <button type="submit" disabled={submitting} className="primary-button">
          {submitting ? "Saving…" : "Save Book"}
        </button>
      </form>
    </div>
  );
}

const inp: React.CSSProperties = { width: "100%", padding: "0.55rem 0.7rem", borderRadius: "6px", border: "1px solid #d1d5db", fontSize: "0.95rem" };

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: "1rem" }}>
      <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "#748095", marginBottom: "0.3rem" }}>{label}</label>
      {children}
    </div>
  );
}
