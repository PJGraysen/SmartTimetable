import { useEffect, useMemo, useState } from "react";
import {
  ScanLine, CheckCircle2, AlertTriangle, Loader2,
  GraduationCap, BookOpen, Library, ChevronRight,
} from "lucide-react";
import * as lib from "../../services/library";

const LIB_BG =
  "radial-gradient(1400px 600px at 85% -5%, rgba(122,78,42,0.07), transparent 60%)," +
  "radial-gradient(900px 500px at -5% 20%, rgba(30,64,175,0.05), transparent 55%)," +
  "linear-gradient(180deg, #f5ecd9 0%, #ecdfc8 100%)";

const CLASSES = ["G7","G8","G9E","G9W","G10E","G10W","G11E","G11W","F3","F4E","F4W"];
type MemberRow = Awaited<ReturnType<typeof lib.listMembers>>[number];
type CopyRow   = Awaited<ReturnType<typeof lib.listCopiesByBook>>[number];
type LoanRow   = Awaited<ReturnType<typeof lib.listActiveLoans>>[number];
type BookRow   = lib.CatalogueSearchRow;

export default function CirculationPage() {
  const [members, setMembers] = useState<MemberRow[]>([]);
  const [subjects, setSubjects] = useState<lib.Subject[]>([]);
  const [membersLoading, setMembersLoading] = useState(true);

  const [issueClass, setIssueClass] = useState("");
  const [issueSubject, setIssueSubject] = useState("");
  const [issueBookSearch, setIssueBookSearch] = useState("");
  const [issueBooks, setIssueBooks] = useState<BookRow[]>([]);
  const [booksLoading, setBooksLoading] = useState(false);
  const [pickedBook, setPickedBook] = useState<BookRow | null>(null);
  const [copies, setCopies] = useState<CopyRow[]>([]);
  const [copiesLoading, setCopiesLoading] = useState(false);
  const [pickedCopy, setPickedCopy] = useState<CopyRow | null>(null);
  const [pickedMember, setPickedMember] = useState<MemberRow | null>(null);
  const [manualBarcode, setManualBarcode] = useState("");
  const [manualMember, setManualMember] = useState("");
  const [issueBusy, setIssueBusy] = useState(false);
  const [issueResult, setIssueResult] = useState<{ ok: boolean; text: string } | null>(null);

  const [returnMode, setReturnMode] = useState<"browse" | "scan">("browse");
  const [returnClass, setReturnClass] = useState("");
  const [returnMember, setReturnMember] = useState<MemberRow | null>(null);
  const [returnLoans, setReturnLoans] = useState<LoanRow[]>([]);
  const [returnLoansLoading, setReturnLoansLoading] = useState(false);
  const [checkedLoans, setCheckedLoans] = useState<Set<string>>(new Set());
  const [bulkBarcodes, setBulkBarcodes] = useState("");
  const [returnBusy, setReturnBusy] = useState(false);
  const [returnResults, setReturnResults] = useState<{ barcode: string; ok: boolean; error: string }[]>([]);

  useEffect(() => {
    Promise.all([lib.listMembers().catch(() => []), lib.getSubjects().catch(() => [])])
      .then(([m, s]) => { setMembers(m); setSubjects(s); })
      .finally(() => setMembersLoading(false));
  }, []);

  const norm = (s?: string) => (s || "").toUpperCase().replace(/\s+/g, "");
  const filteredMembers = useMemo(
    () => (issueClass ? members.filter((m) => norm(m.class_name) === norm(issueClass)) : members),
    [members, issueClass],
  );
  const filteredReturnMembers = useMemo(
    () => (returnClass ? members.filter((m) => norm(m.class_name) === norm(returnClass)) : members),
    [members, returnClass],
  );

  useEffect(() => {
    setBooksLoading(true);
    const t = setTimeout(() => {
      lib.catalogueSearch({ subject: issueSubject || undefined, q: issueBookSearch || undefined })
        .then((r) => setIssueBooks(r.results))
        .catch(() => setIssueBooks([]))
        .finally(() => setBooksLoading(false));
    }, 300);
    return () => clearTimeout(t);
  }, [issueSubject, issueBookSearch]);

  useEffect(() => {
    if (!pickedBook) { setCopies([]); setPickedCopy(null); return; }
    setCopiesLoading(true);
    lib.listCopiesByBook(pickedBook.id)
      .then(setCopies)
      .catch(() => setCopies([]))
      .finally(() => setCopiesLoading(false));
  }, [pickedBook]);

  useEffect(() => {
    if (!returnMember) { setReturnLoans([]); setCheckedLoans(new Set()); return; }
    setReturnLoansLoading(true);
    lib.listActiveLoans({ member: returnMember.id })
      .then(setReturnLoans)
      .catch(() => setReturnLoans([]))
      .finally(() => setReturnLoansLoading(false));
  }, [returnMember]);

  async function doIssue() {
    const barcode = pickedCopy?.barcode || manualBarcode.trim();
    const memberNumber = pickedMember?.member_number || manualMember.trim();
    if (!barcode || !memberNumber) return;
    setIssueBusy(true); setIssueResult(null);
    try {
      const r = await lib.selfCheckout({ barcode, member_number: memberNumber });
      setIssueResult({ ok: true, text: `${r.book_title} issued to ${r.member_name}. Due ${new Date(r.due_at).toLocaleDateString()}.` });
      setPickedBook(null); setPickedCopy(null); setPickedMember(null);
      setManualBarcode(""); setManualMember("");
    } catch (e: any) {
      setIssueResult({ ok: false, text: e?.response?.data?.error || "Checkout failed." });
    } finally { setIssueBusy(false); }
  }

  async function runReturn(barcodes: string[]) {
    setReturnBusy(true); setReturnResults([]);
    try {
      const r = await lib.bulkReturn(barcodes);
      setReturnResults(r.results);
      if (returnMember) {
        const fresh = await lib.listActiveLoans({ member: returnMember.id }).catch(() => returnLoans);
        setReturnLoans(fresh);
        setCheckedLoans(new Set());
      }
    } catch (e: any) {
      setReturnResults([{ barcode: "—", ok: false, error: e?.response?.data?.error || "Bulk return failed." }]);
    } finally { setReturnBusy(false); }
  }

  function doReturnChecked() {
    const selected = returnLoans.filter((l) => checkedLoans.has(l.id));
    const barcodes = selected.map((l) => {
      const anyL = l as any;
      if (anyL.copy_barcode) return anyL.copy_barcode as string;
      if (anyL.copy && typeof anyL.copy === "object" && anyL.copy.barcode) return anyL.copy.barcode as string;
      return null;
    }).filter((x): x is string => !!x);
    if (selected.length === 0) { alert("Select at least one loan first."); return; }
    if (barcodes.length === 0) { alert("Selected loans have no barcode — open DevTools console."); return; }
    void runReturn(barcodes);
  }

  function doReturnScan() {
    const barcodes = bulkBarcodes.split(/[\s,]+/).map((s) => s.trim()).filter(Boolean);
    if (barcodes.length) void runReturn(barcodes);
  }

  const availableCopies = copies.filter((c) => c.is_available !== false);

  return (
    <div style={{ padding: "1.5rem", minHeight: "100vh", background: LIB_BG }}>
      <div style={pageHeader}>
        <span style={kicker}>LIBRARY MANAGEMENT</span>
        <h1 style={{ margin: "0.35rem 0 0", color: "#111827", fontSize: "1.6rem", fontWeight: 800 }}>Circulation Desk</h1>
        <p style={{ margin: "0.25rem 0 0", color: "#748095", fontSize: "0.9rem" }}>
          Cascade filters to issue; browse or scan to return.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(440px, 1fr))", gap: "1.25rem" }}>

        {/* ISSUE */}
        <section style={{ ...card, borderLeftColor: "#1e3a8a" }}>
          <div style={cardHead}>
            <div style={{ ...cardIcon, background: "#1e3a8a" }}><ScanLine size={18} /></div>
            <div>
              <div style={cardTitle}>Issue a resource</div>
              <div style={cardSub}>Class → Subject → Book → Copy → Member.</div>
            </div>
          </div>

          <div style={cascadeRow}>
            <Select label="Class" value={issueClass} onChange={setIssueClass}
                    options={[{ v: "", l: "All classes" }, ...CLASSES.map((c) => ({ v: c, l: c }))]}
                    Icon={GraduationCap} />
            <Select label="Subject" value={issueSubject} onChange={setIssueSubject}
                    options={[{ v: "", l: "All subjects" }, ...subjects.map((s) => ({ v: s.code, l: `${s.code} — ${s.name}` }))]}
                    Icon={BookOpen} />
          </div>

          <div style={{ marginBottom: "0.9rem" }}>
            <Label>Search books</Label>
            <input value={issueBookSearch} onChange={(e) => setIssueBookSearch(e.target.value)}
                   style={inp} placeholder="Title or author…" />
          </div>

          <div style={listPanel}>
            {booksLoading ? (
              <div style={listEmpty}><Loader2 size={14} className="spin" /> Loading books…</div>
            ) : issueBooks.length === 0 ? (
              <div style={listEmpty}>No books match those filters.</div>
            ) : issueBooks.slice(0, 15).map((b) => {
              const active = pickedBook?.id === b.id;
              return (
                <button key={b.id} onClick={() => setPickedBook(active ? null : b)}
                        style={{ ...listRow, background: active ? "#eef2ff" : "#fff", borderColor: active ? "#93c5fd" : "#e5e7eb" }}>
                  <div style={{ flex: 1, minWidth: 0, textAlign: "left" }}>
                    <div style={listRowTitle}>{b.title}</div>
                    <div style={listRowSub}>
                      {b.authors.length ? b.authors.map((a) => a.name).join(", ") : "—"}
                      {" · "}{b.available_copy_count}/{b.copy_count} available
                    </div>
                  </div>
                  <ChevronRight size={14} style={{ color: active ? "#1e3a8a" : "#94a3b8", flexShrink: 0 }} />
                </button>
              );
            })}
          </div>

          {pickedBook ? (
            <div style={{ marginTop: "1rem" }}>
              <Label>Available copies · {pickedBook.title}</Label>
              {copiesLoading ? (
                <div style={listEmpty}><Loader2 size={14} className="spin" /> Loading copies…</div>
              ) : availableCopies.length === 0 ? (
                <div style={listEmpty}>No available copies for this title.</div>
              ) : (
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem" }}>
                  {availableCopies.map((c) => {
                    const active = pickedCopy?.id === c.id;
                    return (
                      <button key={c.id} onClick={() => setPickedCopy(active ? null : c)}
                              style={{ ...barcodeChip, background: active ? "#1e3a8a" : "#fff", color: active ? "#fff" : "#1e3a8a", borderColor: active ? "#1e3a8a" : "#cbd5e1" }}>
                        {c.barcode}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          ) : null}

          <div style={{ marginTop: "1rem" }}>
            <Label>Member {issueClass ? `· filtered to ${issueClass}` : ""}</Label>
            <select value={pickedMember?.id || ""}
                    onChange={(e) => setPickedMember(filteredMembers.find((x) => x.id === e.target.value) || null)}
                    style={inp}>
              <option value="">
                {membersLoading ? "Loading members…" : filteredMembers.length === 0 ? "No members in this class" : "Select a member…"}
              </option>
              {filteredMembers.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.member_number} · {m.full_name || "Unnamed"}
                </option>
              ))}
            </select>
          </div>

          <details style={{ marginTop: "0.75rem" }}>
            <summary style={detailsSummary}>Scan manually instead</summary>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.6rem", marginTop: "0.6rem" }}>
              <input value={manualBarcode} onChange={(e) => setManualBarcode(e.target.value)}
                     style={{ ...inp, fontFamily: "monospace" }} placeholder="BK-000123" />
              <input value={manualMember} onChange={(e) => setManualMember(e.target.value)}
                     style={{ ...inp, fontFamily: "monospace" }} placeholder="STU-001" />
            </div>
          </details>

          <div style={summaryBar}>
            <div style={{ fontSize: "0.8rem", color: "#475569" }}>
              <b style={{ color: "#1e3a8a" }}>{pickedCopy?.barcode || manualBarcode || "—"}</b>
              {" → "}
              <b style={{ color: "#1e3a8a" }}>{pickedMember?.member_number || manualMember || "—"}</b>
            </div>
            <button type="button" onClick={() => void doIssue()}
                    disabled={issueBusy || !(pickedCopy || manualBarcode) || !(pickedMember || manualMember)}
                    className="circ-btn circ-btn-primary">
              {issueBusy ? <Loader2 size={15} className="spin" /> : <CheckCircle2 size={15} />}
              {issueBusy ? "Issuing…" : "Issue loan"}
            </button>
          </div>

          {issueResult ? (
            <div style={{ ...resultBox,
              background: issueResult.ok ? "#ecfdf5" : "#fef2f2",
              borderColor: issueResult.ok ? "#86efac" : "#fecaca",
              color: issueResult.ok ? "#065f46" : "#991b1b" }}>
              {issueResult.ok ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
              {issueResult.text}
            </div>
          ) : null}
        </section>

        {/* RETURN */}
        <section style={{ ...card, borderLeftColor: "#0e7490" }}>
          <div style={cardHead}>
            <div style={{ ...cardIcon, background: "#0e7490" }}><Library size={18} /></div>
            <div>
              <div style={cardTitle}>Return resources</div>
              <div style={cardSub}>Browse a member's active loans, or scan barcodes.</div>
            </div>
          </div>

          <div style={tabStrip}>
            <button onClick={() => setReturnMode("browse")} style={{ ...tabBtn, ...(returnMode === "browse" ? tabActive : {}) }}>Browse loans</button>
            <button onClick={() => setReturnMode("scan")} style={{ ...tabBtn, ...(returnMode === "scan" ? tabActive : {}) }}>Scan barcodes</button>
          </div>

          {returnMode === "browse" ? (
            <>
              <div style={{ ...cascadeRow, marginTop: "0.75rem" }}>
                <Select label="Class" value={returnClass} onChange={setReturnClass}
                        options={[{ v: "", l: "All classes" }, ...CLASSES.map((c) => ({ v: c, l: c }))]}
                        Icon={GraduationCap} />
                <div>
                  <Label>Member</Label>
                  <select value={returnMember?.id || ""}
                          onChange={(e) => setReturnMember(filteredReturnMembers.find((x) => x.id === e.target.value) || null)}
                          style={inp}>
                    <option value="">{filteredReturnMembers.length === 0 ? "No members in class" : "Select a member…"}</option>
                    {filteredReturnMembers.map((m) => (
                      <option key={m.id} value={m.id}>{m.member_number} · {m.full_name || "Unnamed"}</option>
                    ))}
                  </select>
                </div>
              </div>

              {returnMember ? returnLoansLoading ? (
                <div style={listEmpty}><Loader2 size={14} className="spin" /> Loading loans…</div>
              ) : returnLoans.length === 0 ? (
                <div style={listEmpty}>No active loans for {returnMember.member_number}.</div>
              ) : (
                <div style={listPanel}>
                  {returnLoans.map((l) => (
                    <label key={l.id} style={{ ...listRow, cursor: "pointer" }}>
                      <input type="checkbox" checked={checkedLoans.has(l.id)}
                             onChange={() => {
                               setCheckedLoans((prev) => {
                                 const n = new Set(prev);
                                 if (n.has(l.id)) n.delete(l.id); else n.add(l.id);
                                 return n;
                               });
                             }} />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={listRowTitle}>{(l as any).book_title || (l as any).copy?.book?.title || "Unknown title"}</div>
                        <div style={listRowSub}>
                          {(l as any).copy_barcode || (l as any).copy?.barcode || "—"}{l.due_at ? ` · due ${new Date(l.due_at).toLocaleDateString()}` : ""}
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              ) : null}

              <div style={{ display: "flex", gap: "0.5rem", marginTop: "1rem", flexWrap: "wrap" }}>
                <button type="button" onClick={doReturnChecked}
                        disabled={returnBusy || checkedLoans.size === 0}
                        className="circ-btn circ-btn-teal">
                  {returnBusy ? <Loader2 size={15} className="spin" /> : <CheckCircle2 size={15} />}
                  Return selected ({checkedLoans.size})
                </button>
                {returnLoans.length > 0 && checkedLoans.size < returnLoans.length ? (
                  <button type="button" onClick={() => setCheckedLoans(new Set(returnLoans.map((l) => l.id)))} style={ghostBtn}>
                    Select all
                  </button>
                ) : null}
              </div>
            </>
          ) : (
            <>
              <textarea value={bulkBarcodes} onChange={(e) => setBulkBarcodes(e.target.value)}
                        rows={6} style={{ ...inp, fontFamily: "monospace", resize: "vertical", marginTop: "0.75rem" }}
                        placeholder={"BK-000123\nBK-000124\nBK-000125"} />
              <button type="button" onClick={doReturnScan}
                      disabled={returnBusy || !bulkBarcodes.trim()}
                      className="circ-btn circ-btn-teal" style={{ marginTop: "0.75rem" }}>
                {returnBusy ? <Loader2 size={15} className="spin" /> : <CheckCircle2 size={15} />}
                Return all scanned
              </button>
            </>
          )}

          {returnResults.length > 0 ? (
            <div style={{ marginTop: "1rem" }}>
              <div style={{ fontSize: "0.78rem", color: "#64748b", marginBottom: "0.35rem", fontWeight: 700 }}>
                {returnResults.filter((r) => r.ok).length} of {returnResults.length} returned
              </div>
              <div style={{ maxHeight: 220, overflowY: "auto", border: "1px solid #e5e7eb", borderRadius: 6 }}>
                {returnResults.map((r, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: "0.5rem",
                    padding: "0.4rem 0.6rem",
                    borderBottom: i < returnResults.length - 1 ? "1px solid #f1f5f9" : "none",
                    fontSize: "0.82rem", color: r.ok ? "#166534" : "#991b1b" }}>
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
        .circ-btn {
          display: inline-flex; align-items: center; gap: 0.45rem;
          padding: 0.7rem 1.2rem; border-radius: 10px; border: 2px solid transparent;
          color: #fff; font-weight: 800; font-size: 0.85rem; cursor: pointer; font-family: inherit;
          transition: transform 240ms cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 240ms ease, filter 240ms ease;
          box-shadow: 0 4px 12px rgba(15,23,42,0.14);
        }
        .circ-btn-primary { background: #1e3a8a; border-color: #1e3a8a; }
        .circ-btn-teal    { background: #0e7490; border-color: #0e7490; }
        .circ-btn:hover:not(:disabled) { transform: translateY(-3px) scale(1.02); box-shadow: 0 12px 24px rgba(15,23,42,0.25); filter: brightness(1.12) saturate(1.08); }
        .circ-btn:active:not(:disabled) { transform: translateY(-1px) scale(0.99); }
        .circ-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        @media (prefers-reduced-motion: reduce) { .circ-btn { transition: none !important; transform: none !important; } }
      `}</style>
    </div>
  );
}

const kicker: React.CSSProperties = { fontSize: "0.72rem", letterSpacing: "0.08em", color: "#748095", fontWeight: 800 };
const pageHeader: React.CSSProperties = { marginBottom: "1.5rem", padding: "1.5rem", background: "rgba(255,255,255,0.94)", borderRadius: 16, borderLeft: "6px solid #1e3a8a", boxShadow: "0 6px 18px rgba(15,23,42,0.08)" };
const card: React.CSSProperties = { background: "rgba(255,255,255,0.96)", borderRadius: 16, padding: "1.4rem", borderLeft: "6px solid #1e3a8a", boxShadow: "0 6px 18px rgba(15,23,42,0.08)" };
const cardHead: React.CSSProperties = { display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1rem" };
const cardIcon: React.CSSProperties = { width: 42, height: 42, borderRadius: 10, color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 4px 12px rgba(15,23,42,0.2)", flexShrink: 0 };
const cardTitle: React.CSSProperties = { fontSize: "1.05rem", fontWeight: 800, color: "#111827" };
const cardSub: React.CSSProperties = { fontSize: "0.8rem", color: "#64748b", marginTop: "0.2rem" };
const cascadeRow: React.CSSProperties = { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem", marginBottom: "0.9rem" };
const listPanel: React.CSSProperties = { display: "flex", flexDirection: "column", gap: "0.35rem", maxHeight: 260, overflowY: "auto", padding: "0.35rem", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 10 };
const listRow: React.CSSProperties = { display: "flex", alignItems: "center", gap: "0.55rem", padding: "0.55rem 0.7rem", borderRadius: 8, background: "#fff", border: "1px solid #e5e7eb", cursor: "pointer", fontFamily: "inherit", textAlign: "left" };
const listRowTitle: React.CSSProperties = { fontWeight: 700, color: "#111827", fontSize: "0.85rem", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" };
const listRowSub: React.CSSProperties = { fontSize: "0.72rem", color: "#64748b", marginTop: "0.1rem" };
const listEmpty: React.CSSProperties = { padding: "1rem", textAlign: "center", fontSize: "0.82rem", color: "#64748b", display: "flex", alignItems: "center", justifyContent: "center", gap: "0.4rem" };
const barcodeChip: React.CSSProperties = { display: "inline-flex", alignItems: "center", gap: "0.3rem", padding: "0.35rem 0.75rem", borderRadius: 6, fontWeight: 800, fontSize: "0.78rem", fontFamily: "monospace", border: "2px solid #cbd5e1", cursor: "pointer" };
const summaryBar: React.CSSProperties = { display: "flex", alignItems: "center", justifyContent: "space-between", gap: "0.75rem", flexWrap: "wrap", marginTop: "1rem", padding: "0.75rem 1rem", background: "#f8fafc", borderRadius: 10, border: "1px solid #e2e8f0" };
const resultBox: React.CSSProperties = { marginTop: "1rem", padding: "0.75rem 1rem", borderRadius: 8, border: "1px solid", fontSize: "0.85rem", display: "flex", alignItems: "center", gap: "0.5rem", fontWeight: 600 };
const tabStrip: React.CSSProperties = { display: "inline-flex", gap: "0.35rem", background: "#f1f5f9", padding: "0.3rem", borderRadius: 999, marginBottom: "0.75rem" };
const tabBtn: React.CSSProperties = { padding: "0.45rem 0.9rem", borderRadius: 999, border: "none", background: "transparent", color: "#475569", fontSize: "0.82rem", fontWeight: 800, cursor: "pointer", fontFamily: "inherit" };
const tabActive: React.CSSProperties = { background: "#0e7490", color: "#fff", boxShadow: "0 3px 10px rgba(14,116,144,0.3)" };
const ghostBtn: React.CSSProperties = { padding: "0.7rem 1rem", borderRadius: 10, background: "rgba(255,255,255,0.9)", border: "2px solid #cbd5e1", color: "#475569", fontWeight: 800, fontSize: "0.82rem", cursor: "pointer", fontFamily: "inherit" };
const detailsSummary: React.CSSProperties = { cursor: "pointer", fontSize: "0.8rem", color: "#1e3a8a", fontWeight: 700 };
const inp: React.CSSProperties = { width: "100%", padding: "0.6rem 0.75rem", borderRadius: 8, border: "1px solid #cbd5e1", fontSize: "0.9rem", background: "#fdfbf7", fontFamily: "inherit" };

function Label({ children }: { children: React.ReactNode }) {
  return <label style={{ display: "block", fontSize: "0.7rem", fontWeight: 800, color: "#475569", letterSpacing: "0.04em", textTransform: "uppercase", marginBottom: "0.25rem" }}>{children}</label>;
}
function Select({ label, value, onChange, options, Icon }: { label: string; value: string; onChange: (v: string) => void; options: { v: string; l: string }[]; Icon?: any }) {
  return (
    <div>
      <label style={{ display: "flex", alignItems: "center", gap: "0.35rem", fontSize: "0.7rem", fontWeight: 800, color: "#475569", letterSpacing: "0.04em", textTransform: "uppercase", marginBottom: "0.25rem" }}>
        {Icon ? <Icon size={11} /> : null} {label}
      </label>
      <select value={value} onChange={(e) => onChange(e.target.value)} style={inp}>
        {options.map((o) => <option key={o.v} value={o.v}>{o.l}</option>)}
      </select>
    </div>
  );
}