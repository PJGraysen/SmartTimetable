import { useEffect, useState } from "react";
import { Card, C, ErrorBox, PageShell, SimpleTable, btnPrimary, btnSecondary, inputStyle, useLoad, InventoryTabs, downloadCSV, FilterBar } from "./_shared";

export type Field = {
  key: string;
  label: string;
  type?: "text" | "number" | "checkbox" | "select";
  options?: { value: any; label: string }[];
  loadOptions?: () => Promise<{ value: any; label: string }[]>;
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
  const [search, setSearch] = useState("");
  const [dynamicOptions, setDynamicOptions] = useState<Record<string, { value: any; label: string }[]>>({});

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

  useEffect(() => {
    (async () => {
      const next: Record<string, { value: any; label: string }[]> = {};
      for (const f of fields) {
        if (f.type === "select" && f.loadOptions) {
          try { next[f.key] = await f.loadOptions(); }
          catch (e) { next[f.key] = []; }
        } else if (f.type === "select" && f.options) {
          next[f.key] = f.options;
        }
      }
      setDynamicOptions(next);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filteredRows = (data || []).filter((row: any) => {
    if (!search) return true;
    const s = search.toLowerCase();
    return columns.some(c => String(row[c.key] ?? "").toLowerCase().includes(s));
  });

  function handleExport() {
    const headers = columns.map(c => c.label);
    const rows = filteredRows.map((row: any) =>
      columns.map(c => (c.render ? String(c.render(row) ?? "") : String(row[c.key] ?? "")))
    );
    downloadCSV(`${title.toLowerCase().replace(/[^a-z0-9]+/g, "_")}`, headers, rows);
  }

  return (
    <PageShell
      title={title} subtitle={subtitle}
      actions={<button style={btnPrimary} onClick={startNew}>+ New</button>}
    >
      {tabSlug ? <InventoryTabs active={tabSlug} /> : null}
      <FilterBar
        search={search}
        onSearch={setSearch}
        extra={<button style={btnSecondary} onClick={handleExport}>⬇ CSV</button>}
      />
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
          rows={filteredRows}
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
                      {(dynamicOptions[f.key] || f.options || []).map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
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
