import { useMemo, useState } from "react";
import {
  C, ErrorBox, PageShell, InventoryTabs, StatusPill, FilterBar,
  btnPrimary, btnSecondary, smallBtn, Card, SectionTitle,
  downloadCSV, useLoad,
} from "./_shared";
import { AuditSessionModal } from "./Forms2";
import { inventoryApi } from "../../services/inventory";

export default function Audits() {
  const { data, err, loading, reload } = useLoad<any[]>(() => inventoryApi.audits.list());
  const [search, setSearch] = useState("");
  const [fStatus, setFStatus] = useState("");
  const [showNew, setShowNew] = useState(false);
  const [openId, setOpenId] = useState<number | null>(null);

  const rows = useMemo(() => {
    const s = search.toLowerCase();
    return (data || []).filter((r: any) => {
      if (fStatus && r.status !== fStatus) return false;
      if (s) {
        const hay = [r.reference, r.location_code, r.notes].map(x => String(x || "")).join(" ").toLowerCase();
        if (!hay.includes(s)) return false;
      }
      return true;
    });
  }, [data, search, fStatus]);

  const stats = useMemo(() => {
    const all = data || [];
    const open = all.filter((r: any) => r.status === "OPEN").length;
    const closed = all.filter((r: any) => r.status === "CLOSED").length;
    const totalLines = all.reduce((sum: number, r: any) => sum + (r.lines?.length || 0), 0);
    const totalVariance = all.reduce((sum: number, r: any) =>
      sum + (r.lines || []).reduce((s2: number, l: any) => s2 + Math.abs(Number(l.variance || 0)), 0), 0);
    return { total: all.length, open, closed, totalLines, totalVariance };
  }, [data]);

  function exportCSV() {
    downloadCSV("audits",
      ["Reference", "Location", "Status", "Started", "Closed", "Lines", "Variance"],
      rows.map((r: any) => [r.reference, r.location_code, r.status, r.started_at, r.closed_at || "",
                            (r.lines || []).length,
                            (r.lines || []).reduce((s: number, l: any) => s + Math.abs(Number(l.variance || 0)), 0)]));
  }

  return (
    <PageShell title="Stock Audits" subtitle="Physical count sessions, variance tracking, close-out"
      actions={
        <div style={{ display: "flex", gap: 6 }}>
          <button style={btnPrimary} onClick={() => setShowNew(true)}>+ New Audit Session</button>
          <button style={btnSecondary} onClick={exportCSV}>CSV</button>
        </div>
      }>
      <InventoryTabs active="audits" />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 8, marginBottom: 12 }}>
        <Card><div style={{ fontSize: "0.72rem", color: C.MUTED }}>TOTAL</div><div style={{ fontSize: "1.4rem", fontWeight: 700 }}>{stats.total}</div></Card>
        <Card><div style={{ fontSize: "0.72rem", color: C.MUTED }}>OPEN</div><div style={{ fontSize: "1.4rem", fontWeight: 700, color: "#F59E0B" }}>{stats.open}</div></Card>
        <Card><div style={{ fontSize: "0.72rem", color: C.MUTED }}>CLOSED</div><div style={{ fontSize: "1.4rem", fontWeight: 700, color: "#10B981" }}>{stats.closed}</div></Card>
        <Card><div style={{ fontSize: "0.72rem", color: C.MUTED }}>LINES</div><div style={{ fontSize: "1.4rem", fontWeight: 700 }}>{stats.totalLines}</div></Card>
        <Card><div style={{ fontSize: "0.72rem", color: C.MUTED }}>TOTAL VARIANCE</div><div style={{ fontSize: "1.4rem", fontWeight: 700, color: stats.totalVariance > 0 ? "#EF4444" : "#10B981" }}>{stats.totalVariance}</div></Card>
      </div>

      <FilterBar search={search} onSearch={setSearch}
        filters={[
          { label: "Status", value: fStatus, onChange: setFStatus,
            options: [{ value: "", label: "All" },
                      { value: "OPEN", label: "Open" },
                      { value: "CLOSED", label: "Closed" }] },
        ]} />

      <ErrorBox msg={err} />
      {loading ? <div>Loading...</div> : (
        <div style={{ background: "#fff", borderRadius: 10, border: `1px solid ${C.BORDER}`, overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
            <thead>
              <tr style={{ background: "#f8fafc", textAlign: "left" }}>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Reference</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Location</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Status</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Started</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Lines</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Variance</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && (
                <tr><td colSpan={7} style={{ padding: "1rem", textAlign: "center", color: C.MUTED }}>No audits</td></tr>
              )}
              {rows.map((r: any) => {
                const variance = (r.lines || []).reduce((s: number, l: any) => s + Math.abs(Number(l.variance || 0)), 0);
                return (
                  <tr key={r.id} style={{ borderTop: "1px solid #f1f5f9" }}>
                    <td style={{ padding: "0.5rem 0.6rem", fontWeight: 600 }}>{r.reference}</td>
                    <td style={{ padding: "0.5rem 0.6rem" }}>{r.location_code || "-"}</td>
                    <td style={{ padding: "0.5rem 0.6rem" }}><StatusPill value={r.status} /></td>
                    <td style={{ padding: "0.5rem 0.6rem", color: C.MUTED }}>{new Date(r.started_at).toLocaleString()}</td>
                    <td style={{ padding: "0.5rem 0.6rem" }}>{(r.lines || []).length}</td>
                    <td style={{ padding: "0.5rem 0.6rem", color: variance > 0 ? "#EF4444" : "#10B981", fontWeight: 600 }}>{variance}</td>
                    <td style={{ padding: "0.5rem 0.6rem" }}>
                      <button style={smallBtn} onClick={() => setOpenId(openId === r.id ? null : r.id)}>
                        {openId === r.id ? "Hide lines" : "View lines"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {openId !== null && (
        <div style={{ marginTop: 12 }}>
          <Card>
            <SectionTitle>Audit Lines</SectionTitle>
            {(() => {
              const session = (data || []).find((x: any) => x.id === openId);
              if (!session || !session.lines || session.lines.length === 0) {
                return <div style={{ color: C.MUTED, fontSize: "0.85rem" }}>No lines recorded.</div>;
              }
              return (
                <table style={{ width: "100%", fontSize: "0.82rem" }}>
                  <thead>
                    <tr style={{ textAlign: "left", color: C.MUTED }}>
                      <th style={{ padding: 4 }}>Item</th>
                      <th style={{ padding: 4 }}>Expected</th>
                      <th style={{ padding: 4 }}>Counted</th>
                      <th style={{ padding: 4 }}>Variance</th>
                      <th style={{ padding: 4 }}>Notes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {session.lines.map((l: any) => (
                      <tr key={l.id} style={{ borderTop: "1px solid #f1f5f9" }}>
                        <td style={{ padding: 4 }}>{l.item_code} {l.item_name}</td>
                        <td style={{ padding: 4 }}>{l.expected_quantity}</td>
                        <td style={{ padding: 4 }}>{l.counted_quantity}</td>
                        <td style={{ padding: 4, fontWeight: 700, color: Number(l.variance) !== 0 ? "#EF4444" : "#10B981" }}>{l.variance}</td>
                        <td style={{ padding: 4, color: C.MUTED }}>{l.notes || "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              );
            })()}
          </Card>
        </div>
      )}

      <AuditSessionModal open={showNew} onClose={() => setShowNew(false)} onDone={reload} />
    </PageShell>
  );
}
