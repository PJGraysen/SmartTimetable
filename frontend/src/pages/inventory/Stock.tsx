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
      { key: "quantity", label: "Quantity", type: "number", required: true },
      { key: "batch_number", label: "Batch Number" },
    ]}
    tabSlug="stock"
  />;
}
