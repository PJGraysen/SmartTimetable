import { useMemo, useState } from "react";
import {
  C, ErrorBox, PageShell, InventoryTabs, StatusPill, FilterBar,
  btnPrimary, btnSecondary, smallBtn, SectionTitle, useLoad,
  downloadCSV, Card,
} from "./_shared";
import { MaintenanceReportModal } from "./Forms";
import { inventoryApi } from "../../services/inventory";

export default function Maintenance() {
  const { data, err, loading, reload } = useLoad<any[]>(() => inventoryApi.maintenance.list());
  const [search, setSearch] = useState("");
  const [fStatus, setFStatus] = useState("PENDING");
  const [showNew, setShowNew] = useState(false);

  const rows = useMemo(() => {
    const s = search.toLowerCase();
    return (data || []).filter((r: any) => {
      if (fStatus && r.approval_status !== fStatus) return false;
      if (s) {
        const hay = [r.asset_tag, r.description, r.remedy, r.performed_by]
          .map(x => String(x || "")).join(" ").toLowerCase();
        if (!hay.includes(s)) return false;
      }
      return true;
    });
  }, [data, search, fStatus]);

  function exportCSV() {
    downloadCSV("maintenance",
      ["Asset", "Reported", "By", "Description", "Remedy", "Priority", "Status", "Cost", "Approved By", "Approval Note"],
      rows.map((r: any) => [r.asset_tag, r.performed_at || r.created_at, r.performed_by,
                            r.description, r.remedy, r.priority, r.approval_status,
                            r.cost, r.approved_by, r.approval_note]));
  }

  async function approve(id: number) {
    const note = prompt("Approval note (optional):") || "";
    await (inventoryApi as any).maintenanceApi.approve(id, note);
    reload();
  }
  async function reject(id: number) {
    const note = prompt("Rejection reason:");
    if (!note) return;
    await (inventoryApi as any).maintenanceApi.reject(id, note);
    reload();
  }
  async function complete(id: number) {
    if (!confirm("Mark this maintenance as completed? Asset will return to AVAILABLE.")) return;
    await (inventoryApi as any).maintenanceApi.complete(id);
    reload();
  }

  return (
    <PageShell title="Maintenance" subtitle="Report faulty items, approve, track completion"
      actions={
        <div style={{ display: "flex", gap: 6 }}>
          <button style={btnPrimary} onClick={() => setShowNew(true)}>+ Report Faulty Item</button>
          <button style={btnSecondary} onClick={exportCSV}>CSV</button>
        </div>
      }>
      <InventoryTabs active="maintenance" />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 8, marginBottom: 12 }}>
        {["PENDING", "APPROVED", "IN_PROGRESS", "COMPLETED", "REJECTED"].map(s => {
          const count = (data || []).filter((r: any) => r.approval_status === s).length;
          const active = fStatus === s;
          return (
            <Card key={s}
              style={{ cursor: "pointer", borderColor: active ? C.BROWN : undefined }}
              >
              <div onClick={() => setFStatus(s)}>
                <div style={{ fontSize: "0.72rem", color: C.MUTED, letterSpacing: 0.5 }}>{s}</div>
                <div style={{ fontSize: "1.4rem", fontWeight: 700, color: active ? C.BROWN : "#444" }}>{count}</div>
              </div>
            </Card>
          );
        })}
      </div>

      <FilterBar search={search} onSearch={setSearch}
        filters={[
          { label: "Status", value: fStatus, onChange: setFStatus,
            options: [{ value: "", label: "All" },
                      ...["PENDING","APPROVED","IN_PROGRESS","COMPLETED","REJECTED"].map(x => ({ value: x, label: x }))] },
        ]} />

      <ErrorBox msg={err} />
      {loading ? <div>Loading...</div> : (
        <div style={{ background: "#fff", borderRadius: 10, border: `1px solid ${C.BORDER}`, overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
            <thead>
              <tr style={{ background: "#f8fafc", textAlign: "left" }}>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Asset</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Fault</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Priority</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Status</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Cost</th>
                <th style={{ padding: "0.55rem 0.6rem", color: C.MUTED }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && (
                <tr><td colSpan={6} style={{ padding: "1rem", textAlign: "center", color: C.MUTED }}>No maintenance records</td></tr>
              )}
              {rows.map((r: any) => (
                <tr key={r.id} style={{ borderTop: "1px solid #f1f5f9" }}>
                  <td style={{ padding: "0.5rem 0.6rem", fontWeight: 600 }}>{r.asset_tag || r.asset}</td>
                  <td style={{ padding: "0.5rem 0.6rem" }}>
                    <div>{r.description}</div>
                    {r.remedy && <div style={{ fontSize: "0.72rem", color: C.MUTED }}>Remedy: {r.remedy}</div>}
                    {r.performed_by && <div style={{ fontSize: "0.7rem", color: C.MUTED }}>by {r.performed_by}</div>}
                  </td>
                  <td style={{ padding: "0.5rem 0.6rem" }}><StatusPill value={r.priority} /></td>
                  <td style={{ padding: "0.5rem 0.6rem" }}><StatusPill value={r.approval_status} /></td>
                  <td style={{ padding: "0.5rem 0.6rem" }}>KES {Number(r.cost || 0).toLocaleString()}</td>
                  <td style={{ padding: "0.5rem 0.6rem" }}>
                    <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                      {r.approval_status === "PENDING" && (
                        <>
                          <button style={{ ...smallBtn, color: "#10B981", borderColor: "#10B981" }} onClick={() => approve(r.id)}>Approve</button>
                          <button style={{ ...smallBtn, color: "#EF4444", borderColor: "#EF4444" }} onClick={() => reject(r.id)}>Reject</button>
                        </>
                      )}
                      {r.approval_status === "APPROVED" && (
                        <button style={{ ...smallBtn, color: "#10B981", borderColor: "#10B981" }} onClick={() => complete(r.id)}>Mark Complete</button>
                      )}
                      {r.approval_status === "COMPLETED" && (
                        <span style={{ color: "#10B981", fontSize: "0.75rem", fontWeight: 600 }}>✓ Done</span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <MaintenanceReportModal open={showNew} onClose={() => setShowNew(false)} onDone={reload} />
    </PageShell>
  );
}
