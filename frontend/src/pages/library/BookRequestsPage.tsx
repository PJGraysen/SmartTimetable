import { useEffect, useState } from "react";
import { Check, X, BookOpen, Loader2, Pause, Clock, History } from "lucide-react";
import * as lib from "../../services/library";
import { useAuth } from "../../auth/AuthContext";

const STAGE_LABELS: Record<string, string> = {
  PENDING_TEACHER: "Awaiting subject teacher",
  PENDING_LIBRARIAN: "Awaiting librarian",
  HOLD: "On hold",
  APPROVED: "Ready for collection",
  AWARDED: "Awarded",
  REJECTED: "Rejected",
  FULFILLED: "Fulfilled",
  CANCELLED: "Cancelled",
};

const STAGE_COLOURS: Record<string, string> = {
  PENDING_TEACHER: "#b45309",
  PENDING_LIBRARIAN: "#0369a1",
  HOLD: "#7c3aed",
  APPROVED: "#065f46",
  AWARDED: "#0d9488",
  REJECTED: "#991b1b",
  FULFILLED: "#065f46",
  CANCELLED: "#64748b",
};

function Pill({ stage }: { stage: string }) {
  const s = stage || "UNKNOWN";
  const colour = STAGE_COLOURS[s] || "#64748b";
  const label = STAGE_LABELS[s] || s;
  return (
    <span
      style={{
        padding: "2px 8px", borderRadius: 999,
        background: colour + "22", color: colour,
        fontSize: "0.72rem", fontWeight: 800,
        textTransform: "uppercase", letterSpacing: "0.04em",
      }}
    >
      {STAGE_LABELS[stage] || stage}
    </span>
  );
}

