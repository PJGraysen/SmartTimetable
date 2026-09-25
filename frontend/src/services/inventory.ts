import http from "./http";

export type Department = {
  id: number; code: string; name: string; description?: string;
  is_active: boolean;
};
export type Location = {
  id: number; code: string; name: string; location_type: string;
  department?: number | null; department_name?: string;
  parent?: number | null; is_active: boolean;
};
export type Category = {
  id: number; code: string; name: string;
  parent?: number | null; parent_name?: string;
  is_consumable: boolean; is_active: boolean;
};
export type Supplier = {
  id: number; code: string; name: string; contact_person?: string;
  phone?: string; email?: string; is_active: boolean;
};
export type Item = {
  id: number; code: string; name: string; category: number;
  category_name?: string; unit: string;
  tracking_mode: "INDIVIDUAL" | "QUANTITY";
  min_stock: string; reorder_stock: string; unit_cost: string;
  default_supplier?: number | null; supplier_name?: string;
  is_active: boolean;
};
export type Asset = {
  id: number; tag: string; item: number; item_name?: string;
  item_code?: string; serial_number?: string;
  current_location?: number | null; location_code?: string;
  location_name?: string; condition: string; status: string;
  purchase_cost: string; is_active: boolean;
};
export type StockLevel = {
  id: number; item: number; item_name?: string; item_code?: string;
  unit?: string; location: number; location_code?: string;
  quantity: string; batch_number?: string;
};
export type Movement = {
  id: number; movement_type: string; item: number; item_name?: string;
  item_code?: string; quantity: string; occurred_at: string;
  from_code?: string; to_code?: string; actor_name?: string;
};
export type MaintenanceLog = {
  id: number; asset: number; asset_tag?: string;
  performed_by?: string; description: string;
  cost: string; performed_at: string; next_due?: string | null;
};
export type AuditSession = {
  id: number; reference: string; location: number; location_code?: string;
  status: "OPEN" | "CLOSED"; started_at: string; closed_at?: string | null;
  notes?: string;
};

const BASE = "/inventory";

// DRF may return {count, next, previous, results} — unwrap it.
function unwrap<T = any>(data: any): T {
  if (data && typeof data === "object" && Array.isArray(data.results)) {
    return data.results as T;
  }
  return data as T;
}

export const inventoryApi = {
  dashboard: () => http.get(`${BASE}/dashboard/`).then(r => unwrap(r.data)),

  departments: {
    list: () => http.get(`${BASE}/departments/`).then(r => unwrap(r.data)),
    create: (d: Partial<Department>) => http.post(`${BASE}/departments/`, d).then(r => unwrap(r.data)),
    update: (id: number, d: Partial<Department>) => http.patch(`${BASE}/departments/${id}/`, d).then(r => unwrap(r.data)),
    remove: (id: number) => http.delete(`${BASE}/departments/${id}/`),
  },
  locations: {
    list: () => http.get(`${BASE}/locations/`).then(r => unwrap(r.data)),
    create: (d: Partial<Location>) => http.post(`${BASE}/locations/`, d).then(r => unwrap(r.data)),
    update: (id: number, d: Partial<Location>) => http.patch(`${BASE}/locations/${id}/`, d).then(r => unwrap(r.data)),
    remove: (id: number) => http.delete(`${BASE}/locations/${id}/`),
  },
  categories: {
    list: () => http.get(`${BASE}/categories/`).then(r => unwrap(r.data)),
    create: (d: Partial<Category>) => http.post(`${BASE}/categories/`, d).then(r => unwrap(r.data)),
    update: (id: number, d: Partial<Category>) => http.patch(`${BASE}/categories/${id}/`, d).then(r => unwrap(r.data)),
    remove: (id: number) => http.delete(`${BASE}/categories/${id}/`),
  },
  suppliers: {
    list: () => http.get(`${BASE}/suppliers/`).then(r => unwrap(r.data)),
    create: (d: Partial<Supplier>) => http.post(`${BASE}/suppliers/`, d).then(r => unwrap(r.data)),
    update: (id: number, d: Partial<Supplier>) => http.patch(`${BASE}/suppliers/${id}/`, d).then(r => unwrap(r.data)),
    remove: (id: number) => http.delete(`${BASE}/suppliers/${id}/`),
  },
  items: {
    list: () => http.get(`${BASE}/items/`).then(r => unwrap(r.data)),
    create: (d: Partial<Item>) => http.post(`${BASE}/items/`, d).then(r => unwrap(r.data)),
    update: (id: number, d: Partial<Item>) => http.patch(`${BASE}/items/${id}/`, d).then(r => unwrap(r.data)),
    remove: (id: number) => http.delete(`${BASE}/items/${id}/`),
  },
  assets: {
    list: (params?: Record<string, any>) => http.get(`${BASE}/assets/`, { params }).then(r => unwrap(r.data)),
    create: (d: Partial<Asset>) => http.post(`${BASE}/assets/`, d).then(r => unwrap(r.data)),
    update: (id: number, d: Partial<Asset>) => http.patch(`${BASE}/assets/${id}/`, d).then(r => unwrap(r.data)),
    remove: (id: number) => http.delete(`${BASE}/assets/${id}/`),
  },
  stock: {
    list: () => http.get(`${BASE}/stock/`).then(r => unwrap(r.data)),
    create: (d: Partial<StockLevel>) => http.post(`${BASE}/stock/`, d).then(r => unwrap(r.data)),
    update: (id: number, d: Partial<StockLevel>) => http.patch(`${BASE}/stock/${id}/`, d).then(r => unwrap(r.data)),
    remove: (id: number) => http.delete(`${BASE}/stock/${id}/`),
  },
  movements: {
    list: () => http.get(`${BASE}/movements/`).then(r => unwrap(r.data)),
    create: (d: Partial<Movement>) => http.post(`${BASE}/movements/`, d).then(r => unwrap(r.data)),
  },
  maintenance: {
    list: () => http.get(`${BASE}/maintenance/`).then(r => unwrap(r.data)),
    create: (d: Partial<MaintenanceLog>) => http.post(`${BASE}/maintenance/`, d).then(r => unwrap(r.data)),
  },
  audits: {
    list: () => http.get(`${BASE}/audits/`).then(r => unwrap(r.data)),
    create: (d: Partial<AuditSession>) => http.post(`${BASE}/audits/`, d).then(r => unwrap(r.data)),
    update: (id: number, d: Partial<AuditSession>) => http.patch(`${BASE}/audits/${id}/`, d).then(r => unwrap(r.data)),
  },
};

