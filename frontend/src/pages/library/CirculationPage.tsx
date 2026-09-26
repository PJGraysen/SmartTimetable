import { useState } from "react";
import { ScanLine, CheckCircle2, AlertTriangle, Loader2 } from "lucide-react";
import * as lib from "../../services/library";
import LibraryTabs from "../../components/library/LibraryTabs";

export default function CirculationPage() {
  const [barcode, setBarcode] = useState("");
  const [memberNumber, setMemberNumber] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; text: string } | null>(null);

  const [bulkBarcodes, setBulkBarcodes] = useState("");
  const [bulkBusy, setBulkBusy] = useState(false);
  const [bulkResults, setBulkResults] = useState<{ barcode: string; ok: boolean; error: string }[]>([]);

  async function doCheckout() {
    if (!barcode || !memberNumber) return;
    setBusy(true); setResult(null);
    try {
      const r = await lib.selfCheckout({ barcode: barcode.trim(), member_number: memberNumber.trim() });
      setResult({ ok: true, text: `${r.book_title} issued to ${r.member_name}. Due ${new Date(r.due_at).toLocaleDateString()}.` });
      setBarcode(""); setMemberNumber("");
    } catch (e: any) {
      setResult({ ok: false, text: e?.response?.data?.error || "Checkout failed." });
    } finally {
      setBusy(false);
    }
  }

  async function doBulkReturn() {
    const barcodes = bulkBarcodes.split(/[\s,]+/).map((s) => s.trim()).filter(Boolean);
    if (!barcodes.length) return;
    setBulkBusy(true); setBulkResults([]);
    try {
      const r = await lib.bulkReturn(barcodes);
      setBulkResults(r.results);
      setBulkBarcodes("");
    } catch (e: any) {
      setBulkResults([{ barcode: "—", ok: false, error: e?.response?.data?.error || "Bulk return failed." }]);
    } finally {
      setBulkBusy(false);
    }
  }

  return (
    <div style={{ padding: "1.5rem", maxWidth: 1100 }}>
      <div style={{ marginBottom: "1rem" }}>
        <span style={{ fontSize: "0.75rem", letterSpacing: "0.08em", color: "#748095", fontWeight: 700 }}>
          LIBRARY MANAGEMENT
        </span>
        <h1 style={{ marginTop: "0.35rem" }}>Circulation Desk</h1>
        <p style={{ color: "#748095" }}>Self-checkout and bulk return.</p>
      </div>

      <LibraryTabs />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(380px, 1fr))", gap: "1.25rem" }}>
        <section style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: "10px", padding: "1.5rem" }}>
          <h2 style={{ marginTop: 0, fontSize: "1.05rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <ScanLine size={18} style={{ color: "#1e3a8a" }} /> Self-checkout
          </h2>
          <p style={{ color: "#748095", fontSize: "0.85rem", marginBottom: "1rem" }}>
            Scan or type the copy barcode and the member number.
          </p>
          <div style={{ marginBottom: "0.75rem" }}>
            <label style={lbl}>Copy barcode</label>
            <input value={barcode} onChange={(e) => setBarcode(e.target.value)} style={inp}
                   placeholder="BK-000123" autoFocus autoComplete="off" />
          </div>
          <div style={{ marginBottom: "1rem" }}>
            <label style={lbl}>Member number</label>
            <input value={memberNumber} onChange={(e) => setMemberNumber(e.target.value)} style={inp}
                   placeholder="STU-001" autoComplete="off" />
          </div>
          <button type="button" onClick={doCheckout} disabled={busy || !barcode || !memberNumber}
                  className="primary-button"
                  style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem" }}>
            {busy ? <Loader2 size={15} className="spin" /> : <CheckCircle2 size={15} />}
            {busy ? "Issuing…" : "Issue loan"}
          </button>
          {result ? (
            <div style={{
              marginTop: "1rem", padding: "0.75rem 1rem", borderRadius: "8px",
              background: result.ok ? "#ecfdf5" : "#fef2f2",
              border: `1px solid ${result.ok ? "#86efac" : "#fecaca"}`,
              color: result.ok ? "#065f46" : "#991b1b", fontSize: "0.85rem",
              display: "flex", alignItems: "center", gap: "0.5rem",
            }}>
              {result.ok ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
              {result.text}
            </div>
          ) : null}
        </section>

        <section style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: "10px", padding: "1.5rem" }}>
          <h2 style={{ marginTop: 0, fontSize: "1.05rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <ScanLine size={18} style={{ color: "#0e7490" }} /> Bulk return
          </h2>
          <p style={{ color: "#748095", fontSize: "0.85rem", marginBottom: "1rem" }}>
            Paste or scan multiple barcodes, one per line or comma-separated.
          </p>
          <textarea
            value={bulkBarcodes}
            onChange={(e) => setBulkBarcodes(e.target.value)}
            rows={6}
            style={{ ...inp, fontFamily: "monospace", resize: "vertical" }}
            placeholder={"BK-000123\nBK-000124\nBK-000125"}
          />
          <button type="button" onClick={doBulkReturn} disabled={bulkBusy || !bulkBarcodes.trim()}
                  className="primary-button"
                  style={{ marginTop: "0.75rem", display: "inline-flex", alignItems: "center", gap: "0.4rem" }}>
            {bulkBusy ? <Loader2 size={15} className="spin" /> : <CheckCircle2 size={15} />}
            {bulkBusy ? "Processing…" : "Return all"}
          </button>

          {bulkResults.length > 0 ? (
            <div style={{ marginTop: "1rem" }}>
              <div style={{ fontSize: "0.78rem", color: "#64748b", marginBottom: "0.4rem" }}>
                {bulkResults.filter((r) => r.ok).length} of {bulkResults.length} returned
              </div>
              <div style={{ maxHeight: 220, overflowY: "auto", border: "1px solid #e5e7eb", borderRadius: "6px" }}>
                {bulkResults.map((r, i) => (
                  <div key={i} style={{
                    display: "flex", alignItems: "center", gap: "0.5rem",
                    padding: "0.4rem 0.6rem", borderBottom: i < bulkResults.length - 1 ? "1px solid #f1f5f9" : "none",
                    fontSize: "0.82rem", color: r.ok ? "#166534" : "#991b1b",
                  }}>
                    {r.ok ? <CheckCircle2 size={13} /> : <AlertTriangle size={13} />}
                    <span style={{ fontFamily: "monospace" }}>{r.barcode}</span>
                    {!r.ok ? <span style={{ color: "#64748b", marginLeft: "auto" }}>{r.error}</span> : null}
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </section>
      </div>

      <style>{`
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}

const lbl: React.CSSProperties = { display: "block", fontSize: "0.75rem", fontWeight: 700, color: "#748095", marginBottom: "0.3rem" };
const inp: React.CSSProperties = { width: "100%", padding: "0.6rem 0.7rem", borderRadius: "6px", border: "1px solid #d1d5db", fontSize: "0.95rem" };
