import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import * as lib from "../../services/library";

export default function MemberDetailPage() {
  const { id = "" } = useParams();
  const [member, setMember] = useState<lib.Member | null>(null);
  const [loans, setLoans] = useState<lib.Loan[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) return;
    Promise.all([lib.getMember(id), lib.memberLoans(id)])
      .then(([m, l]) => { setMember(m); setLoans(l); })
      .catch((e) => setError(e?.response?.data?.detail || "Failed to load member."));
  }, [id]);

  if (!member) return <div style={{ padding: "1.5rem" }}>{error || "Loading…"}</div>;

  return (
    <div style={{ padding: "1.5rem" }}>
      <Link to="/library/members" style={{ display: "inline-flex", alignItems: "center", gap: "0.35rem", color: "#1e3a8a", marginBottom: "1rem" }}>
        <ArrowLeft size={16} /> Back to members
      </Link>
      <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: "10px", padding: "1.5rem", marginBottom: "1.5rem" }}>
        <h1 style={{ margin: 0 }}>{member.full_name}</h1>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "1rem", marginTop: "1rem" }}>
          <F label="Member #" v={member.member_number} />
          <F label="Type" v={member.member_type} />
          <F label="Email" v={member.email || "—"} />
          <F label="Phone" v={member.phone || "—"} />
          <F label="Status" v={member.is_active ? "Active" : "Inactive"} />
          <F label="Joined" v={member.joined_at} />
        </div>
      </div>

      <h2>Loans ({loans.length})</h2>
      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr><th>Copy</th><th>Book</th><th>Issued</th><th>Due</th><th>Returned</th><th>Status</th><th>Fine</th></tr>
          </thead>
          <tbody>
            {loans.length === 0 ? (
              <tr><td colSpan={7} style={{ textAlign: "center", color: "#748095", padding: "1rem" }}>No loans.</td></tr>
            ) : loans.map((l) => (
              <tr key={l.id}>
                <td><code>{l.copy_barcode}</code></td>
                <td>{l.book_title}</td>
                <td>{new Date(l.issued_at).toLocaleDateString()}</td>
                <td>{new Date(l.due_at).toLocaleDateString()}</td>
                <td>{l.returned_at ? new Date(l.returned_at).toLocaleDateString() : "—"}</td>
                <td>{l.status}{l.is_overdue ? " (overdue)" : ""}</td>
                <td>{l.fine_accrued}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function F({ label, v }: { label: string; v: string }) {
  return (
    <div>
      <div style={{ fontSize: "0.7rem", color: "#748095", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</div>
      <div style={{ marginTop: "0.2rem" }}>{v}</div>
    </div>
  );
}
