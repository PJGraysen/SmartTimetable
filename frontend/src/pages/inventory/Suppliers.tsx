import { useMemo, useState, useEffect } from "react";
import {
  C, ErrorBox, PageShell, InventoryTabs, Drawer, StatusPill,
  KV, SectionTitle, FilterBar, btnPrimary, btnSecondary, smallBtn,
  downloadCSV, useLoad, Modal, inputStyle, copyToClipboard,
} from "./_shared";
import { inventoryApi } from "../../services/inventory";

const lbl: React.CSSProperties = {
  display: "block", fontSize: "0.78rem", color: C.MUTED, marginBottom: 3,
};

function Field({ label, value, setValue, type = "text" }: any) {
  return (
    <div style={{ marginBottom: 8 }}>
      <label style={lbl}>{label}</label>
      <input style={inputStyle} type={type} value={value ?? ""}
             onChange={e => setValue(e.target.value)} />
    </div>
  );
}

function SupplierForm({ open, onClose, onDone, edit }: any) {
  const [f, setF] = useState<any>({ is_active: true });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!open) return;
    setF(edit || { is_active: true });
    setErr("");
    setBusy(false);
  }, [open, edit]);

  async function save() {
    setBusy(true); setErr("");
    try {
      const payload = {
        code: f.code, name: f.name,
        contact_person: f.contact_person || "",
        phone: f.phone || "", email: f.email || "",
        whatsapp: f.whatsapp || "", address: f.address || "",
        payment_terms: f.payment_terms || "",
        lead_time_days: Number(f.lead_time_days || 7),
        rating: Number(f.rating || 0),
        notes: f.notes || "", is_active: f.is_active !== false,
      };
      if (edit?.id) await inventoryApi.suppliers.update(edit.id, payload);
      else await inventoryApi.suppliers.create(payload);
      onDone?.();
      onClose();
    } catch (e: any) {
      setErr(e?.response?.data ? JSON.stringify(e.response.data) : String(e));
    } finally { setBusy(false); }
  }

  return (
    <Modal open={open} onClose={onClose} title={edit?.id ? "Edit Supplier" : "New Supplier"} width={640}>
      <ErrorBox msg={err} />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        <Field label="Code *" value={f.code} setValue={(v: any) => setF({ ...f, code: v })} />
        <Field label="Name *" value={f.name} setValue={(v: any) => setF({ ...f, name: v })} />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        <Field label="Contact Person" value={f.contact_person} setValue={(v: any) => setF({ ...f, contact_person: v })} />
        <Field label="Payment Terms" value={f.payment_terms} setValue={(v: any) => setF({ ...f, payment_terms: v })} />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
        <Field label="Phone" value={f.phone} setValue={(v: any) => setF({ ...f, phone: v })} />
        <Field label="WhatsApp" value={f.whatsapp} setValue={(v: any) => setF({ ...f, whatsapp: v })} />
        <Field label="Email" value={f.email} setValue={(v: any) => setF({ ...f, email: v })} />
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        <Field label="Lead Time (days)" type="number" value={f.lead_time_days} setValue={(v: any) => setF({ ...f, lead_time_days: v })} />
        <Field label="Rating (0-5)" type="number" value={f.rating} setValue={(v: any) => setF({ ...f, rating: v })} />
      </div>
      <Field label="Address" value={f.address} setValue={(v: any) => setF({ ...f, address: v })} />
      <div style={{ marginBottom: 8 }}>
        <label style={lbl}>Notes</label>
        <textarea style={{ ...inputStyle, minHeight: 70 }} value={f.notes ?? ""}
                  onChange={e => setF({ ...f, notes: e.target.value })} />
      </div>
      <label style={{ fontSize: "0.82rem", display: "block", marginTop: 6 }}>
        <input type="checkbox" checked={f.is_active !== false}
               onChange={e => setF({ ...f, is_active: e.target.checked })} /> Active
      </label>
      <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
        <button style={btnPrimary} disabled={busy || !f.code || !f.name} onClick={save}>
          {busy ? "Saving..." : (edit?.id ? "Update Supplier" : "Create Supplier")}
        </button>
        <button style={btnSecondary} onClick={onClose}>Cancel</button>
      </div>
    </Modal>
  );
}

