import { useEffect, useState } from "react";
import { BookOpen, CheckCircle2, XCircle, Loader2, Plus, X } from "lucide-react";
import * as lib from "../../services/library";

const STATUSES = ["", "WAITING", "READY", "FULFILLED", "CANCELLED", "EXPIRED"];

export default function ReservationsPage() {
  const [status, setStatus] = useState("");
  const [rows, setRows] = useState<lib.ReservationRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState("");

  const [showNew, setShowNew] = useState(false);
  const [books, setBooks] = useState<lib.Book[]>([]);
  const [members, setMembers] = useState<lib.Member[]>([]);
  const [newBook, setNewBook] = useState("");
  const [newMember, setNewMember] = useState("");
  const [creating, setCreating] = useState(false);

  async function load() {
    setLoading(true); setError("");
    try { setRows(await lib.listReservations({ status: status || undefined })); }
    catch (e: any) { setError(e?.response?.data?.detail || "Failed to load reservations."); }
    finally { setLoading(false); }
  }
  useEffect(() => { void load(); }, [status]);

  async function openNew() {
    setShowNew(true);
    try {
      const [bs, ms] = await Promise.all([
        lib.listBooks({}),
        lib.listMembers({}),
      ]);
      setBooks(bs); setMembers(ms);
    } catch {}
  }

  async function doCreate() {
    if (!newBook || !newMember) return;
    setCreating(true);
    try {
      await lib.createReservation(newBook, newMember);
      setShowNew(false); setNewBook(""); setNewMember("");
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Could not create reservation.");
    } finally { setCreating(false); }
  }

  async function act(kind: "cancel" | "fulfill", id: string) {
    setBusyId(id);
    try {
      if (kind === "cancel") await lib.cancelReservation(id);
      else await lib.fulfillReservation(id);
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Action failed.");
    } finally { setBusyId(null); }
  }

  return (
    <div style={{ padding: "1.5rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "1rem" }}>
        <div>
          <span style={{ fontSize: "0.75rem", letterSpacing: "0.08em", color: "#748095", fontWeight: 700 }}>
            LIBRARY MANAGEMENT
          </span>
          <h1 style={{ marginTop: "0.35rem" }}>Reservations</h1>
          <p style={{ color: "#748095" }}>Holds and queues for high-demand titles.</p>
        </div>
        <button type="button" onClick={openNew} className="primary-button"
                style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem", alignSelf: "flex-start" }}>
          <Plus size={15} /> New reservation
        </button>
      </div>

      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem", flexWrap: "wrap" }}>
        {STATUSES.map((s) => (
          <button key={s || "all"} type="button" onClick={() => setStatus(s)}
                  className={status === s ? "primary-button" : "secondary-button"}>
            {s || "All"}
          </button>
        ))}
      </div>

      {error ? <div className="tt-error">{error}</div> : null}

      {loading ? (
        <div style={{ padding: "2rem", textAlign: "center", color: "#748095" }}>Loading…</div>
      ) : rows.length === 0 ? (
        <div style={{ padding: "3rem", textAlign: "center", color: "#748095",
                      border: "1px dashed #d1d5db", borderRadius: 10 }}>
          No reservations.
        </div>
      ) : (
        <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "#f1f5f9" }}>
                <th style={th}>#</th><th style={th}>Book</th><th style={th}>Member</th>
                <th style={th}>Status</th><th style={th}>Requested</th><th style={th}></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                  <td style={td}><strong>{r.position}</strong></td>
                  <td style={td}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
                      <BookOpen size={13} style={{ color: "#1e3a8a" }} />
                      {r.book_title}
                    </div>
                  </td>
                  <td style={td}>{r.member_number} — {r.member_name}</td>
                  <td style={td}>
                    <span style={{ fontWeight: 700,
                                   color: r.status === "WAITING" ? "#0284c7"
                                        : r.status === "READY" ? "#a16207"
                                        : r.status === "FULFILLED" ? "#166534" : "#64748b" }}>
                      {r.status}
                    </span>
                  </td>
                  <td style={td}>{new Date(r.requested_at).toLocaleDateString()}</td>
                  <td style={{ ...td, textAlign: "right" }}>
                    {r.status === "WAITING" || r.status === "READY" ? (
                      <div style={{ display: "inline-flex", gap: "0.35rem" }}>
                        <button type="button" onClick={() => act("fulfill", r.id)}
                                disabled={busyId === r.id} style={btnSmall}>
                          {busyId === r.id ? <Loader2 size={12} className="spin" /> : <CheckCircle2 size={12} />}
                          Fulfil
                        </button>
                        <button type="button" onClick={() => act("cancel", r.id)}
                                disabled={busyId === r.id}
                                style={{ ...btnSmall, color: "#b91c1c" }}>
                          <XCircle size={12} /> Cancel
                        </button>
                      </div>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showNew ? (
        <div onClick={() => setShowNew(false)}
             style={{ position: "fixed", inset: 0, background: "rgba(15,23,42,0.5)",
                      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999 }}>
          <div onClick={(e) => e.stopPropagation()}
               style={{ background: "#fff", borderRadius: 10, padding: "1.5rem", width: "min(520px, 92vw)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
              <h2 style={{ margin: 0, fontSize: "1.1rem" }}>New reservation</h2>
              <button type="button" onClick={() => setShowNew(false)}
                      style={{ background: "transparent", border: "none", cursor: "pointer", color: "#64748b" }}>
                <X size={16} />
              </button>
            </div>
            <label style={lbl}>Book</label>
            <select value={newBook} onChange={(e) => setNewBook(e.target.value)} style={inp}>
              <option value="">Select a book…</option>
              {books.map((b) => <option key={b.id} value={b.id}>{b.title}</option>)}
            </select>
            <label style={{ ...lbl, marginTop: "0.75rem" }}>Member</label>
            <select value={newMember} onChange={(e) => setNewMember(e.target.value)} style={inp}>
              <option value="">Select a member…</option>
              {members.map((m) => <option key={m.id} value={m.id}>{m.member_number} — {m.full_name}</option>)}
            </select>
            <div style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end", marginTop: "1.25rem" }}>
              <button type="button" onClick={() => setShowNew(false)} className="secondary-button">Cancel</button>
              <button type="button" onClick={doCreate} disabled={creating || !newBook || !newMember}
                      className="primary-button"
                      style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem" }}>
                {creating ? <Loader2 size={13} className="spin" /> : <Plus size={13} />}
                {creating ? "Creating…" : "Create"}
              </button>
            </div>
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
const lbl: React.CSSProperties = { display: "block", fontSize: "0.75rem", fontWeight: 700,
                                    color: "#748095", marginBottom: "0.3rem" };
const inp: React.CSSProperties = { width: "100%", padding: "0.6rem 0.7rem", borderRadius: 6,
                                    border: "1px solid #d1d5db", fontSize: "0.9rem" };
