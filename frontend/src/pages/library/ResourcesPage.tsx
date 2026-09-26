import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Upload, FileText, Trash2, Loader2, Download } from "lucide-react";
import * as lib from "../../services/library";
import LibraryTabs from "../../components/library/LibraryTabs";

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

function fmtBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export default function ResourcesPage() {
  const [rows, setRows] = useState<lib.DigitalAsset[]>([]);
  const [subjects, setSubjects] = useState<lib.Subject[]>([]);
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [subject, setSubject] = useState("");
  const [loading, setLoading] = useState(true);

  const [showUpload, setShowUpload] = useState(false);
  const [upTitle, setUpTitle] = useState("");
  const [upDesc, setUpDesc] = useState("");
  const [upCat, setUpCat] = useState<lib.DigitalAssetCategory>("PAST_PAPER");
  const [upSubj, setUpSubj] = useState("");
  const [upAllowDl, setUpAllowDl] = useState(false);
  const [upAllowPrint, setUpAllowPrint] = useState(false);
  const [upWatermark, setUpWatermark] = useState("");
  const [upFile, setUpFile] = useState<File | null>(null);
  const [upBusy, setUpBusy] = useState(false);
  const [upMsg, setUpMsg] = useState("");
  const fileRef = useRef<HTMLInputElement | null>(null);

  async function load() {
    setLoading(true);
    try {
      setRows(await lib.listResources({ q: q || undefined, category: category || undefined, subject: subject || undefined }));
    } finally { setLoading(false); }
  }

  useEffect(() => { void load(); /* eslint-disable-next-line */ }, [q, category, subject]);
  useEffect(() => { lib.getSubjects().then(setSubjects).catch(() => setSubjects([])); }, []);

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

  return (
    <div style={{ padding: "1.5rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "1rem" }}>
        <div>
          <span style={{ fontSize: "0.75rem", letterSpacing: "0.08em", color: "#748095", fontWeight: 700 }}>
            LIBRARY MANAGEMENT
          </span>
          <h1 style={{ marginTop: "0.35rem" }}>Digital Resources</h1>
          <p style={{ color: "#748095" }}>Past papers, syllabus, research and teacher resources.</p>
        </div>
        <button type="button" onClick={() => setShowUpload((v) => !v)} className="primary-button"
                style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem", alignSelf: "flex-start" }}>
          <Upload size={15} /> {showUpload ? "Close" : "Upload"}
        </button>
      </div>

      <LibraryTabs />

      {showUpload ? (
        <section style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: "10px",
                          padding: "1.25rem", marginBottom: "1.25rem" }}>
          <h3 style={{ marginTop: 0, fontSize: "1rem", color: "#111827" }}>Upload a resource</h3>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "0.75rem" }}>
            <div>
              <label style={lbl}>Title *</label>
              <input value={upTitle} onChange={(e) => setUpTitle(e.target.value)} style={inp} />
            </div>
            <div>
              <label style={lbl}>Category</label>
              <select value={upCat} onChange={(e) => setUpCat(e.target.value as lib.DigitalAssetCategory)} style={inp}>
                {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
              </select>
            </div>
            <div>
              <label style={lbl}>Subject</label>
              <select value={upSubj} onChange={(e) => setUpSubj(e.target.value)} style={inp}>
                <option value="">(none)</option>
                {subjects.map((s) => <option key={s.id} value={s.id}>{s.code} — {s.name}</option>)}
              </select>
            </div>
            <div>
              <label style={lbl}>Watermark text (optional)</label>
              <input value={upWatermark} onChange={(e) => setUpWatermark(e.target.value)} style={inp}
                     placeholder="School Name · Confidential" />
            </div>
          </div>
          <div style={{ marginTop: "0.75rem" }}>
            <label style={lbl}>Description</label>
            <textarea value={upDesc} onChange={(e) => setUpDesc(e.target.value)} rows={2}
                      style={{ ...inp, resize: "vertical" }} />
          </div>
          <div style={{ display: "flex", gap: "1rem", alignItems: "center", marginTop: "0.75rem", flexWrap: "wrap" }}>
            <label style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.85rem" }}>
              <input type="checkbox" checked={upAllowDl} onChange={(e) => setUpAllowDl(e.target.checked)} />
              Allow download
            </label>
            <label style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.85rem" }}>
              <input type="checkbox" checked={upAllowPrint} onChange={(e) => setUpAllowPrint(e.target.checked)} />
              Allow print
            </label>
            <input ref={fileRef} type="file" onChange={(e) => setUpFile(e.target.files?.[0] ?? null)}
                   style={{ marginLeft: "auto" }} />
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "1rem", marginTop: "1rem" }}>
            <button type="button" onClick={doUpload} disabled={upBusy || !upFile || !upTitle}
                    className="primary-button"
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
               style={{ flex: "1 1 240px", padding: "0.6rem 0.75rem", borderRadius: "6px", border: "1px solid #d1d5db" }} />
        <select value={category} onChange={(e) => setCategory(e.target.value)}
                style={{ padding: "0.6rem 0.75rem", borderRadius: "6px", border: "1px solid #d1d5db" }}>
          <option value="">All categories</option>
          {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
        </select>
        <select value={subject} onChange={(e) => setSubject(e.target.value)}
                style={{ padding: "0.6rem 0.75rem", borderRadius: "6px", border: "1px solid #d1d5db" }}>
          <option value="">All subjects</option>
          {subjects.map((s) => <option key={s.id} value={s.code}>{s.code}</option>)}
        </select>
      </div>

      {loading ? (
        <div style={{ padding: "2rem", textAlign: "center", color: "#64748b" }}>Loading…</div>
      ) : rows.length === 0 ? (
        <div style={{ padding: "2rem", background: "#f8fafc", borderRadius: "10px",
                      textAlign: "center", color: "#64748b" }}>
          <FileText size={28} style={{ color: "#94a3b8", marginBottom: "0.5rem" }} />
          <div>No resources yet. Click Upload to add the first one.</div>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "1rem" }}>
          {rows.map((r) => (
            <div key={r.id} style={{ background: "#fff", border: "1px solid #e5e7eb",
                                     borderRadius: "10px", padding: "1rem" }}>
              <div style={{ display: "flex", gap: "0.6rem", alignItems: "flex-start" }}>
                <div style={{ width: 40, height: 40, borderRadius: 8, background: "#1e3a8a",
                              color: "#fff", display: "flex", alignItems: "center",
                              justifyContent: "center", fontSize: "0.7rem", fontWeight: 800 }}>
                  {r.format}
                </div>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ fontWeight: 700, color: "#111827", fontSize: "0.92rem" }}>{r.title}</div>
                  <div style={{ fontSize: "0.72rem", color: "#64748b", marginTop: "0.2rem" }}>
                    {r.subject ? r.subject.code + " · " : ""}{fmtBytes(r.size_bytes)} · {r.view_count} views
                  </div>
                </div>
              </div>
              <div style={{ display: "flex", gap: "0.4rem", marginTop: "0.75rem" }}>
                <Link to={`/library/resources/${r.id}`} className="primary-button"
                      style={{ fontSize: "0.78rem", padding: "0.35rem 0.7rem" }}>
                  Open
                </Link>
                {r.allow_download ? (
                  <a href={lib.resourceStreamUrl(r.id, "download")} target="_blank" rel="noreferrer"
                     style={btnGhost}>
                    <Download size={12} /> Download
                  </a>
                ) : null}
                <button type="button" onClick={() => doDelete(r.id)} style={btnGhostDanger}>
                  <Trash2 size={12} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <style>{`
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}

const lbl: React.CSSProperties = { display: "block", fontSize: "0.72rem", fontWeight: 700,
                                    color: "#748095", marginBottom: "0.25rem" };
const inp: React.CSSProperties = { width: "100%", padding: "0.55rem 0.65rem", borderRadius: "6px",
                                    border: "1px solid #d1d5db", fontSize: "0.9rem" };
const btnGhost: React.CSSProperties = { display: "inline-flex", alignItems: "center", gap: "0.3rem",
  fontSize: "0.78rem", padding: "0.35rem 0.7rem", borderRadius: 6,
  background: "#f1f5f9", color: "#1e3a8a", border: "1px solid #cbd5e1", textDecoration: "none",
  fontWeight: 700 };
const btnGhostDanger: React.CSSProperties = { ...btnGhost, color: "#b91c1c", marginLeft: "auto" };
