import { useState } from "react";
import { Card, C, ErrorBox, PageShell, SimpleTable, btnPrimary, btnSecondary, inputStyle, useLoad, InventoryTabs } from "./_shared";

export type Field = {
  key: string;
  label: string;
  type?: "text" | "number" | "checkbox" | "select";
  options?: { value: any; label: string }[];
  required?: boolean;
};

export function CrudPage({
  title, subtitle,
  api, columns, fields, tabSlug,
}: {
  title: string;
  subtitle?: string;
  api: { list: () => Promise<any>; create: (d: any) => Promise<any>; update: (id: number, d: any) => Promise<any>; remove: (id: number) => Promise<any> };
  columns: { key: string; label: string; render?: (row: any) => any }[];
  fields: Field[];
  tabSlug?: string;
}) {
  const { data, err, loading, reload } = useLoad<any[]>(() => api.list());
  const [editing, setEditing] = useState<any | null>(null);
  const [busy, setBusy] = useState(false);
  const [formErr, setFormErr] = useState("");

  function startNew() {
    const empty: any = {};
    fields.forEach(f => empty[f.key] = f.type === "checkbox" ? false : "");
    setEditing(empty);
    setFormErr("");
  }

  async function save() {
    setBusy(true); setFormErr("");
    try {
      const payload = { ...editing };
      delete payload.id;
      if (editing.id) await api.update(editing.id, payload);
      else await api.create(payload);
      setEditing(null);
      await reload();
    } catch (e: any) {
      setFormErr(e?.response?.data ? JSON.stringify(e.response.data) : String(e));
    } finally { setBusy(false); }
  }

  async function remove(id: number) {
    if (!confirm("Delete this record?")) return;
    try { await api.remove(id); await reload(); }
    catch (e: any) { alert(String(e)); }
  }

  return (
    <PageShell
      title={title} subtitle={subtitle}
      actions={<button style={btnPrimary} onClick={startNew}>+ New</button>}
    >
      {tabSlug ? <InventoryTabs active={tabSlug} /> : null}
      <ErrorBox msg={err} />
      {loading ? <div>Loading...</div> : (
        <SimpleTable
          columns={[
            ...columns,
            {
              key: "_actions", label: "Actions", render: (r) => (
                <div style={{ display: "flex", gap: 6 }}>
                  <button style={btnSecondary} onClick={() => setEditing({ ...r })}>Edit</button>
                  <button style={{ ...btnSecondary, color: C.RED }} onClick={() => remove(r.id)}>Delete</button>
                </div>
              ),
            },
          ]}
          rows={data || []}
        />
      )}

      {editing ? (
        <div style={{
          position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)",
          display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100,
        }} onClick={() => setEditing(null)}>
          <Card style={{ width: 480, maxHeight: "85vh", overflowY: "auto" }} >
            <div onClick={(e) => e.stopPropagation()}>
              <h3 style={{ margin: "0 0 12px", color: C.BROWN }}>
                {editing.id ? "Edit" : "New"} {title.replace(/s$/, "")}
              </h3>
              {formErr ? <ErrorBox msg={formErr} /> : null}
              {fields.map(f => (
                <div key={f.key} style={{ marginBottom: 10 }}>
                  <label style={{ display: "block", fontSize: "0.8rem", color: C.MUTED, marginBottom: 3 }}>{f.label}</label>
                  {f.type === "checkbox" ? (
                    <input type="checkbox" checked={!!editing[f.key]} onChange={e => setEditing({ ...editing, [f.key]: e.target.checked })} />
                  ) : f.type === "select" ? (
                    <select style={inputStyle} value={editing[f.key] ?? ""} onChange={e => setEditing({ ...editing, [f.key]: e.target.value })}>
                      <option value="">— select —</option>
                      {(f.options || []).map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </select>
                  ) : (
                    <input
                      style={inputStyle}
                      type={f.type === "number" ? "number" : "text"}
                      value={editing[f.key] ?? ""}
                      onChange={e => setEditing({ ...editing, [f.key]: e.target.value })}
                    />
                  )}
                </div>
              ))}
              <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                <button style={btnPrimary} disabled={busy} onClick={save}>{busy ? "Saving..." : "Save"}</button>
                <button style={btnSecondary} onClick={() => setEditing(null)}>Cancel</button>
              </div>
            </div>
          </Card>
        </div>
      ) : null}
    </PageShell>
  );
}
