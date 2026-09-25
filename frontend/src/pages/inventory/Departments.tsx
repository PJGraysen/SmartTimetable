import { CrudPage } from "./_CrudPage";
import { inventoryApi } from "../../services/inventory";

export default function Departments() {
  return <CrudPage
    title="Departments"
    subtitle="Organisational units that own assets and locations"
    api={inventoryApi.departments as any}
    columns={[
      { key: "code", label: "Code" },
      { key: "name", label: "Name" },
      { key: "description", label: "Description" },
      { key: "is_active", label: "Active", render: r => r.is_active ? "✓" : "—" },
    ]}
    fields={[
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "description", label: "Description" },
      { key: "is_active", label: "Active", type: "checkbox" },
    ]}
    tabSlug="departments"
  />;
}
