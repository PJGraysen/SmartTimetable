import { useEffect, useState } from "react";
import * as lib from "../../services/library";

export default function ReportsPage() {
  const [circ, setCirc] = useState<any>(null);
  const [inv, setInv] = useState<any>(null);
  const [overdue, setOverdue] = useState<lib.Loan[]>([]);
  const [top, setTop] = useState<any[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([lib.reportCirculation(), lib.reportInventory(), lib.reportOverdue(), lib.reportTopBorrowers()])
      .then(([c, i, o, t]) => { setCirc(c); setInv(i); setOverdue(o); setTop(t); })
      .catch((e) => setError(e?.response?.data?.detail || "Failed to load reports."));
  }, []);

  return (
    <div style={{ padding: "1.5rem" }}>
      <h1 style={{ marginTop: 0 }}>Reports</h1>
      {error ? <div className="tt-error">{error}</div> : null}

      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "1rem", marginBottom: "2rem" }}>
        <Panel title="Circulation (last 30 days)">
          {circ ? (
            <>
              <Row k="Issued" v={String(circ.loans_issued)} />
              <Row k="Returned" v={String(circ.loans_returned)} />
            </>
          ) : "Loading…"}
        </Panel>
        <Panel title="Inventory">
          {inv ? (
            inv.by_status.map((s: any) => <Row key={s.status} k={s.status} v={String(s.count)} />)
          ) : "Loading…"}
        </Panel>
      </section>

      <h2>Overdue Loans ({overdue.length})</h2>
      <div className="table-wrapper" style={{ marginBottom: "2rem" }}>
        <table className="data-table">
          <thead><tr><th>Copy</th><th>Book</th><th>Member</th><th>Due</th><th>Days Overdue</th></tr></thead>
          <tbody>
            {overdue.length === 0 ? (
              <tr><td colSpan={5} style={{ textAlign: "center", color: "#748095", padding: "1rem" }}>No overdue loans.</td></tr>
            ) : overdue.map((l) => (
              <tr key={l.id}>
                <td><code>{l.copy_barcode}</code></td>
                <td>{l.book_title}</td>
                <td>{l.member_number} — {l.member_name}</td>
                <td>{new Date(l.due_at).toLocaleDateString()}</td>
                <td style={{ color: "#dc2626", fontWeight: 600 }}>{l.overdue_days}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2>Top Borrowers</h2>
      <div className="table-wrapper">
        <table className="data-table">
          <thead><tr><th>Member #</th><th>Name</th><th>Loans</th></tr></thead>
          <tbody>
            {top.map((m) => (
              <tr key={m.id}>
                <td>{m.member_number}</td>
                <td>{m.full_name}</td>
                <td>{m.loan_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Panel({ title, children }: any) {
  return (
    <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: "10px", padding: "1.25rem" }}>
      <h3 style={{ marginTop: 0 }}>{title}</h3>
      {children}
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", padding: "0.4rem 0", borderBottom: "1px solid #f3f4f6" }}>
      <span style={{ color: "#748095" }}>{k}</span>
      <strong>{v}</strong>
    </div>
  );
}
