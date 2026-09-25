import { CrudPage } from "./_CrudPage";
import { inventoryApi } from "../../services/inventory";

export default function Items() {
  return <CrudPage
    title="Items"
    subtitle="Catalogue of every item — individually tracked or by quantity"
    api={inventoryApi.items as any}
    columns={[
      { key: "code", label: "Code" },
      { key: "name", label: "Name" },
      { key: "category_name", label: "Category" },
      { key: "unit", label: "Unit" },
      { key: "tracking_mode", label: "Tracking" },
      { key: "unit_cost", label: "Unit Cost" },
      { key: "is_active", label: "Active", render: r => r.is_active ? "✓" : "—" },
    ]}
    fields={[
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "category", label: "Category", type: "select", loadOptions: async () => {
          const d = await inventoryApi.categories.list();
          return (d || []).map((c: any) => ({ value: c.id, label: `${c.code} — ${c.name}` }));
        }},
      { key: "unit", label: "Unit (pcs, kg, L)" },
      { key: "tracking_mode", label: "Tracking", type: "select", options: [
        { value: "INDIVIDUAL", label: "Individual (serialized)" },
        { value: "QUANTITY", label: "Quantity (bulk)" },
      ]},
      { key: "default_supplier", label: "Default Supplier", type: "select", loadOptions: async () => {
          const d = await inventoryApi.suppliers.list();
          return (d || []).map((s: any) => ({ value: s.id, label: s.name }));
        }},
      { key: "unit_cost", label: "Unit Cost", type: "number" },
      { key: "min_stock", label: "Min Stock", type: "number" },
      { key: "reorder_stock", label: "Reorder Stock", type: "number" },
      { key: "is_active", label: "Active", type: "checkbox" },
    ]}
    tabSlug="items"
  />;
}
