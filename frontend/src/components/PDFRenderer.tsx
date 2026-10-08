import { useEffect, useRef, useState, useCallback } from "react";
import * as pdfjsLib from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import {
  ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Loader2,
  AlertCircle, Maximize2, RotateCw, Download,
} from "lucide-react";
import "./PDFRenderer.css";

pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl;

type Props = {
  src: string;
  title?: string;
  allowDownload?: boolean;
};

export default function PDFRenderer({ src, title, allowDownload = false }: Props) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [pdf, setPdf] = useState<any>(null);
  const [pageNum, setPageNum] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [zoom, setZoom] = useState(1.15);
  const [rotation, setRotation] = useState(0);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const renderTaskRef = useRef<any>(null);

  // Load PDF
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    setPdf(null);
    setTotalPages(0);
    setPageNum(1);

    (async () => {
      try {
        // Fetch the whole PDF ourselves with credentials, then hand the
        // raw bytes to pdf.js. This bypasses pdf.js's own HEAD/Range
        // probing, which our DRF endpoint answers with 204 on HEAD —
        // confusing pdf.js into thinking the document is empty.
        const res = await fetch(src, {
          method: "GET",
          credentials: "include",
          cache: "no-store",
          headers: { Accept: "application/pdf,*/*" },
        });
        const contentLength = res.headers.get("content-length");
        const contentType = res.headers.get("content-type");
        // eslint-disable-next-line no-console
        console.log(
          "[PDFRenderer] GET",
          src,
          "-> status:", res.status,
          "type:", contentType,
          "length:", contentLength,
        );
        if (!res.ok) {
          const text = await res.text().catch(() => "");
          throw new Error(
            `Failed to load PDF (${res.status}): ${text.slice(0, 200)}`,
          );
        }
        const buf = await res.arrayBuffer();
        // eslint-disable-next-line no-console
        console.log("[PDFRenderer] received bytes:", buf.byteLength);
        if (buf.byteLength === 0) {
          throw new Error(
            "Server returned 0 bytes for the PDF. " +
            "Check the backend [DAM-STREAM] log line.",
          );
        }
        if (cancelled) return;

        const loadingTask = pdfjsLib.getDocument({ data: buf });
        const doc = await loadingTask.promise;
        if (cancelled) return;
        setPdf(doc);
        setTotalPages(doc.numPages);
      } catch (e: any) {
        if (!cancelled) setError(e?.message || "Could not load PDF");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
      if (renderTaskRef.current) {
        try { renderTaskRef.current.cancel(); } catch { /* noop */ }
      }
    };
  }, [src]);

  // Render current page
  useEffect(() => {
    if (!pdf || !canvasRef.current) return;
    let cancelled = false;

    (async () => {
      try {
        if (renderTaskRef.current) {
          try { renderTaskRef.current.cancel(); } catch { /* noop */ }
        }

        const page = await pdf.getPage(pageNum);
        if (cancelled) return;

        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        const viewport = page.getViewport({ scale: zoom, rotation });
        const outputScale = window.devicePixelRatio || 1;

        canvas.width = Math.floor(viewport.width * outputScale);
        canvas.height = Math.floor(viewport.height * outputScale);
        canvas.style.width = `${Math.floor(viewport.width)}px`;
        canvas.style.height = `${Math.floor(viewport.height)}px`;

        const transform = outputScale !== 1
          ? [outputScale, 0, 0, outputScale, 0, 0]
          : undefined;

        const task = page.render({
          canvasContext: ctx,
          viewport,
          transform,
        } as any);
        renderTaskRef.current = task;
        await task.promise;
        renderTaskRef.current = null;
      } catch (e: any) {
        if (e?.name !== "RenderingCancelledException" && !cancelled) {
          setError(e?.message || "Render failed");
        }
      }
    })();

    return () => { cancelled = true; };
  }, [pdf, pageNum, zoom, rotation]);

  const goto = useCallback((p: number) => {
    if (!totalPages) return;
    setPageNum(Math.max(1, Math.min(totalPages, p)));
  }, [totalPages]);

  // Keyboard nav
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement) return;
      if (e.key === "ArrowLeft" || e.key === "PageUp") goto(pageNum - 1);
      if (e.key === "ArrowRight" || e.key === "PageDown") goto(pageNum + 1);
      if (e.key === "+" || e.key === "=") setZoom((z) => Math.min(3, z + 0.15));
      if (e.key === "-") setZoom((z) => Math.max(0.4, z - 0.15));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [goto, pageNum]);

  if (loading) {
    return (
      <div className="pdfr-state">
        <Loader2 className="pdfr-spin" size={28} />
        <p>Loading document…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="pdfr-state pdfr-state-error">
        <AlertCircle size={28} />
        <p>{error}</p>
        {allowDownload && (
          <a className="pdfr-fallback" href={src} download>
            <Download size={14} /> Download instead
          </a>
        )}
      </div>
    );
  }

  return (
    <div className="pdfr-root">
      <div className="pdfr-toolbar">
        <div className="pdfr-toolbar-left">
          <button
            className="pdfr-btn"
            onClick={() => goto(pageNum - 1)}
            disabled={pageNum <= 1}
            title="Previous page"
          >
            <ChevronLeft size={16} />
          </button>
          <span className="pdfr-page-indicator">
            Page{" "}
            <input
              className="pdfr-page-input"
              type="number"
              min={1}
              max={totalPages || 1}
              value={pageNum}
              onChange={(e) => goto(parseInt(e.target.value, 10) || 1)}
            />{" "}
            / {totalPages}
          </span>
          <button
            className="pdfr-btn"
            onClick={() => goto(pageNum + 1)}
            disabled={pageNum >= totalPages}
            title="Next page"
          >
            <ChevronRight size={16} />
          </button>
        </div>

        <div className="pdfr-toolbar-right">
          <button
            className="pdfr-btn"
            onClick={() => setZoom((z) => Math.max(0.4, z - 0.15))}
            title="Zoom out"
          >
            <ZoomOut size={16} />
          </button>
          <span className="pdfr-zoom">{Math.round(zoom * 100)}%</span>
          <button
            className="pdfr-btn"
            onClick={() => setZoom((z) => Math.min(3, z + 0.15))}
            title="Zoom in"
          >
            <ZoomIn size={16} />
          </button>
          <button
            className="pdfr-btn"
            onClick={() => setRotation((r) => (r + 90) % 360)}
            title="Rotate 90°"
          >
            <RotateCw size={16} />
          </button>
          <button
            className="pdfr-btn"
            onClick={() => { setZoom(1.15); setRotation(0); }}
            title="Reset"
          >
            <Maximize2 size={16} />
          </button>
        </div>
      </div>

      <div className="pdfr-canvas-wrap" ref={wrapRef}>
        <canvas ref={canvasRef} className="pdfr-canvas" aria-label={title} />
      </div>
    </div>
  );
}
