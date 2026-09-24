import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Search, Plus } from "lucide-react";
import * as lib from "../../services/library";

export default function MembersPage() {
  const [query, setQuery] = useState("");
  const [type, setType] = useState("");
  const [members, setMembers] = useState<lib.Member[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    lib.listMembers({ q: query, type: type || undefined })
      .then(setMembers)
      .catch((e) => setError(e?.response?.data?.detail || "Failed to load members."))
      .finally(() => setLoading(false));
  }, [query, type]);

  return (
    <div style={{ padding: "1.5rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "1.5rem" }}>
        <div>
          <span style={{ fontSize: "0.75rem", letterSpacing: "0.08em", color: "#748095", fontWeight: 700 }}>LIBRARY</span>
          <h1 style={{ marginTop: "0.35rem" }}>Members</h1>
        </div>
        <Link to="/library/members/new" className="primary-button"><Plus size={16} /> Add Member</Link>
      </div>

      <div style={{ display: "flex", gap: "0.75rem", marginBottom: "1rem", alignItems: "center" }}>
        <Search size={18} style={{ color: "#748095" }} />
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search by name, number, email"
          style={{ flex: 1, padding: "0.6rem 0.75rem", border: "1px solid #d1d5db", borderRadius: "6px", fontSize: "0.95rem" }} />
        <select value={type} onChange={(e) => setType(e.target.value)} style={{ padding: "0.6rem", border: "1px solid #d1d5db", borderRadius: "6px" }}>
          <option value="">All types</option>
          <option value="STUDENT">Student</option>
          <option value="TEACHER">Teacher</option>
          <option value="STAFF">Staff</option>
          <option value="EXTERNAL">External</option>
        </select>
      </div>

      {error ? <div className="tt-error">{error}</div> : null}

      {loading ? (
        <div style={{ padding: "2rem", textAlign: "center", color: "#748095" }}>Loading…</div>
      ) : members.length === 0 ? (
        <div style={{ padding: "3rem", textAlign: "center", color: "#748095", border: "1px dashed #d1d5db", borderRadius: "10px" }}>No members yet.</div>
      ) : (
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr><th>Member #</th><th>Name</th><th>Type</th><th>Email</th><th>Status</th></tr>
            </thead>
            <tbody>
              {members.map((m) => (
                <tr key={m.id}>
                  <td><Link to={`/library/members/${m.id}`} style={{ color: "#1e3a8a", fontWeight: 600 }}>{m.member_number}</Link></td>
                  <td>{m.full_name}</td>
                  <td>{m.member_type}</td>
                  <td>{m.email || "—"}</td>
                  <td>{m.is_active ? "Active" : "Inactive"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
