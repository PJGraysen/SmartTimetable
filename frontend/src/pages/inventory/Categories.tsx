import { CrudPage } from "./_CrudPage";
import { inventoryApi } from "../../services/inventory";

export default function Categories() {
  return <CrudPage
    title="Categories"
    subtitle="Item classification tree"
    api={inventoryApi.categories as any}
    columns={[
      { key: "code", label: "Code" },
      { key: "name", label: "Name" },
      { key: "parent_name", label: "Parent" },
      { key: "is_consumable", label: "Consumable", render: r => r.is_consumable ? "✓" : "—" },
      { key: "is_active", label: "Active", render: r => r.is_active ? "✓" : "—" },
    ]}
    fields={[
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "is_consumable", label: "Consumable", type: "checkbox" },
      { key: "is_active", label: "Active", type: "checkbox" },
    ]}
    tabSlug="categories"
  />;
}
