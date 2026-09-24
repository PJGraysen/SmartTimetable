import { useEffect, useState } from "react";
import * as lib from "../../services/library";

export default function LoansPage() {
  const [status, setStatus] = useState("ACTIVE");
  const [loans, setLoans] = useState<lib.Loan[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

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
    try {
      if (action === "return") await lib.returnLoan(id);
      else await lib.renewLoan(id);
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Action failed.");
    }
  }

  return (
    <div style={{ padding: "1.5rem" }}>
      <h1 style={{ marginTop: 0 }}>Loans</h1>
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
        {["ACTIVE", "RETURNED", "LOST", ""].map((s) => (
          <button key={s || "all"} type="button" onClick={() => setStatus(s)} className={status === s ? "primary-button" : "secondary-button"}>
            {s || "All"}
          </button>
        ))}
      </div>

      {error ? <div className="tt-error">{error}</div> : null}

      {loading ? (
        <div style={{ padding: "2rem", textAlign: "center", color: "#748095" }}>Loading…</div>
      ) : loans.length === 0 ? (
        <div style={{ padding: "3rem", textAlign: "center", color: "#748095", border: "1px dashed #d1d5db", borderRadius: "10px" }}>No loans.</div>
      ) : (
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Copy</th><th>Book</th><th>Member</th>
                <th>Issued</th><th>Due</th><th>Status</th><th>Fine</th><th></th>
              </tr>
            </thead>
            <tbody>
              {loans.map((l) => (
                <tr key={l.id}>
                  <td><code>{l.copy_barcode}</code></td>
                  <td>{l.book_title}</td>
                  <td>{l.member_number} — {l.member_name}</td>
                  <td>{new Date(l.issued_at).toLocaleDateString()}</td>
                  <td>{new Date(l.due_at).toLocaleDateString()}{l.is_overdue ? <span style={{ color: "#dc2626" }}> · {l.overdue_days}d</span> : null}</td>
                  <td>{l.status}</td>
                  <td>{l.fine_accrued}</td>
                  <td style={{ display: "flex", gap: "0.4rem" }}>
                    {l.status === "ACTIVE" ? (
                      <>
                        <button type="button" className="secondary-button" onClick={() => act("return", l.id)}>Return</button>
                        {!l.is_overdue && l.renewal_count < 3 ? (
                          <button type="button" className="secondary-button" onClick={() => act("renew", l.id)}>Renew</button>
                        ) : null}
                      </>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
