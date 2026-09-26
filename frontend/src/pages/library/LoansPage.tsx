import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BookOpen, RotateCcw, Wallet, CheckCircle2, AlertTriangle, Loader2 } from "lucide-react";
import * as lib from "../../services/library";

export default function LoansPage() {
  const [status, setStatus] = useState("ACTIVE");
  const [loans, setLoans] = useState<lib.Loan[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [ledgerMsg, setLedgerMsg] = useState<{ id: string; ok: boolean; text: string } | null>(null);

  async function load() {
    setLoading(true);
    try {
      const data = await lib.listLoans({ status: status || undefined });
      setLoans(data);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Failed to load loans.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, [status]);

  async function act(action: "return" | "renew", id: string) {
    setBusyId(id);
    try {
      if (action === "return") await lib.returnLoan(id);
      else await lib.renewLoan(id);
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Action failed.");
    } finally {
      setBusyId(null);
    }
  }

  async function postFine(l: lib.Loan) {
    const amount = l.fine_accrued;
    if (!amount || Number(amount) <= 0) {
      setLedgerMsg({ id: l.id, ok: false, text: "No fine amount on this loan." });
      return;
    }
    setBusyId(l.id);
    try {
      const r = await lib.postLoanFine(l.id, amount, "Library fine posted from Loans page");
      setLedgerMsg({ id: l.id, ok: true, text: `Posted. Balance: ${r.balance_after}` });
    } catch (e: any) {
      setLedgerMsg({ id: l.id, ok: false, text: e?.response?.data?.error || "Post failed." });
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div style={{ padding: "1.5rem" }}>
      <div style={{ marginBottom: "1rem" }}>
        <span style={{ fontSize: "0.75rem", letterSpacing: "0.08em", color: "#748095", fontWeight: 700 }}>
          LIBRARY MANAGEMENT
        </span>
        <h1 style={{ marginTop: "0.35rem" }}>Loans</h1>
        <p style={{ color: "#748095" }}>Active, overdue, and returned loans. Fines can post to the fee ledger.</p>
      </div>

      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem", flexWrap: "wrap" }}>
        {["ACTIVE", "RETURNED", "LOST", ""].map((s) => (
          <button key={s || "all"} type="button" onClick={() => setStatus(s)}
                  className={status === s ? "primary-button" : "secondary-button"}>
            {s || "All"}
          </button>
        ))}
      </div>

      {error ? <div className="tt-error">{error}</div> : null}

      {loading ? (
        <div style={{ padding: "2rem", textAlign: "center", color: "#748095" }}>Loading…</div>
      ) : loans.length === 0 ? (
        <div style={{ padding: "3rem", textAlign: "center", color: "#748095",
                      border: "1px dashed #d1d5db", borderRadius: "10px" }}>
          No loans.
        </div>
      ) : (
        <div className="table-wrapper" style={{ background: "#fff", borderRadius: 10,
                                                  border: "1px solid #e5e7eb", overflow: "hidden" }}>
          <table className="data-table" style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "#f1f5f9" }}>
                <th style={th}>Copy</th><th style={th}>Book</th><th style={th}>Member</th>
                <th style={th}>Issued</th><th style={th}>Due</th><th style={th}>Status</th>
                <th style={th}>Fine</th><th style={th}></th>
              </tr>
            </thead>
            <tbody>
              {loans.map((l) => (
                <tr key={l.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                  <td style={td}><code>{l.copy_barcode}</code></td>
                  <td style={td}>
                    <Link to={`/library/catalogue/${l.copy}`} style={{ color: "#1e3a8a", fontWeight: 700 }}>
                      {l.book_title}
                    </Link>
                  </td>
                  <td style={td}>{l.member_number} — {l.member_name}</td>
                  <td style={td}>{new Date(l.issued_at).toLocaleDateString()}</td>
                  <td style={td}>
                    {new Date(l.due_at).toLocaleDateString()}
                    {l.is_overdue ? (
                      <span style={{ color: "#dc2626", fontWeight: 700 }}> · {l.overdue_days}d</span>
                    ) : null}
                  </td>
                  <td style={td}>{l.status}</td>
                  <td style={td}>
                    <span style={{ fontWeight: 700,
                                   color: Number(l.fine_accrued) > 0 ? "#b91c1c" : "#64748b" }}>
                      {l.fine_accrued}
                    </span>
                  </td>
                  <td style={{ ...td, textAlign: "right" }}>
                    <div style={{ display: "inline-flex", gap: "0.35rem", flexWrap: "wrap" }}>
                      {l.status === "ACTIVE" ? (
                        <>
                          <button type="button" className="secondary-button" onClick={() => act("return", l.id)}
                                  disabled={busyId === l.id}
                                  style={btnSmall}>
                            {busyId === l.id ? <Loader2 size={12} className="spin" /> : <RotateCcw size={12} />}
                            Return
                          </button>
                          {!l.is_overdue && l.renewal_count < 3 ? (
                            <button type="button" className="secondary-button" onClick={() => act("renew", l.id)}
                                    disabled={busyId === l.id} style={btnSmall}>
                              Renew
                            </button>
                          ) : null}
                        </>
                      ) : null}
                      {Number(l.fine_accrued) > 0 ? (
                        <button type="button" onClick={() => postFine(l)} disabled={busyId === l.id}
                                style={{ ...btnSmall, background: "#1e3a8a", color: "#fff", border: "1px solid #1e3a8a" }}>
                          {busyId === l.id ? <Loader2 size={12} className="spin" /> : <Wallet size={12} />}
                          Post to ledger
                        </button>
                      ) : null}
                    </div>
                    {ledgerMsg?.id === l.id ? (
                      <div style={{ fontSize: "0.72rem", marginTop: "0.35rem",
                                    color: ledgerMsg.ok ? "#166534" : "#b91c1c",
                                    display: "flex", justifyContent: "flex-end",
                                    alignItems: "center", gap: "0.25rem" }}>
                        {ledgerMsg.ok ? <CheckCircle2 size={12} /> : <AlertTriangle size={12} />}
                        {ledgerMsg.text}
                      </div>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <style>{`
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}

const th: React.CSSProperties = { textAlign: "left", padding: "0.7rem", fontSize: "0.72rem",
                                   fontWeight: 800, color: "#475569", letterSpacing: "0.04em",
                                   textTransform: "uppercase" };
const td: React.CSSProperties = { padding: "0.7rem", fontSize: "0.85rem", color: "#334155" };
const btnSmall: React.CSSProperties = {
  display: "inline-flex", alignItems: "center", gap: "0.3rem",
  fontSize: "0.72rem", padding: "0.35rem 0.6rem", borderRadius: 5,
  background: "#f1f5f9", color: "#1e3a8a", border: "1px solid #cbd5e1",
  fontWeight: 700, cursor: "pointer",
};
