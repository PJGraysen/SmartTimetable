import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Search, Plus } from "lucide-react";
import * as lib from "../../services/library";

export default function CataloguePage() {
  const [query, setQuery] = useState("");
  const [books, setBooks] = useState<lib.Book[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    lib.listBooks({ q: query })
      .then(setBooks)
      .catch((e) => setError(e?.response?.data?.detail || "Failed to load books."))
      .finally(() => setLoading(false));
  }, [query]);

  return (
    <div style={{ padding: "1.5rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "1.5rem" }}>
        <div>
          <span style={{ fontSize: "0.75rem", letterSpacing: "0.08em", color: "#748095", fontWeight: 700 }}>LIBRARY</span>
          <h1 style={{ marginTop: "0.35rem" }}>Catalogue</h1>
        </div>
        <Link to="/library/catalogue/new" className="primary-button">
          <Plus size={16} /> Add Book
        </Link>
      </div>

      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem", alignItems: "center" }}>
        <Search size={18} style={{ color: "#748095" }} />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by title, author, ISBN"
          style={{
            flex: 1, padding: "0.6rem 0.75rem", border: "1px solid #d1d5db",
            borderRadius: "6px", fontSize: "0.95rem",
          }}
        />
      </div>

      {error ? <div className="tt-error">{error}</div> : null}

      {loading ? (
        <div style={{ padding: "2rem", textAlign: "center", color: "#748095" }}>Loading…</div>
      ) : books.length === 0 ? (
        <div style={{ padding: "3rem", textAlign: "center", color: "#748095", border: "1px dashed #d1d5db", borderRadius: "10px" }}>
          No books yet.
        </div>
      ) : (
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Authors</th>
                <th>ISBN</th>
                <th>Copies</th>
                <th>Available</th>
              </tr>
            </thead>
            <tbody>
              {books.map((b) => (
                <tr key={b.id}>
                  <td>
                    <Link to={`/library/catalogue/${b.id}`} style={{ color: "#1e3a8a", fontWeight: 600 }}>
                      {b.title}
                    </Link>
                    {b.subtitle ? <div style={{ color: "#748095", fontSize: "0.85rem" }}>{b.subtitle}</div> : null}
                  </td>
                  <td>{b.authors.map((a) => a.name).join(", ") || "—"}</td>
                  <td>{b.isbn || "—"}</td>
                  <td>{b.copy_count}</td>
                  <td>{b.available_copy_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
