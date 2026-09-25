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
  { to: "/inventory/reports",     label: "Reports" },
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

// ---------- Pro utilities ----------
export function downloadCSV(
  filename: string,
  headers: string[],
  rows: (string | number | null | undefined)[][],
) {
  const esc = (v: any) => {
    if (v === null || v === undefined) return "";
    const s = String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const csv = [headers.map(esc).join(","), ...rows.map(r => r.map(esc).join(","))].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename.endsWith(".csv") ? filename : filename + ".csv";
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 500);
}

export function Modal({
  open, onClose, title, children, width = 520,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  width?: number;
}) {
  if (!open) return null;
  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)",
        display: "flex", alignItems: "center", justifyContent: "center", zIndex: 200,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "#fff", borderRadius: 12, width, maxHeight: "90vh",
          overflowY: "auto", boxShadow: "0 20px 40px rgba(0,0,0,0.25)",
        }}
      >
        <div style={{
          padding: "0.9rem 1.1rem", borderBottom: `1px solid ${C.BORDER}`,
          display: "flex", justifyContent: "space-between", alignItems: "center",
        }}>
          <h3 style={{ margin: 0, color: C.BROWN, fontSize: "1rem", fontWeight: 700 }}>{title}</h3>
          <button onClick={onClose} style={{ ...btnSecondary, padding: "0.2rem 0.5rem" }}>✕</button>
        </div>
        <div style={{ padding: "1rem 1.1rem" }}>{children}</div>
      </div>
    </div>
  );
}

export function FilterBar({
  search, onSearch, filters, extra,
}: {
  search: string;
  onSearch: (v: string) => void;
  filters?: { label: string; value: string; onChange: (v: string) => void; options: { value: string; label: string }[] }[];
  extra?: ReactNode;
}) {
  return (
    <div style={{
      display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center",
      marginBottom: 12,
    }}>
      <input
        placeholder="Search..."
        value={search}
        onChange={e => onSearch(e.target.value)}
        style={{ ...inputStyle, maxWidth: 260 }}
      />
      {filters?.map(f => (
        <select
          key={f.label}
          value={f.value}
          onChange={e => f.onChange(e.target.value)}
          style={{ ...inputStyle, maxWidth: 200 }}
        >
          {f.options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      ))}
      <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
        {extra}
      </div>
    </div>
  );
}


// ---------------- Pro additions ----------------

export function Drawer({
  open, onClose, title, subtitle, children, width = 560,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: ReactNode;
  width?: number;
}) {
  if (!open) return null;
  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, background: "rgba(0,0,0,0.35)",
        zIndex: 300, display: "flex", justifyContent: "flex-end",
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "#fff", width, height: "100vh", overflowY: "auto",
          boxShadow: "-10px 0 30px rgba(0,0,0,0.2)",
          animation: "slideIn 200ms ease",
        }}
      >
        <div style={{
          padding: "1rem 1.2rem", borderBottom: `1px solid ${C.BORDER}`,
          display: "flex", justifyContent: "space-between", alignItems: "flex-start",
          position: "sticky", top: 0, background: "#fff", zIndex: 2,
        }}>
          <div>
            <h3 style={{ margin: 0, color: C.BROWN, fontSize: "1.05rem", fontWeight: 700 }}>{title}</h3>
            {subtitle ? <div style={{ fontSize: "0.8rem", color: C.MUTED, marginTop: 2 }}>{subtitle}</div> : null}
          </div>
          <button onClick={onClose} style={{ ...btnSecondary, padding: "0.2rem 0.55rem" }}>✕</button>
        </div>
        <div style={{ padding: "1rem 1.2rem" }}>{children}</div>
      </div>
    </div>
  );
}


export function StatusPill({ value }: { value: string }) {
  const v = String(value || "").toUpperCase();
  const map: Record<string, string> = {
    AVAILABLE: "#22C55E", IN_USE: "#3B82F6", MAINTENANCE: "#F59E0B",
    LOANED: "#3B82F6", LOST: "#EF4444", DISPOSED: "#6B7280",
    NEW: "#22C55E", GOOD: "#10B981", FAIR: "#F59E0B", POOR: "#F97316",
    DAMAGED: "#EF4444", OPEN: "#F59E0B", CLOSED: "#10B981",
  };
  const bg = map[v] || "#6B7280";
  return (
    <span style={{
      display: "inline-block", padding: "2px 8px", borderRadius: 999,
      background: bg + "22", color: bg, fontSize: "0.72rem",
      fontWeight: 700, letterSpacing: "0.03em",
    }}>{v || "—"}</span>
  );
}


export function BulkBar({
  count, onClear, children,
}: {
  count: number;
  onClear: () => void;
  children: ReactNode;
}) {
  if (count === 0) return null;
  return (
    <div style={{
      position: "fixed", bottom: 20, left: "50%", transform: "translateX(-50%)",
      background: C.BROWN, color: "#fff", padding: "0.7rem 1.1rem",
      borderRadius: 12, boxShadow: "0 12px 32px rgba(0,0,0,0.3)",
      display: "flex", gap: 10, alignItems: "center", zIndex: 250,
      fontSize: "0.85rem", flexWrap: "wrap",
    }}>
      <b>{count} selected</b>
      <span style={{ opacity: 0.6 }}>|</span>
      {children}
      <button onClick={onClear} style={{
        padding: "0.3rem 0.6rem", borderRadius: 6, border: "1px solid rgba(255,255,255,0.4)",
        background: "transparent", color: "#fff", cursor: "pointer", fontSize: "0.8rem",
      }}>Clear</button>
    </div>
  );
}


export function KV({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div style={{ display: "flex", gap: 8, padding: "0.35rem 0", fontSize: "0.85rem",
                  borderBottom: `1px solid #f1f5f9` }}>
      <div style={{ color: C.MUTED, minWidth: 130 }}>{label}</div>
      <div style={{ fontWeight: 500, flex: 1, wordBreak: "break-word" }}>{value ?? "—"}</div>
    </div>
  );
}


export function SectionTitle({ children }: { children: ReactNode }) {
  return (
    <h4 style={{
      margin: "14px 0 6px", fontSize: "0.85rem", color: C.BROWN,
      textTransform: "uppercase", letterSpacing: "0.05em",
    }}>{children}</h4>
  );
}

export const smallBtn: React.CSSProperties = {
  padding: "0.35rem 0.7rem", borderRadius: 6,
  border: `1px solid ${C.BORDER}`, background: "#fff",
  cursor: "pointer", fontSize: "0.78rem", fontWeight: 600,
};
