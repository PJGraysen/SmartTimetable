import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import * as lib from "../../services/library";

export default function MemberFormPage() {
  const navigate = useNavigate();
  const [memberNumber, setMemberNumber] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [memberType, setMemberType] = useState<lib.MemberType>("STUDENT");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true); setError("");
    try {
      const created = await lib.createMember({
        member_number: memberNumber,
        full_name: fullName,
        email, phone,
        member_type: memberType,
        notes,
      } as any);
      navigate(`/library/members/${created.id}`);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Could not create member.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={{ padding: "1.5rem", maxWidth: "640px" }}>
      <Link to="/library/members" style={{ display: "inline-flex", alignItems: "center", gap: "0.35rem", color: "#1e3a8a", marginBottom: "1rem" }}>
        <ArrowLeft size={16} /> Back to members
      </Link>
      <h1 style={{ marginBottom: "1.5rem" }}>Add Member</h1>

      <form onSubmit={submit} style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: "10px", padding: "1.5rem" }}>
        <R label="Member number *"><input required value={memberNumber} onChange={(e) => setMemberNumber(e.target.value)} style={inp} /></R>
        <R label="Full name *"><input required value={fullName} onChange={(e) => setFullName(e.target.value)} style={inp} /></R>
        <R label="Member type *">
          <select value={memberType} onChange={(e) => setMemberType(e.target.value as lib.MemberType)} style={inp}>
            <option value="STUDENT">Student</option>
            <option value="TEACHER">Teacher</option>
            <option value="STAFF">Staff</option>
            <option value="EXTERNAL">External</option>
          </select>
        </R>
        <R label="Email"><input value={email} onChange={(e) => setEmail(e.target.value)} style={inp} /></R>
        <R label="Phone"><input value={phone} onChange={(e) => setPhone(e.target.value)} style={inp} /></R>
        <R label="Notes"><textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} style={{ ...inp, resize: "vertical" }} /></R>

        {error ? <div style={{ color: "#b91c1c", marginBottom: "1rem" }}>{error}</div> : null}

        <button type="submit" disabled={submitting} className="primary-button">{submitting ? "Saving…" : "Save Member"}</button>
      </form>
    </div>
  );
}

const inp: React.CSSProperties = { width: "100%", padding: "0.55rem 0.7rem", borderRadius: "6px", border: "1px solid #d1d5db", fontSize: "0.95rem" };

function R({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: "1rem" }}>
      <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "#748095", marginBottom: "0.3rem" }}>{label}</label>
      {children}
    </div>
  );
}
