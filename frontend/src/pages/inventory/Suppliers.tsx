import { CrudPage } from "./_CrudPage";
import { inventoryApi } from "../../services/inventory";

export default function Suppliers() {
  return <CrudPage
    title="Suppliers"
    subtitle="Vendors and service providers"
    api={inventoryApi.suppliers as any}
    columns={[
      { key: "code", label: "Code" },
      { key: "name", label: "Name" },
      { key: "contact_person", label: "Contact" },
      { key: "phone", label: "Phone" },
      { key: "email", label: "Email" },
      { key: "is_active", label: "Active", render: r => r.is_active ? "✓" : "—" },
    ]}
    fields={[
      { key: "code", label: "Code", required: true },
      { key: "name", label: "Name", required: true },
      { key: "contact_person", label: "Contact Person" },
      { key: "phone", label: "Phone" },
      { key: "email", label: "Email" },
      { key: "is_active", label: "Active", type: "checkbox" },
    ]}
    tabSlug="suppliers"
  />;
}
