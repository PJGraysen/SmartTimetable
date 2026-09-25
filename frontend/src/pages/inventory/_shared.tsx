import { Link } from "react-router-dom";
import { useEffect, useState, ReactNode } from "react";

export const C = {
  BROWN: "#2b1a0f",
  BROWN2: "#5a3a1e",
  SKY: "#22b4f0",
  CREAM: "#f5eee2",
  BORDER: "#e5e7eb",
  MUTED: "#64748b",
  GREEN: "#10b981",
  AMBER: "#f59e0b",
  RED: "#ef4444",
};

export const inputStyle: React.CSSProperties = {
  padding: "0.5rem 0.7rem", borderRadius: 6,
  border: `1px solid ${C.BORDER}`, fontSize: "0.88rem",
  width: "100%", background: "#fff",
};

export const btnPrimary: React.CSSProperties = {
  padding: "0.5rem 1rem", borderRadius: 6, border: "none",
  background: C.BROWN, color: "#fff", cursor: "pointer",
  fontSize: "0.85rem", fontWeight: 600,
};

export const btnSecondary: React.CSSProperties = {
  padding: "0.4rem 0.8rem", borderRadius: 6,
  border: `1px solid ${C.BORDER}`, background: "#fff",
  cursor: "pointer", fontSize: "0.82rem",
};

export function PageShell({ title, subtitle, children, actions }: {
  title: string; subtitle?: string; children: ReactNode; actions?: ReactNode;
}) {
  return (
    <div style={{ padding: "1.2rem 1.4rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 16 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: "1.35rem", color: C.BROWN, fontWeight: 700 }}>{title}</h1>
          {subtitle ? <p style={{ margin: "4px 0 0", color: C.MUTED, fontSize: "0.85rem" }}>{subtitle}</p> : null}
        </div>
        {actions ? <div>{actions}</div> : null}
      </div>
      {children}
    </div>
  );
}

export function Card({ children, style }: { children: ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{
      background: "#fff", border: `1px solid ${C.BORDER}`,
      borderRadius: 10, padding: "1rem 1.1rem", ...style,
    }}>{children}</div>
  );
}

export function useLoad<T>(loader: () => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [err, setErr] = useState<string>("");
  const [loading, setLoading] = useState(true);

  async function reload() {
    setLoading(true); setErr("");
    try {
      const d = await loader();
      setData(d);
    } catch (e: any) {
      setErr(e?.response?.data?.detail || e?.message || String(e));
    } finally { setLoading(false); }
  }

  useEffect(() => { reload(); /* eslint-disable-next-line */ }, []);

  return { data, err, loading, reload };
}

export function SimpleTable({ columns, rows }: {
  columns: { key: string; label: string; render?: (row: any) => ReactNode }[];
  rows: any[];
}) {
  return (
    <div style={{ overflowX: "auto", background: "#fff", borderRadius: 10, border: `1px solid ${C.BORDER}` }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
        <thead>
          <tr style={{ background: "#f8fafc", textAlign: "left" }}>
            {columns.map(c => (
              <th key={c.key} style={{ padding: "0.6rem 0.8rem", borderBottom: `1px solid ${C.BORDER}`, color: C.MUTED, fontWeight: 600 }}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr><td colSpan={columns.length} style={{ padding: "1rem", color: C.MUTED, textAlign: "center" }}>No records</td></tr>
          ) : rows.map((r, i) => (
            <tr key={r.id ?? i} style={{ borderBottom: `1px solid #f1f5f9` }}>
              {columns.map(c => (
                <td key={c.key} style={{ padding: "0.55rem 0.8rem" }}>
                  {c.render ? c.render(r) : (r[c.key] ?? "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ErrorBox({ msg }: { msg: string }) {
  if (!msg) return null;
  return <div style={{ padding: "0.7rem 0.9rem", background: "#fef2f2", color: "#b91c1c", borderRadius: 8, marginBottom: 12, fontSize: "0.85rem" }}>{msg}</div>;
}

const INVENTORY_TABS: { to: string; label: string }[] = [
  { to: "/inventory/dashboard",   label: "Dashboard" },
  { to: "/inventory/items",       label: "Items" },
  { to: "/inventory/assets",      label: "Assets" },
  { to: "/inventory/stock",       label: "Stock" },
  { to: "/inventory/movements",   label: "Movements" },
  { to: "/inventory/maintenance", label: "Maintenance" },
  { to: "/inventory/audits",      label: "Audits" },
  { to: "/inventory/categories",  label: "Categories" },
  { to: "/inventory/locations",   label: "Locations" },
  { to: "/inventory/departments", label: "Departments" },
  { to: "/inventory/suppliers",   label: "Suppliers" },
];

export function InventoryTabs({ active }: { active: string }) {
  return (
    <div style={{
      display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 16,
      borderBottom: `1px solid ${C.BORDER}`, paddingBottom: 8,
    }}>
      {INVENTORY_TABS.map((t) => {
        const isActive = t.to.endsWith("/" + active);
        return (
          <Link key={t.to} to={t.to} style={{
            padding: "0.35rem 0.75rem", borderRadius: 6,
            fontSize: "0.82rem", textDecoration: "none",
            background: isActive ? C.BROWN : "#fff",
            color: isActive ? "#fff" : C.BROWN,
            border: `1px solid ${isActive ? C.BROWN : C.BORDER}`,
            fontWeight: isActive ? 600 : 500,
          }}>{t.label}</Link>
        );
      })}
    </div>
  );
}
