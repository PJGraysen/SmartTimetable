import {SimpleTable, PageShell, useLoad, ErrorBox, Card, C, InventoryTabs} from "./_shared";
import { inventoryApi } from "../../services/inventory";

export default function Movements() {
  const { data, err, loading } = useLoad<any[]>(() => inventoryApi.movements.list());
  return (
    <PageShell title="Movements" subtitle="Unified audit trail of every receipt, issue, transfer, return, disposal">
      <InventoryTabs active="movements" />
      <ErrorBox msg={err} />
      {loading ? <div>Loading...</div> : (
        <SimpleTable
          columns={[
            { key: "occurred_at", label: "When", render: r => new Date(r.occurred_at).toLocaleString() },
            { key: "movement_type", label: "Type" },
            { key: "item_code", label: "Item" },
            { key: "item_name", label: "Name" },
            { key: "from_code", label: "From" },
            { key: "to_code", label: "To" },
            { key: "quantity", label: "Qty" },
            { key: "actor_name", label: "By" },
            { key: "notes", label: "Notes" },
          ]}
          rows={data || []}
        />
      )}
    </PageShell>
  );
}