export const inventoryActions = {
  receive: (payload: { item: number; location: number; quantity: number; batch_number?: string; reference?: string; notes?: string }) =>
    http.post("/inventory/actions/receive/", payload).then(r => unwrap(r.data)),
  issue: (payload: { item: number; location: number; quantity: number; batch_number?: string; recipient?: string; notes?: string }) =>
    http.post("/inventory/actions/issue/", payload).then(r => unwrap(r.data)),
  transfer: (payload: { item: number; from_location: number; to_location: number; quantity: number; batch_number?: string; notes?: string }) =>
    http.post("/inventory/actions/transfer/", payload).then(r => unwrap(r.data)),
  moveAsset: (payload: { asset: number; to_location: number; notes?: string }) =>
    http.post("/inventory/actions/move-asset/", payload).then(r => unwrap(r.data)),
};

// Attach reports to the main api object
(inventoryApi as any).reports = {
  lowStock: () => http.get("/inventory/reports/low-stock/").then(r => unwrap(r.data)),
  expiring: (days = 90) => http.get("/inventory/reports/expiring/", { params: { days } }).then(r => unwrap(r.data)),
  valuation: () => http.get("/inventory/reports/valuation/").then(r => unwrap(r.data)),
  movements: (days = 30) => http.get("/inventory/reports/movements/", { params: { days } }).then(r => unwrap(r.data)),
};

(inventoryApi as any).actions = inventoryActions;


// Detail + history
(inventoryApi as any).assetDetail = (id: number) =>
  http.get(`/inventory/assets/${id}/detail/`).then(r => r.data);
(inventoryApi as any).itemDetail = (id: number) =>
  http.get(`/inventory/items/${id}/detail/`).then(r => r.data);
(inventoryApi as any).locationContents = (id: number) =>
  http.get(`/inventory/locations/${id}/contents/`).then(r => r.data);
(inventoryApi as any).departmentSummary = (id: number) =>
  http.get(`/inventory/departments/${id}/summary/`).then(r => r.data);
(inventoryApi as any).dashboardV2 = () =>
  http.get("/inventory/dashboard/v2/").then(r => r.data);

// Bulk operations
(inventoryApi as any).bulk = {
  transfer: (payload: { asset_ids: number[]; to_location: number; notes?: string }) =>
    http.post("/inventory/actions/bulk-transfer-assets/", payload).then(r => r.data),
  status: (payload: { asset_ids: number[]; status?: string; condition?: string }) =>
    http.post("/inventory/actions/bulk-status-assets/", payload).then(r => r.data),
  maintenance: (payload: { asset_ids: number[]; description?: string; cost?: number }) =>
    http.post("/inventory/actions/bulk-maintenance-assets/", payload).then(r => r.data),
};
