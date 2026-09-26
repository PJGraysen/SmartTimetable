
import { useState, useEffect } from "react";
import { C, Modal, inputStyle, btnPrimary, btnSecondary, ErrorBox } from "./_shared";
import { inventoryApi } from "../../services/inventory";

// ---------- Transfer Asset ----------
export function TransferAssetModal({
  open, onClose, assetId, assetTag, onDone,
}: { open: boolean; onClose: () => void; assetId: number | null;
   assetTag?: string; onDone?: () => void }) {
  const [locations, setLocations] = useState<any[]>([]);
  const [to, setTo] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!open) return;
    inventoryApi.locations.list().then(l => setLocations(l || []));
  }, [open]);

  async function go() {
    if (!assetId || !to) return;
    setBusy(true); setErr("");
    try {
      await inventoryApi.actions.moveAsset({ asset: assetId, to_location: Number(to), notes });
      onDone?.(); onClose();
    } catch (e: any) {
      setErr(e?.response?.data?.detail || String(e));
    } finally { setBusy(false); }
  }

  return (
    <Modal open={open} onClose={onClose} placement="right" title={`Transfer Asset ${assetTag ? "— " + assetTag : ""}`}>
      <ErrorBox msg={err} />
      <label style={{ display: "block", fontSize: "0.8rem", color: C.MUTED, marginBottom: 4 }}>Destination Location</label>
      <select style={inputStyle} value={to} onChange={e => setTo(e.target.value)}>
        <option value="">— select —</option>
        {locations.map(l => <option key={l.id} value={l.id}>{l.code} — {l.name}</option>)}
      </select>
      <div style={{ height: 10 }} />
      <label style={{ display: "block", fontSize: "0.8rem", color: C.MUTED, marginBottom: 4 }}>Notes</label>
      <textarea style={{ ...inputStyle, minHeight: 70 }} value={notes}
                onChange={e => setNotes(e.target.value)} />
      <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
        <button style={btnPrimary} disabled={busy || !to} onClick={go}>{busy ? "Moving..." : "Transfer"}</button>
        <button style={btnSecondary} onClick={onClose}>Cancel</button>
      </div>
    </Modal>
  );
}

// ---------- Receive Stock ----------
export function ReceiveStockModal({
  open, onClose, onDone,
}: { open: boolean; onClose: () => void; onDone?: () => void }) {
  const [items, setItems] = useState<any[]>([]);
  const [locs, setLocs] = useState<any[]>([]);
  const [item, setItem] = useState("");
  const [loc, setLoc] = useState("");
  const [qty, setQty] = useState("");
  const [batch, setBatch] = useState("");
  const [ref, setRef] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!open) return;
    inventoryApi.items.list().then(i => setItems(i || []));
    inventoryApi.locations.list().then(l => setLocs(l || []));
  }, [open]);

  async function go() {
    setBusy(true); setErr("");
    try {
      await inventoryApi.actions.receive({
        item: Number(item), location: Number(loc),
        quantity: Number(qty), batch_number: batch,
        reference: ref, notes,
      });
      onDone?.(); onClose();
    } catch (e: any) {
      setErr(e?.response?.data?.detail || String(e));
    } finally { setBusy(false); }
  }

  return (
    <Modal open={open} onClose={onClose} placement="right" title="Receive Stock">
      <ErrorBox msg={err} />
      <Select label="Item" value={item} setValue={setItem} options={items.map((i:any) => ({value:i.id,label:`${i.code} — ${i.name}`}))} />
      <Select label="Location" value={loc} setValue={setLoc} options={locs.map((l:any) => ({value:l.id,label:`${l.code} — ${l.name}`}))} />
      <Field label="Quantity" value={qty} setValue={setQty} type="number" />
      <Field label="Batch #" value={batch} setValue={setBatch} />
      <Field label="Reference" value={ref} setValue={setRef} />
      <Field label="Notes" value={notes} setValue={setNotes} />
      <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
        <button style={btnPrimary} disabled={busy || !item || !loc || !qty} onClick={go}>{busy ? "…" : "Receive"}</button>
        <button style={btnSecondary} onClick={onClose}>Cancel</button>
      </div>
    </Modal>
  );
}

