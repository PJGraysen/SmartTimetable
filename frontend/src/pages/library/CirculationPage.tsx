import { useState } from "react";
import { CheckCircle2, RotateCcw, BookOpen } from "lucide-react";
import * as lib from "../../services/library";

export default function CirculationPage() {
  const [issueBarcode, setIssueBarcode] = useState("");
  const [issueMemberNumber, setIssueMemberNumber] = useState("");
  const [issueStatus, setIssueStatus] = useState<{ kind: "ok" | "err"; msg: string } | null>(null);

  const [returnBarcode, setReturnBarcode] = useState("");
  const [returnStatus, setReturnStatus] = useState<{ kind: "ok" | "err"; msg: string } | null>(null);

  async function doIssue() {
    setIssueStatus(null);
    try {
      const copy = await lib.getCopyByBarcode(issueBarcode.trim());
      const members = await lib.listMembers({ q: issueMemberNumber.trim() });
      const member = members.find((m) => m.member_number === issueMemberNumber.trim()) ?? members[0];
      if (!member) throw new Error("Member not found.");
      const loan = await lib.issueLoan({ copy: copy.id, member: member.id });
      setIssueStatus({ kind: "ok", msg: `Issued ${copy.barcode} to ${member.full_name}. Due ${new Date(loan.due_at).toLocaleDateString()}.` });
      setIssueBarcode(""); setIssueMemberNumber("");
    } catch (e: any) {
      setIssueStatus({ kind: "err", msg: e?.response?.data?.detail || e?.message || "Issue failed." });
    }
  }

  async function doReturn() {
    setReturnStatus(null);
    try {
      const copy = await lib.getCopyByBarcode(returnBarcode.trim());
      const loans = await lib.listLoans({ status: "ACTIVE" });
      const loan = loans.find((l) => l.copy === copy.id);
      if (!loan) throw new Error("No active loan for this copy.");
      const returned = await lib.returnLoan(loan.id);
      setReturnStatus({ kind: "ok", msg: `Returned ${copy.barcode}. Fine accrued: ${returned.fine_accrued}` });
      setReturnBarcode("");
    } catch (e: any) {
      setReturnStatus({ kind: "err", msg: e?.response?.data?.detail || e?.message || "Return failed." });
    }
  }

  return (
    <div style={{ padding: "1.5rem" }}>
      <h1 style={{ marginTop: 0 }}>Circulation Desk</h1>
      <p style={{ color: "#748095", marginBottom: "1.5rem" }}>Barcode-driven issue and return console.</p>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))", gap: "1.5rem" }}>
        <section style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: "10px", padding: "1.5rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1rem" }}>
            <BookOpen size={20} style={{ color: "#1e3a8a" }} />
            <h2 style={{ margin: 0 }}>Issue</h2>
          </div>
          <label style={lbl}>Copy barcode</label>
          <input value={issueBarcode} onChange={(e) => setIssueBarcode(e.target.value)} style={inp} autoFocus />
          <label style={lbl}>Member number</label>
          <input value={issueMemberNumber} onChange={(e) => setIssueMemberNumber(e.target.value)} style={inp} />
          <button type="button" className="primary-button" onClick={doIssue} disabled={!issueBarcode || !issueMemberNumber} style={{ width: "100%", marginTop: "1rem" }}>
            Issue Copy
          </button>
          {issueStatus ? <Banner kind={issueStatus.kind} msg={issueStatus.msg} /> : null}
        </section>

        <section style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: "10px", padding: "1.5rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1rem" }}>
            <RotateCcw size={20} style={{ color: "#7c3aed" }} />
            <h2 style={{ margin: 0 }}>Return</h2>
          </div>
          <label style={lbl}>Copy barcode</label>
          <input value={returnBarcode} onChange={(e) => setReturnBarcode(e.target.value)} style={inp} />
          <button type="button" className="primary-button" onClick={doReturn} disabled={!returnBarcode} style={{ width: "100%", marginTop: "1rem" }}>
            Return Copy
          </button>
          {returnStatus ? <Banner kind={returnStatus.kind} msg={returnStatus.msg} /> : null}
        </section>
      </div>
    </div>
  );
}

const lbl: React.CSSProperties = { display: "block", fontSize: "0.75rem", fontWeight: 700, color: "#748095", marginTop: "0.75rem", marginBottom: "0.25rem" };
const inp: React.CSSProperties = { width: "100%", padding: "0.6rem 0.75rem", border: "1px solid #d1d5db", borderRadius: "6px", fontSize: "0.95rem" };

function Banner({ kind, msg }: { kind: "ok" | "err"; msg: string }) {
  const ok = kind === "ok";
  return (
    <div style={{
      marginTop: "1rem", padding: "0.6rem 0.75rem", borderRadius: "6px",
      background: ok ? "#ecfdf5" : "#fef2f2",
      color: ok ? "#047857" : "#b91c1c", fontSize: "0.9rem",
    }}>
      {ok ? <CheckCircle2 size={14} style={{ marginRight: 6, verticalAlign: "middle" }} /> : null}
      {msg}
    </div>
  );
}
