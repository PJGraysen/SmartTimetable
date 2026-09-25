import { CrudPage } from "./_CrudPage";
import { inventoryApi } from "../../services/inventory";

const TYPES = ["LAB", "OFFICE", "STORE", "CLASSROOM", "LIBRARY", "HALL", "SPORTS", "OTHER"];

export default function Locations() {
  return <CrudPage
    title="Locations"
    subtitle="Labs, offices, stores, classrooms"
    api={inventoryApi.locations as any}
    columns={[
      { key: "code", label: "Code" },
      { key: "name", label: "Name" },
      { key: "location_type", label: "Type" },
      { key: "department_name", label: "Department" },
      { key: "is_active", label: "Active", render: r => r.is_active ? "✓" : "—" },
    ]}
    fields={[
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "location_type", label: "Type", type: "select", options: TYPES.map(t => ({ value: t, label: t })) },
      { key: "department", label: "Department", type: "select", loadOptions: async () => {
          const d = await inventoryApi.departments.list();
          return (d || []).map((x: any) => ({ value: x.id, label: x.name }));
        }},
      { key: "is_active", label: "Active", type: "checkbox" },
    ]}
    tabSlug="locations"
  />;
}