export default function Suppliers() {
  const { data, err, loading, reload } = useLoad<any[]>(() => inventoryApi.suppliers.list());
  const [search, setSearch] = useState("");
  const [drawerId, setDrawerId] = useState<number | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editRow, setEditRow] = useState<any>(null);

  const rows = useMemo(() => {
    const s = search.toLowerCase();
    return (data || []).filter((r: any) => {
      if (!s) return true;
      const hay = [r.code, r.name, r.contact_person, r.phone, r.email, r.whatsapp]
        .map(x => String(x || "")).join(" ").toLowerCase();
      return hay.includes(s);
    });
  }, [data, search]);

  function exportCSV() {
    downloadCSV("suppliers",
      ["Code", "Name", "Contact", "Phone", "WhatsApp", "Email", "Terms", "Lead Days", "Rating"],
      rows.map((r: any) => [r.code, r.name, r.contact_person, r.phone, r.whatsapp,
                            r.email, r.payment_terms, r.lead_time_days, r.rating]));
  }

  function openNew() { setEditRow(null); setModalOpen(true); }
  function openEdit(row: any) { setEditRow(row); setModalOpen(true); }
  function closeModal() { setModalOpen(false); }

  async function remove(id: number, name: string) {
    if (!confirm(`Delete supplier "${name}"?`)) return;
    try { await inventoryApi.suppliers.remove(id); reload(); }
    catch (e: any) { alert("Delete failed: " + (e?.response?.data?.detail || String(e))); }
  }

  return (
    <PageShell title="Suppliers" subtitle="Vendors and service providers - click for items supplied"
      actions={
        <div style={{ display: "flex", gap: 6 }}>
          <button style={btnPrimary} onClick={openNew}>+ New Supplier</button>
          <button style={btnSecondary} onClick={exportCSV}>CSV</button>
        </div>
      }>
      <InventoryTabs active="suppliers" />
      <FilterBar search={search} onSearch={setSearch} />
      <ErrorBox msg={err} />
      {loading ? <div>Loading...</div> : (
        <div style={{ background: "#fff", borderRadius: 10, border: `1px solid ${C.BORDER}`, overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
            <thead>
              <tr style={{ background: "#f8fafc", textAlign: "left" }}>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Code</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Name</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Contact</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Phone</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Rating</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && (
                <tr><td colSpan={6} style={{ padding: "1rem", textAlign: "center", color: C.MUTED }}>No suppliers</td></tr>
              )}
              {rows.map((r: any) => (
                <tr key={r.id} style={{ borderTop: "1px solid #f1f5f9" }}>
                  <td style={{ padding: "0.5rem 0.6rem", fontWeight: 600 }}>
                    <a href="#" onClick={(e) => { e.preventDefault(); setDrawerId(r.id); }}
                       style={{ color: C.BROWN, textDecoration: "none" }}>{r.code}</a>
                  </td>
                  <td style={{ padding: "0.5rem 0.6rem" }}>{r.name}</td>
                  <td style={{ padding: "0.5rem 0.6rem" }}>{r.contact_person || "-"}</td>
                  <td style={{ padding: "0.5rem 0.6rem" }}>{r.phone || "-"}</td>
                  <td style={{ padding: "0.5rem 0.6rem" }}>
                    {r.rating ? Number(r.rating).toFixed(1) + " / 5" : "-"}
                  </td>
                  <td style={{ padding: "0.5rem 0.6rem" }}>
                    <div style={{ display: "flex", gap: 4 }}>
                      <button style={smallBtn} onClick={() => setDrawerId(r.id)}>View</button>
                      <button style={smallBtn} onClick={() => openEdit(r)}>Edit</button>
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

      <SupplierDrawer supplierId={drawerId} onClose={() => setDrawerId(null)}
        onEdit={(r: any) => { setDrawerId(null); openEdit(r); }} />

      <SupplierForm open={modalOpen} onClose={closeModal} onDone={reload} edit={editRow} />
    </PageShell>
  );
}

function SupplierDrawer({ supplierId, onClose, onEdit }: any) {
  const [d, setD] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [contacted, setContacted] = useState("");
  const [itemsSupplied, setItemsSupplied] = useState<any[]>([]);

  useEffect(() => {
    if (supplierId == null) { setD(null); return; }
    setLoading(true);
    inventoryApi.suppliers.list().then((all: any) => {
      const s = (all || []).find((x: any) => x.id === supplierId);
      setD(s);
    }).finally(() => setLoading(false));
    inventoryApi.items.list().then((all: any) => {
      setItemsSupplied((all || []).filter((i: any) => i.default_supplier === supplierId));
    });
  }, [supplierId]);

  async function logContact(method: string) {
    if (!supplierId) return;
    const note = prompt(`${method} contact note (optional):`) || "";
    await (inventoryApi as any).supplierContact(supplierId, method, note);
    setContacted(method + " logged");
    setTimeout(() => setContacted(""), 2000);
  }

  if (supplierId == null) return null;

  return (
    <Drawer open={!!supplierId} onClose={onClose} title={d?.name || "Supplier"} subtitle={d?.code}>
      {loading ? <div>Loading...</div> : !d ? <div>Not found</div> : (
        <>
          {contacted && (
            <div style={{ marginBottom: 8, padding: 6, background: "#ecfdf5",
                          color: "#065f46", borderRadius: 6, fontSize: "0.8rem" }}>{contacted}</div>
          )}
          <div style={{ display: "flex", gap: 6, marginBottom: 12, flexWrap: "wrap" }}>
            {d.phone && (
              <>
                <a href={`tel:${d.phone}`} style={{ ...smallBtn, textDecoration: "none" }}
                   onClick={() => logContact("call")}>📞 Call</a>
                <button style={smallBtn} title="Copy phone"
                        onClick={() => copyToClipboard(d.phone, "Phone")}>📋</button>
              </>
            )}
            {d.email && (
              <>
                <a href={`mailto:${d.email}`} style={{ ...smallBtn, textDecoration: "none" }}
                   onClick={() => logContact("email")}>✉️ Email</a>
                <button style={smallBtn} title="Copy email"
                        onClick={() => copyToClipboard(d.email, "Email")}>📋</button>
              </>
            )}
            {d.whatsapp && (
              <>
                <a href={`https://wa.me/${String(d.whatsapp).replace(/\D/g, "")}`} target="_blank" rel="noreferrer"
                   style={{ ...smallBtn, textDecoration: "none" }}
                   onClick={() => logContact("whatsapp")}>💬 WhatsApp</a>
                <button style={smallBtn} title="Copy WhatsApp"
                        onClick={() => copyToClipboard(d.whatsapp, "WhatsApp")}>📋</button>
              </>
            )}
            <button style={smallBtn} onClick={() => onEdit(d)}>Edit</button>
          </div>

          <SectionTitle>Contact</SectionTitle>
          <KV label="Code" value={d.code} />
          <KV label="Name" value={d.name} />
          <KV label="Contact Person" value={d.contact_person || "-"} />
          <KV label="Phone" value={d.phone || "-"} />
          <KV label="WhatsApp" value={d.whatsapp || "-"} />
          <KV label="Email" value={d.email || "-"} />
          <KV label="Address" value={d.address || "-"} />

          <SectionTitle>Commercial</SectionTitle>
          <KV label="Payment Terms" value={d.payment_terms || "-"} />
          <KV label="Lead Time" value={`${d.lead_time_days || 0} days`} />
          <KV label="Rating" value={d.rating ? `${Number(d.rating).toFixed(1)} / 5` : "-"} />

          <SectionTitle>Items Supplied ({itemsSupplied.length})</SectionTitle>
          {itemsSupplied.length === 0 && <div style={{ color: C.MUTED, fontSize: "0.85rem" }}>No items linked</div>}
          {itemsSupplied.map((i: any) => (
            <div key={i.id} style={{ padding: "0.3rem 0", borderBottom: "1px solid #f1f5f9",
                                     fontSize: "0.82rem", display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontWeight: 600 }}>{i.code}</span>
              <span style={{ color: C.MUTED, flex: 1, marginLeft: 8 }}>{i.name}</span>
              <span>KES {Number(i.unit_cost || 0).toLocaleString()}</span>
            </div>
          ))}

          {d.notes && (
            <>
              <SectionTitle>Notes / Contact Log</SectionTitle>
              <div style={{ fontSize: "0.8rem", whiteSpace: "pre-wrap", color: "#444" }}>{d.notes}</div>
            </>
          )}
        </>
      )}
    </Drawer>
  );
}
