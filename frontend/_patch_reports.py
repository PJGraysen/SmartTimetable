from pathlib import Path
p = Path("src/pages/inventory/Reports.tsx")
src = p.read_text(encoding="utf-8")

if "comprehensive" in src:
    print("[3] Reports already has comprehensive")
else:
    # Add tab to the tab list
    src = src.replace(
        'const [tab, setTab] = useState<"low-stock" | "expiring" | "valuation" | "movements">("low-stock");',
        'const [tab, setTab] = useState<"low-stock" | "expiring" | "valuation" | "movements" | "comprehensive">("low-stock");',
        1,
    )
    src = src.replace(
        'const movements = useLoad<any>(() => inventoryApi.reports.movements());',
        'const movements = useLoad<any>(() => inventoryApi.reports.movements());\n  const comprehensive = useLoad<any>(() => (inventoryApi as any).comprehensiveReport());',
        1,
    )
    src = src.replace(
        '''                : tab === "valuation" ? valuation
                : movements;''',
        '''                : tab === "valuation" ? valuation
                : tab === "comprehensive" ? comprehensive
                : movements;''',
        1,
    )
    src = src.replace(
        '''        {(["low-stock", "expiring", "valuation", "movements"] as const).map(t => (''',
        '''        {(["low-stock", "expiring", "valuation", "movements", "comprehensive"] as const).map(t => (''',
        1,
    )
    src = src.replace(
        '''              : t === "valuation" ? "Valuation"
              : "Movements"}''',
        '''              : t === "valuation" ? "Valuation"
              : t === "comprehensive" ? "Comprehensive"
              : "Movements"}''',
        1,
    )
    src = src.replace(
        '''          {tab === "movements" && <Movements data={movements.data} search={search} />}''',
        '''          {tab === "movements" && <Movements data={movements.data} search={search} />}
          {tab === "comprehensive" && <Comprehensive data={comprehensive.data} />}''',
        1,
    )
    # Add Comprehensive component at the bottom
    src = src.rstrip() + '''

function Comprehensive({ data }: any) {
  if (!data) return <div>Loading...</div>;
  const t = data.totals || {};
  function exportAll() {
    const lines: string[][] = [];
    lines.push(["Metric", "Value"]);
    Object.entries(t).forEach(([k, v]) => lines.push([k, String(v)]));
    downloadCSV("inventory_comprehensive_summary", ["Metric", "Value"], lines);
  }
  function exportCategory() {
    downloadCSV("items_by_category",
      ["Category", "Count", "Value"],
      (data.items_by_category || []).map((r: any) => [r.category__name, r.count, r.value]));
  }
  function exportDept() {
    downloadCSV("assets_by_department",
      ["Department", "Assets", "Value"],
      (data.assets_by_department || []).map((r: any) => [r.current_location__department__name, r.assets, r.value]));
  }
  function exportSupplier() {
    downloadCSV("items_by_supplier",
      ["Supplier", "Items"],
      (data.items_by_supplier || []).map((r: any) => [r.default_supplier__name, r.items]));
  }

  return (
    <div>
      <div style={{ display: "flex", gap: 6, marginBottom: 12, flexWrap: "wrap" }}>
        <button style={btnSecondary} onClick={exportAll}>⬇ Summary CSV</button>
        <button style={btnSecondary} onClick={exportCategory}>⬇ By Category</button>
        <button style={btnSecondary} onClick={exportDept}>⬇ By Department</button>
        <button style={btnSecondary} onClick={exportSupplier}>⬇ By Supplier</button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10, marginBottom: 16 }}>
        <Stat label="Active Items" value={t.items_active} />
        <Stat label="Retired Items" value={t.items_retired} />
        <Stat label="Assets" value={t.assets} />
        <Stat label="Asset Value" value={`KES ${Number(t.assets_value || 0).toLocaleString()}`} />
        <Stat label="Locations" value={t.locations} />
        <Stat label="Departments" value={t.departments} />
        <Stat label="Suppliers" value={t.suppliers} />
      </div>

      <h3 style={{ margin: "12px 0 6px", color: C.BROWN }}>Items by Category</h3>
      <table style={{ width: "100%", fontSize: "0.85rem", marginBottom: 16 }}>
        <thead><tr style={{ textAlign: "left", color: C.MUTED }}>
          <th style={{ padding: 6 }}>Category</th>
          <th style={{ padding: 6 }}>Items</th>
          <th style={{ padding: 6 }}>Value</th>
        </tr></thead>
        <tbody>
          {(data.items_by_category || []).map((r: any, i: number) => (
            <tr key={i} style={{ borderTop: "1px solid #f1f5f9" }}>
              <td style={{ padding: 6 }}>{r.category__name}</td>
              <td style={{ padding: 6 }}>{r.count}</td>
              <td style={{ padding: 6 }}>KES {Number(r.value || 0).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3 style={{ margin: "12px 0 6px", color: C.BROWN }}>Assets by Department</h3>
      <table style={{ width: "100%", fontSize: "0.85rem", marginBottom: 16 }}>
        <thead><tr style={{ textAlign: "left", color: C.MUTED }}>
          <th style={{ padding: 6 }}>Department</th>
          <th style={{ padding: 6 }}>Assets</th>
          <th style={{ padding: 6 }}>Value</th>
        </tr></thead>
        <tbody>
          {(data.assets_by_department || []).map((r: any, i: number) => (
            <tr key={i} style={{ borderTop: "1px solid #f1f5f9" }}>
              <td style={{ padding: 6 }}>{r.current_location__department__name || "Unassigned"}</td>
              <td style={{ padding: 6 }}>{r.assets}</td>
              <td style={{ padding: 6 }}>KES {Number(r.value || 0).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3 style={{ margin: "12px 0 6px", color: C.BROWN }}>Items by Supplier</h3>
      <table style={{ width: "100%", fontSize: "0.85rem" }}>
        <thead><tr style={{ textAlign: "left", color: C.MUTED }}>
          <th style={{ padding: 6 }}>Supplier</th>
          <th style={{ padding: 6 }}>Items</th>
        </tr></thead>
        <tbody>
          {(data.items_by_supplier || []).map((r: any, i: number) => (
            <tr key={i} style={{ borderTop: "1px solid #f1f5f9" }}>
              <td style={{ padding: 6 }}>{r.default_supplier__name}</td>
              <td style={{ padding: 6 }}>{r.items}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Stat({ label, value }: any) {
  return (
    <Card>
      <div style={{ fontSize: "0.72rem", color: C.MUTED, textTransform: "uppercase" }}>{label}</div>
      <div style={{ fontSize: "1.3rem", fontWeight: 700, color: C.BROWN, marginTop: 4 }}>{value}</div>
    </Card>
  );
}
'''
    p.write_text(src, encoding="utf-8")
    print("[3] Reports comprehensive tab added")
