from pathlib import Path
import re

p = Path("src/pages/inventory/_shared.tsx")
src = p.read_text(encoding="utf-8")

# Find the Modal function and replace with portal-based version
start = src.find("export function Modal(")
if start == -1:
    print("[1] ABORT: Modal not found"); raise SystemExit(1)

end = src.find("\n}\n", start)
if end == -1:
    print("[1] ABORT: close not found"); raise SystemExit(1)
end += len("\n}\n")

NEW = '''export function Modal({
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

  const panel = (
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
  return createPortal(panel, document.body);
}
'''

src = src[:start] + NEW + src[end:]
p.write_text(src, encoding="utf-8")
print("[1] Modal now uses createPortal")

# Also make sure createPortal is imported
if "createPortal" not in src.split("import { useState")[0]:
    if 'import { createPortal } from "react-dom";' not in src:
        src = 'import { createPortal } from "react-dom";\n' + src
        p.write_text(src, encoding="utf-8")
        print("[2] createPortal import verified")
