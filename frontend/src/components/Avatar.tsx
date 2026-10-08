// Deterministic initials avatar. No assets, no storage, no downloads.
// Color is derived from the employee code so it is stable across sessions
// and unique-looking per teacher — like Slack/GitHub avatars.

const PALETTE: [string, string][] = [
  ["#0ea5e9", "#0369a1"],
  ["#10b981", "#047857"],
  ["#f59e0b", "#b45309"],
  ["#a855f7", "#7c3aed"],
  ["#ef4444", "#b91c1c"],
  ["#14b8a6", "#0f766e"],
  ["#8b5cf6", "#6d28d9"],
  ["#f97316", "#c2410c"],
];

function hash(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return Math.abs(h);
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function Avatar({
  name, code, size = 44, ring,
}: { name: string; code: string; size?: number; ring?: boolean }) {
  const [c1, c2] = PALETTE[hash(code || name) % PALETTE.length];
  const text = initials(name);
  return (
    <div
      style={{
        width: size, height: size, borderRadius: "50%",
        background: `linear-gradient(135deg, ${c1}, ${c2})`,
        color: "#fff",
        display: "grid", placeItems: "center",
        fontSize: Math.max(12, Math.round(size * 0.4)),
        fontWeight: 800, letterSpacing: 0.5,
        boxShadow: ring ? `0 0 0 3px #fff, 0 4px 12px ${c2}55` : `0 2px 8px ${c2}55`,
        flexShrink: 0,
        userSelect: "none",
      }}
    >
      {text}
    </div>
  );
}
