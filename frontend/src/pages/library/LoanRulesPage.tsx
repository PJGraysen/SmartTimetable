import { useEffect, useState } from "react";
import * as lib from "../../services/library";
import { useAuth } from "../../auth/AuthContext";

export default function LoanRulesPage() {
  const { role } = useAuth();
  const canEdit = role !== "STUDENT";

  const [rules, setRules] = useState<lib.LoanRule[]>([]);
  const [editing, setEditing] = useState<lib.LoanRule | null>(null);
  const [error, setError] = useState("");

  function load() {
    lib.listRules()
      .then(setRules)
      .catch((e) => setError(e?.response?.data?.detail || "Failed to load rules."));
  }
  useEffect(load, []);

  async function save() {
    if (!editing) return;
    try {
      await lib.updateRule(editing.id, editing);
      setEditing(null);
      load();
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Save failed.");
    }
  }

  return (
    <div style={{ padding: "1.5rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "1rem" }}>
        <div>
          <h1 style={{ marginTop: 0 }}>Loan Rules</h1>
          {!canEdit && (
            <p style={{ margin: "4px 0 0", color: "#64748b", fontSize: "0.85rem" }}>
              These are the borrowing rules that apply to you. Contact the librarian for changes.
            </p>
          )}
        </div>
        {canEdit && (
          <button
            type="button"
            className="secondary-button"
            onClick={async () => {
              try {
                await lib.ensureDefaultRules();
                load();
              } catch (e: any) {
                setError(e?.response?.data?.detail || "Could not create defaults.");
              }
            }}
          >
            Fix missing defaults
          </button>
        )}
      </div>

      {error ? <div className="tt-error">{error}</div> : null}

      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>Member Type</th>
              <th>Max Loans</th>
              <th>Loan Days</th>
              <th>Max Renewals</th>
              <th>Fine/Day</th>
              <th>Grace Days</th>
              <th>Max Fine</th>
              {canEdit && <th></th>}
            </tr>
          </thead>
          <tbody>
            {rules.map((r) => (
              <tr key={r.id}>
                <td><strong>{r.member_type}</strong></td>
                <td>{r.max_concurrent_loans}</td>
                <td>{r.loan_days}</td>
                <td>{r.max_renewals}</td>
                <td>{r.fine_per_day}</td>
                <td>{r.grace_days}</td>
                <td>{r.max_fine ?? "—"}</td>
                {canEdit && (
                  <td>
                    <button
                      type="button"
                      className="secondary-button"
                      onClick={() => setEditing({ ...r })}
                    >
                      Edit
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {canEdit && editing ? (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0,0,0,0.4)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
          }}
        >
          <div style={{ background: "#fff", borderRadius: "10px", padding: "1.5rem", width: "420px" }}>
            <h2 style={{ marginTop: 0 }}>Edit {editing.member_type} Rule</h2>
            {(["max_concurrent_loans", "loan_days", "max_renewals", "grace_days"] as const).map((k) => (
              <Num
                key={k}
                label={k.replace(/_/g, " ")}
                value={editing[k] as number}
                onChange={(v) => setEditing({ ...editing, [k]: v })}
              />
            ))}
            <Num
              label="fine per day"
              value={Number(editing.fine_per_day)}
              onChange={(v) => setEditing({ ...editing, fine_per_day: String(v) })}
            />
            <div style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end", marginTop: "1rem" }}>
              <button type="button" className="secondary-button" onClick={() => setEditing(null)}>
                Cancel
              </button>
              <button type="button" className="primary-button" onClick={save}>
                Save
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function Num({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <div style={{ marginBottom: "0.75rem" }}>
      <label
        style={{
          display: "block",
          fontSize: "0.75rem",
          fontWeight: 700,
          color: "#748095",
          marginBottom: "0.25rem",
          textTransform: "capitalize",
        }}
      >
        {label}
      </label>
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ width: "100%", padding: "0.5rem", border: "1px solid #d1d5db", borderRadius: "6px" }}
      />
    </div>
  );
}
