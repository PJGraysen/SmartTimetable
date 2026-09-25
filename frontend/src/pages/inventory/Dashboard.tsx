import { useNavigate } from "react-router-dom";
import {
  Card, C, ErrorBox, PageShell, InventoryTabs, useLoad,
  StatusPill, SectionTitle, smallBtn,
} from "./_shared";
import { inventoryApi } from "../../services/inventory";

export default function InventoryDashboard() {
  const navigate = useNavigate();
  const { data, err, loading } = useLoad<any>(() => (inventoryApi as any).dashboardV2());

  if (loading) return <PageShell title="Inventory Dashboard"><InventoryTabs active="dashboard" /><div>Loading...</div></PageShell>;
  if (err) return <PageShell title="Inventory Dashboard"><InventoryTabs active="dashboard" /><ErrorBox msg={err} /></PageShell>;

  const total_assets = data?.total_assets ?? 0;
  const total_value = data?.asset_value ?? 0;
  const byCond = data?.by_condition || {};
  const byStat = data?.by_status || {};
  const byDept = data?.assets_by_department || [];
  const lowStock = data?.low_stock || [];
  const recent = data?.recent_movements || [];

  return (
    <PageShell title="Inventory Dashboard" subtitle="Live snapshot of assets, stock, and movements">
      <InventoryTabs active="dashboard" />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginBottom: 16 }}>
        <Stat label="Total Assets" value={total_assets} onClick={() => navigate("/inventory/assets")} />
        <Stat label="Asset Value" value={`KES ${Number(total_value).toLocaleString()}`} />
        <Stat label="Low Stock Items" value={lowStock.length} onClick={() => navigate("/inventory/reports")} highlight={lowStock.length > 0} />
        <Stat label="Departments" value={byDept.length} onClick={() => navigate("/inventory/departments")} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 16 }}>
        <Card>
          <SectionTitle>Assets by Condition</SectionTitle>
          {Object.keys(byCond).length === 0
            ? <div style={{ color: C.MUTED, fontSize: "0.85rem" }}>No data</div>
            : Object.entries(byCond).map(([k, v]) => (
                <Bar key={k} label={k} value={v as number}
                     max={Math.max(...(Object.values(byCond) as number[])) || 1}
                     color="#22C55E" />
              ))}
        </Card>
        <Card>
          <SectionTitle>Assets by Status</SectionTitle>
          {Object.keys(byStat).length === 0
            ? <div style={{ color: C.MUTED, fontSize: "0.85rem" }}>No data</div>
            : Object.entries(byStat).map(([k, v]) => (
                <Bar key={k} label={k} value={v as number}
                     max={Math.max(...(Object.values(byStat) as number[])) || 1}
                     color="#3B82F6" />
              ))}
        </Card>
      </div>

      <div style={{ marginBottom: 16 }}>
        <Card>
          <SectionTitle>Assets by Department</SectionTitle>
          {byDept.length === 0
            ? <div style={{ color: C.MUTED, fontSize: "0.85rem" }}>No data</div>
            : (
              <table style={{ width: "100%", fontSize: "0.85rem", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ textAlign: "left", color: C.MUTED }}>
                    <th style={{ padding: "4px 8px" }}>Department</th>
                    <th style={{ padding: "4px 8px" }}>Assets</th>
                    <th style={{ padding: "4px 8px" }}>Value</th>
                    <th style={{ padding: "4px 8px" }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {byDept.map((d: any, i: number) => (
                    <tr key={i} style={{ borderTop: "1px solid #f1f5f9" }}>
                      <td style={{ padding: "4px 8px", fontWeight: 500 }}>{d.current_location__department__name || "Unassigned"}</td>
                      <td style={{ padding: "4px 8px" }}>{d.count}</td>
                      <td style={{ padding: "4px 8px" }}>KES {Number(d.value || 0).toLocaleString()}</td>
                      <td style={{ padding: "4px 8px" }}>
                        {d.current_location__department__id && (
                          <button style={smallBtn}
                                  onClick={() => navigate(`/inventory/departments`)}>
                            View dept
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
        </Card>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 16 }}>
        <Card>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <SectionTitle>Low Stock</SectionTitle>
            <button style={smallBtn} onClick={() => navigate("/inventory/reports")}>View All</button>
          </div>
          {lowStock.length === 0
            ? <div style={{ color: C.MUTED, fontSize: "0.85rem" }}>All items above min stock</div>
            : <ul style={{ margin: 0, paddingLeft: 18, fontSize: "0.85rem" }}>
                {lowStock.slice(0, 8).map((s: any, i: number) => (
                  <li key={i} style={{ color: "#b91c1c", marginBottom: 3 }}>
                    <b>{s.item_code}</b> {s.item_name} @ {s.location_code}: {s.quantity}/{s.min_stock} {s.unit}
                  </li>
                ))}
              </ul>}
        </Card>
        <Card>
          <SectionTitle>Recent Movements</SectionTitle>
          {recent.length === 0
            ? <div style={{ color: C.MUTED, fontSize: "0.85rem" }}>No movements yet</div>
            : <div style={{ fontSize: "0.8rem" }}>
                {recent.slice(0, 6).map((m: any, i: number) => (
                  <div key={i} style={{ padding: "3px 0", borderBottom: "1px solid #f1f5f9" }}>
                    <b>{m.movement_type}</b> — {m.item_code} {m.item_name}{" "}
                    <span style={{ color: C.MUTED }}>
                      {m.from_location__code || "-"} → {m.to_location__code || "-"} · qty {m.quantity}
                    </span>
                  </div>
                ))}
              </div>}
        </Card>
      </div>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button style={smallBtn} onClick={() => navigate("/inventory/items")}>Items</button>
        <button style={smallBtn} onClick={() => navigate("/inventory/assets")}>Assets</button>
        <button style={smallBtn} onClick={() => navigate("/inventory/stock")}>Stock</button>
        <button style={smallBtn} onClick={() => navigate("/inventory/movements")}>Movements</button>
        <button style={smallBtn} onClick={() => navigate("/inventory/maintenance")}>Maintenance</button>
        <button style={smallBtn} onClick={() => navigate("/inventory/audits")}>Audits</button>
        <button style={smallBtn} onClick={() => navigate("/inventory/reports")}>Reports</button>
        <button style={smallBtn} onClick={() => navigate("/inventory/categories")}>Categories</button>
        <button style={smallBtn} onClick={() => navigate("/inventory/locations")}>Locations</button>
        <button style={smallBtn} onClick={() => navigate("/inventory/departments")}>Departments</button>
        <button style={smallBtn} onClick={() => navigate("/inventory/suppliers")}>Suppliers</button>
      </div>
    </PageShell>
  );
}

function Stat({ label, value, onClick, highlight }: {
  label: string; value: any; onClick?: () => void; highlight?: boolean;
}) {
  return (
    <Card style={{ cursor: onClick ? "pointer" : "default",
                   borderColor: highlight ? "#F97316" : undefined }}
          >
      <div onClick={onClick}>
        <div style={{ fontSize: "0.78rem", color: C.MUTED, textTransform: "uppercase", letterSpacing: 0.6 }}>{label}</div>
        <div style={{ fontSize: "1.5rem", fontWeight: 700, color: highlight ? "#F97316" : C.BROWN, marginTop: 4 }}>{value}</div>
      </div>
    </Card>
  );
}

function Bar({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const pct = Math.max(4, Math.round((value / (max || 1)) * 100));
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", color: C.MUTED, marginBottom: 3 }}>
        <span>{label}</span><span>{value}</span>
      </div>
      <div style={{ height: 8, background: "#f1f5f9", borderRadius: 4, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color }} />
      </div>
    </div>
  );
}
