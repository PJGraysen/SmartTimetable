import { useEffect, useState } from "react";
import { BookOpen, Bookmark, BookmarkX, Trash2 } from "lucide-react";
import http from "../services/http";

type SavedBook = {
  id: string;
  book_id: string;
  title: string;
  author: string;
  cover_url?: string | null;
  saved_at: string;
};

const STORAGE_KEY = "stp.myLibrary.v1";

function loadSaved(): SavedBook[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch { return []; }
}

function persist(list: SavedBook[]) {
  try { window.localStorage.setItem(STORAGE_KEY, JSON.stringify(list)); } catch {}
}

export default function MyLibraryPage() {
  const [items, setItems] = useState<SavedBook[]>(loadSaved);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Best-effort: sync from backend if endpoint exists
    setLoading(true);
    http.get("/library/my-shelves/")
      .then((r) => {
        if (Array.isArray(r.data)) {
          const merged = [...r.data];
          setItems(merged);
          persist(merged);
        }
      })
      .catch(() => { /* local-only fallback is fine */ })
      .finally(() => setLoading(false));
  }, []);

  function remove(id: string) {
    const next = items.filter((x) => x.id !== id);
    setItems(next);
    persist(next);
    // best-effort backend delete
    http.delete(`/library/my-shelves/${id}/`).catch(() => {});
  }

  return (
    <div className="ml-page">
      <header className="ml-head">
        <div>
          <h1>My Library</h1>
          <p className="ml-sub">
            Books you've saved for quick access and reading.
          </p>
        </div>
        <div className="ml-count">
          <Bookmark size={16} /> {items.length} saved
        </div>
      </header>

      {loading ? (
        <div className="ml-empty">Loading…</div>
      ) : items.length === 0 ? (
        <div className="ml-empty">
          <BookmarkX size={28} />
          <p>No saved books yet.</p>
          <p className="ml-hint">
            Visit the <b>Catalogue</b> and bookmark a book to see it here.
          </p>
        </div>
      ) : (
        <ul className="ml-grid">
          {items.map((b) => (
            <li key={b.id} className="ml-card">
              <div className="ml-cover">
                {b.cover_url ? (
                  <img src={b.cover_url} alt={b.title} />
                ) : (
                  <BookOpen size={28} />
                )}
              </div>
              <div className="ml-meta">
                <div className="ml-title">{b.title}</div>
                <div className="ml-author">{b.author}</div>
                <div className="ml-actions">
                  <button
                    className="ml-btn"
                    onClick={() => window.open(`/library/read/${b.book_id}`, "_blank")}
                  >
                    <BookOpen size={14} /> Read
                  </button>
                  <button
                    className="ml-btn ml-btn-danger"
                    onClick={() => remove(b.id)}
                    title="Remove from My Library"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
