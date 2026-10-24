import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Download, ExternalLink, Loader2, ShieldAlert, FileText } from "lucide-react";
import * as lib from "../../services/library";
import PDFRenderer from "../../components/PDFRenderer";

const LIB_BG =
  "radial-gradient(1400px 600px at 85% -5%, rgba(122,78,42,0.07), transparent 60%)," +
  "radial-gradient(900px 500px at -5% 20%, rgba(30,64,175,0.05), transparent 55%)," +
  "linear-gradient(180deg, #f5ecd9 0%, #ecdfc8 100%)";

export default function ResourceViewerPage() {
  const { id = "" } = useParams();
  const [asset, setAsset] = useState<lib.DigitalAsset | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) return;
    lib.getResource(id)
      .then(setAsset)
      .catch((e) => setError(e?.response?.data?.detail || "Could not load resource."))
      .finally(() => setLoading(false));
  }, [id]);

  const stream = id ? lib.resourceStreamUrlWithToken(id, "view") : "";

  return (
    <div
      style={{
        padding: "1.25rem",
        height: "calc(100vh - 40px)",
        display: "flex",
        flexDirection: "column",
        gap: "1rem",
        background: LIB_BG,
        overflow: "hidden",
      }}
    >
      {/* Header card */}
      <div style={{ flexShrink: 0 }}>
        <Link to="/library/resources" style={backBtn}>
          <ArrowLeft size={15} /> Back to resources
        </Link>

        <div style={headerCard}>
          <div style={{ display: "flex", alignItems: "center", gap: "1rem", minWidth: 0, flex: 1 }}>
            <div style={headerIcon}>
              <FileText size={24} />
            </div>
            <div style={{ minWidth: 0 }}>
              <span style={kicker}>LIBRARY · RESOURCE VIEWER</span>
              <h1 style={{ margin: "0.3rem 0 0", color: "#111827", fontSize: "1.35rem", fontWeight: 800,
                           overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {asset?.title || "Resource"}
              </h1>
              <div style={{ color: "#64748b", fontSize: "0.82rem", marginTop: "0.2rem" }}>
                {asset?.format}
                {asset?.subject ? ` · ${asset.subject.code}` : ""}
                {asset ? ` · ${asset.view_count} views` : ""}
              </div>
            </div>
          </div>

          <div style={{ display: "flex", gap: "0.5rem", flexShrink: 0, flexWrap: "wrap" }}>
            <a href={stream} target="_blank" rel="noreferrer" className="viewer-btn viewer-btn-ghost">
              <ExternalLink size={14} /> Open in browser
            </a>
            {asset?.allow_download ? (
              <a href={lib.resourceStreamUrl(id, "download")}
                 target="_blank" rel="noreferrer" className="viewer-btn viewer-btn-primary">
                <Download size={14} /> Download
              </a>
            ) : null}
          </div>
        </div>
      </div>

      {/* Reader area — fills remaining height */}
      <div style={{
        flex: 1,
        minHeight: 0,
        background: "rgba(255,255,255,0.94)",
        borderRadius: 16,
        border: "1px solid #cbd5e1",
        boxShadow: "0 6px 22px rgba(15,23,42,0.08)",
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
      }}>
        {loading ? (
          <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "#64748b", gap: "0.5rem" }}>
            <Loader2 size={22} className="spin" /> Loading resource…
          </div>
        ) : error ? (
          <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center",
                        color: "#b91c1c", gap: "0.5rem", fontWeight: 600 }}>
            <ShieldAlert size={20} /> {error}
          </div>
        ) : asset?.format === "PDF" ? (
          <PDFRenderer src={stream} title={asset.title} allowDownload={asset.allow_download} />
        ) : (
          <iframe
            src={stream}
            title={asset?.title || "Resource"}
            style={{ flex: 1, width: "100%", border: "none", background: "#fff" }}
          />
        )}
      </div>

      <style>{`
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }

        .viewer-btn {
          display: inline-flex; align-items: center; gap: 0.4rem;
          padding: 0.55rem 0.9rem; border-radius: 8px;
          font-weight: 800; font-size: 0.82rem;
          text-decoration: none; font-family: inherit;
          transition: transform 200ms ease, box-shadow 200ms ease, filter 200ms ease;
        }
        .viewer-btn-primary {
          background: #1e3a8a; color: #fff; border: 2px solid #1e3a8a;
        }
        .viewer-btn-ghost {
          background: rgba(255,255,255,0.9); color: #1e3a8a; border: 2px solid #cbd5e1;
        }
        .viewer-btn:hover {
          transform: translateY(-2px) scale(1.02);
          box-shadow: 0 8px 20px rgba(15,23,42,0.2);
          filter: brightness(1.08);
        }
        .viewer-btn:active { transform: translateY(0) scale(0.99); }

        @media (prefers-reduced-motion: reduce) {
          .viewer-btn { transition: none !important; transform: none !important; }
        }
      `}</style>
    </div>
  );
}

const backBtn: React.CSSProperties = {
  display: "inline-flex", alignItems: "center", gap: "0.35rem",
  padding: "0.5rem 0.9rem", borderRadius: 8,
  background: "rgba(255,255,255,0.9)", border: "1px solid #cbd5e1",
  color: "#1e3a8a", marginBottom: "0.75rem", fontSize: "0.85rem",
  fontWeight: 700, textDecoration: "none",
};
const headerCard: React.CSSProperties = {
  display: "flex", alignItems: "center", justifyContent: "space-between",
  gap: "1rem", flexWrap: "wrap",
  padding: "1rem 1.25rem", borderRadius: 14,
  background: "rgba(255,255,255,0.94)",
  borderLeft: "6px solid #1e3a8a",
  boxShadow: "0 4px 14px rgba(15,23,42,0.06)",
};
const headerIcon: React.CSSProperties = {
  width: 52, height: 52, borderRadius: 12,
  background: "#1e3a8a", color: "#fff",
  display: "flex", alignItems: "center", justifyContent: "center",
  flexShrink: 0, boxShadow: "0 6px 14px rgba(30,58,138,0.3)",
};
const kicker: React.CSSProperties = {
  fontSize: "0.7rem", letterSpacing: "0.08em", color: "#748095", fontWeight: 800,
};