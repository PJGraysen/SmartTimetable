import { useEffect, useMemo, useState } from "react";
import {
  C, ErrorBox, PageShell, InventoryTabs, Drawer, StatusPill,
  KV, SectionTitle, FilterBar, btnSecondary, smallBtn,
  downloadCSV, useLoad,
} from "./_shared";
import { inventoryApi } from "../../services/inventory";

export default function Departments() {
  const { data, err, loading } = useLoad<any[]>(() => inventoryApi.departments.list());
  const [search, setSearch] = useState("");
  const [drawerId, setDrawerId] = useState<number | null>(null);

  const rows = useMemo(() => {
    const s = search.toLowerCase();
    return (data || []).filter((r: any) => {
      if (!s) return true;
      const hay = [r.code, r.name, r.description].map(x => String(x || "")).join(" ").toLowerCase();
      return hay.includes(s);
    });
  }, [data, search]);

  function exportCSV() {
    downloadCSV("departments",
      ["Code", "Name", "Description", "Active"],
      rows.map((r: any) => [r.code, r.name, r.description, r.is_active ? "yes" : "no"]));
  }

  return (
    <PageShell title="Departments" subtitle="Organisational units — click for summary"
      actions={<button style={btnSecondary} onClick={exportCSV}>⬇ CSV</button>}>
      <InventoryTabs active="departments" />
      <FilterBar search={search} onSearch={setSearch} />
      <ErrorBox msg={err} />
      {loading ? <div>Loading...</div> : (
        <div style={{ background: "#fff", borderRadius: 10, border: `1px solid ${C.BORDER}`, overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
            <thead>
              <tr style={{ background: "#f8fafc", textAlign: "left" }}>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Code</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Name</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Description</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Active</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && (
                <tr><td colSpan={5} style={{ padding: "1rem", textAlign: "center", color: C.MUTED }}>No departments</td></tr>
              )}
              {rows.map((r: any) => (
                <tr key={r.id} style={{ borderTop: "1px solid #f1f5f9" }}>
                  <td style={{ padding: "0.5rem 0.6rem", fontWeight: 600 }}>
                    <a href="#" onClick={(e) => { e.preventDefault(); setDrawerId(r.id); }}
                       style={{ color: C.BROWN, textDecoration: "none" }}>{r.code}</a>
                  </td>
                  <td style={{ padding: "0.5rem 0.6rem" }}>{r.name}</td>
                  <td style={{ padding: "0.5rem 0.6rem", color: C.MUTED }}>{r.description || "-"}</td>
                  <td style={{ padding: "0.5rem 0.6rem" }}>{r.is_active ? "✓" : "-"}</td>
                  <td style={{ padding: "0.5rem 0.6rem" }}>
                    <button style={smallBtn} onClick={() => setDrawerId(r.id)}>Summary</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <DepartmentDrawer departmentId={drawerId} onClose={() => setDrawerId(null)} />
    </PageShell>
  );
}

function DepartmentDrawer({ departmentId, onClose }: { departmentId: number | null; onClose: () => void }) {
  const [d, setD] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (departmentId == null) { setD(null); return; }
    setLoading(true);
    (inventoryApi as any).departmentSummary(departmentId)
      .then((x: any) => setD(x)).catch(() => setD(null)).finally(() => setLoading(false));
  }, [departmentId]);

  if (departmentId == null) return null;
  const dep = d?.department;

  return (
    <Drawer open={!!departmentId} onClose={onClose} title={dep?.name || "Department"} subtitle={dep?.code}>
      {loading ? <div>Loading...</div> : !dep ? <div>Not found</div> : (
        <>
          <SectionTitle>Overview</SectionTitle>
          <KV label="Code" value={dep.code} />
          <KV label="Name" value={dep.name} />
          <KV label="Description" value={dep.description || "-"} />
          <KV label="Locations" value={d.locations?.length || 0} />
          <KV label="Assets" value={d.asset_count} />
          <KV label="Asset Value" value={`KES ${Number(d.asset_value).toLocaleString()}`} />

          <SectionTitle>By Condition</SectionTitle>
          {Object.keys(d.by_condition || {}).length === 0
            ? <div style={{ color: C.MUTED, fontSize: "0.85rem" }}>No assets</div>
            : Object.entries(d.by_condition || {}).map(([k, v]) => (
                <KV key={k} label={k} value={v} />
              ))}

          <SectionTitle>By Status</SectionTitle>
          {Object.keys(d.by_status || {}).length === 0
            ? <div style={{ color: C.MUTED, fontSize: "0.85rem" }}>No assets</div>
            : Object.entries(d.by_status || {}).map(([k, v]) => (
                <KV key={k} label={k} value={v} />
              ))}

          <SectionTitle>Locations ({d.locations?.length || 0})</SectionTitle>
          {(d.locations || []).map((l: any) => (
            <div key={l.id} style={{ padding: "0.3rem 0", borderBottom: "1px solid #f1f5f9", fontSize: "0.82rem", display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontWeight: 600 }}>{l.code}</span>
              <span style={{ color: C.MUTED, flex: 1, marginLeft: 8 }}>{l.name}</span>
              <StatusPill value={l.location_type} />
            </div>
          ))}
        </>
      )}
    </Drawer>
  );
}
