import { useEffect, useState } from "react";
import { C, Modal, inputStyle, btnPrimary, btnSecondary, ErrorBox } from "./_shared";
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

// ================= MOVEMENT =================
export function MovementModal({ open, onClose, onDone }: any) {
  const [items, setItems] = useState<any[]>([]);
  const [assets, setAssets] = useState<any[]>([]);
  const [locs, setLocs] = useState<any[]>([]);
  const [f, setF] = useState<any>({ movement_type: "TRANSFER" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!open) return;
    inventoryApi.items.list().then((i: any) => setItems(i || []));
    inventoryApi.assets.list().then((a: any) => setAssets(a || []));
    inventoryApi.locations.list().then((l: any) => setLocs(l || []));
  }, [open]);

  async function save() {
    setBusy(true); setErr("");
    try {
      const api = inventoryApi as any;
      if (f.movement_type === "RECEIPT") {
        await api.actions.receive({
          item: Number(f.item), location: Number(f.to_location),
          quantity: Number(f.quantity), batch_number: f.batch_number || "",
          reference: f.reference || "", notes: f.reason || "",
        });
      } else if (f.movement_type === "ISSUE") {
        await api.actions.issue({
          item: Number(f.item), location: Number(f.from_location),
          quantity: Number(f.quantity), recipient: f.recipient || "",
          notes: f.reason || "",
        });
      } else if (f.movement_type === "TRANSFER") {
        if (f.asset) {
          await api.actions.moveAsset({
            asset: Number(f.asset), to_location: Number(f.to_location),
            notes: f.reason || "",
          });
        } else {
          await api.actions.transfer({
            item: Number(f.item),
            from_location: Number(f.from_location),
            to_location: Number(f.to_location),
            quantity: Number(f.quantity),
            batch_number: f.batch_number || "",
            notes: f.reason || "",
          });
        }
      }
      onDone?.(); onClose();
      setF({ movement_type: "TRANSFER" });
    } catch (e: any) {
      setErr(e?.response?.data?.detail || (e?.response?.data ? JSON.stringify(e.response.data) : String(e)));
    } finally { setBusy(false); }
  }

  const isReceipt = f.movement_type === "RECEIPT";
  const isIssue = f.movement_type === "ISSUE";
  const isTransfer = f.movement_type === "TRANSFER";

  return (
    <Modal open={open} onClose={onClose} title="New Movement" width={560}>
      <ErrorBox msg={err} />
      <Select label="Movement Type" value={f.movement_type}
        setValue={(v: any) => setF({ ...f, movement_type: v, item: "", asset: "", quantity: "" })}
        options={[
          { value: "RECEIPT", label: "Receipt (into stock)" },
          { value: "ISSUE", label: "Issue (out to recipient)" },
          { value: "TRANSFER", label: "Transfer (between locations)" },
        ]} />

      {isTransfer && (
        <Select label="Move an Asset (skip for bulk stock)" value={f.asset}
          setValue={(v: any) => setF({ ...f, asset: v, item: "" })}
          options={assets.slice(0, 300).map((a: any) => ({ value: a.id, label: `${a.tag} - ${a.item_name || ""}` }))} />
      )}

      {(!isTransfer || !f.asset) && (
        <Select label="Item" value={f.item} setValue={(v: any) => setF({ ...f, item: v })} required
          options={items.map((i: any) => ({ value: i.id, label: `${i.code} - ${i.name}` }))} />
      )}

      {!isReceipt && (
        <Select label="From Location" value={f.from_location}
          setValue={(v: any) => setF({ ...f, from_location: v })} required={isIssue || (isTransfer && !f.asset)}
          options={locs.map((l: any) => ({ value: l.id, label: `${l.code} - ${l.name}` }))} />
      )}

      {!isIssue && (
        <Select label="To Location" value={f.to_location}
          setValue={(v: any) => setF({ ...f, to_location: v })} required
          options={locs.map((l: any) => ({ value: l.id, label: `${l.code} - ${l.name}` }))} />
      )}

      {!f.asset && (
        <Field label="Quantity" type="number" value={f.quantity} setValue={(v: any) => setF({ ...f, quantity: v })} required />
      )}

      {isReceipt && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          <Field label="Batch #" value={f.batch_number} setValue={(v: any) => setF({ ...f, batch_number: v })} />
          <Field label="Reference" value={f.reference} setValue={(v: any) => setF({ ...f, reference: v })} />
        </div>
      )}

      {isIssue && (
        <Field label="Recipient" value={f.recipient} setValue={(v: any) => setF({ ...f, recipient: v })} />
      )}

      <div style={{ marginBottom: 8 }}>
        <label style={{ display: "block", fontSize: "0.78rem", color: C.MUTED, marginBottom: 3 }}>
          Reason / Notes *
        </label>
        <textarea style={{ ...inputStyle, minHeight: 70 }} value={f.reason ?? ""}
          onChange={e => setF({ ...f, reason: e.target.value })} />
      </div>

      <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
        <button style={btnPrimary} disabled={busy || !f.reason} onClick={save}>
          {busy ? "Recording..." : "Record Movement"}
        </button>
        <button style={btnSecondary} onClick={onClose}>Cancel</button>
      </div>
    </Modal>
  );
}

