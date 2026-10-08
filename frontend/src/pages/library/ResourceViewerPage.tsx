import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ArrowLeft, Download, ExternalLink, Loader2, ShieldAlert } from "lucide-react";
import * as lib from "../../services/library";
import PDFRenderer from "../../components/PDFRenderer";

export default function ResourceViewerPage() {
  const { id = "" } = useParams();
  const [asset, setAsset] = useState<lib.DigitalAsset | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [frameError, setFrameError] = useState(false);

  useEffect(() => {
    if (!id) return;
    lib.getResource(id)
      .then(setAsset)
      .catch((e) => setError(e?.response?.data?.detail || "Could not load resource."))
      .finally(() => setLoading(false));
  }, [id]);

  const stream = id ? lib.resourceStreamUrlWithToken(id, "view") : "";


  return (
    <div style={{ padding: "1.5rem", height: "calc(100vh - 40px)", display: "flex", flexDirection: "column" }}>
      <div style={{ marginBottom: "1rem" }}>
        <Link
          to="/library/resources"
          style={{
            display: "inline-flex", alignItems: "center", gap: "0.35rem",
            color: "#1e3a8a", marginBottom: "0.5rem",
          }}
        >
          <ArrowLeft size={16} /> Back to resources
        </Link>
        {asset ? (
          <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: "1rem", flexWrap: "wrap" }}>
            <div>
              <h1 style={{ margin: 0 }}>{asset.title}</h1>
              <div style={{ color: "#64748b", fontSize: "0.83rem", marginTop: "0.2rem" }}>
                {asset.format}
                {asset.subject ? " · " + asset.subject.code : ""}
                {" · "}{asset.view_count} views
              </div>
            </div>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <a
                href={stream}
                target="_blank"
                rel="noreferrer"
                style={{
                  display: "inline-flex", alignItems: "center", gap: "0.4rem",
                  padding: "0.55rem 0.9rem", borderRadius: 6,
                  background: "#f1f5f9", color: "#1e3a8a",
                  border: "1px solid #cbd5e1",
                  fontWeight: 700, textDecoration: "none",
                }}
              >
                <ExternalLink size={14} /> Open in browser
              </a>
              {asset.allow_download ? (
                <a
                  href={lib.resourceStreamUrl(id, "download")}
                  target="_blank"
                  rel="noreferrer"
                  style={{
                    display: "inline-flex", alignItems: "center", gap: "0.4rem",
                    padding: "0.55rem 0.9rem", borderRadius: 6,
                    background: "#1e3a8a", color: "#fff",
                    fontWeight: 700, textDecoration: "none",
                  }}
                >
                  <Download size={14} /> Download
                </a>
              ) : null}
            </div>
          </div>
        ) : null}
      </div>

      {loading ? (
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "#64748b" }}>
          <Loader2 size={22} className="spin" />
        </div>
      ) : error ? (
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center",
                      color: "#b91c1c", gap: "0.5rem" }}>
          <ShieldAlert size={20} /> {error}
        </div>
      ) : (
        <div style={{ flex: 1, minHeight: 0 }}>
          {asset?.format === "PDF" ? (
            <PDFRenderer
              src={stream}
              title={asset.title}
              allowDownload={asset.allow_download}
            />
          ) : (
            <iframe
              src={stream}
              title={asset?.title || "Resource"}
              style={{ width: "100%", height: "100%", border: "1px solid #e5e7eb", borderRadius: 10 }}
            />
          )}
        </div>
      )}

      <style>{`
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
