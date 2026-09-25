
import { useState } from "react";
import {
  Card, C, ErrorBox, PageShell, useLoad, downloadCSV, FilterBar, btnSecondary, InventoryTabs,
} from "./_shared";
import { inventoryApi } from "../../services/inventory";

export default function Reports() {
  const [tab, setTab] = useState<"low-stock" | "expiring" | "valuation" | "movements">("low-stock");
  const [search, setSearch] = useState("");

  const lowStock = useLoad<any>(() => inventoryApi.reports.lowStock());
  const expiring = useLoad<any>(() => inventoryApi.reports.expiring());
  const valuation = useLoad<any>(() => inventoryApi.reports.valuation());
  const movements = useLoad<any>(() => inventoryApi.reports.movements());

  const current = tab === "low-stock" ? lowStock
                : tab === "expiring" ? expiring
                : tab === "valuation" ? valuation
                : movements;

  return (
    <PageShell title="Inventory Reports" subtitle="Operational reports across the whole estate">
      <InventoryTabs active="reports" />
      <FilterBar search={search} onSearch={setSearch} />

      <div style={{ display: "flex", gap: 6, marginBottom: 12, flexWrap: "wrap" }}>
        {(["low-stock", "expiring", "valuation", "movements"] as const).map(t => (
          <button key={t} style={{
            ...btnSecondary,
            background: tab === t ? C.BROWN : "#fff",
            color: tab === t ? "#fff" : C.BROWN,
            fontWeight: tab === t ? 700 : 500,
          }} onClick={() => setTab(t)}>
            {t === "low-stock" ? "Low Stock"
              : t === "expiring" ? "Expiring Soon"
              : t === "valuation" ? "Valuation"
              : "Movements"}
          </button>
        ))}
      </div>

      <ErrorBox msg={current.err} />
      {current.loading ? <div>Loading…</div> : (
        <Card>
          {tab === "low-stock" && <LowStockTable data={lowStock.data} search={search} />}
          {tab === "expiring" && <ExpiringTable data={expiring.data} search={search} />}
          {tab === "valuation" && <Valuation data={valuation.data} />}
          {tab === "movements" && <Movements data={movements.data} search={search} />}
        </Card>
      )}
    </PageShell>
  );
}

