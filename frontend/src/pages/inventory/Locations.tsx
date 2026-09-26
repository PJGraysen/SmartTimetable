import { useMemo, useState, useEffect } from "react";
import {
  C, ErrorBox, PageShell, InventoryTabs, Drawer, StatusPill,
  KV, SectionTitle, FilterBar, btnPrimary, btnSecondary, smallBtn,
  downloadCSV, useLoad,
} from "./_shared";
import { NewLocationModal } from "./Forms2";
import { inventoryApi } from "../../services/inventory";

const TYPES = ["LAB","OFFICE","STORE","CLASSROOM","LIBRARY","HALL","SPORTS","OTHER"];

export default function Locations() {
  const { data, err, loading, reload } = useLoad<any[]>(() => inventoryApi.locations.list());
  const [search, setSearch] = useState("");
  const [fType, setFType] = useState("");
  const [drawerId, setDrawerId] = useState<number | null>(null);
  const [showNew, setShowNew] = useState(false);

  const rows = useMemo(() => {
    const s = search.toLowerCase();
    return (data || []).filter((r: any) => {
      if (fType && r.location_type !== fType) return false;
      if (s) {
        const hay = [r.code, r.name, r.department_name, r.description].map(x => String(x || "")).join(" ").toLowerCase();
        if (!hay.includes(s)) return false;
      }
      return true;
    });
  }, [data, search, fType]);

  function exportCSV() {
    downloadCSV("locations",
      ["Code", "Name", "Type", "Department", "Description"],
      rows.map((r: any) => [r.code, r.name, r.location_type, r.department_name, r.description]));
  }

  async function remove(id: number, name: string) {
    if (!confirm(`Delete location "${name}"? This cannot be undone.`)) return;
    try {
      await inventoryApi.locations.remove(id);
      reload();
    } catch (e: any) {
      alert("Delete failed: " + (e?.response?.data?.detail || String(e)));
    }
  }

  return (
    <PageShell title="Locations" subtitle="Labs, offices, stores, classrooms - click for full contents"
      actions={
        <div style={{ display: "flex", gap: 6 }}>
          <button style={btnPrimary} onClick={() => setShowNew(true)}>+ New Location</button>
          <button style={btnSecondary} onClick={exportCSV}>CSV</button>
        </div>
      }>
      <InventoryTabs active="locations" />
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
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Code</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Name</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Type</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Department</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && (
                <tr><td colSpan={5} style={{ padding: "1rem", textAlign: "center", color: C.MUTED }}>No locations match filters</td></tr>
              )}
              {rows.map((r: any) => (
                <tr key={r.id} style={{ borderTop: "1px solid #f1f5f9" }}>
                  <td style={{ padding: "0.5rem 0.6rem", fontWeight: 600 }}>
                    <a href="#" onClick={(e) => { e.preventDefault(); setDrawerId(r.id); }}
                       style={{ color: C.BROWN, textDecoration: "none" }}>{r.code}</a>
                  </td>
                  <td style={{ padding: "0.5rem 0.6rem" }}>{r.name}</td>
                  <td style={{ padding: "0.5rem 0.6rem" }}><StatusPill value={r.location_type} /></td>
                  <td style={{ padding: "0.5rem 0.6rem" }}>{r.department_name || "-"}</td>
                  <td style={{ padding: "0.5rem 0.6rem" }}>
                    <div style={{ display: "flex", gap: 4 }}>
                      <button style={smallBtn} onClick={() => setDrawerId(r.id)}>Contents</button>
                      <button style={{ ...smallBtn, color: C.RED, borderColor: C.RED }}
                              onClick={() => remove(r.id, r.name)}>Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <LocationDrawer locationId={drawerId} onClose={() => setDrawerId(null)} />
      <NewLocationModal open={showNew} onClose={() => setShowNew(false)} onDone={reload} />
    </PageShell>
  );
}

function LocationDrawer({ locationId, onClose }: { locationId: number | null; onClose: () => void }) {
  const [d, setD] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (locationId == null) { setD(null); return; }
    setLoading(true);
    (inventoryApi as any).locationContents(locationId)
      .then((x: any) => setD(x)).catch(() => setD(null)).finally(() => setLoading(false));
  }, [locationId]);

  if (locationId == null) return null;
  const l = d?.location;

  return (
    <Drawer open={!!locationId} onClose={onClose} title={l?.name || "Location"} subtitle={l?.code}>
      {loading ? <div>Loading...</div> : !l ? <div>Not found</div> : (
        <>
          <SectionTitle>Details</SectionTitle>
          <KV label="Code" value={l.code} />
          <KV label="Type" value={<StatusPill value={l.location_type} />} />
          <KV label="Department" value={l.department || "-"} />
          <KV label="Parent" value={l.parent || "-"} />
          <KV label="Total Value" value={`KES ${Number(d.total_value || 0).toLocaleString()}`} />

          <SectionTitle>Assets ({d.assets_count || 0})</SectionTitle>
          {(d.assets || []).length === 0 && <div style={{ color: C.MUTED, fontSize: "0.85rem" }}>No assets here</div>}
          {(d.assets || []).slice(0, 40).map((a: any) => (
            <div key={a.id} style={{ padding: "0.3rem 0", borderBottom: "1px solid #f1f5f9", fontSize: "0.82rem", display: "flex", justifyContent: "space-between", gap: 8 }}>
              <span style={{ fontWeight: 600 }}>{a.tag}</span>
              <span style={{ color: C.MUTED, flex: 1 }}>{a.item__name}</span>
              <StatusPill value={a.status} />
            </div>
          ))}

          <SectionTitle>Stock ({d.stock_count || 0})</SectionTitle>
          {(d.stock || []).length === 0 && <div style={{ color: C.MUTED, fontSize: "0.85rem" }}>No bulk stock</div>}
          {(d.stock || []).map((s: any) => (
            <div key={s.id} style={{ padding: "0.3rem 0", borderBottom: "1px solid #f1f5f9", fontSize: "0.82rem", display: "flex", justifyContent: "space-between" }}>
              <span>{s.item__code} {s.item__name}</span>
              <span>{s.quantity} {s.item__unit}</span>
            </div>
          ))}
        </>
      )}
    </Drawer>
  );
}
