import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Upload, FileText, Trash2, Loader2, Download, ArrowLeft, BookOpen } from "lucide-react";
import * as lib from "../../services/library";

const CATEGORIES: { value: lib.DigitalAssetCategory; label: string }[] = [
  { value: "PAST_PAPER", label: "Past Papers" },
  { value: "SYLLABUS", label: "Syllabus" },
  { value: "RESEARCH", label: "Research" },
  { value: "NOTES", label: "Lesson Notes" },
  { value: "TEACHER_RESOURCE", label: "Teacher Resources" },
  { value: "EBOOK", label: "E-books" },
  { value: "AUDIOBOOK", label: "Audiobooks" },
  { value: "OTHER", label: "Other" },
];

const CAT_COLOURS: Record<string, string> = {
  PAST_PAPER: "#991b1b", SYLLABUS: "#3730a3", RESEARCH: "#7e22ce", NOTES: "#0e7490",
  TEACHER_RESOURCE: "#a16207", EBOOK: "#1e3a8a", AUDIOBOOK: "#166534", OTHER: "#4d7c0f",
};
const RES_PALETTE = ["#1e3a8a","#0e7490","#166534","#a16207","#7e22ce","#991b1b","#3730a3","#4d7c0f"];
function resourceColour(r: any): string {
  const cat = String(r?.category || "").toUpperCase();
  if (cat && CAT_COLOURS[cat]) return CAT_COLOURS[cat];
  let h = 0;
  const id = String(r?.id || "");
  for (let i = 0; i < id.length; i++) h = ((h * 31) + id.charCodeAt(i)) >>> 0;
  return RES_PALETTE[h % RES_PALETTE.length];
}
function fmtBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}
const LIB_BG =
  "radial-gradient(1400px 600px at 85% -5%, rgba(122,78,42,0.07), transparent 60%)," +
  "radial-gradient(900px 500px at -5% 20%, rgba(30,64,175,0.05), transparent 55%)," +
  "linear-gradient(180deg, #f5ecd9 0%, #ecdfc8 100%)";

