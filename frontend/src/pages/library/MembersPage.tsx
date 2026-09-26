import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Users, RefreshCw, Wallet, Loader2 } from "lucide-react";
import * as lib from "../../services/library";

export default function MembersPage() {
  const [rows, setRows] = useState<lib.Member[]>([]);
  const [q, setQ] = useState("");
  const [type, setType] = useState("");
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncNotice, setSyncNotice] = useState("");
  const [error, setError] = useState("");

  const [feeMember, setFeeMember] = useState<lib.Member | null>(null);
  const [feeAccount, setFeeAccount] = useState<lib.FeeAccount | null>(null);
  const [feeLoading, setFeeLoading] = useState(false);

  async function load() {
    setLoading(true); setError("");
    try {
      const r = await lib.listMembers({ q: q || undefined, type: type || undefined });
      setRows(r);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Could not load members.");
    } finally { setLoading(false); }
  }

  useEffect(() => { void load(); /* eslint-disable-next-line */ }, [q, type]);

  async function doSync() {
    setSyncing(true); setSyncNotice("");
    try {
      const r = await lib.rosterSync();
      setSyncNotice(`Synced: +${r.created_students} students, +${r.created_teachers} teachers, ${r.updated} updated.`);
      await load();
    } catch (e: any) {
      setSyncNotice(e?.response?.data?.detail || "Sync failed.");
    } finally { setSyncing(false); }
  }

  async function openFee(member: lib.Member) {
    setFeeMember(member); setFeeAccount(null); setFeeLoading(true);
    try { setFeeAccount(await lib.memberFeeAccount(member.id)); }
    catch { setFeeAccount(null); }
    finally { setFeeLoading(false); }
  }

  return (
    <div style={{ padding: "1.5rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "1rem" }}>
        <div>
          <span style={{ fontSize: "0.75rem", letterSpacing: "0.08em", color: "#748095", fontWeight: 700 }}>
            LIBRARY MANAGEMENT
          </span>
          <h1 style={{ marginTop: "0.35rem" }}>Members</h1>
          <p style={{ color: "#748095" }}>Students, teachers, and staff who borrow.</p>
        </div>
        <div style={{ display: "flex", gap: "0.5rem", alignSelf: "flex-start" }}>
          <button type="button" onClick={doSync} disabled={syncing} className="primary-button"
                  style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem" }}>
            {syncing ? <Loader2 size={14} className="spin" /> : <RefreshCw size={14} />}
            {syncing ? "Syncing…" : "Sync from roster"}
          </button>
          <Link to="/library/members/new" className="secondary-button">Add Member</Link>
        </div>
      </div>


      {syncNotice ? (
        <div style={{ background: "#ecfdf5", border: "1px solid #86efac", color: "#065f46",
                      padding: "0.6rem 0.9rem", borderRadius: "8px", fontSize: "0.85rem", marginBottom: "1rem" }}>
          {syncNotice}
        </div>
      ) : null}

      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search name or member number…"
               style={{ flex: 1, padding: "0.6rem 0.75rem", borderRadius: "6px", border: "1px solid #d1d5db" }} />
        <select value={type} onChange={(e) => setType(e.target.value)}
                style={{ padding: "0.6rem 0.75rem", borderRadius: "6px", border: "1px solid #d1d5db", fontWeight: 700 }}>
          <option value="">All types</option>
          <option value="STUDENT">Students</option>
          <option value="TEACHER">Teachers</option>
          <option value="STAFF">Staff</option>
          <option value="EXTERNAL">External</option>
        </select>
      </div>

      {error ? <div className="tt-error">{error}</div> : null}

      {loading ? (
        <div style={{ padding: "2rem", color: "#64748b", textAlign: "center" }}>Loading…</div>
      ) : rows.length === 0 ? (
        <div style={{ padding: "2rem", background: "#f8fafc", borderRadius: "10px", textAlign: "center", color: "#64748b" }}>
          No members yet. Click "Sync from roster" to import students and teachers.
        </div>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", background: "#fff", borderRadius: "10px", overflow: "hidden" }}>
          <thead>
            <tr style={{ background: "#f1f5f9" }}>
              <th style={th}>Member #</th>
              <th style={th}>Name</th>
              <th style={th}>Type</th>
              <th style={th}>Contact</th>
              <th style={th}>Active</th>
              <th style={th}></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((m) => (
              <tr key={m.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                <td style={td}>{m.member_number}</td>
                <td style={td}><Link to={`/library/members/${m.id}`} style={{ color: "#1e3a8a", fontWeight: 700 }}>{m.full_name}</Link></td>
                <td style={td}>{m.member_type}</td>
                <td style={td}>{m.email || m.phone || "—"}</td>
                <td style={td}>{m.is_active ? "✅" : "—"}</td>
                <td style={{ ...td, textAlign: "right" }}>
                  <button type="button" onClick={() => openFee(m)}
                          style={{ display: "inline-flex", alignItems: "center", gap: "0.3rem",
                                   background: "#f1f5f9", color: "#1e3a8a", border: "1px solid #cbd5e1",
                                   padding: "0.3rem 0.6rem", borderRadius: "5px", fontWeight: 700,
                                   fontSize: "0.75rem", cursor: "pointer" }}>
                    <Wallet size={12} /> Fees
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {feeMember ? (
        <div onClick={() => setFeeMember(null)}
             style={{ position: "fixed", inset: 0, background: "rgba(15,23,42,0.5)",
                      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100 }}>
          <div onClick={(e) => e.stopPropagation()}
               style={{ background: "#fff", borderRadius: "10px", padding: "1.5rem",
                        maxWidth: 600, width: "90%", maxHeight: "80vh", overflowY: "auto" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "1rem" }}>
              <div>
                <h2 style={{ margin: 0, fontSize: "1.15rem" }}>{feeMember.full_name}</h2>
                <div style={{ color: "#64748b", fontSize: "0.83rem" }}>{feeMember.member_number} · {feeMember.member_type}</div>
              </div>
              <button type="button" onClick={() => setFeeMember(null)}
                      style={{ background: "transparent", border: "none", color: "#64748b", cursor: "pointer", fontSize: "1.2rem" }}>✕</button>
            </div>
            {feeLoading ? (
              <div style={{ padding: "1rem", color: "#64748b" }}>Loading account…</div>
            ) : feeAccount ? (
              <>
                <div style={{ background: "#f8fafc", borderRadius: "8px", padding: "1rem", marginBottom: "1rem",
                              display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <div style={{ fontSize: "0.72rem", color: "#64748b", letterSpacing: "0.04em", fontWeight: 700 }}>BALANCE</div>
                    <div style={{ fontSize: "1.6rem", fontWeight: 800, color: Number(feeAccount.balance) > 0 ? "#b91c1c" : "#166534" }}>
                      {feeAccount.currency} {feeAccount.balance}
                    </div>
                  </div>
                  <Wallet size={32} style={{ color: "#1e3a8a" }} />
                </div>
                <h3 style={{ fontSize: "0.9rem", color: "#111827", marginBottom: "0.5rem" }}>Ledger</h3>
                {feeAccount.entries.length === 0 ? (
                  <div style={{ color: "#64748b", fontSize: "0.83rem" }}>No entries yet.</div>
                ) : (
                  <div style={{ border: "1px solid #e5e7eb", borderRadius: "6px", overflow: "hidden" }}>
                    {feeAccount.entries.map((e) => (
                      <div key={e.id} style={{ display: "flex", gap: "0.75rem", padding: "0.5rem 0.75rem",
                                                borderBottom: "1px solid #f1f5f9", fontSize: "0.82rem" }}>
                        <span style={{ width: 70, fontWeight: 700, color: e.kind === "CHARGE" ? "#b91c1c" : "#166534" }}>{e.kind}</span>
                        <span style={{ width: 70, color: "#64748b" }}>{e.source}</span>
                        <span style={{ width: 90, textAlign: "right", fontWeight: 700 }}>{e.amount}</span>
                        <span style={{ flex: 1, color: "#64748b" }}>{e.description}</span>
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <div style={{ color: "#b91c1c" }}>Could not load fee account.</div>
            )}
          </div>
        </div>
      ) : null}

      <style>{`
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}

const th: React.CSSProperties = { textAlign: "left", padding: "0.75rem", fontSize: "0.75rem",
                                   fontWeight: 800, color: "#475569", letterSpacing: "0.04em", textTransform: "uppercase" };
const td: React.CSSProperties = { padding: "0.75rem", fontSize: "0.88rem", color: "#334155" };
