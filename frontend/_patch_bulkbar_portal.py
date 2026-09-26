from pathlib import Path

p = Path("src/pages/inventory/_shared.tsx")
src = p.read_text(encoding="utf-8")

# 1. Add createPortal import (top of file)
if "createPortal" not in src:
    src = 'import { createPortal } from "react-dom";\n' + src
    print("[1] createPortal imported")

# 2. Replace BulkBar with portal-based version
import re
pattern = re.compile(
    r"export function BulkBar\(\{[\s\S]*?\n\}\n",
    re.MULTILINE,
)

NEW = '''export function BulkBar({
  count, onClear, children,
}: {
  count: number;
  onClear: () => void;
  children: ReactNode;
}) {
  if (count === 0) return null;
  const panel = (
    <div
      style={{
        position: "fixed",
        right: 16,
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
        zIndex: 9999,
        fontSize: "0.82rem",
        minWidth: 190,
        maxWidth: 230,
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderBottom: "1px solid rgba(255,255,255,0.2)",
          paddingBottom: 6,
        }}
      >
        <b style={{ fontSize: "0.9rem" }}>{count} selected</b>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
        {children}
      </div>
      <button
        onClick={onClear}
        style={{
          padding: "0.35rem 0.6rem",
          borderRadius: 6,
          border: "1px solid rgba(255,255,255,0.4)",
          background: "transparent",
          color: "#fff",
          cursor: "pointer",
          fontSize: "0.78rem",
          marginTop: 4,
        }}
      >
        Clear selection
      </button>
    </div>
  );
  return createPortal(panel, document.body);
}
'''

match = pattern.search(src)
if not match:
    print("[2] ABORT: BulkBar function not matched. Current BulkBar definition:")
    idx = src.find("export function BulkBar")
    if idx != -1:
        print(src[idx:idx+1200])
    raise SystemExit(1)

src = src[:match.start()] + NEW + src[match.end():]
p.write_text(src, encoding="utf-8")
print("[2] BulkBar replaced with portal version")

# 3. Verify
import subprocess, sys
out = subprocess.run(
    ["powershell", "-NoProfile", "-Command",
     "Select-String -Path src\\pages\\inventory\\_shared.tsx -Pattern 'createPortal|zIndex: 9999' | Select-Object LineNumber, Line"],
    capture_output=True, text=True,
)
print(out.stdout)