// ================= AUDIT SESSION =================
export function AuditSessionModal({ open, onClose, onDone }: any) {
  const [locs, setLocs] = useState<any[]>([]);
  const [f, setF] = useState<any>({});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!open) return;
    inventoryApi.locations.list().then((l: any) => setLocs(l || []));
  }, [open]);

  async function save() {
    setBusy(true); setErr("");
    try {
      const ref = f.reference || `AUD-${Date.now().toString().slice(-6)}`;
      await inventoryApi.audits.create({
        reference: ref,
        location: Number(f.location),
        notes: f.notes || "",
        status: "OPEN",
      });
      onDone?.(); onClose();
      setF({});
    } catch (e: any) {
      setErr(e?.response?.data ? JSON.stringify(e.response.data) : String(e));
    } finally { setBusy(false); }
  }

  return (
    <Modal open={open} onClose={onClose} title="New Audit Session" width={520}>
      <ErrorBox msg={err} />
      <Field label="Reference (auto if empty)" value={f.reference} setValue={(v: any) => setF({ ...f, reference: v })} />
      <Select label="Location" value={f.location} setValue={(v: any) => setF({ ...f, location: v })} required
        options={locs.map((l: any) => ({ value: l.id, label: `${l.code} - ${l.name}` }))} />
      <Field label="Notes" value={f.notes} setValue={(v: any) => setF({ ...f, notes: v })} />
      <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
        <button style={btnPrimary} disabled={busy || !f.location} onClick={save}>
          {busy ? "Creating..." : "Create Session"}
        </button>
        <button style={btnSecondary} onClick={onClose}>Cancel</button>
      </div>
    </Modal>
  );
}

// ================= NEW LOCATION =================
export function NewLocationModal({ open, onClose, onDone }: any) {
  const [depts, setDepts] = useState<any[]>([]);
  const [f, setF] = useState<any>({ location_type: "OTHER", is_active: true });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!open) return;
    inventoryApi.departments.list().then((d: any) => setDepts(d || []));
  }, [open]);

  async function save() {
    setBusy(true); setErr("");
    try {
      await inventoryApi.locations.create({
        code: f.code, name: f.name,
        location_type: f.location_type,
        department: f.department ? Number(f.department) : null,
        description: f.description || "",
        is_active: f.is_active,
      });
      onDone?.(); onClose();
      setF({ location_type: "OTHER", is_active: true });
    } catch (e: any) {
      setErr(e?.response?.data ? JSON.stringify(e.response.data) : String(e));
    } finally { setBusy(false); }
  }

  const TYPES = ["LAB","OFFICE","STORE","CLASSROOM","LIBRARY","HALL","SPORTS","OTHER"];
  return (
    <Modal open={open} onClose={onClose} title="New Location" width={520}>
      <ErrorBox msg={err} />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        <Field label="Code" value={f.code} setValue={(v: any) => setF({ ...f, code: v })} required />
        <Field label="Name" value={f.name} setValue={(v: any) => setF({ ...f, name: v })} required />
      </div>
      <Select label="Type" value={f.location_type} setValue={(v: any) => setF({ ...f, location_type: v })}
        options={TYPES.map(t => ({ value: t, label: t }))} />
      <Select label="Department" value={f.department} setValue={(v: any) => setF({ ...f, department: v })}
        options={depts.map((d: any) => ({ value: d.id, label: d.name }))} />
      <Field label="Description" value={f.description} setValue={(v: any) => setF({ ...f, description: v })} />
      <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
        <button style={btnPrimary} disabled={busy || !f.code || !f.name} onClick={save}>
          {busy ? "Creating..." : "Create Location"}
        </button>
        <button style={btnSecondary} onClick={onClose}>Cancel</button>
      </div>
    </Modal>
  );
}

// ================= NEW DEPARTMENT =================
export function NewDepartmentModal({ open, onClose, onDone }: any) {
  const [f, setF] = useState<any>({ is_active: true });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function save() {
    setBusy(true); setErr("");
    try {
      await inventoryApi.departments.create({
        code: f.code, name: f.name,
        description: f.description || "",
        email: f.email || "",
        phone: f.phone || "",
        is_active: f.is_active,
      });
      onDone?.(); onClose();
      setF({ is_active: true });
    } catch (e: any) {
      setErr(e?.response?.data ? JSON.stringify(e.response.data) : String(e));
    } finally { setBusy(false); }
  }

  return (
    <Modal open={open} onClose={onClose} title="New Department" width={520}>
      <ErrorBox msg={err} />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        <Field label="Code" value={f.code} setValue={(v: any) => setF({ ...f, code: v })} required />
        <Field label="Name" value={f.name} setValue={(v: any) => setF({ ...f, name: v })} required />
      </div>
      <Field label="Description" value={f.description} setValue={(v: any) => setF({ ...f, description: v })} />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        <Field label="Email" value={f.email} setValue={(v: any) => setF({ ...f, email: v })} />
        <Field label="Phone" value={f.phone} setValue={(v: any) => setF({ ...f, phone: v })} />
      </div>
      <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
        <button style={btnPrimary} disabled={busy || !f.code || !f.name} onClick={save}>
          {busy ? "Creating..." : "Create Department"}
        </button>
        <button style={btnSecondary} onClick={onClose}>Cancel</button>
      </div>
    </Modal>
  );
}
