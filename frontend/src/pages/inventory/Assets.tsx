import { useEffect, useMemo, useState } from "react";
import {
  C, ErrorBox, PageShell, InventoryTabs, Drawer, StatusPill,
  BulkBar, KV, SectionTitle, FilterBar, btnPrimary, btnSecondary,
  smallBtn, downloadCSV, useLoad,
} from "./_shared";
import {
  TransferAssetModal, ScheduleMaintenanceModal, ChangeStatusModal,
} from "./ActionModals";
import { NewAssetModal } from "./Forms";
import { inventoryApi } from "../../services/inventory";

const CONDITIONS = ["NEW","GOOD","FAIR","POOR","DAMAGED","DISPOSED"];
const STATUSES = ["AVAILABLE","IN_USE","MAINTENANCE","LOANED","LOST","DISPOSED"];

export default function Assets() {
  const { data, err, loading, reload } = useLoad<any[]>(() => inventoryApi.assets.list());
  const [search, setSearch] = useState("");
  const [fStatus, setFStatus] = useState("");
  const [fCondition, setFCondition] = useState("");
  const [fLocation, setFLocation] = useState("");

  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [drawerId, setDrawerId] = useState<number | null>(null);

  const [showTransfer, setShowTransfer] = useState<number | null>(null);
  const [showMaint, setShowMaint] = useState<number[] | null>(null);
  const [showStatus, setShowStatus] = useState<number[] | null>(null);
  const [showNew, setShowNew] = useState(false);
  const [locations, setLocations] = useState<any[]>([]);

  useEffect(() => {
    inventoryApi.locations.list().then((l: any) => setLocations(l || []));
  }, []);

  const rows = useMemo(() => {
    const all = data || [];
    const s = search.toLowerCase();
    return all.filter((r: any) => {
      if (fStatus && r.status !== fStatus) return false;
      if (fCondition && r.condition !== fCondition) return false;
      if (fLocation && String(r.current_location) !== String(fLocation)) return false;
      if (s) {
        const hay = [r.tag, r.item_name, r.item_code, r.location_code, r.serial_number]
          .map((x: any) => String(x || "")).join(" ").toLowerCase();
        if (!hay.includes(s)) return false;
      }
      return true;
    });
  }, [data, search, fStatus, fCondition, fLocation]);

  function toggle(id: number) {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id); else next.add(id);
    setSelected(next);
  }
  function toggleAll() {
    if (selected.size === rows.length) setSelected(new Set());
    else setSelected(new Set(rows.map((r: any) => r.id)));
  }
  function clearSel() { setSelected(new Set()); }

  function exportCSV() {
    downloadCSV("assets",
      ["Tag", "Serial", "Item Code", "Item", "Location", "Condition", "Status", "Cost"],
      rows.map((r: any) => [r.tag, r.serial_number, r.item_code, r.item_name,
                            r.location_code, r.condition, r.status, r.purchase_cost]));
  }

  const selectedIds = Array.from(selected);

  return (
    <PageShell
      title="Assets"
      subtitle="Serially-tracked items - click a row to open its history"
      actions={
        <div style={{ display: "flex", gap: 6 }}>
          <button style={btnPrimary} onClick={() => setShowNew(true)}>+ New Asset</button>
          <button style={btnSecondary} onClick={exportCSV}>CSV</button>
        </div>
      }
    >
      <InventoryTabs active="assets" />
      <FilterBar
        search={search}
        onSearch={setSearch}
        filters={[
          { label: "Status", value: fStatus, onChange: setFStatus,
            options: [{ value: "", label: "All Statuses" },
                      ...STATUSES.map(s => ({ value: s, label: s }))] },
          { label: "Condition", value: fCondition, onChange: setFCondition,
            options: [{ value: "", label: "All Conditions" },
                      ...CONDITIONS.map(s => ({ value: s, label: s }))] },
          { label: "Location", value: fLocation, onChange: setFLocation,
            options: [{ value: "", label: "All Locations" },
                      ...locations.map((l: any) => ({ value: String(l.id), label: l.code }))] },
        ]}
      />

      <ErrorBox msg={err} />
      {loading ? <div>Loading...</div> : (
        <div style={{ background: "#fff", borderRadius: 10, border: `1px solid ${C.BORDER}`, overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
            <thead>
              <tr style={{ background: "#f8fafc", textAlign: "left" }}>
                <th style={{ padding: "0.55rem 0.6rem", width: 32 }}>
                  <input type="checkbox"
                    checked={rows.length > 0 && selected.size === rows.length}
                    onChange={toggleAll} />
                </th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Tag</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Item</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Location</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Condition</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Status</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && (
                <tr><td colSpan={7} style={{ padding: "1rem", textAlign: "center", color: C.MUTED }}>No assets match filters</td></tr>
              )}
              {rows.map((r: any) => (
                <tr key={r.id} style={{ borderTop: "1px solid #f1f5f9" }}>
                  <td style={{ padding: "0.5rem 0.6rem" }}>
                    <input type="checkbox" checked={selected.has(r.id)} onChange={() => toggle(r.id)} />
                  </td>
                  <td style={{ padding: "0.5rem 0.6rem", fontWeight: 600 }}>
                    <a href="#" onClick={(e) => { e.preventDefault(); setDrawerId(r.id); }}
                       style={{ color: C.BROWN, textDecoration: "none" }}>{r.tag}</a>
                  </td>
                  <td style={{ padding: "0.5rem 0.6rem" }}>
                    <div style={{ fontWeight: 500 }}>{r.item_name}</div>
                    <div style={{ fontSize: "0.72rem", color: C.MUTED }}>{r.item_code}</div>
                  </td>
                  <td style={{ padding: "0.5rem 0.6rem" }}>{r.location_code || "-"}</td>
                  <td style={{ padding: "0.5rem 0.6rem" }}><StatusPill value={r.condition} /></td>
                  <td style={{ padding: "0.5rem 0.6rem" }}><StatusPill value={r.status} /></td>
                  <td style={{ padding: "0.5rem 0.6rem" }}>
                    <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                      <button style={smallBtn} onClick={() => setDrawerId(r.id)}>Details</button>
                      <button style={smallBtn} onClick={() => setShowTransfer(r.id)}>Transfer</button>
                      <button style={smallBtn} onClick={() => setShowMaint([r.id])}>Service</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <BulkBar count={selected.size} onClear={clearSel}>
        <button style={{ ...smallBtn, background: "transparent", color: "#fff", borderColor: "rgba(255,255,255,0.5)" }}
                onClick={() => setShowMaint(selectedIds)}>Schedule maintenance</button>
        <button style={{ ...smallBtn, background: "transparent", color: "#fff", borderColor: "rgba(255,255,255,0.5)" }}
                onClick={() => setShowStatus(selectedIds)}>Change status</button>
        <button style={{ ...smallBtn, background: "transparent", color: "#fff", borderColor: "rgba(255,255,255,0.5)" }}
                onClick={() => setShowTransfer(selectedIds[0])}
                disabled={selectedIds.length !== 1}>Transfer (1 only)</button>
      </BulkBar>

      <AssetDrawer
        assetId={drawerId}
        onClose={() => setDrawerId(null)}
        onTransfer={() => { if (drawerId) setShowTransfer(drawerId); }}
        onService={() => { if (drawerId) setShowMaint([drawerId]); }}
      />

      <TransferAssetModal
        open={showTransfer !== null}
        onClose={() => setShowTransfer(null)}
        assetId={showTransfer}
        onDone={reload}
      />
      <ScheduleMaintenanceModal
        open={showMaint !== null}
        onClose={() => setShowMaint(null)}
        assetIds={showMaint || []}
        onDone={reload}
      />
      <ChangeStatusModal
        open={showStatus !== null}
        onClose={() => setShowStatus(null)}
        assetIds={showStatus || []}
        onDone={reload}
      />
      <NewAssetModal
        open={showNew}
        onClose={() => setShowNew(false)}
        onDone={reload}
      />
    </PageShell>
  );
}

function AssetDrawer({
  assetId, onClose, onTransfer, onService,
}: { assetId: number | null; onClose: () => void; onTransfer: () => void; onService: () => void }) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (assetId == null) { setData(null); return; }
    setLoading(true);
    (inventoryApi as any).assetDetail(assetId)
      .then((d: any) => setData(d))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [assetId]);

  if (assetId == null) return null;
  const a = data?.asset;

  return (
    <Drawer open={!!assetId} onClose={onClose} title={a?.tag || "Asset"} subtitle={a?.item_name}>
      {loading ? <div>Loading...</div> : !a ? <div>Not found</div> : (
        <>
          <div style={{ display: "flex", gap: 6, marginBottom: 12, flexWrap: "wrap" }}>
            <button style={btnPrimary} onClick={onTransfer}>Transfer</button>
            <button style={btnSecondary} onClick={onService}>Schedule Service</button>
          </div>

          <SectionTitle>Identity</SectionTitle>
          <KV label="Tag" value={a.tag} />
          <KV label="Serial #" value={a.serial_number || "-"} />
          <KV label="Item" value={`${a.item_code} - ${a.item_name}`} />
          <KV label="Category" value={a.category || "-"} />
          <KV label="Status" value={<StatusPill value={a.status} />} />
          <KV label="Condition" value={<StatusPill value={a.condition} />} />

          <SectionTitle>Location</SectionTitle>
          <KV label="Location" value={a.location_code ? `${a.location_code} - ${a.location_name}` : "-"} />
          <KV label="Department" value={a.department || "-"} />

          <SectionTitle>Financials</SectionTitle>
          <KV label="Purchase Date" value={a.purchase_date || "-"} />
          <KV label="Purchase Cost" value={`KES ${Number(a.purchase_cost).toLocaleString()}`} />
          <KV label="Supplier" value={a.supplier || "-"} />
          <KV label="Warranty Expiry" value={a.warranty_expiry || "-"} />

          <SectionTitle>Movements ({data.movements?.length || 0})</SectionTitle>
          {(data.movements || []).length === 0 && <div style={{ color: C.MUTED, fontSize: "0.85rem" }}>No movements</div>}
          {(data.movements || []).map((m: any) => (
            <div key={m.id} style={{ padding: "0.4rem 0", borderBottom: "1px solid #f1f5f9", fontSize: "0.8rem" }}>
              <div style={{ fontWeight: 600 }}>{m.movement_type} - {new Date(m.occurred_at).toLocaleDateString()}</div>
              <div style={{ color: C.MUTED }}>
                {m.from_location__code || "-"} to {m.to_location__code || "-"}
                {m.actor__username ? ` - by ${m.actor__username}` : ""}
              </div>
              {m.notes && <div style={{ color: C.MUTED, fontStyle: "italic" }}>{m.notes}</div>}
            </div>
          ))}

          <SectionTitle>Maintenance ({data.maintenance?.length || 0})</SectionTitle>
          {(data.maintenance || []).length === 0 && <div style={{ color: C.MUTED, fontSize: "0.85rem" }}>No maintenance records</div>}
          {(data.maintenance || []).map((m: any) => (
            <div key={m.id} style={{ padding: "0.4rem 0", borderBottom: "1px solid #f1f5f9", fontSize: "0.8rem" }}>
              <div style={{ fontWeight: 600 }}>{m.performed_at} - KES {Number(m.cost || 0).toLocaleString()}</div>
              <div>{m.description}</div>
              {m.next_due && <div style={{ color: C.MUTED }}>Next due: {m.next_due}</div>}
            </div>
          ))}
        </>
      )}
    </Drawer>
  );
}
