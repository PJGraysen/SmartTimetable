import { useEffect, useMemo, useState } from "react";
import {
  C, ErrorBox, PageShell, InventoryTabs, Drawer, StatusPill,
  KV, SectionTitle, FilterBar, btnPrimary, btnSecondary, smallBtn,
  downloadCSV, useLoad,
} from "./_shared";
import { NewItemModal } from "./Forms";
import { inventoryApi } from "../../services/inventory";

export default function Items() {
  const { data, err, loading, reload } = useLoad<any[]>(() => inventoryApi.items.list());
  const [search, setSearch] = useState("");
  const [fCategory, setFCategory] = useState("");
  const [fTracking, setFTracking] = useState("");
  const [fRetired, setFRetired] = useState("active");
  const [drawerId, setDrawerId] = useState<number | null>(null);
  const [categories, setCategories] = useState<any[]>([]);
  const [showNew, setShowNew] = useState(false);

  useEffect(() => { inventoryApi.categories.list().then((c: any) => setCategories(c || [])); }, []);

  const rows = useMemo(() => {
    const s = search.toLowerCase();
    return (data || []).filter((r: any) => {
      if (fRetired === "active" && r.is_retired) return false;
      if (fRetired === "retired" && !r.is_retired) return false;
      if (fCategory && String(r.category) !== String(fCategory)) return false;
      if (fTracking && r.tracking_mode !== fTracking) return false;
      if (s) {
        const hay = [r.code, r.name, r.category_name].map(x => String(x || "")).join(" ").toLowerCase();
        if (!hay.includes(s)) return false;
      }
      return true;
    });
  }, [data, search, fCategory, fTracking, fRetired]);

  function exportCSV() {
    downloadCSV("items",
      ["Code", "Name", "Category", "Unit", "Tracking", "Unit Cost", "Min", "Reorder", "Retired"],
      rows.map((r: any) => [r.code, r.name, r.category_name, r.unit, r.tracking_mode,
                            r.unit_cost, r.min_stock, r.reorder_stock, r.is_retired ? "yes" : "no"]));
  }

  async function retire(id: number) {
    const reason = prompt("Reason for retiring this item?");
    if (!reason) return;
    await (inventoryApi as any).retireItem(id, reason);
    reload();
  }
  async function unretire(id: number) {
    if (!confirm("Restore this item to active catalogue?")) return;
    await (inventoryApi as any).unretireItem(id);
    reload();
  }

  return (
    <PageShell title="Items" subtitle="Catalogue of every item - click a row for stock and usage history"
      actions={
        <div style={{ display: "flex", gap: 6 }}>
          <button style={btnPrimary} onClick={() => setShowNew(true)}>+ New Item</button>
          <button style={btnSecondary} onClick={exportCSV}>CSV</button>
        </div>
      }>
      <InventoryTabs active="items" />
      <FilterBar search={search} onSearch={setSearch}
        filters={[
          { label: "Category", value: fCategory, onChange: setFCategory,
            options: [{ value: "", label: "All Categories" },
                      ...categories.map((c: any) => ({ value: String(c.id), label: c.name }))] },
          { label: "Tracking", value: fTracking, onChange: setFTracking,
            options: [{ value: "", label: "All Modes" },
                      { value: "INDIVIDUAL", label: "Individual" },
                      { value: "QUANTITY", label: "Quantity" }] },
          { label: "State", value: fRetired, onChange: setFRetired,
            options: [{ value: "active", label: "Active" },
                      { value: "retired", label: "Retired" },
                      { value: "", label: "All" }] },
        ]} />

      <ErrorBox msg={err} />
      {loading ? <div>Loading...</div> : (
        <div style={{ background: "#fff", borderRadius: 10, border: `1px solid ${C.BORDER}`, overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
            <thead>
              <tr style={{ background: "#f8fafc", textAlign: "left" }}>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Code</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Name</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Category</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Unit</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Tracking</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Unit Cost</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && (
                <tr><td colSpan={7} style={{ padding: "1rem", textAlign: "center", color: C.MUTED }}>No items match filters</td></tr>
              )}
              {rows.map((r: any) => (
                <tr key={r.id} style={{ borderTop: "1px solid #f1f5f9", opacity: r.is_retired ? 0.55 : 1 }}>
                  <td style={{ padding: "0.5rem 0.6rem", fontWeight: 600 }}>
                    <a href="#" onClick={(e) => { e.preventDefault(); setDrawerId(r.id); }}
                       style={{ color: C.BROWN, textDecoration: "none" }}>{r.code}</a>
                    {r.is_retired && <span style={{ marginLeft: 6, fontSize: "0.7rem", color: C.RED }}>[retired]</span>}
                  </td>
                  <td style={{ padding: "0.5rem 0.6rem" }}>{r.name}</td>
                  <td style={{ padding: "0.5rem 0.6rem" }}>{r.category_name || "-"}</td>
                  <td style={{ padding: "0.5rem 0.6rem" }}>{r.unit}</td>
                  <td style={{ padding: "0.5rem 0.6rem" }}><StatusPill value={r.tracking_mode} /></td>
                  <td style={{ padding: "0.5rem 0.6rem" }}>KES {Number(r.unit_cost || 0).toLocaleString()}</td>
                  <td style={{ padding: "0.5rem 0.6rem" }}>
                    <div style={{ display: "flex", gap: 4 }}>
                      <button style={smallBtn} onClick={() => setDrawerId(r.id)}>Details</button>
                      {!r.is_retired && <button style={smallBtn} onClick={() => retire(r.id)}>Retire</button>}
                      {r.is_retired && <button style={smallBtn} onClick={() => unretire(r.id)}>Restore</button>}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <ItemDrawer itemId={drawerId} onClose={() => setDrawerId(null)} />
      <NewItemModal open={showNew} onClose={() => setShowNew(false)} onDone={reload} />
    </PageShell>
  );
}

function ItemDrawer({ itemId, onClose }: { itemId: number | null; onClose: () => void }) {
  const [d, setD] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (itemId == null) { setD(null); return; }
    setLoading(true);
    (inventoryApi as any).itemDetail(itemId)
      .then((x: any) => setD(x)).catch(() => setD(null)).finally(() => setLoading(false));
  }, [itemId]);

  if (itemId == null) return null;
  const it = d?.item;

  return (
    <Drawer open={!!itemId} onClose={onClose} title={it?.name || "Item"} subtitle={it?.code}>
      {loading ? <div>Loading...</div> : !it ? <div>Not found</div> : (
        <>
          <SectionTitle>Details</SectionTitle>
          <KV label="Code" value={it.code} />
          <KV label="Category" value={it.category_name || "-"} />
          <KV label="Unit" value={it.unit} />
          <KV label="Tracking" value={<StatusPill value={it.tracking_mode} />} />
          <KV label="Unit Cost" value={`KES ${Number(it.unit_cost).toLocaleString()}`} />
          <KV label="Min Stock" value={it.min_stock} />
          <KV label="Reorder Point" value={it.reorder_stock} />
          <KV label="Supplier" value={it.supplier_name || "-"} />

          <SectionTitle>Stock ({d.stock?.length || 0} locations - total {d.total_quantity})</SectionTitle>
          {(d.stock || []).length === 0 && <div style={{ color: C.MUTED, fontSize: "0.85rem" }}>No stock recorded</div>}
          {(d.stock || []).map((s: any) => (
            <div key={s.id} style={{ padding: "0.35rem 0", borderBottom: "1px solid #f1f5f9", fontSize: "0.82rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ fontWeight: 600 }}>{s.location__code}</span>
                <span>{s.quantity}</span>
              </div>
              {s.batch_number && <div style={{ color: C.MUTED }}>Batch: {s.batch_number}</div>}
              {s.expiry_date && <div style={{ color: C.MUTED }}>Expires: {s.expiry_date}</div>}
            </div>
          ))}

          <SectionTitle>Serialized Assets ({d.assets_count || 0})</SectionTitle>
          {(d.assets || []).length === 0 && <div style={{ color: C.MUTED, fontSize: "0.85rem" }}>No serialized units</div>}
          {(d.assets || []).slice(0, 30).map((a: any) => (
            <div key={a.id} style={{ padding: "0.3rem 0", borderBottom: "1px solid #f1f5f9", fontSize: "0.82rem", display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontWeight: 600 }}>{a.tag}</span>
              <span style={{ color: C.MUTED }}>{a.current_location__code}</span>
              <StatusPill value={a.status} />
            </div>
          ))}

          <SectionTitle>Recent Movements ({d.usage?.length || 0})</SectionTitle>
          {(d.usage || []).length === 0 && <div style={{ color: C.MUTED, fontSize: "0.85rem" }}>No movements</div>}
          {(d.usage || []).slice(0, 15).map((m: any) => (
            <div key={m.id} style={{ padding: "0.35rem 0", borderBottom: "1px solid #f1f5f9", fontSize: "0.8rem" }}>
              <div style={{ fontWeight: 600 }}>{m.movement_type} - qty {m.quantity}</div>
              <div style={{ color: C.MUTED }}>
                {new Date(m.occurred_at).toLocaleDateString()} - {m.from_location__code || "-"} to {m.to_location__code || "-"}
              </div>
            </div>
          ))}
        </>
      )}
    </Drawer>
  );
}
