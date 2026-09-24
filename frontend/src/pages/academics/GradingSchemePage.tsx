import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Award, Plus, Save, Trash2 } from "lucide-react";
import {
  createBand, deleteBand, listSchemes, updateBand,
  type GradingBand, type GradingScheme,
} from "../../services/grading";

const BROWN = "#2b1a0f", BROWN2 = "#5a3a1e", SKY = "#22b4f0", CREAM = "#f5eee2";
const cardStyle: React.CSSProperties = {
  background: "#fff", border: "1px solid #e5e7eb", borderRadius: "14px",
  padding: "1.1rem 1.25rem", boxShadow: "0 4px 14px rgba(10,18,29,0.05)",
};

export default function GradingSchemePage() {
  const navigate = useNavigate();
  const [schemes, setSchemes] = useState<GradingScheme[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const rows = await listSchemes();
      setSchemes(rows);
      if (rows.length && !selectedId) setSelectedId(rows[0].id);
    } catch (e) { setError(e instanceof Error ? e.message : "Load failed"); }
  }
  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  const selected = schemes.find((s) => s.id === selectedId) ?? null;

  function patchBandLocal(id: string, patch: Partial<GradingBand>) {
    setSchemes((prev) => prev.map((s) => ({
      ...s, bands: s.bands.map((b) => b.id === id ? { ...b, ...patch } : b),
    })));
  }

  async function saveBand(b: GradingBand) {
    setSaving(true); setError(null); setMessage(null);
    try {
      await updateBand(b.id, {
        min_score: b.min_score, max_score: b.max_score,
        grade: b.grade, points: b.points, descriptor: b.descriptor,
      });
      setMessage("Band saved.");
      setTimeout(() => setMessage(null), 1500);
    } catch (e) { setError(e instanceof Error ? e.message : "Save failed"); }
    finally { setSaving(false); }
  }

  async function addBand() {
    if (!selected) return;
    setSaving(true); setError(null);
    try {
      const newBand = await createBand({
        scheme: selected.id, min_score: "0", max_score: "0",
        grade: "X", points: "0", descriptor: "",
      });
      setSchemes((prev) => prev.map((s) =>
        s.id === selected.id ? { ...s, bands: [...s.bands, newBand] } : s,
      ));
    } catch (e) { setError(e instanceof Error ? e.message : "Create failed"); }
    finally { setSaving(false); }
  }

  async function removeBand(id: string) {
    if (!confirm("Delete this band?")) return;
    try {
      await deleteBand(id);
      setSchemes((prev) => prev.map((s) => ({ ...s, bands: s.bands.filter((b) => b.id !== id) })));
    } catch (e) { setError(e instanceof Error ? e.message : "Delete failed"); }
  }

  return (
    <div style={{ padding: "2rem", maxWidth: "1200px", margin: "0 auto" }}>
      <button type="button" onClick={() => navigate(-1)} style={{
        display: "inline-flex", alignItems: "center", gap: "6px",
        background: "transparent", border: "none", color: BROWN2,
        fontWeight: 600, cursor: "pointer", marginBottom: "1rem",
      }}><ArrowLeft size={16} /> Back</button>

      <div style={{ display: "flex", alignItems: "center", gap: "14px", marginBottom: "1.5rem" }}>
        <div style={{
          width: "52px", height: "52px", borderRadius: "14px",
          background: `linear-gradient(135deg, ${SKY}, #0b5d8c)`,
          color: "#fff", display: "flex", alignItems: "center", justifyContent: "center",
          boxShadow: "0 6px 18px rgba(34,180,240,0.35)",
        }}><Award size={26} /></div>
        <div>
          <h1 style={{ margin: 0, fontSize: "1.7rem", color: "#1e2e40", fontWeight: 800 }}>Grading Scheme</h1>
          <p style={{ margin: "2px 0 0", color: "#748095", fontSize: "0.9rem" }}>
            Versioned grade boundaries — changes never overwrite raw marks.
          </p>
        </div>
      </div>

      {error && <div style={{ padding: "0.7rem 1rem", borderRadius: "10px", background: "#fee2e2", color: "#991b1b", marginBottom: "1rem" }}>{error}</div>}
      {message && <div style={{ padding: "0.7rem 1rem", borderRadius: "10px", background: "#dcfce7", color: "#166534", marginBottom: "1rem" }}>{message}</div>}

      <div style={{ ...cardStyle, marginBottom: "1rem", display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
        <label style={{ fontSize: "0.72rem", fontWeight: 700, color: "#748095", letterSpacing: "0.06em" }}>SCHEME:</label>
        <select value={selectedId} onChange={(e) => setSelectedId(e.target.value)}
          style={{ padding: "5px 8px", border: `1px solid ${SKY}`, borderRadius: "8px", fontWeight: 600, color: BROWN2, minWidth: "260px" }}>
          {schemes.map((s) => <option key={s.id} value={s.id}>{s.name}{s.is_active ? " (active)" : ""}</option>)}
        </select>
        {selected && (
          <>
            <span style={{ color: "#748095", fontSize: "0.85rem" }}>
              Curriculum: <strong>{selected.curriculum || "—"}</strong> · {selected.bands.length} bands
            </span>
            <button type="button" onClick={addBand} disabled={saving}
              style={{
                marginLeft: "auto", display: "inline-flex", alignItems: "center", gap: "4px",
                background: SKY, color: "#fff", border: "none",
                padding: "6px 12px", borderRadius: "8px",
                cursor: "pointer", fontWeight: 700, fontSize: "0.82rem",
              }}><Plus size={14} /> Add band</button>
          </>
        )}
      </div>

      {selected && (
        <div style={{ ...cardStyle, padding: 0, overflow: "hidden" }}>
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.86rem" }}>
              <thead>
                <tr style={{ background: `linear-gradient(135deg, ${BROWN}, ${BROWN2})`, color: CREAM }}>
                  <th style={{ textAlign: "left", padding: "0.7rem 1rem" }}>Grade</th>
                  <th style={{ textAlign: "right", padding: "0.7rem 1rem" }}>Min %</th>
                  <th style={{ textAlign: "right", padding: "0.7rem 1rem" }}>Max %</th>
                  <th style={{ textAlign: "right", padding: "0.7rem 1rem" }}>Points</th>
                  <th style={{ textAlign: "left", padding: "0.7rem 1rem" }}>Descriptor</th>
                  <th style={{ textAlign: "right", padding: "0.7rem 1rem" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {selected.bands
                  .slice()
                  .sort((a, b) => Number(b.min_score) - Number(a.min_score))
                  .map((b) => (
                  <tr key={b.id} style={{ borderTop: "1px solid #f1f5f9" }}>
                    <td style={{ padding: "0.55rem 1rem" }}>
                      <input value={b.grade} onChange={(e) => patchBandLocal(b.id, { grade: e.target.value })}
                        style={{ width: "60px", padding: "4px 6px", border: "1px solid #cbd5e1", borderRadius: "6px", fontWeight: 800, textAlign: "center" }} />
                    </td>
                    <td style={{ padding: "0.55rem 1rem", textAlign: "right" }}>
                      <input value={b.min_score} onChange={(e) => patchBandLocal(b.id, { min_score: e.target.value })}
                        style={{ width: "80px", padding: "4px 6px", border: "1px solid #cbd5e1", borderRadius: "6px", textAlign: "right" }} />
                    </td>
                    <td style={{ padding: "0.55rem 1rem", textAlign: "right" }}>
                      <input value={b.max_score} onChange={(e) => patchBandLocal(b.id, { max_score: e.target.value })}
                        style={{ width: "80px", padding: "4px 6px", border: "1px solid #cbd5e1", borderRadius: "6px", textAlign: "right" }} />
                    </td>
                    <td style={{ padding: "0.55rem 1rem", textAlign: "right" }}>
                      <input value={b.points} onChange={(e) => patchBandLocal(b.id, { points: e.target.value })}
                        style={{ width: "70px", padding: "4px 6px", border: "1px solid #cbd5e1", borderRadius: "6px", textAlign: "right" }} />
                    </td>
                    <td style={{ padding: "0.55rem 1rem" }}>
                      <input value={b.descriptor} onChange={(e) => patchBandLocal(b.id, { descriptor: e.target.value })}
                        style={{ width: "100%", padding: "4px 6px", border: "1px solid #cbd5e1", borderRadius: "6px" }} />
                    </td>
                    <td style={{ padding: "0.55rem 1rem", textAlign: "right", whiteSpace: "nowrap" }}>
                      <button type="button" onClick={() => saveBand(b)} disabled={saving}
                        style={{
                          display: "inline-flex", alignItems: "center", gap: "4px",
                          background: SKY, color: "#fff", border: "none",
                          padding: "5px 10px", borderRadius: "6px",
                          cursor: "pointer", fontWeight: 600, fontSize: "0.78rem",
                          marginRight: "6px",
                        }}><Save size={13} /> Save</button>
                      <button type="button" onClick={() => removeBand(b.id)}
                        style={{
                          background: "transparent", color: "#ef4444",
                          border: "1px solid #ef4444", padding: "5px 10px",
                          borderRadius: "6px", cursor: "pointer", fontWeight: 600, fontSize: "0.78rem",
                          display: "inline-flex", alignItems: "center", gap: "4px",
                        }}><Trash2 size={13} /></button>
                    </td>
                  </tr>
                ))}
                {selected.bands.length === 0 && (
                  <tr><td colSpan={6} style={{ padding: "2rem", textAlign: "center", color: "#94a3b8" }}>No bands. Click "Add band".</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}