import { useMemo, useState } from "react";
import {
  C, ErrorBox, PageShell, InventoryTabs, FilterBar, StatusPill,
  btnPrimary, btnSecondary, downloadCSV, useLoad,
} from "./_shared";
import { MovementModal } from "./Forms2";
import { inventoryApi } from "../../services/inventory";

const TYPES = ["RECEIPT","ISSUE","TRANSFER","RETURN","DISPOSAL","ADJUSTMENT","MAINTENANCE_OUT","MAINTENANCE_IN"];

export default function Movements() {
  const { data, err, loading, reload } = useLoad<any[]>(() => inventoryApi.movements.list());
  const [search, setSearch] = useState("");
  const [fType, setFType] = useState("");
  const [showNew, setShowNew] = useState(false);

  const rows = useMemo(() => {
    const s = search.toLowerCase();
    return (data || []).filter((r: any) => {
      if (fType && r.movement_type !== fType) return false;
      if (s) {
        const hay = [r.item_code, r.item_name, r.from_code, r.to_code, r.recipient, r.actor_name, r.notes]
          .map(x => String(x || "")).join(" ").toLowerCase();
        if (!hay.includes(s)) return false;
      }
      return true;
    });
  }, [data, search, fType]);

  function exportCSV() {
    downloadCSV("movements",
      ["When", "Type", "Item", "From", "To", "Qty", "By", "Recipient", "Notes"],
      rows.map((r: any) => [r.occurred_at, r.movement_type, r.item_code + " " + r.item_name,
                            r.from_code, r.to_code, r.quantity, r.actor_name, r.recipient, r.notes]));
  }

  return (
    <PageShell title="Movements" subtitle="Unified audit trail of every receipt, issue, transfer, return, disposal"
      actions={
        <div style={{ display: "flex", gap: 6 }}>
          <button style={btnPrimary} onClick={() => setShowNew(true)}>+ New Movement</button>
          <button style={btnSecondary} onClick={exportCSV}>CSV</button>
        </div>
      }>
      <InventoryTabs active="movements" />
      <FilterBar search={search} onSearch={setSearch}
        filters={[
          { label: "Type", value: fType, onChange: setFType,
            options: [{ value: "", label: "All Types" },
                      ...TYPES.map(t => ({ value: t, label: t }))] },
        ]} />

      <ErrorBox msg={err} />
      {loading ? <div>Loading...</div> : (
        <div style={{ background: "#fff", borderRadius: 10, border: `1px solid ${C.BORDER}`, overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
            <thead>
              <tr style={{ background: "#f8fafc", textAlign: "left" }}>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>When</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Type</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Item</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>From</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>To</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Qty</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>By</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Reason</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && (
                <tr><td colSpan={8} style={{ padding: "1rem", textAlign: "center", color: C.MUTED }}>No movements match filters</td></tr>
              )}
              {rows.map((r: any) => (
                <tr key={r.id} style={{ borderTop: "1px solid #f1f5f9" }}>
                  <td style={{ padding: "0.5rem 0.6rem", color: C.MUTED }}>{new Date(r.occurred_at).toLocaleString()}</td>
                  <td style={{ padding: "0.5rem 0.6rem" }}><StatusPill value={r.movement_type} /></td>
                  <td style={{ padding: "0.5rem 0.6rem" }}>
                    <div style={{ fontWeight: 600 }}>{r.item_code}</div>
                    <div style={{ fontSize: "0.72rem", color: C.MUTED }}>{r.item_name}</div>
                  </td>
                  <td style={{ padding: "0.5rem 0.6rem" }}>{r.from_code || "-"}</td>
                  <td style={{ padding: "0.5rem 0.6rem" }}>{r.to_code || "-"}</td>
                  <td style={{ padding: "0.5rem 0.6rem", fontWeight: 600 }}>{r.quantity}</td>
                  <td style={{ padding: "0.5rem 0.6rem" }}>{r.actor_name || "-"}</td>
                  <td style={{ padding: "0.5rem 0.6rem", color: C.MUTED, fontSize: "0.78rem" }}>{r.notes || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <MovementModal open={showNew} onClose={() => setShowNew(false)} onDone={reload} />
    </PageShell>
  );
}
