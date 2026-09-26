from pathlib import Path
p = Path("src/pages/inventory/_shared.tsx")
src = p.read_text(encoding="utf-8")

OLD = '''export function BulkBar({
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
}'''

NEW = '''export function BulkBar({
  count, onClear, children,
}: {
  count: number;
  onClear: () => void;
  children: ReactNode;
}) {
  if (count === 0) return null;
  return (
    <div style={{
      position: "fixed",
      right: 20,
      top: "50%",
      transform: "translateY(-50%)",
      background: C.BROWN,
      color: "#fff",
      padding: "1rem 0.9rem",
      borderRadius: 12,
      boxShadow: "0 12px 32px rgba(0,0,0,0.35)",
      display: "flex",
      flexDirection: "column",
      gap: 8,
      alignItems: "stretch",
      zIndex: 250,
      fontSize: "0.82rem",
      minWidth: 180,
      maxWidth: 220,
      animation: "slideInRight 200ms ease",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center",
                    borderBottom: "1px solid rgba(255,255,255,0.2)", paddingBottom: 6 }}>
        <b style={{ fontSize: "0.9rem" }}>{count} selected</b>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
        {children}
      </div>
      <button onClick={onClear} style={{
        padding: "0.35rem 0.6rem", borderRadius: 6,
        border: "1px solid rgba(255,255,255,0.4)",
        background: "transparent", color: "#fff",
        cursor: "pointer", fontSize: "0.78rem", marginTop: 4,
      }}>Clear selection</button>
    </div>
  );
}'''

if NEW in src:
    print("[1] BulkBar already right-aligned")
elif OLD in src:
    src = src.replace(OLD, NEW, 1)
    p.write_text(src, encoding="utf-8")
    print("[1] BulkBar moved to right-center")
else:
    print("[1] WARN: BulkBar pattern not found")
