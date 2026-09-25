import {Card, C, PageShell, useLoad, ErrorBox, InventoryTabs} from "./_shared";
import { inventoryApi } from "../../services/inventory";

export default function InventoryDashboard() {
  const { data, err, loading } = useLoad<any>(() => inventoryApi.dashboard());
  if (loading) return <PageShell title="Inventory Dashboard">
      <InventoryTabs active="dashboard" />Loading...</PageShell>;
  if (err) return <PageShell title="Inventory Dashboard"><ErrorBox msg={err} /></PageShell>;
  const t = data.totals || {};
  const cond = data.assets_by_condition || {};
  const stat = data.assets_by_status || {};

  return (
    <PageShell title="Inventory Dashboard" subtitle="Live snapshot of assets, stock, and movements">
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginBottom: 16 }}>
        <Stat label="Total Assets" value={t.assets ?? 0} />
        <Stat label="Total Items" value={t.items ?? 0} />
        <Stat label="Locations" value={t.locations ?? 0} />
        <Stat label="Departments" value={t.departments ?? 0} />
        <Stat label="Suppliers" value={t.suppliers ?? 0} />
        <Stat label="Asset Value" value={`KES ${Number(t.asset_value ?? 0).toLocaleString()}`} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 16 }}>
        <Card>
          <h3 style={{ margin: "0 0 10px", fontSize: "0.95rem", color: C.BROWN }}>Assets by Condition</h3>
          {Object.entries(cond).length === 0 ? <div style={{ color: C.MUTED, fontSize: "0.85rem" }}>No data</div> :
            Object.entries(cond).map(([k, v]) => (
              <Bar key={k} label={k} value={v as number} max={Math.max(...Object.values(cond) as number[]) || 1} />
            ))}
        </Card>
        <Card>
          <h3 style={{ margin: "0 0 10px", fontSize: "0.95rem", color: C.BROWN }}>Assets by Status</h3>
          {Object.entries(stat).length === 0 ? <div style={{ color: C.MUTED, fontSize: "0.85rem" }}>No data</div> :
            Object.entries(stat).map(([k, v]) => (
              <Bar key={k} label={k} value={v as number} max={Math.max(...Object.values(stat) as number[]) || 1} />
            ))}
        </Card>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        <Card>
          <h3 style={{ margin: "0 0 10px", fontSize: "0.95rem", color: C.BROWN }}>Low Stock</h3>
          {(!data.low_stock || data.low_stock.length === 0)
            ? <div style={{ color: C.MUTED, fontSize: "0.85rem" }}>All items above min stock</div>
            : <ul style={{ margin: 0, paddingLeft: 18, fontSize: "0.85rem" }}>
                {data.low_stock.map((s: any, i: number) => (
                  <li key={i} style={{ color: "#b91c1c" }}>
                    <b>{s.item_code}</b> {s.item_name} @ {s.location}: {s.quantity}/{s.min_stock} {s.unit}
                  </li>
                ))}
              </ul>}
        </Card>
        <Card>
          <h3 style={{ margin: "0 0 10px", fontSize: "0.95rem", color: C.BROWN }}>Warranty / Maintenance due (30d)</h3>
          <div style={{ fontSize: "0.85rem" }}>
            {(data.warranty_due_30d || []).map((x: any, i: number) => (
              <div key={`w${i}`} style={{ marginBottom: 4 }}>🔧 <b>{x.tag}</b> {x.item__name} — exp {x.warranty_expiry}</div>
            ))}
            {(data.maintenance_due_30d || []).map((x: any, i: number) => (
              <div key={`m${i}`} style={{ marginBottom: 4 }}>📅 <b>{x.asset__tag}</b> {x.asset__item__name} — due {x.next_due}</div>
            ))}
            {(data.warranty_due_30d || []).length === 0 && (data.maintenance_due_30d || []).length === 0 && (
              <div style={{ color: C.MUTED }}>Nothing due</div>
            )}
          </div>
        </Card>
      </div>

      <div style={{ marginTop: 16 }}>
        <Card>
          <h3 style={{ margin: "0 0 10px", fontSize: "0.95rem", color: C.BROWN }}>Recent Movements</h3>
          {(!data.recent_movements || data.recent_movements.length === 0)
            ? <div style={{ color: C.MUTED, fontSize: "0.85rem" }}>No movements yet</div>
            : <table style={{ width: "100%", fontSize: "0.83rem", borderCollapse: "collapse" }}>
                <thead><tr style={{ textAlign: "left", color: C.MUTED }}>
                  <th style={{ padding: "4px 8px" }}>When</th>
                  <th style={{ padding: "4px 8px" }}>Type</th>
                  <th style={{ padding: "4px 8px" }}>Item</th>
                  <th style={{ padding: "4px 8px" }}>From → To</th>
                  <th style={{ padding: "4px 8px" }}>Qty</th>
                </tr></thead>
                <tbody>
                  {data.recent_movements.map((m: any, i: number) => (
                    <tr key={i} style={{ borderTop: "1px solid #f1f5f9" }}>
                      <td style={{ padding: "4px 8px" }}>{new Date(m.occurred_at).toLocaleString()}</td>
                      <td style={{ padding: "4px 8px" }}>{m.movement_type}</td>
                      <td style={{ padding: "4px 8px" }}>{m.item__code} {m.item__name}</td>
                      <td style={{ padding: "4px 8px" }}>{m.from_location__code || "—"} → {m.to_location__code || "—"}</td>
                      <td style={{ padding: "4px 8px" }}>{m.quantity}</td>
                    </tr>
                  ))}
                </tbody>
              </table>}
        </Card>
      </div>
    </PageShell>
  );
}

function Stat({ label, value }: { label: string; value: any }) {
  return (
    <Card>
      <div style={{ fontSize: "0.78rem", color: C.MUTED, textTransform: "uppercase", letterSpacing: 0.6 }}>{label}</div>
      <div style={{ fontSize: "1.5rem", fontWeight: 700, color: C.BROWN, marginTop: 4 }}>{value}</div>
    </Card>
  );
}

function Bar({ label, value, max }: { label: string; value: number; max: number }) {
  const pct = Math.max(4, Math.round((value / (max || 1)) * 100));
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", color: C.MUTED, marginBottom: 3 }}>
        <span>{label}</span><span>{value}</span>
      </div>
      <div style={{ height: 8, background: "#f1f5f9", borderRadius: 4, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: C.SKY }} />
      </div>
    </div>
  );
}
