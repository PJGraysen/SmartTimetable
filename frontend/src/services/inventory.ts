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

export const inventoryApi = {
  dashboard: () => http.get(`${BASE}/dashboard/`).then(r => r.data),

  departments: {
    list: () => http.get(`${BASE}/departments/`).then(r => r.data),
    create: (d: Partial<Department>) => http.post(`${BASE}/departments/`, d).then(r => r.data),
    update: (id: number, d: Partial<Department>) => http.patch(`${BASE}/departments/${id}/`, d).then(r => r.data),
    remove: (id: number) => http.delete(`${BASE}/departments/${id}/`),
  },
  locations: {
    list: () => http.get(`${BASE}/locations/`).then(r => r.data),
    create: (d: Partial<Location>) => http.post(`${BASE}/locations/`, d).then(r => r.data),
    update: (id: number, d: Partial<Location>) => http.patch(`${BASE}/locations/${id}/`, d).then(r => r.data),
    remove: (id: number) => http.delete(`${BASE}/locations/${id}/`),
  },
  categories: {
    list: () => http.get(`${BASE}/categories/`).then(r => r.data),
    create: (d: Partial<Category>) => http.post(`${BASE}/categories/`, d).then(r => r.data),
    update: (id: number, d: Partial<Category>) => http.patch(`${BASE}/categories/${id}/`, d).then(r => r.data),
    remove: (id: number) => http.delete(`${BASE}/categories/${id}/`),
  },
  suppliers: {
    list: () => http.get(`${BASE}/suppliers/`).then(r => r.data),
    create: (d: Partial<Supplier>) => http.post(`${BASE}/suppliers/`, d).then(r => r.data),
    update: (id: number, d: Partial<Supplier>) => http.patch(`${BASE}/suppliers/${id}/`, d).then(r => r.data),
    remove: (id: number) => http.delete(`${BASE}/suppliers/${id}/`),
  },
  items: {
    list: () => http.get(`${BASE}/items/`).then(r => r.data),
    create: (d: Partial<Item>) => http.post(`${BASE}/items/`, d).then(r => r.data),
    update: (id: number, d: Partial<Item>) => http.patch(`${BASE}/items/${id}/`, d).then(r => r.data),
    remove: (id: number) => http.delete(`${BASE}/items/${id}/`),
  },
  assets: {
    list: (params?: Record<string, any>) => http.get(`${BASE}/assets/`, { params }).then(r => r.data),
    create: (d: Partial<Asset>) => http.post(`${BASE}/assets/`, d).then(r => r.data),
    update: (id: number, d: Partial<Asset>) => http.patch(`${BASE}/assets/${id}/`, d).then(r => r.data),
    remove: (id: number) => http.delete(`${BASE}/assets/${id}/`),
  },
  stock: {
    list: () => http.get(`${BASE}/stock/`).then(r => r.data),
    create: (d: Partial<StockLevel>) => http.post(`${BASE}/stock/`, d).then(r => r.data),
    update: (id: number, d: Partial<StockLevel>) => http.patch(`${BASE}/stock/${id}/`, d).then(r => r.data),
    remove: (id: number) => http.delete(`${BASE}/stock/${id}/`),
  },
  movements: {
    list: () => http.get(`${BASE}/movements/`).then(r => r.data),
    create: (d: Partial<Movement>) => http.post(`${BASE}/movements/`, d).then(r => r.data),
  },
  maintenance: {
    list: () => http.get(`${BASE}/maintenance/`).then(r => r.data),
    create: (d: Partial<MaintenanceLog>) => http.post(`${BASE}/maintenance/`, d).then(r => r.data),
  },
  audits: {
    list: () => http.get(`${BASE}/audits/`).then(r => r.data),
    create: (d: Partial<AuditSession>) => http.post(`${BASE}/audits/`, d).then(r => r.data),
    update: (id: number, d: Partial<AuditSession>) => http.patch(`${BASE}/audits/${id}/`, d).then(r => r.data),
  },
};