export default function BookRequestsPage() {
  const { role } = useAuth();
  const [rows, setRows] = useState<lib.BookRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<string | null>(null);

  const isLibrarian =
    role === "LIBRARIAN" ||
    role === "ADMIN" ||
    role === "PRINCIPAL" ||
    role === "SUPER_ADMIN";

  async function load() {
    setLoading(true);
    try {
      setRows(await lib.pendingApprovals());
      setError("");
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Could not load requests.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  async function act(r: lib.BookRequest, action: string) {
    let note = "";
    if (action.includes("reject") || action === "hold" || action === "award") {
      const reason = prompt(
        action === "award"
          ? "Notes (optional, e.g. 'handed over at desk'):"
          : action === "hold"
          ? "Reason (optional):"
          : "Reason for rejection (optional):",
      );
      if (reason === null) return;
      note = reason || "";
    }
    setBusy(r.id);
    try {
      await lib.requestAction(r.id, action as any, note);
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Action failed.");
    } finally {
      setBusy(null);
    }
  }

  // Split into pending (needs my action now) vs history (done)
  const isPending = (s: string) => s === "PENDING_TEACHER" || s === "PENDING_LIBRARIAN";
  const pending = rows.filter((r) => isPending(r.approval_stage));
  const history = rows.filter((r) => !isPending(r.approval_stage));

  return (
    <div style={{ padding: "1.5rem", maxWidth: 1200, margin: "0 auto" }}>
      <header style={{ marginBottom: "1.25rem" }}>
        <h1 style={{ margin: 0 }}>Book Requests</h1>
        <p style={{ color: "#64748b", fontSize: "0.88rem", marginTop: "4px" }}>
          {isLibrarian
            ? "Pending approvals, plus the history of everything you've handled."
            : "Requests from your students — approve, hold, or decline."}
        </p>
      </header>

      {error ? (
        <div style={{ padding: "0.75rem 1rem", borderRadius: 8,
                      background: "#fef2f2", border: "1px solid #fecaca",
                      color: "#991b1b", marginBottom: "1rem" }}>
          {error}
        </div>
      ) : null}

      {loading ? (
        <div style={{ display: "flex", gap: "0.5rem", justifyContent: "center",
                      padding: "2rem", color: "#64748b" }}>
          <Loader2 size={18} className="spin" /> Loading…
        </div>
      ) : (
        <>
          <Section
            title="Pending"
            count={pending.length}
            icon={<Clock size={14} />}
            emptyText="No pending requests."
          >
            {pending.map((r) => (
              <Row
                key={r.id}
                r={r}
                busy={busy === r.id}
                act={act}
                isLibrarian={isLibrarian}
              />
            ))}
          </Section>

          <Section
            title="History"
            count={history.length}
            icon={<History size={14} />}
            emptyText="Nothing yet."
          >
            {history.map((r) => (
              <Row
                key={r.id}
                r={r}
                busy={busy === r.id}
                act={act}
                isLibrarian={isLibrarian}
              />
            ))}
          </Section>
        </>
      )}

      <style>{`
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}

function Section({
  title, count, icon, emptyText, children,
}: {
  title: string;
  count: number;
  icon: React.ReactNode;
  emptyText: string;
  children: React.ReactNode;
}) {
  const hasChildren = Array.isArray(children) ? children.length > 0 : !!children;
  return (
    <section style={{ marginBottom: "1.75rem" }}>
      <h2 style={{ display: "flex", alignItems: "center", gap: 8,
                   fontSize: "0.95rem", marginBottom: "0.5rem",
                   color: "#334155", textTransform: "uppercase",
                   letterSpacing: "0.05em" }}>
        {icon} {title}
        <span style={{ background: "#e2e8f0", color: "#475569",
                       padding: "1px 8px", borderRadius: 999,
                       fontSize: "0.75rem", fontWeight: 800 }}>
          {count}
        </span>
      </h2>
      {hasChildren ? (
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Book</th>
                <th>Member</th>
                <th>Stage</th>
                <th>Requested</th>
                <th></th>
              </tr>
            </thead>
            <tbody>{children}</tbody>
          </table>
        </div>
      ) : (
        <div style={{ padding: "1rem 1.25rem", background: "#f8fafc",
                      border: "1px dashed #cbd5e1", borderRadius: 8,
                      color: "#64748b", fontSize: "0.85rem" }}>
          {emptyText}
        </div>
      )}
    </section>
  );
}

function Row({
  r,
  busy,
  act,
  isLibrarian,
}: {
  r: lib.BookRequest;
  busy: boolean;
  act: (r: lib.BookRequest, action: string) => void;
  isLibrarian: boolean;
}) {
  const stage = r.approval_stage || "UNKNOWN";
  const isTeacherStage = stage === "PENDING_TEACHER";
  const isLibrarianStage = stage === "PENDING_LIBRARIAN";
  const isApproved = stage === "APPROVED";

  return (
    <tr>
      <td>
        <div style={{ fontWeight: 700 }}>{r.book_title || "(no title)"}</div>
        <div style={{ fontSize: "0.78rem", color: "#64748b" }}>
          {r.book_author || "-"}
        </div>
        {r.subject_teacher ? (
          <div style={{ fontSize: "0.72rem", color: "#94a3b8", marginTop: 2 }}>
            Subject teacher: {r.subject_teacher}
          </div>
        ) : null}
      </td>
      <td>{r.member_name || "-"}</td>
      <td><Pill stage={stage} /></td>
      <td style={{ color: "#64748b", fontSize: "0.82rem" }}>
        {r.requested_at ? new Date(r.requested_at).toLocaleString() : "-"}
      </td>
      <td>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {isTeacherStage && (
            <>
              <button type="button" className="primary-button" disabled={busy}
                onClick={() => act(r, "teacher-approve")}
                style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                <Check size={14} /> Approve
              </button>
              <button type="button" className="secondary-button" disabled={busy}
                onClick={() => act(r, "hold")}
                style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                <Pause size={14} /> Hold
              </button>
              <button type="button" className="secondary-button" disabled={busy}
                onClick={() => act(r, "teacher-reject")}
                style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                <X size={14} /> Reject
              </button>
            </>
          )}

          {isLibrarianStage && (
            <>
              <button type="button" className="primary-button" disabled={busy}
                onClick={() => act(r, "librarian-approve")}
                style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                <Check size={14} /> Approve
              </button>
              <button type="button" className="secondary-button" disabled={busy}
                onClick={() => act(r, "hold")}
                style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                <Pause size={14} /> Hold
              </button>
              <button type="button" className="secondary-button" disabled={busy}
                onClick={() => act(r, "librarian-reject")}
                style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                <X size={14} /> Reject
              </button>
            </>
          )}

          {isApproved && isLibrarian && (
            <button type="button" className="primary-button" disabled={busy}
              onClick={() => act(r, "award")}
              style={{ display: "inline-flex", alignItems: "center", gap: 4, background: "#0d9488" }}>
              <Check size={14} /> Mark as Awarded
            </button>
          )}
        </div>
      </td>
    </tr>
  );
}
