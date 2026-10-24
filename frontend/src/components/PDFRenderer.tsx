import { useEffect, useRef, useState, useCallback } from "react";
import * as pdfjsLib from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import {
  ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Loader2,
  AlertCircle, Maximize2, Minimize2, RotateCw, Download,
  Maximize, MoveHorizontal, ScanLine,
} from "lucide-react";
import "./PDFRenderer.css";

pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl;

type Props = {
  src: string;
  title?: string;
  allowDownload?: boolean;
};

type FitMode = "page" | "width" | "manual";

export default function PDFRenderer({ src, title, allowDownload = false }: Props) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [pdf, setPdf] = useState<any>(null);
  const [pageNum, setPageNum] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [zoom, setZoom] = useState(1.15); // used only in manual mode
  const [fitMode, setFitMode] = useState<FitMode>("page");
  const [rotation, setRotation] = useState(0);
  const [containerSize, setContainerSize] = useState({ w: 0, h: 0 });
  const [isFullscreen, setIsFullscreen] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const rootRef = useRef<HTMLDivElement | null>(null);
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
        // Fetch the whole PDF with credentials, then hand raw bytes to pdf.js.
        // This bypasses pdf.js's HEAD/Range probing — our DRF endpoint answers
        // HEAD with 204, confusing pdf.js into thinking the doc is empty.
        const res = await fetch(src, {
          method: "GET",
          credentials: "include",
          cache: "no-store",
          headers: { Accept: "application/pdf,*/*" },
        });
        if (!res.ok) {
          const text = await res.text().catch(() => "");
          throw new Error(`Failed to load PDF (${res.status}): ${text.slice(0, 200)}`);
        }
        const buf = await res.arrayBuffer();
        if (buf.byteLength === 0) {
          throw new Error("Server returned 0 bytes for the PDF. Check the backend [DAM-STREAM] log line.");
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

  // Track container size (window resize + fullscreen transitions)
  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const update = () => {
      setContainerSize({ w: el.clientWidth, h: el.clientHeight });
    };
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    window.addEventListener("resize", update);
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", update);
    };
  }, [pdf]); // re-attach when pdf finishes mounting (wrap exists)

  // Fullscreen state listener
  useEffect(() => {
    const onFs = () => {
      setIsFullscreen(!!document.fullscreenElement);
      // Re-measure after browser finishes the layout
      setTimeout(() => {
        const el = wrapRef.current;
        if (el) setContainerSize({ w: el.clientWidth, h: el.clientHeight });
      }, 100);
    };
    document.addEventListener("fullscreenchange", onFs);
    return () => document.removeEventListener("fullscreenchange", onFs);
  }, []);

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

        // Compute effective scale from fit mode
        const base = page.getViewport({ scale: 1, rotation });
        let effectiveScale: number;
        if (fitMode === "page" && containerSize.w > 0 && containerSize.h > 0) {
          const sx = containerSize.w / base.width;
          const sy = containerSize.h / base.height;
          effectiveScale = Math.min(sx, sy) * 0.97; // 3% margin so borders are visible
        } else if (fitMode === "width" && containerSize.w > 0) {
          effectiveScale = (containerSize.w / base.width) * 0.97;
        } else {
          effectiveScale = zoom;
        }
        effectiveScale = Math.max(0.2, Math.min(4, effectiveScale));

        const viewport = page.getViewport({ scale: effectiveScale, rotation });
        const outputScale = window.devicePixelRatio || 1;

        canvas.width = Math.floor(viewport.width * outputScale);
        canvas.height = Math.floor(viewport.height * outputScale);
        canvas.style.width = `${Math.floor(viewport.width)}px`;
        canvas.style.height = `${Math.floor(viewport.height)}px`;

        const transform = outputScale !== 1 ? [outputScale, 0, 0, outputScale, 0, 0] : undefined;

        const task = page.render({ canvasContext: ctx, viewport, transform } as any);
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
  }, [pdf, pageNum, zoom, rotation, fitMode, containerSize]);

  const goto = useCallback((p: number) => {
    if (!totalPages) return;
    setPageNum(Math.max(1, Math.min(totalPages, p)));
  }, [totalPages]);

  const toggleFullscreen = useCallback(async () => {
    const el = rootRef.current;
    if (!el) return;
    try {
      if (!document.fullscreenElement) {
        await el.requestFullscreen();
      } else {
        await document.exitFullscreen();
      }
    } catch { /* user denied or browser doesn't support */ }
  }, []);

  // Keyboard nav
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement) return;
      if (e.key === "ArrowLeft" || e.key === "PageUp") goto(pageNum - 1);
      if (e.key === "ArrowRight" || e.key === "PageDown") goto(pageNum + 1);
      if (e.key === "+" || e.key === "=") { setFitMode("manual"); setZoom((z) => Math.min(3, z + 0.15)); }
      if (e.key === "-") { setFitMode("manual"); setZoom((z) => Math.max(0.4, z - 0.15)); }
      if (e.key === "f" || e.key === "F") void toggleFullscreen();
      if (e.key === "Escape" && document.fullscreenElement) void document.exitFullscreen();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [goto, pageNum, toggleFullscreen]);

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

  const zoomDisplay = fitMode === "manual"
    ? `${Math.round(zoom * 100)}%`
    : fitMode === "page" ? "Fit page" : "Fit width";

  return (
    <div className="pdfr-root" ref={rootRef}>
      <div className="pdfr-toolbar">
        <div className="pdfr-toolbar-left">
          <button className="pdfr-btn" onClick={() => goto(pageNum - 1)}
                  disabled={pageNum <= 1} title="Previous page">
            <ChevronLeft size={16} />
          </button>
          <span className="pdfr-page-indicator">
            Page{" "}
            <input
              className="pdfr-page-input" type="number" min={1} max={totalPages || 1}
              value={pageNum}
              onChange={(e) => goto(parseInt(e.target.value, 10) || 1)}
            />{" "}
            / {totalPages}
          </span>
          <button className="pdfr-btn" onClick={() => goto(pageNum + 1)}
                  disabled={pageNum >= totalPages} title="Next page">
            <ChevronRight size={16} />
          </button>
        </div>

        <div className="pdfr-toolbar-right">
          <button className={"pdfr-btn" + (fitMode === "page" ? " active" : "")}
                  onClick={() => setFitMode("page")}
                  title="Fit whole page">
            <Maximize size={16} />
          </button>
          <button className={"pdfr-btn" + (fitMode === "width" ? " active" : "")}
                  onClick={() => setFitMode("width")}
                  title="Fit to width">
            <MoveHorizontal size={16} />
          </button>
          <button className={"pdfr-btn" + (fitMode === "manual" ? " active" : "")}
                  onClick={() => setFitMode("manual")}
                  title="Manual zoom">
            <ScanLine size={16} />
          </button>

          <span className="pdfr-divider" />

          <button className="pdfr-btn"
                  onClick={() => { setFitMode("manual"); setZoom((z) => Math.max(0.4, z - 0.15)); }}
                  title="Zoom out">
            <ZoomOut size={16} />
          </button>
          <span className="pdfr-zoom" style={{ minWidth: 72, textAlign: "center", fontWeight: 700 }}>
            {zoomDisplay}
          </span>
          <button className="pdfr-btn"
                  onClick={() => { setFitMode("manual"); setZoom((z) => Math.min(3, z + 0.15)); }}
                  title="Zoom in">
            <ZoomIn size={16} />
          </button>

          <span className="pdfr-divider" />

          <button className="pdfr-btn"
                  onClick={() => setRotation((r) => (r + 90) % 360)}
                  title="Rotate 90°">
            <RotateCw size={16} />
          </button>
          <button className={"pdfr-btn" + (isFullscreen ? " active" : "")}
                  onClick={() => void toggleFullscreen()}
                  title={isFullscreen ? "Exit fullscreen (Esc)" : "Fullscreen (F)"}>
            {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
          </button>
        </div>
      </div>

      <div className="pdfr-canvas-wrap" ref={wrapRef}>
        <canvas ref={canvasRef} className="pdfr-canvas" aria-label={title} />
      </div>

      <style>{`
        .pdfr-root {
          display: flex !important;
          flex-direction: column !important;
          height: 100% !important;
          min-height: 0 !important;
        }
        .pdfr-canvas-wrap {
          flex: 1 !important;
          min-height: 0 !important;
          display: flex !important;
          justify-content: center !important;
          align-items: flex-start !important;
          padding: 14px !important;
          overflow: auto !important;
          background: #eef1f6 !important;
        }
        .pdfr-canvas {
          display: block !important;
          box-shadow: 0 6px 24px rgba(15,23,42,0.18) !important;
          background: #fff !important;
          border-radius: 4px !important;
        }
        .pdfr-btn.active {
          background: #1e3a8a !important;
          color: #fff !important;
          border-color: #1e3a8a !important;
        }
        .pdfr-divider {
          display: inline-block;
          width: 1px;
          height: 20px;
          background: #cbd5e1;
          margin: 0 4px;
        }
        .pdfr-root:fullscreen {
          background: #0f172a !important;
        }
        .pdfr-root:fullscreen .pdfr-canvas-wrap {
          background: #0f172a !important;
        }
        .pdfr-root:fullscreen .pdfr-toolbar {
          background: #1e293b !important;
          border-bottom: 1px solid #334155 !important;
        }
        .pdfr-root:fullscreen .pdfr-btn {
          background: #334155 !important;
          color: #e2e8f0 !important;
          border-color: #475569 !important;
        }
        .pdfr-root:fullscreen .pdfr-btn:hover {
          background: #475569 !important;
          color: #fff !important;
        }
        .pdfr-root:fullscreen .pdfr-btn.active {
          background: #1e3a8a !important;
          color: #fff !important;
          border-color: #1e3a8a !important;
        }
        .pdfr-root:fullscreen .pdfr-page-indicator,
        .pdfr-root:fullscreen .pdfr-zoom {
          color: #e2e8f0 !important;
        }
        @media (prefers-reduced-motion: reduce) {
          .pdfr-canvas { transition: none !important; }
        }
      `}</style>
    </div>
  );
}