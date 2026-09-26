from pathlib import Path
import re

p = Path("src/pages/inventory/_shared.tsx")
src = p.read_text(encoding="utf-8")

if "placement?: \"center\" | \"right\"" in src:
    print("[1] Modal already supports placement")
else:
    # Locate the whole Modal function
    start = src.find("export function Modal(")
    if start == -1:
        print("[1] ABORT: Modal function not found"); raise SystemExit(1)

    # Find matching close brace (naive: next "\n}\n" after start)
    end = src.find("\n}\n", start)
    if end == -1:
        print("[1] ABORT: could not find Modal close"); raise SystemExit(1)
    end += len("\n}\n")

    NEW_MODAL = '''export function Modal({
  open, onClose, title, children, width = 520, placement = "center",
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  width?: number;
  placement?: "center" | "right";
}) {
  if (!open) return null;

  const overlayStyle: React.CSSProperties =
    placement === "right"
      ? {
          position: "fixed",
          inset: 0,
          background: "rgba(0,0,0,0.12)",
          display: "flex",
          alignItems: "center",
          justifyContent: "flex-end",
          paddingRight: 260,
          zIndex: 9998,
        }
      : {
          position: "fixed",
          inset: 0,
          background: "rgba(0,0,0,0.35)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 200,
        };

  return (
    <div onClick={onClose} style={overlayStyle}>
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "#fff",
          borderRadius: 12,
          width,
          maxHeight: "90vh",
          overflowY: "auto",
          boxShadow: "0 20px 40px rgba(0,0,0,0.25)",
        }}
      >
        <div
          style={{
            padding: "0.9rem 1.1rem",
            borderBottom: `1px solid ${C.BORDER}`,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <h3 style={{ margin: 0, color: C.BROWN, fontSize: "1rem", fontWeight: 700 }}>
            {title}
          </h3>
          <button onClick={onClose} style={{ ...btnSecondary, padding: "0.2rem 0.5rem" }}>
            ✕
          </button>
        </div>
        <div style={{ padding: "1rem 1.1rem" }}>{children}</div>
      </div>
    </div>
  );
}
'''

    src = src[:start] + NEW_MODAL + src[end:]
    p.write_text(src, encoding="utf-8")
    print("[1] Modal updated with placement prop")
