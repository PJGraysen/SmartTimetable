from pathlib import Path
p = Path("src/pages/inventory/_shared.tsx")
src = p.read_text(encoding="utf-8")

if "export function copyToClipboard" in src:
    print("[1] copyToClipboard already exists")
else:
    ADD = '''

export function copyToClipboard(text: string, label = "Copied") {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text);
    } else {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    }
    // Lightweight toast
    const el = document.createElement("div");
    el.textContent = label + ": " + text;
    el.style.cssText = "position:fixed;top:20px;right:20px;padding:10px 14px;" +
      "background:#2b1a0f;color:#fff;border-radius:8px;font-size:0.85rem;" +
      "z-index:99999;box-shadow:0 6px 20px rgba(0,0,0,0.3);opacity:0.95;";
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 1800);
  } catch { /* ignore */ }
}
'''
    p.write_text(src.rstrip() + ADD, encoding="utf-8")
    print("[1] copyToClipboard added")
