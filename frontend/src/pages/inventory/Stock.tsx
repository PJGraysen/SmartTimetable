import { CrudPage } from "./_CrudPage";
import { inventoryApi } from "../../services/inventory";

export default function Stock() {
  return <CrudPage
    title="Stock Levels"
    subtitle="Bulk quantities per item per location (with batch tracking)"
    api={inventoryApi.stock as any}
    columns={[
      { key: "item_code", label: "Item" },
      { key: "item_name", label: "Name" },
      { key: "location_code", label: "Location" },
      { key: "quantity", label: "Quantity" },
      { key: "unit", label: "Unit" },
      { key: "batch_number", label: "Batch" },
    ]}
    fields={[
      { key: "item", label: "Item", type: "select", required: true, loadOptions: async () => {
          const d = await inventoryApi.items.list();
          return (d || []).map((i: any) => ({ value: i.id, label: `${i.code} — ${i.name}` }));
        }},
      { key: "location", label: "Location", type: "select", required: true, loadOptions: async () => {
          const d = await inventoryApi.locations.list();
          return (d || []).map((l: any) => ({ value: l.id, label: `${l.code} — ${l.name}` }));
        }},
      { key: "quantity", label: "Quantity", type: "number", required: true },
      { key: "batch_number", label: "Batch Number" },
    ]}
    tabSlug="stock"
  />;
}
