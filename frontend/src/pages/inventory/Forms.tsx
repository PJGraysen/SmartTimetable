import { useEffect, useState } from "react";
import { C, Modal, inputStyle, btnPrimary, btnSecondary, ErrorBox, smallBtn } from "./_shared";
import { inventoryApi } from "../../services/inventory";

function Field({ label, value, setValue, type = "text", required = false }: any) {
  return (
    <div style={{ marginBottom: 8 }}>
      <label style={{ display: "block", fontSize: "0.78rem", color: C.MUTED, marginBottom: 3 }}>
        {label}{required ? " *" : ""}
      </label>
      <input style={inputStyle} type={type} value={value ?? ""} onChange={e => setValue(e.target.value)} />
    </div>
  );
}

function Select({ label, value, setValue, options, required = false }: any) {
  return (
    <div style={{ marginBottom: 8 }}>
      <label style={{ display: "block", fontSize: "0.78rem", color: C.MUTED, marginBottom: 3 }}>
        {label}{required ? " *" : ""}
      </label>
      <select style={inputStyle} value={value ?? ""} onChange={e => setValue(e.target.value)}>
        <option value="">- select -</option>
        {(options || []).map((o: any) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}

// ================= NEW ITEM =================
export function NewItemModal({ open, onClose, onDone }: any) {
  const [cats, setCats] = useState<any[]>([]);
  const [depts, setDepts] = useState<any[]>([]);
  const [locs, setLocs] = useState<any[]>([]);
  const [suppliers, setSuppliers] = useState<any[]>([]);
  const [f, setF] = useState<any>({ tracking_mode: "INDIVIDUAL", unit: "pcs", initial_quantity: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [showNewCat, setShowNewCat] = useState(false);
  const [newCat, setNewCat] = useState({ code: "", name: "", is_consumable: false });

  useEffect(() => {
    if (!open) return;
    inventoryApi.categories.list().then((c: any) => setCats(c || []));
    inventoryApi.departments.list().then((d: any) => setDepts(d || []));
    inventoryApi.locations.list().then((l: any) => setLocs(l || []));
    inventoryApi.suppliers.list().then((s: any) => setSuppliers(s || []));
  }, [open]);

  async function createCategory() {
    if (!newCat.code || !newCat.name) return;
    try {
      const c = await inventoryApi.categories.create(newCat);
      setCats([...cats, c]);
      setF({ ...f, category: c.id });
      setShowNewCat(false);
      setNewCat({ code: "", name: "", is_consumable: false });
    } catch (e: any) {
      setErr(e?.response?.data ? JSON.stringify(e.response.data) : String(e));
    }
  }

  async function save() {
    setBusy(true); setErr("");
    try {
      const payload = { ...f };
      if (!payload.initial_quantity) delete payload.initial_quantity;
      await (inventoryApi as any).quickAddItem(payload);
      onDone?.(); onClose();
      setF({ tracking_mode: "INDIVIDUAL", unit: "pcs", initial_quantity: "" });
    } catch (e: any) {
      setErr(e?.response?.data?.detail || (e?.response?.data ? JSON.stringify(e.response.data) : String(e)));
    } finally { setBusy(false); }
  }

  return (
    <Modal open={open} onClose={onClose} title="New Item" width={620}>
      <ErrorBox msg={err} />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        <Field label="Item Code" value={f.code} setValue={(v: any) => setF({ ...f, code: v })} required />
        <Field label="Name" value={f.name} setValue={(v: any) => setF({ ...f, name: v })} required />
      </div>

      <div style={{ marginBottom: 8 }}>
        <label style={{ display: "block", fontSize: "0.78rem", color: C.MUTED, marginBottom: 3 }}>Category *</label>
        <div style={{ display: "flex", gap: 6 }}>
          <select style={inputStyle} value={f.category ?? ""} onChange={e => setF({ ...f, category: e.target.value })}>
            <option value="">- select -</option>
            {cats.map((c: any) => <option key={c.id} value={c.id}>{c.code} - {c.name}</option>)}
          </select>
          <button style={smallBtn} type="button" onClick={() => setShowNewCat(!showNewCat)}>+ New</button>
        </div>
        {showNewCat && (
          <div style={{ padding: 10, marginTop: 6, background: "#f8fafc", borderRadius: 8, border: `1px solid ${C.BORDER}` }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: 6, marginBottom: 6 }}>
              <input style={inputStyle} placeholder="Code" value={newCat.code} onChange={e => setNewCat({ ...newCat, code: e.target.value })} />
              <input style={inputStyle} placeholder="Name" value={newCat.name} onChange={e => setNewCat({ ...newCat, name: e.target.value })} />
            </div>
            <label style={{ fontSize: "0.75rem" }}>
              <input type="checkbox" checked={newCat.is_consumable} onChange={e => setNewCat({ ...newCat, is_consumable: e.target.checked })} /> Consumable
            </label>
            <div style={{ marginTop: 6 }}>
              <button style={smallBtn} onClick={createCategory}>Create category</button>
            </div>
          </div>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        <Select label="Owning Department" value={f.department} setValue={(v: any) => setF({ ...f, department: v })}
          options={depts.map((d: any) => ({ value: d.id, label: d.name }))} />
        <Select label="Tracking" value={f.tracking_mode} setValue={(v: any) => setF({ ...f, tracking_mode: v })}
          options={[{ value: "INDIVIDUAL", label: "Individual (serialized)" }, { value: "QUANTITY", label: "Quantity (bulk)" }]} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
        <Field label="Unit" value={f.unit} setValue={(v: any) => setF({ ...f, unit: v })} />
        <Field label="Unit Cost" type="number" value={f.unit_cost} setValue={(v: any) => setF({ ...f, unit_cost: v })} />
        <Select label="Supplier" value={f.default_supplier} setValue={(v: any) => setF({ ...f, default_supplier: v })}
          options={suppliers.map((s: any) => ({ value: s.id, label: s.name }))} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        <Field label="Min Stock" type="number" value={f.min_stock} setValue={(v: any) => setF({ ...f, min_stock: v })} />
        <Field label="Reorder Stock" type="number" value={f.reorder_stock} setValue={(v: any) => setF({ ...f, reorder_stock: v })} />
      </div>

      <div style={{ padding: 10, marginTop: 8, background: "#fef9c3", borderRadius: 8 }}>
        <div style={{ fontSize: "0.75rem", color: "#92400e", marginBottom: 6 }}>
          Optional: seed initial inventory now
        </div>
        <Select label="Initial Location" value={f.initial_location} setValue={(v: any) => setF({ ...f, initial_location: v })}
          options={locs.map((l: any) => ({ value: l.id, label: `${l.code} - ${l.name}` }))} />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <Field label="Initial Quantity" type="number" value={f.initial_quantity} setValue={(v: any) => setF({ ...f, initial_quantity: v })} />
          <Field label="Tag Prefix" value={f.tag_prefix} setValue={(v: any) => setF({ ...f, tag_prefix: v })} />
        </div>
        <div style={{ fontSize: "0.72rem", color: C.MUTED, marginTop: 4 }}>
          If tracking = Individual, N asset tags will be created (e.g. MICR-0001..N).
          If tracking = Quantity, one stock row with N units will be created.
        </div>
      </div>

      <Field label="Description" value={f.description} setValue={(v: any) => setF({ ...f, description: v })} />

      <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
        <button style={btnPrimary} disabled={busy || !f.code || !f.name || !f.category} onClick={save}>
          {busy ? "Creating..." : "Create Item"}
        </button>
        <button style={btnSecondary} onClick={onClose}>Cancel</button>
      </div>
    </Modal>
  );
}

// ================= NEW ASSET =================
export function NewAssetModal({ open, onClose, onDone }: any) {
  const [items, setItems] = useState<any[]>([]);
  const [locs, setLocs] = useState<any[]>([]);
  const [suppliers, setSuppliers] = useState<any[]>([]);
  const [f, setF] = useState<any>({ condition: "NEW", status: "AVAILABLE" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!open) return;
    inventoryApi.items.list().then((i: any) => setItems(i || []));
    inventoryApi.locations.list().then((l: any) => setLocs(l || []));
    inventoryApi.suppliers.list().then((s: any) => setSuppliers(s || []));
  }, [open]);

  async function save() {
    setBusy(true); setErr("");
    try {
      await inventoryApi.assets.create(f);
      onDone?.(); onClose();
      setF({ condition: "NEW", status: "AVAILABLE" });
    } catch (e: any) {
      setErr(e?.response?.data ? JSON.stringify(e.response.data) : String(e));
    } finally { setBusy(false); }
  }

  return (
    <Modal open={open} onClose={onClose} title="New Asset" width={560}>
      <ErrorBox msg={err} />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        <Field label="Asset Tag" value={f.tag} setValue={(v: any) => setF({ ...f, tag: v })} required />
        <Field label="Serial Number" value={f.serial_number} setValue={(v: any) => setF({ ...f, serial_number: v })} />
      </div>
      <Select label="Item" value={f.item} setValue={(v: any) => setF({ ...f, item: v })} required
        options={items.map((i: any) => ({ value: i.id, label: `${i.code} - ${i.name}` }))} />
      <Select label="Location" value={f.current_location} setValue={(v: any) => setF({ ...f, current_location: v })}
        options={locs.map((l: any) => ({ value: l.id, label: `${l.code} - ${l.name}` }))} />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        <Select label="Condition" value={f.condition} setValue={(v: any) => setF({ ...f, condition: v })}
          options={["NEW","GOOD","FAIR","POOR","DAMAGED","DISPOSED"].map(x => ({ value: x, label: x }))} />
        <Select label="Status" value={f.status} setValue={(v: any) => setF({ ...f, status: v })}
          options={["AVAILABLE","IN_USE","MAINTENANCE","LOANED","LOST","DISPOSED"].map(x => ({ value: x, label: x }))} />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        <Field label="Purchase Date" type="date" value={f.purchase_date} setValue={(v: any) => setF({ ...f, purchase_date: v })} />
        <Field label="Purchase Cost" type="number" value={f.purchase_cost} setValue={(v: any) => setF({ ...f, purchase_cost: v })} />
      </div>
      <Select label="Supplier" value={f.supplier} setValue={(v: any) => setF({ ...f, supplier: v })}
        options={suppliers.map((s: any) => ({ value: s.id, label: s.name }))} />
      <Field label="Warranty Expiry" type="date" value={f.warranty_expiry} setValue={(v: any) => setF({ ...f, warranty_expiry: v })} />
      <Field label="Notes" value={f.notes} setValue={(v: any) => setF({ ...f, notes: v })} />
      <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
        <button style={btnPrimary} disabled={busy || !f.tag || !f.item} onClick={save}>
          {busy ? "Creating..." : "Create Asset"}
        </button>
        <button style={btnSecondary} onClick={onClose}>Cancel</button>
      </div>
    </Modal>
  );
}

// ================= MAINTENANCE REPORT =================
export function MaintenanceReportModal({ open, onClose, onDone, presetAssetId }: any) {
  const [assets, setAssets] = useState<any[]>([]);
  const [f, setF] = useState<any>({ priority: "NORMAL", asset: presetAssetId ?? "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!open) return;
    inventoryApi.assets.list().then((a: any) => setAssets(a || []));
    if (presetAssetId) setF({ ...f, asset: presetAssetId });
  }, [open, presetAssetId]);

  async function save() {
    setBusy(true); setErr("");
    try {
      await (inventoryApi as any).maintenanceApi.report(f);
      onDone?.(); onClose();
      setF({ priority: "NORMAL", asset: "" });
    } catch (e: any) {
      setErr(e?.response?.data?.detail || String(e));
    } finally { setBusy(false); }
  }

  return (
    <Modal open={open} onClose={onClose} title="Report Faulty Item" width={560}>
      <ErrorBox msg={err} />
      <Select label="Asset" value={f.asset} setValue={(v: any) => setF({ ...f, asset: v })} required
        options={assets.map((a: any) => ({ value: a.id, label: `${a.tag} - ${a.item_name || ""}` }))} />
      <Field label="What is faulty" value={f.description} setValue={(v: any) => setF({ ...f, description: v })} required />
      <Field label="Proposed Remedy" value={f.remedy} setValue={(v: any) => setF({ ...f, remedy: v })} />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        <Field label="Estimated Cost" type="number" value={f.cost} setValue={(v: any) => setF({ ...f, cost: v })} />
        <Select label="Priority" value={f.priority} setValue={(v: any) => setF({ ...f, priority: v })}
          options={["LOW","NORMAL","HIGH","CRITICAL"].map(x => ({ value: x, label: x }))} />
      </div>
      <div style={{ fontSize: "0.75rem", color: C.MUTED, marginTop: 8 }}>
        Your report will go to the admin for approval.
      </div>
      <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
        <button style={btnPrimary} disabled={busy || !f.asset || !f.description} onClick={save}>
          {busy ? "Submitting..." : "Submit Report"}
        </button>
        <button style={btnSecondary} onClick={onClose}>Cancel</button>
      </div>
    </Modal>
  );
}