export default function ResourcesPage() {
  const [searchParams] = useSearchParams();
  const initialCategory = searchParams.get("category") || "";
  const initialSubject = (searchParams.get("subject") || "").toUpperCase();
  const initialClass = searchParams.get("class") || "";

  const [rows, setRows] = useState<lib.DigitalAsset[]>([]);
  const [subjects, setSubjects] = useState<lib.Subject[]>([]);
  const [q, setQ] = useState("");
  const [category, setCategory] = useState(initialCategory);
  const [subject, setSubject] = useState(initialSubject);
  const [loading, setLoading] = useState(true);

  const [showUpload, setShowUpload] = useState(false);
  const [upTitle, setUpTitle] = useState("");
  const [upDesc, setUpDesc] = useState("");
  const [upCat, setUpCat] = useState<lib.DigitalAssetCategory>(
    (initialCategory as lib.DigitalAssetCategory) || "PAST_PAPER"
  );
  const [upSubj, setUpSubj] = useState("");
  const [upAllowDl, setUpAllowDl] = useState(false);
  const [upAllowPrint, setUpAllowPrint] = useState(false);
  const [upWatermark, setUpWatermark] = useState("");
  const [upFile, setUpFile] = useState<File | null>(null);
  const [upBusy, setUpBusy] = useState(false);
  const [upMsg, setUpMsg] = useState("");
  const fileRef = useRef<HTMLInputElement | null>(null);
  const appliedUrlDefaults = useRef(false);

  async function load() {
    setLoading(true);
    try {
      setRows(await lib.listResources({ q: q || undefined, category: category || undefined, subject: subject || undefined }));
    } finally { setLoading(false); }
  }

  useEffect(() => { void load(); /* eslint-disable-next-line */ }, [q, category, subject]);
  useEffect(() => { lib.getSubjects().then(setSubjects).catch(() => setSubjects([])); }, []);

  useEffect(() => {
    if (appliedUrlDefaults.current || !initialSubject || subjects.length === 0) return;
    const s = subjects.find((x) => x.code.toUpperCase() === initialSubject.toUpperCase());
    if (s) { setUpSubj(s.id); appliedUrlDefaults.current = true; }
  }, [subjects, initialSubject]);

  async function doUpload() {
    if (!upFile || !upTitle) { setUpMsg("Title and file are required."); return; }
    setUpBusy(true); setUpMsg("");
    try {
      const fd = new FormData();
      fd.append("file", upFile);
      fd.append("title", upTitle);
      fd.append("description", upDesc);
      fd.append("category", upCat);
      if (upSubj) fd.append("subject_id", upSubj);
      fd.append("allow_download", upAllowDl ? "true" : "false");
      fd.append("allow_print", upAllowPrint ? "true" : "false");
      fd.append("watermark_text", upWatermark);
      const r = await lib.uploadResource(fd);
      setUpMsg(`Uploaded ${r.format} (${fmtBytes(r.size_bytes)}).`);
      setUpTitle(""); setUpDesc(""); setUpFile(null);
      if (fileRef.current) fileRef.current.value = "";
      await load();
    } catch (e: any) {
      setUpMsg(e?.response?.data?.error || "Upload failed.");
    } finally { setUpBusy(false); }
  }

  async function doDelete(id: string) {
    if (!confirm("Deactivate this resource?")) return;
    try { await lib.deleteResource(id); await load(); } catch {}
  }

  const contextCategory = initialCategory
    ? (CATEGORIES.find((c) => c.value === initialCategory)?.label || initialCategory)
    : null;
  const contextSubject = initialSubject || null;
  const emptyColour = initialCategory ? (CAT_COLOURS[initialCategory] || "#1e3a8a") : "#1e3a8a";
  const showEmptyState = !loading && rows.length === 0;
  const hasContext = !!contextCategory || !!contextSubject;

  return (
    <div style={{ padding: "1.5rem", minHeight: "100vh", background: LIB_BG }}>
      {hasContext ? (
        <Link to={contextSubject ? `/library/subject/${encodeURIComponent(contextSubject)}` : "/library"} style={backBtn}>
          <ArrowLeft size={15} /> Back
        </Link>
      ) : null}

      <div style={hasContext ? { ...contextHeader, borderLeftColor: emptyColour } : plainHeader}>
        <div>
          <span style={kicker}>LIBRARY {contextCategory ? `· ${contextCategory.toUpperCase()}` : "· DIGITAL RESOURCES"}</span>
          <h1 style={{ color: "#111827", fontSize: "1.6rem", fontWeight: 800, margin: "0.35rem 0 0" }}>
            {contextCategory || "Digital Resources"}
          </h1>
          {initialClass ? <span style={{ ...classChip, background: emptyColour }}>Class: {initialClass}</span> : null}
          <p style={{ color: "#748095", marginTop: "0.5rem", marginBottom: 0 }}>
            {contextSubject
              ? `Subject ${contextSubject} · ${rows.length} resource${rows.length === 1 ? "" : "s"}`
              : "Past papers, syllabus, research and teacher resources."}
          </p>
        </div>
        <button type="button" onClick={() => setShowUpload((v) => !v)} className="primary-button"
                style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem", alignSelf: "flex-start" }}>
          <Upload size={15} /> {showUpload ? "Close" : "Upload"}
        </button>
      </div>

      {showUpload ? (
        <section style={uploadPanel}>
          <h3 style={{ marginTop: 0, fontSize: "1rem", color: "#111827" }}>Upload a resource</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "0.75rem" }}>
            <div><label style={lbl}>Title *</label>
              <input value={upTitle} onChange={(e) => setUpTitle(e.target.value)} style={inp} /></div>
            <div><label style={lbl}>Category</label>
              <select value={upCat} onChange={(e) => setUpCat(e.target.value as lib.DigitalAssetCategory)} style={inp}>
                {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select></div>
            <div><label style={lbl}>Subject</label>
              <select value={upSubj} onChange={(e) => setUpSubj(e.target.value)} style={inp}>
                <option value="">(none)</option>
                {subjects.map((s) => <option key={s.id} value={s.id}>{s.code} — {s.name}</option>)}
              </select></div>
            <div><label style={lbl}>Watermark (optional)</label>
              <input value={upWatermark} onChange={(e) => setUpWatermark(e.target.value)} style={inp}
                     placeholder="School Name · Confidential" /></div>
          </div>
          <div style={{ marginTop: "0.75rem" }}>
            <label style={lbl}>Description</label>
            <textarea value={upDesc} onChange={(e) => setUpDesc(e.target.value)} rows={2}
                      style={{ ...inp, resize: "vertical" }} />
          </div>
          <div style={{ display: "flex", gap: "1rem", alignItems: "center", marginTop: "0.75rem", flexWrap: "wrap" }}>
            <label style={checkLbl}><input type="checkbox" checked={upAllowDl} onChange={(e) => setUpAllowDl(e.target.checked)} /> Allow download</label>
            <label style={checkLbl}><input type="checkbox" checked={upAllowPrint} onChange={(e) => setUpAllowPrint(e.target.checked)} /> Allow print</label>
            <input ref={fileRef} type="file" onChange={(e) => setUpFile(e.target.files?.[0] ?? null)} style={{ marginLeft: "auto" }} />
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginTop: "1rem" }}>
            <button type="button" onClick={doUpload} disabled={upBusy || !upFile || !upTitle} className="primary-button"
                    style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem" }}>
              {upBusy ? <Loader2 size={14} className="spin" /> : <Upload size={14} />}
              {upBusy ? "Uploading…" : "Upload"}
            </button>
            {upMsg ? <span style={{ fontSize: "0.83rem", color: "#334155" }}>{upMsg}</span> : null}
          </div>
        </section>
      ) : null}

      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem", flexWrap: "wrap" }}>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search title…"
               style={{ flex: "1 1 240px", padding: "0.6rem 0.75rem", borderRadius: 8,
                        border: "1px solid #d1d5db", background: "#fff", fontFamily: "inherit" }} />
        <select value={category} onChange={(e) => setCategory(e.target.value)}
                style={{ padding: "0.6rem 0.75rem", borderRadius: 8, border: "1px solid #d1d5db",
                         background: "#fff", fontFamily: "inherit" }}>
          <option value="">All categories</option>
          {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
        </select>
        <select value={subject} onChange={(e) => setSubject(e.target.value)}
                style={{ padding: "0.6rem 0.75rem", borderRadius: 8, border: "1px solid #d1d5db",
                         background: "#fff", fontFamily: "inherit" }}>
          <option value="">All subjects</option>
          {subjects.map((s) => <option key={s.id} value={s.code}>{s.code}</option>)}
        </select>
      </div>

      {loading ? (
        <div style={{ padding: "2rem", textAlign: "center", color: "#64748b" }}>Loading…</div>
      ) : showEmptyState ? (
        <div style={emptyStateCard}>
          <div style={{ ...emptyIcon, background: emptyColour }}><FileText size={34} /></div>
          <h3 style={emptyTitle}>
            {contextCategory
              ? `No ${contextCategory}${contextSubject ? ` for ${contextSubject}` : ""} yet`
              : "No resources match those filters"}
          </h3>
          <p style={emptySub}>
            {contextCategory
              ? `Upload a ${contextCategory.toLowerCase()} file, or browse the catalogue to add related textbooks.`
              : "Try clearing filters, or upload the first resource."}
          </p>
          <div style={{ display: "flex", gap: "0.6rem", justifyContent: "center", marginTop: "1.25rem", flexWrap: "wrap" }}>
            <button type="button" onClick={() => setShowUpload(true)} className="primary-button"
                    style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem" }}>
              <Upload size={15} /> Upload resource
            </button>
            <Link to={contextSubject ? `/library/catalogue?subject=${encodeURIComponent(contextSubject)}` : "/library/catalogue"}
                  className="secondary-button"
                  style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem" }}>
              <BookOpen size={15} /> Browse catalogue
            </Link>
          </div>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "1rem" }}>
          {rows.map((r, i) => {
            const colour = resourceColour(r);
            return (
              <div key={r.id} className="res-card"
                   style={{ background: colour, border: `2px solid ${colour}`,
                            borderRadius: 14, padding: "1.25rem", color: "#fff",
                            position: "relative", overflow: "hidden",
                            boxShadow: "0 6px 16px rgba(15,23,42,0.14), inset 0 1px 0 rgba(255,255,255,0.12)",
                            animationDelay: `${Math.min(i * 40, 400)}ms` }}>
                <div style={{ display: "flex", gap: "0.85rem", alignItems: "flex-start", marginBottom: "0.9rem" }}>
                  <div style={{ width: 52, height: 52, borderRadius: 12,
                                background: "rgba(255,255,255,0.2)",
                                border: "1px solid rgba(255,255,255,0.3)",
                                display: "flex", alignItems: "center", justifyContent: "center",
                                fontSize: "0.68rem", fontWeight: 800, letterSpacing: "0.05em",
                                flexShrink: 0 }}>
                    {r.format}
                  </div>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div style={{ fontWeight: 800, color: "#fff", fontSize: "1rem", lineHeight: 1.3, marginBottom: "0.3rem" }}>
                      {r.title}
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.78)" }}>
                      {r.subject ? `${r.subject.code} · ` : ""}{fmtBytes(r.size_bytes)} · {r.view_count} views
                    </div>
                  </div>
                </div>
                <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
                  <Link to={`/library/resources/${r.id}`}
                        style={{ display: "inline-flex", alignItems: "center", gap: "0.35rem",
                                 padding: "0.45rem 0.8rem", borderRadius: 8,
                                 background: "rgba(255,255,255,0.92)", color: colour,
                                 fontWeight: 800, fontSize: "0.78rem", textDecoration: "none",
                                 border: "1px solid rgba(255,255,255,0.4)" }}>
                    Open
                  </Link>
                  {r.allow_download ? (
                    <a href={lib.resourceStreamUrl(r.id, "download")} target="_blank" rel="noreferrer"
                       style={{ display: "inline-flex", alignItems: "center", gap: "0.35rem",
                                padding: "0.45rem 0.7rem", borderRadius: 8,
                                background: "rgba(255,255,255,0.15)", color: "#fff",
                                border: "1px solid rgba(255,255,255,0.28)",
                                fontWeight: 700, fontSize: "0.78rem", textDecoration: "none" }}>
                      <Download size={12} /> Download
                    </a>
                  ) : null}
                  <button type="button" onClick={() => doDelete(r.id)}
                          style={{ marginLeft: "auto", display: "inline-flex", alignItems: "center", gap: "0.35rem",
                                   padding: "0.45rem 0.7rem", borderRadius: 8,
                                   background: "rgba(255,255,255,0.15)", color: "#fff",
                                   border: "1px solid rgba(255,255,255,0.28)",
                                   fontWeight: 700, fontSize: "0.78rem", cursor: "pointer", fontFamily: "inherit" }}>
                    <Trash2 size={12} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <style>{`
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }
        @keyframes resFadeUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
        .res-card { animation: resFadeUp 340ms ease both;
                    transition: transform 240ms cubic-bezier(0.34, 1.56, 0.64, 1),
                                box-shadow 240ms ease, filter 240ms ease;
                    will-change: transform, filter; }
        .res-card:hover { transform: translateY(-6px) scale(1.02);
                          box-shadow: 0 20px 40px rgba(15,23,42,0.28);
                          filter: brightness(1.12) saturate(1.08); }
        .res-card:active { transform: translateY(-1px) scale(0.99); transition-duration: 80ms; }
        @media (prefers-reduced-motion: reduce) {
          .res-card { animation: none !important; transition: none !important; transform: none !important; filter: none !important; }
        }
      `}</style>
    </div>
  );
}

const kicker: React.CSSProperties = { fontSize: "0.75rem", letterSpacing: "0.08em", color: "#748095", fontWeight: 700 };
const backBtn: React.CSSProperties = {
  display: "inline-flex", alignItems: "center", gap: "0.35rem",
  padding: "0.5rem 0.9rem", borderRadius: 8,
  background: "rgba(255,255,255,0.9)", border: "1px solid #cbd5e1",
  color: "#1e3a8a", marginBottom: "1.25rem", fontSize: "0.85rem", fontWeight: 700, textDecoration: "none",
};
const contextHeader: React.CSSProperties = {
  marginBottom: "1.5rem", padding: "1.5rem",
  background: "rgba(255,255,255,0.94)", borderRadius: 16, borderLeft: "6px solid #1e3a8a",
  boxShadow: "0 6px 18px rgba(15,23,42,0.08)",
  display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: "1rem",
};
const plainHeader: React.CSSProperties = {
  marginBottom: "1.5rem",
  display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: "1rem",
};
const classChip: React.CSSProperties = {
  display: "inline-block", marginTop: "0.5rem", fontSize: "0.72rem", fontWeight: 800,
  padding: "0.2rem 0.6rem", color: "#fff", borderRadius: 6,
};
const uploadPanel: React.CSSProperties = {
  background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10,
  padding: "1.25rem", marginBottom: "1.25rem",
};
const emptyStateCard: React.CSSProperties = {
  padding: "3rem 2rem", textAlign: "center",
  background: "rgba(255,255,255,0.94)", borderRadius: 16, border: "2px dashed #cbd5e1",
};
const emptyIcon: React.CSSProperties = {
  width: 72, height: 72, borderRadius: "50%", color: "#fff",
  display: "inline-flex", alignItems: "center", justifyContent: "center",
  marginBottom: "1rem", boxShadow: "0 8px 20px rgba(15,23,42,0.25)",
};
const emptyTitle: React.CSSProperties = { margin: 0, color: "#0f172a", fontSize: "1.25rem", fontWeight: 800 };
const emptySub: React.CSSProperties = {
  color: "#64748b", fontSize: "0.95rem", marginTop: "0.5rem",
  maxWidth: 480, margin: "0.5rem auto 0", lineHeight: 1.5,
};
const lbl: React.CSSProperties = { display: "block", fontSize: "0.72rem", fontWeight: 700, color: "#748095", marginBottom: "0.25rem" };
const inp: React.CSSProperties = {
  width: "100%", padding: "0.55rem 0.65rem", borderRadius: 6,
  border: "1px solid #d1d5db", fontSize: "0.9rem", background: "#fff", fontFamily: "inherit",
};
const checkLbl: React.CSSProperties = { display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.85rem" };