function LowStockTable({ data, search }: any) {
  const rows = (data?.rows || []).filter((r: any) =>
    !search || (r.item_name + r.item_code + r.location_code).toLowerCase().includes(search.toLowerCase())
  );
  function exportCSV() {
    downloadCSV("low_stock", ["Item Code", "Item", "Location", "Qty", "Min", "Reorder", "Unit", "Shortfall"],
      rows.map((r: any) => [r.item_code, r.item_name, r.location_code, r.quantity, r.min_stock, r.reorder_stock, r.unit, r.shortfall]));
  }
  return (
    <>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <h3 style={{ margin: 0, color: C.BROWN }}>Low Stock ({rows.length})</h3>
        <button style={btnSecondary} onClick={exportCSV}>⬇ CSV</button>
      </div>
      <table style={{ width: "100%", fontSize: "0.85rem", borderCollapse: "collapse" }}>
        <thead><tr style={{ textAlign: "left", color: C.MUTED }}>
          <th style={{ padding: 6 }}>Item</th><th style={{ padding: 6 }}>Location</th>
          <th style={{ padding: 6 }}>Qty</th><th style={{ padding: 6 }}>Min</th>
          <th style={{ padding: 6 }}>Shortfall</th>
        </tr></thead>
        <tbody>
          {rows.map((r: any, i: number) => (
            <tr key={i} style={{ borderTop: "1px solid #f1f5f9", background: r.shortfall > 5 ? "#fef2f2" : "" }}>
              <td style={{ padding: 6 }}><b>{r.item_code}</b> {r.item_name}</td>
              <td style={{ padding: 6 }}>{r.location_code}</td>
              <td style={{ padding: 6 }}>{r.quantity} {r.unit}</td>
              <td style={{ padding: 6 }}>{r.min_stock}</td>
              <td style={{ padding: 6, color: "#b91c1c", fontWeight: 700 }}>{r.shortfall}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

function ExpiringTable({ data, search }: any) {
  const rows = (data?.rows || []).filter((r: any) =>
    !search || (r.item_name + r.item_code + r.location_code).toLowerCase().includes(search.toLowerCase())
  );
  function exportCSV() {
    downloadCSV("expiring_stock", ["Item", "Location", "Qty", "Unit", "Batch", "Expiry", "Days Left"],
      rows.map((r: any) => [r.item_name, r.location_code, r.quantity, r.unit, r.batch_number, r.expiry_date, r.days_left]));
  }
  return (
    <>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
        <h3 style={{ margin: 0, color: C.BROWN }}>Expiring Soon ({rows.length})</h3>
        <button style={btnSecondary} onClick={exportCSV}>⬇ CSV</button>
      </div>
      <table style={{ width: "100%", fontSize: "0.85rem", borderCollapse: "collapse" }}>
        <thead><tr style={{ textAlign: "left", color: C.MUTED }}>
          <th style={{ padding: 6 }}>Item</th><th style={{ padding: 6 }}>Location</th>
          <th style={{ padding: 6 }}>Qty</th><th style={{ padding: 6 }}>Batch</th>
          <th style={{ padding: 6 }}>Expiry</th><th style={{ padding: 6 }}>Days</th>
        </tr></thead>
        <tbody>
          {rows.map((r: any, i: number) => (
            <tr key={i} style={{ borderTop: "1px solid #f1f5f9", background: r.days_left < 30 ? "#fef3c7" : "" }}>
              <td style={{ padding: 6 }}>{r.item_name}</td>
              <td style={{ padding: 6 }}>{r.location_code}</td>
              <td style={{ padding: 6 }}>{r.quantity} {r.unit}</td>
              <td style={{ padding: 6 }}>{r.batch_number || "—"}</td>
              <td style={{ padding: 6 }}>{r.expiry_date}</td>
              <td style={{ padding: 6 }}>{r.days_left}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

function Valuation({ data }: any) {
  if (!data) return <div>Loading…</div>;
  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 12 }}>
        <div><div style={{ color: C.MUTED, fontSize: "0.78rem" }}>Total Asset Value</div>
          <div style={{ fontSize: "1.3rem", fontWeight: 700 }}>KES {Number(data.total_asset_value).toLocaleString()}</div></div>
        <div><div style={{ color: C.MUTED, fontSize: "0.78rem" }}>Items</div>
          <div style={{ fontSize: "1.3rem", fontWeight: 700 }}>{data.total_items}</div></div>
        <div><div style={{ color: C.MUTED, fontSize: "0.78rem" }}>Assets</div>
          <div style={{ fontSize: "1.3rem", fontWeight: 700 }}>{data.total_assets}</div></div>
      </div>
      <h3 style={{ margin: "12px 0 6px", color: C.BROWN }}>Assets by Department</h3>
      <table style={{ width: "100%", fontSize: "0.85rem" }}>
        <thead><tr style={{ textAlign: "left", color: C.MUTED }}>
          <th style={{ padding: 6 }}>Department</th><th style={{ padding: 6 }}>Assets</th><th style={{ padding: 6 }}>Value</th>
        </tr></thead>
        <tbody>
          {(data.assets_by_department || []).map((d: any, i: number) => (
            <tr key={i} style={{ borderTop: "1px solid #f1f5f9" }}>
              <td style={{ padding: 6 }}>{d.current_location__department__name || "Unassigned"}</td>
              <td style={{ padding: 6 }}>{d.count}</td>
              <td style={{ padding: 6 }}>KES {Number(d.value || 0).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Movements({ data, search }: any) {
  if (!data) return <div>Loading…</div>;
  const byType = (data.by_type || []).filter((r: any) =>
    !search || String(r.movement_type).toLowerCase().includes(search.toLowerCase())
  );
  return (
    <div>
      <h3 style={{ margin: "0 0 8px", color: C.BROWN }}>By Type (last {data.window_days} days)</h3>
      <table style={{ width: "100%", fontSize: "0.85rem", marginBottom: 16 }}>
        <thead><tr style={{ textAlign: "left", color: C.MUTED }}>
          <th style={{ padding: 6 }}>Type</th><th style={{ padding: 6 }}>Count</th><th style={{ padding: 6 }}>Total Qty</th>
        </tr></thead>
        <tbody>
          {byType.map((r: any, i: number) => (
            <tr key={i} style={{ borderTop: "1px solid #f1f5f9" }}>
              <td style={{ padding: 6 }}>{r.movement_type}</td>
              <td style={{ padding: 6 }}>{r.count}</td>
              <td style={{ padding: 6 }}>{r.total_qty}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <h3 style={{ margin: "0 0 8px", color: C.BROWN }}>Top Items</h3>
      <table style={{ width: "100%", fontSize: "0.85rem" }}>
        <thead><tr style={{ textAlign: "left", color: C.MUTED }}>
          <th style={{ padding: 6 }}>Item</th><th style={{ padding: 6 }}>Count</th><th style={{ padding: 6 }}>Total Qty</th>
        </tr></thead>
        <tbody>
          {(data.top_items || []).map((r: any, i: number) => (
            <tr key={i} style={{ borderTop: "1px solid #f1f5f9" }}>
              <td style={{ padding: 6 }}>{r.item_code} {r.item_name}</td>
              <td style={{ padding: 6 }}>{r.count}</td>
              <td style={{ padding: 6 }}>{r.total_qty}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
