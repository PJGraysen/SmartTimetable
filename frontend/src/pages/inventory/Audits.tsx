import {SimpleTable, PageShell, useLoad, ErrorBox, InventoryTabs} from "./_shared";
import { inventoryApi } from "../../services/inventory";

export default function Audits() {
  const { data, err, loading } = useLoad<any[]>(() => inventoryApi.audits.list());
  return (
    <PageShell title="Stock Audits" subtitle="Periodic physical count sessions and variances">
      <InventoryTabs active="audits" />
      <ErrorBox msg={err} />
      {loading ? <div>Loading...</div> : (
        <SimpleTable
          columns={[
            { key: "reference", label: "Reference" },
            { key: "location_code", label: "Location" },
            { key: "status", label: "Status" },
            { key: "started_at", label: "Started", render: r => new Date(r.started_at).toLocaleString() },
            { key: "closed_at", label: "Closed", render: r => r.closed_at ? new Date(r.closed_at).toLocaleString() : "—" },
          ]}
          rows={data || []}
        />
      )}
    </PageShell>
  );
}
