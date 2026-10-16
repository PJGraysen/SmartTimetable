import { useEffect, useState } from "react";
import { getSchedulingScopes, type ScopeList, type ScopePick } from "../services/scheduling";

type Pick = ScopePick;

export default function ScopePicker({
  value,
  onChange,
  showSubjects = false,
}: {
  value: Pick | null;
  onChange: (p: Pick) => void;
  showSubjects?: boolean;
}) {
  const [data, setData] = useState<ScopeList | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSchedulingScopes()
      .then(setData)
      .catch((e) => setError(String(e)));
  }, []);

  if (error) return <div style={{ color: "#a00", fontSize: 12 }}>scopes: {error}</div>;
  if (!data) return <div style={{ fontSize: 12, color: "#666" }}>loading scopes…</div>;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <label style={{ fontSize: 12, fontWeight: 600 }}>Regeneration scope</label>
      <button
        type="button"
        onClick={() => onChange({ kind: "master", id: null, label: data.master.label })}
        style={{
          textAlign: "left",
          padding: "6px 10px",
          border: "1px solid #ccc",
          borderRadius: 6,
          background: value?.kind === "master" ? "#eef" : "white",
          cursor: "pointer",
        }}
      >
        {data.master.label}
      </button>

      <div style={{ fontSize: 11, color: "#666", marginTop: 4 }}>Grades</div>
      {data.grades.map((g) => (
        <button
          key={`g-${g.id}`}
          type="button"
          onClick={() => onChange({ kind: "grade", id: g.id, label: g.label, groups: g.groups })}
          style={{
            textAlign: "left",
            padding: "6px 10px",
            border: "1px solid #ccc",
            borderRadius: 6,
            background:
              value?.kind === "grade" && value.id === g.id ? "#eef" : "white",
            cursor: "pointer",
          }}
        >
          {g.label}{" "}
          <span style={{ color: "#666", fontSize: 11 }}>({g.groups.join(", ")})</span>
        </button>
      ))}

      {showSubjects && (
        <>
      <div style={{ fontSize: 11, color: "#666", marginTop: 4 }}>Subjects</div>
      <select
        value={value?.kind === "subject" ? value.id || "" : ""}
        onChange={(e) => {
          const id = e.target.value;
          if (!id) return;
          const s = data.subjects.find((x) => x.id === id);
          if (s) onChange({ kind: "subject", id: s.id, label: s.label, code: s.code });
        }}
        style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid #ccc" }}
      >
        <option value="">— pick a subject —</option>
        {data.subjects.map((s) => (
          <option key={`s-${s.id}`} value={s.id}>
            {s.label} ({s.code})
          </option>
        ))}
      </select>
        </>
      )}

      {value && (
        <div style={{ fontSize: 11, color: "#333", marginTop: 6 }}>
          Selected: <strong>{value.label}</strong>{" "}
          <span style={{ color: "#666" }}>[{value.kind}]</span>
        </div>
      )}
    </div>
  );
}
