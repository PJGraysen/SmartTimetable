import { useEffect, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, ShieldCheck, ShieldAlert, Loader2 } from "lucide-react";
import * as lib from "../../services/library";

export default function BookReaderPage() {
  const { bookId = "" } = useParams();
  const [book, setBook] = useState<lib.Book | null>(null);
  const [loading, setLoading] = useState(true);
  const [blurred, setBlurred] = useState(false);
  const wrapRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!bookId) return;
    lib.getBook(bookId)
      .then(setBook)
      .catch(() => setBook(null))
      .finally(() => setLoading(false));
  }, [bookId]);

  // Screenshot deterrence: blur content when window/tab loses focus.
  useEffect(() => {
    const onBlur = () => setBlurred(true);
    const onFocus = () => setBlurred(false);
    const onVis = () => setBlurred(document.visibilityState !== "visible");
    window.addEventListener("blur", onBlur);
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onVis);
    return () => {
      window.removeEventListener("blur", onBlur);
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onVis);
    };
  }, []);

  // Disable right click, contextmenu, drag on the reading surface.
  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const block = (e: Event) => e.preventDefault();
    el.addEventListener("contextmenu", block);
    el.addEventListener("dragstart", block);
    el.addEventListener("copy", block);
    return () => {
      el.removeEventListener("contextmenu", block);
      el.removeEventListener("dragstart", block);
      el.removeEventListener("copy", block);
    };
  }, []);

  if (loading) {
    return (
      <div style={{ padding: "2rem", color: "#64748b", display: "flex",
                    alignItems: "center", gap: "0.5rem" }}>
        <Loader2 size={18} className="spin" /> Loading reader…
      </div>
    );
  }

  if (!book) {
    return <div style={{ padding: "2rem" }}>Book not found.</div>;
  }

  const asset = book.read_asset;

  if (!asset) {
    return (
      <div style={{ padding: "2rem", maxWidth: 720 }}>
        <Link to={`/library/catalogue/${book.id}`}
              style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem",
                       color: "#1e3a8a", marginBottom: "1rem" }}>
          <ArrowLeft size={16} /> Back to book
        </Link>
        <div style={{ background: "#fef2f2", border: "1px solid #fecaca",
                      borderRadius: 10, padding: "1.25rem", display: "flex",
                      alignItems: "center", gap: "0.6rem", color: "#991b1b" }}>
          <ShieldAlert size={20} />
          <div>
            <div style={{ fontWeight: 700 }}>No digital copy available</div>
            <div style={{ fontSize: "0.85rem" }}>This title exists only as a physical copy. Please visit the circulation desk.</div>
          </div>
        </div>
      </div>
    );
  }

  const stream = lib.resourceStreamUrl(asset.id, "view") + "#toolbar=0&navpanes=0&scrollbar=0";

  return (
    <div style={{ padding: "1rem 1.5rem 1.5rem", height: "calc(100vh - 40px)",
                  display: "flex", flexDirection: "column" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
                    marginBottom: "0.75rem" }}>
        <div>
          <Link to={`/library/catalogue/${book.id}`}
                style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem",
                         color: "#1e3a8a", marginBottom: "0.35rem", fontSize: "0.85rem" }}>
            <ArrowLeft size={16} /> Back to book
          </Link>
          <h1 style={{ margin: 0, fontSize: "1.15rem" }}>{book.title}</h1>
          <div style={{ color: "#64748b", fontSize: "0.8rem", marginTop: "0.15rem" }}>
            {asset.format}
            {asset.read_only ? " · Read only" : ""}
            {asset.allow_download ? " · Download allowed" : " · Download blocked"}
            {asset.allow_print ? " · Print allowed" : " · Print blocked"}
          </div>
        </div>
        <div style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem",
                      background: "#ecfdf5", color: "#065f46", padding: "0.35rem 0.75rem",
                      borderRadius: 6, fontSize: "0.78rem", fontWeight: 700 }}>
          <ShieldCheck size={14} /> Protected view
        </div>
      </div>

      <div
        ref={wrapRef}
        style={{
          flex: 1, position: "relative",
          border: "1px solid #e5e7eb", borderRadius: 10, overflow: "hidden",
          background: "#0f172a",
          userSelect: "none",
          filter: blurred ? "blur(14px)" : "none",
          transition: "filter 120ms ease",
        }}
        onContextMenu={(e) => e.preventDefault()}
      >
        <iframe
          src={stream}
          title={book.title}
          style={{ width: "100%", height: "100%", border: "none" }}
        />
        {asset.watermark_text ? (
          <div aria-hidden="true" style={{
            position: "absolute", inset: 0, pointerEvents: "none",
            display: "flex", alignItems: "center", justifyContent: "center",
            color: "rgba(255,255,255,0.06)", fontSize: "4rem", fontWeight: 900,
            transform: "rotate(-30deg)", letterSpacing: "0.1em",
            textShadow: "0 2px 6px rgba(0,0,0,0.15)",
          }}>
            {asset.watermark_text}
          </div>
        ) : null}
      </div>

      {blurred ? (
        <div style={{ position: "fixed", inset: 0, zIndex: 50, display: "flex",
                      alignItems: "center", justifyContent: "center",
                      color: "#f8fafc", fontWeight: 700, fontSize: "1.1rem",
                      background: "rgba(15,23,42,0.4)" }}>
          Reading paused — click to resume
        </div>
      ) : null}

      <style>{`
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
