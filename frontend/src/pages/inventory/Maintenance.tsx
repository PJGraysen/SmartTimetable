import {SimpleTable, PageShell, useLoad, ErrorBox, InventoryTabs} from "./_shared";
import { inventoryApi } from "../../services/inventory";

export default function Maintenance() {
  const { data, err, loading } = useLoad<any[]>(() => inventoryApi.maintenance.list());
  return (
    <PageShell title="Maintenance" subtitle="Asset maintenance history and scheduled service">
      <InventoryTabs active="maintenance" />
      <ErrorBox msg={err} />
      {loading ? <div>Loading...</div> : (
        <SimpleTable
          columns={[
            { key: "asset_tag", label: "Asset" },
            { key: "performed_at", label: "Performed" },
            { key: "performed_by", label: "By" },
            { key: "description", label: "Description" },
            { key: "cost", label: "Cost" },
            { key: "next_due", label: "Next Due", render: r => r.next_due || "—" },
          ]}
          rows={data || []}
        />
      )}
    </PageShell>
  );
}
