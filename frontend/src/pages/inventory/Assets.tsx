import { CrudPage } from "./_CrudPage";
import { inventoryApi } from "../../services/inventory";

const CONDITIONS = ["NEW", "GOOD", "FAIR", "POOR", "DAMAGED", "DISPOSED"];
const STATUSES = ["AVAILABLE", "IN_USE", "MAINTENANCE", "LOANED", "LOST", "DISPOSED"];

export default function Assets() {
  return <CrudPage
    title="Assets"
    subtitle="Serially-tracked items with location, custodian, and warranty"
    api={inventoryApi.assets as any}
    columns={[
      { key: "tag", label: "Tag" },
      { key: "item_code", label: "Item" },
      { key: "item_name", label: "Name" },
      { key: "location_code", label: "Location" },
      { key: "condition", label: "Condition" },
      { key: "status", label: "Status" },
      { key: "is_active", label: "Active", render: r => r.is_active ? "✓" : "—" },
    ]}
    fields={[
      { key: "tag", label: "Asset Tag", required: true },
      { key: "serial_number", label: "Serial Number" },
      { key: "condition", label: "Condition", type: "select", options: CONDITIONS.map(c => ({ value: c, label: c })) },
      { key: "status", label: "Status", type: "select", options: STATUSES.map(c => ({ value: c, label: c })) },
      { key: "purchase_cost", label: "Purchase Cost", type: "number" },
      { key: "is_active", label: "Active", type: "checkbox" },
    ]}
    tabSlug="assets"
  />;
}
