import { useEffect, useMemo, useState } from "react";
import {
  C, ErrorBox, PageShell, InventoryTabs, FilterBar, btnSecondary, btnPrimary,
  smallBtn, downloadCSV, useLoad,
} from "./_shared";
import { ReceiveStockModal, IssueStockModal } from "./ActionModals";
import { inventoryApi } from "../../services/inventory";

export default function Stock() {
  const { data, err, loading, reload } = useLoad<any[]>(() => inventoryApi.stock.list());
  const [search, setSearch] = useState("");
  const [fItem, setFItem] = useState("");
  const [fLocation, setFLocation] = useState("");
  const [showReceive, setShowReceive] = useState(false);
  const [showIssue, setShowIssue] = useState(false);
  const [items, setItems] = useState<any[]>([]);
  const [locations, setLocations] = useState<any[]>([]);

  useEffect(() => {
    inventoryApi.items.list().then((i: any) => setItems(i || []));
    inventoryApi.locations.list().then((l: any) => setLocations(l || []));
  }, []);

  const rows = useMemo(() => {
    const s = search.toLowerCase();
    return (data || []).filter((r: any) => {
      if (fItem && String(r.item) !== String(fItem)) return false;
      if (fLocation && String(r.location) !== String(fLocation)) return false;
      if (s) {
        const hay = [r.item_code, r.item_name, r.location_code, r.batch_number].map(x => String(x || "")).join(" ").toLowerCase();
        if (!hay.includes(s)) return false;
      }
      return true;
    });
  }, [data, search, fItem, fLocation]);

  function exportCSV() {
    downloadCSV("stock_levels",
      ["Item Code", "Item", "Location", "Quantity", "Unit", "Batch", "Expiry"],
      rows.map((r: any) => [r.item_code, r.item_name, r.location_code, r.quantity, r.unit, r.batch_number, r.expiry_date]));
  }

  return (
    <PageShell title="Stock Levels" subtitle="Bulk quantities per item per location"
      actions={
        <div style={{ display: "flex", gap: 6 }}>
          <button style={btnPrimary} onClick={() => setShowReceive(true)}>+ Receive</button>
          <button style={btnSecondary} onClick={() => setShowIssue(true)}>− Issue</button>
          <button style={btnSecondary} onClick={exportCSV}>⬇ CSV</button>
        </div>
      }>
      <InventoryTabs active="stock" />
      <FilterBar search={search} onSearch={setSearch}
        filters={[
          { label: "Item", value: fItem, onChange: setFItem,
            options: [{ value: "", label: "All Items" },
                      ...items.map((i: any) => ({ value: String(i.id), label: `${i.code} - ${i.name}` }))] },
          { label: "Location", value: fLocation, onChange: setFLocation,
            options: [{ value: "", label: "All Locations" },
                      ...locations.map((l: any) => ({ value: String(l.id), label: l.code }))] },
        ]} />
      <ErrorBox msg={err} />
      {loading ? <div>Loading...</div> : (
        <div style={{ background: "#fff", borderRadius: 10, border: `1px solid ${C.BORDER}`, overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
            <thead>
              <tr style={{ background: "#f8fafc", textAlign: "left" }}>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Item</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Location</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Quantity</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Unit</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Batch</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Expiry</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && (
                <tr><td colSpan={6} style={{ padding: "1rem", textAlign: "center", color: C.MUTED }}>No stock rows</td></tr>
              )}
              {rows.map((r: any) => (
                <tr key={r.id} style={{ borderTop: "1px solid #f1f5f9" }}>
                  <td style={{ padding: "0.5rem 0.6rem" }}>
                    <div style={{ fontWeight: 600 }}>{r.item_code}</div>
                    <div style={{ fontSize: "0.72rem", color: C.MUTED }}>{r.item_name}</div>
                  </td>
                  <td style={{ padding: "0.5rem 0.6rem" }}>{r.location_code}</td>
                  <td style={{ padding: "0.5rem 0.6rem", fontWeight: 700 }}>{r.quantity}</td>
                  <td style={{ padding: "0.5rem 0.6rem" }}>{r.unit}</td>
                  <td style={{ padding: "0.5rem 0.6rem", color: C.MUTED }}>{r.batch_number || "-"}</td>
                  <td style={{ padding: "0.5rem 0.6rem", color: C.MUTED }}>{r.expiry_date || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <ReceiveStockModal open={showReceive} onClose={() => setShowReceive(false)} onDone={reload} />
      <IssueStockModal open={showIssue} onClose={() => setShowIssue(false)} onDone={reload} />
    </PageShell>
  );
}