// ---------- Issue Stock ----------
export function IssueStockModal({
  open, onClose, onDone,
}: { open: boolean; onClose: () => void; onDone?: () => void }) {
  const [items, setItems] = useState<any[]>([]);
  const [locs, setLocs] = useState<any[]>([]);
  const [item, setItem] = useState("");
  const [loc, setLoc] = useState("");
  const [qty, setQty] = useState("");
  const [recipient, setRecipient] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!open) return;
    inventoryApi.items.list().then(i => setItems(i || []));
    inventoryApi.locations.list().then(l => setLocs(l || []));
  }, [open]);

  async function go() {
    setBusy(true); setErr("");
    try {
      await inventoryApi.actions.issue({
        item: Number(item), location: Number(loc),
        quantity: Number(qty), recipient, notes,
      });
      onDone?.(); onClose();
    } catch (e: any) {
      setErr(e?.response?.data?.detail || String(e));
    } finally { setBusy(false); }
  }

  return (
    <Modal open={open} onClose={onClose} placement="right" title="Issue Stock">
      <ErrorBox msg={err} />
      <Select label="Item" value={item} setValue={setItem} options={items.map((i:any) => ({value:i.id,label:`${i.code} — ${i.name}`}))} />
      <Select label="Location" value={loc} setValue={setLoc} options={locs.map((l:any) => ({value:l.id,label:`${l.code} — ${l.name}`}))} />
      <Field label="Quantity" value={qty} setValue={setQty} type="number" />
      <Field label="Recipient" value={recipient} setValue={setRecipient} />
      <Field label="Notes" value={notes} setValue={setNotes} />
      <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
        <button style={btnPrimary} disabled={busy || !item || !loc || !qty} onClick={go}>{busy ? "…" : "Issue"}</button>
        <button style={btnSecondary} onClick={onClose}>Cancel</button>
      </div>
    </Modal>
  );
}

// ---------- Schedule Maintenance ----------
export function ScheduleMaintenanceModal({
  open, onClose, assetIds, onDone,
}: { open: boolean; onClose: () => void; assetIds: number[];
   onDone?: () => void }) {
  const [desc, setDesc] = useState("");
  const [cost, setCost] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function go() {
    setBusy(true); setErr("");
    try {
      await inventoryApi.bulk.maintenance({
        asset_ids: assetIds,
        description: desc || "Scheduled maintenance",
        cost: cost ? Number(cost) : 0,
      });
      onDone?.(); onClose();
    } catch (e: any) {
      setErr(e?.response?.data?.detail || String(e));
    } finally { setBusy(false); }
  }

  return (
    <Modal open={open} onClose={onClose} placement="right" title={`Schedule Maintenance (${assetIds.length} asset(s))`}>
      <ErrorBox msg={err} />
      <Field label="Description" value={desc} setValue={setDesc} />
      <Field label="Estimated Cost" value={cost} setValue={setCost} type="number" />
      <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
        <button style={btnPrimary} disabled={busy} onClick={go}>{busy ? "…" : "Schedule"}</button>
        <button style={btnSecondary} onClick={onClose}>Cancel</button>
      </div>
    </Modal>
  );
}

// ---------- Change Status/Condition ----------
export function ChangeStatusModal({
  open, onClose, assetIds, onDone,
}: { open: boolean; onClose: () => void; assetIds: number[];
   onDone?: () => void }) {
  const [status, setStatus] = useState("");
  const [condition, setCondition] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function go() {
    setBusy(true); setErr("");
    try {
      await inventoryApi.bulk.status({
        asset_ids: assetIds,
        status: status || undefined,
        condition: condition || undefined,
      });
      onDone?.(); onClose();
    } catch (e: any) {
      setErr(e?.response?.data?.detail || String(e));
    } finally { setBusy(false); }
  }

  return (
    <Modal open={open} onClose={onClose} placement="right" title={`Change Status (${assetIds.length} asset(s))`}>
      <ErrorBox msg={err} />
      <Select label="New Status" value={status} setValue={setStatus}
        options={["AVAILABLE","IN_USE","MAINTENANCE","LOANED","LOST","DISPOSED"]
          .map(v => ({ value: v, label: v }))} />
      <Select label="New Condition" value={condition} setValue={setCondition}
        options={["NEW","GOOD","FAIR","POOR","DAMAGED","DISPOSED"]
          .map(v => ({ value: v, label: v }))} />
      <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
        <button style={btnPrimary} disabled={busy || (!status && !condition)} onClick={go}>Apply</button>
        <button style={btnSecondary} onClick={onClose}>Cancel</button>
      </div>
    </Modal>
  );
}

// ---------- Small helpers ----------
function Field({ label, value, setValue, type = "text" }: any) {
  return (
    <div style={{ marginBottom: 10 }}>
      <label style={{ display: "block", fontSize: "0.8rem", color: C.MUTED, marginBottom: 3 }}>{label}</label>
      <input style={inputStyle} type={type} value={value} onChange={e => setValue(e.target.value)} />
    </div>
  );
}

function Select({ label, value, setValue, options }: any) {
  return (
    <div style={{ marginBottom: 10 }}>
      <label style={{ display: "block", fontSize: "0.8rem", color: C.MUTED, marginBottom: 3 }}>{label}</label>
      <select style={inputStyle} value={value} onChange={e => setValue(e.target.value)}>
        <option value="">— select —</option>
        {options.map((o: any) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}
