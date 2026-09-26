import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ScanLine, Play, CheckCircle2, Loader2, XCircle } from "lucide-react";
import * as lib from "../../services/library";

export default function AuditsPage() {
  const [rows, setRows] = useState<lib.AuditRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [scanCode, setScanCode] = useState("");
  const [scanning, setScanning] = useState(false);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [active, setActive] = useState<(lib.AuditRow & { lines: lib.AuditLine[] }) | null>(null);
  const scanRef = useRef<HTMLInputElement | null>(null);

  async function load() {
    setLoading(true);
    try { setRows(await lib.listAudits()); } finally { setLoading(false); }
  }
  useEffect(() => { void load(); }, []);
  useEffect(() => {
    if (!activeId) { setActive(null); return; }
    const t = setInterval(() => { lib.getAudit(activeId).then(setActive).catch(() => {}); }, 3000);
    lib.getAudit(activeId).then(setActive).catch(() => {});
    return () => clearInterval(t);
  }, [activeId]);

  async function doStart() {
    setStarting(true);
    try { const r = await lib.startAudit("FULL"); setActiveId(r.id); await load(); }
    finally { setStarting(false); }
  }
  async function doScan(e: React.FormEvent) {
    e.preventDefault();
    if (!activeId || !scanCode.trim()) return;
    setScanning(true);
    try {
      await lib.scanAuditBarcode(activeId, scanCode.trim());
      setScanCode(""); scanRef.current?.focus();
      const r = await lib.getAudit(activeId); setActive(r);
    } finally { setScanning(false); }
  }
  async function doFinish() {
    if (!activeId) return;
    if (!confirm("Finish this audit?")) return;
    await lib.finishAudit(activeId);
    setActiveId(null); await load();
  }

  return (
    <div style={{ padding: "1.5rem", maxWidth: 1200 }}>
      <div style={{ marginBottom: "1rem" }}>
        <span style={{ fontSize: "0.75rem", letterSpacing: "0.08em", color: "#748095", fontWeight: 700 }}>
          LIBRARY MANAGEMENT
        </span>
        <h1 style={{ marginTop: "0.35rem" }}>Inventory Audits</h1>
        <p style={{ color: "#748095" }}>Scan shelves, reconcile, and flag missing or misplaced copies.</p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "1.25rem" }}>
        <section style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, padding: "1.25rem" }}>
          <h2 style={{ marginTop: 0, fontSize: "1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <ScanLine size={18} style={{ color: "#1e3a8a" }} />
            {activeId ? "Live scan" : "Start a new audit"}
          </h2>
          {!activeId ? (
            <>
              <p style={{ color: "#64748b", fontSize: "0.85rem" }}>Snapshots every copy's shelf location.</p>
              <button type="button" onClick={doStart} disabled={starting} className="primary-button"
                      style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem" }}>
                {starting ? <Loader2 size={14} className="spin" /> : <Play size={14} />}
                {starting ? "Starting…" : "Start full audit"}
              </button>
            </>
          ) : (
            <>
              <div style={{ fontSize: "0.78rem", color: "#64748b", marginBottom: "0.5rem" }}>
                {active?.lines.filter((l) => l.scanned_at).length ?? 0} scanned ·{" "}
                {active?.lines.filter((l) => l.result === "MISSING").length ?? 0} missing
              </div>
              <form onSubmit={doScan} style={{ display: "flex", gap: "0.4rem" }}>
                <input ref={scanRef} value={scanCode} onChange={(e) => setScanCode(e.target.value)}
                       autoFocus placeholder="Scan or type barcode, then Enter"
                       style={{ flex: 1, padding: "0.75rem 0.9rem", borderRadius: 6,
                                border: "1px solid #d1d5db", fontSize: "1rem", fontFamily: "monospace" }} />
                <button type="submit" disabled={scanning || !scanCode.trim()} className="primary-button">
                  {scanning ? <Loader2 size={14} className="spin" /> : <ScanLine size={14} />}
                </button>
              </form>
              <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.75rem" }}>
                <button type="button" onClick={doFinish} className="primary-button">Finish audit</button>
                <button type="button" onClick={() => setActiveId(null)}
                        style={{ ...btnGhost, color: "#64748b" }}>
                  <XCircle size={13} /> Close
                </button>
              </div>
              {active ? (
                <div style={{ marginTop: "1rem", maxHeight: 380, overflowY: "auto",
                              border: "1px solid #e5e7eb", borderRadius: 6 }}>
                  {active.lines.slice(0, 200).map((l) => (
                    <div key={l.id} style={{ display: "flex", gap: "0.5rem", padding: "0.45rem 0.6rem",
                                             borderBottom: "1px solid #f1f5f9", fontSize: "0.82rem",
                                             color: l.result === "MISSING" ? "#b91c1c"
                                                  : l.result === "MISPLACED" ? "#a16207"
                                                  : l.result === "UNKNOWN" ? "#7c3aed" : "#166534" }}>
                      <span style={{ fontFamily: "monospace", width: 130 }}>{l.barcode || "—"}</span>
                      <span style={{ flex: 1 }}>{l.book_title}</span>
                      <span style={{ fontWeight: 700 }}>{l.result}</span>
                    </div>
                  ))}
                </div>
              ) : null}
            </>
          )}
        </section>

        <section style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, padding: "1.25rem" }}>
          <h2 style={{ marginTop: 0, fontSize: "1rem" }}>Audit history</h2>
          {loading ? <div style={{ color: "#64748b" }}>Loading…</div>
            : rows.length === 0 ? <div style={{ color: "#64748b", fontSize: "0.85rem" }}>No audits yet.</div>
            : <div style={{ maxHeight: 480, overflowY: "auto" }}>
                {rows.map((r) => (
                  <Link key={r.id} to="#" onClick={(e) => { e.preventDefault(); setActiveId(r.id); }}
                        style={{ display: "block", padding: "0.55rem 0", borderBottom: "1px solid #f1f5f9",
                                 textDecoration: "none", color: "inherit" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem" }}>
                      <span style={{ fontWeight: 700 }}>{new Date(r.started_at).toLocaleString()}</span>
                      <span style={{ color: r.status === "OPEN" ? "#0284c7" : "#166534", fontWeight: 700 }}>{r.status}</span>
                    </div>
                    <div style={{ fontSize: "0.75rem", color: "#64748b", marginTop: "0.15rem" }}>
                      {r.total_scanned}/{r.total_expected} · {r.total_missing} missing · {r.total_misplaced} misplaced
                    </div>
                  </Link>
                ))}
              </div>}
        </section>
      </div>

      <style>{`
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}

const btnGhost: React.CSSProperties = {
  display: "inline-flex", alignItems: "center", gap: "0.3rem",
  fontSize: "0.8rem", padding: "0.55rem 0.9rem", borderRadius: 6,
  background: "#f1f5f9", color: "#1e3a8a", border: "1px solid #cbd5e1",
  fontWeight: 700, cursor: "pointer",
};
