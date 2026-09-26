import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import * as lib from "../../services/library";

function BarChart({ data, colour = "#1e3a8a" }: { data: { label: string; value: number }[]; colour?: string }) {
  const max = Math.max(1, ...data.map((d) => d.value));
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: "0.35rem", height: 180, padding: "0.5rem 0" }}>
      {data.map((d) => (
        <div key={d.label} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center" }}>
          <div title={`${d.label}: ${d.value}`} style={{
            width: "100%", maxWidth: 40, height: `${(d.value / max) * 140}px`,
            background: colour, borderRadius: 4, transition: "height 200ms ease",
          }} />
          <div style={{ fontSize: "0.65rem", color: "#64748b", marginTop: 4,
                        writingMode: "vertical-rl", transform: "rotate(180deg)" }}>{d.label}</div>
        </div>
      ))}
    </div>
  );
}

function LineChart({ data }: { data: { date: string; count: number }[] }) {
  if (data.length === 0) return <div style={{ color: "#64748b" }}>No data</div>;
  const max = Math.max(1, ...data.map((d) => d.count));
  const w = 600, h = 160;
  const points = data.map((d, i) => {
    const x = (i / Math.max(1, data.length - 1)) * w;
    const y = h - (d.count / max) * (h - 20) - 10;
    return `${x},${y}`;
  }).join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none"
         style={{ width: "100%", height: 180, background: "#f8fafc", borderRadius: 8 }}>
      <polyline fill="none" stroke="#1e3a8a" strokeWidth="2" points={points} />
      <line x1="0" y1={h - 10} x2={w} y2={h - 10} stroke="#cbd5e1" strokeWidth="1" />
    </svg>
  );
}

export default function AnalyticsPage() {
  const [loading, setLoading] = useState(true);
  const [circ, setCirc] = useState<any>(null);
  const [subj, setSubj] = useState<any>(null);
  const [peak, setPeak] = useState<any>(null);
  const [top, setTop] = useState<any>(null);

  useEffect(() => {
    Promise.all([
      lib.analyticsCirculation(30).catch(() => null),
      lib.analyticsSubjectMix().catch(() => null),
      lib.analyticsPeakPeriods().catch(() => null),
      lib.analyticsTopTitles().catch(() => null),
    ]).then(([c, s, p, t]) => { setCirc(c); setSubj(s); setPeak(p); setTop(t); })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div style={{ padding: "2rem", display: "flex", alignItems: "center", gap: "0.5rem", color: "#64748b" }}>
      <Loader2 size={18} className="spin" /> Loading analytics…
    </div>
  );

  return (
    <div style={{ padding: "1.5rem" }}>
      <div style={{ marginBottom: "1rem" }}>
        <span style={{ fontSize: "0.75rem", letterSpacing: "0.08em", color: "#748095", fontWeight: 700 }}>
          LIBRARY INTELLIGENCE
        </span>
        <h1 style={{ marginTop: "0.35rem" }}>Analytics</h1>
        <p style={{ color: "#748095" }}>Circulation trends, subject mix, and top titles.</p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: "1.25rem", marginBottom: "1.25rem" }}>
        <section style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, padding: "1.25rem" }}>
          <h2 style={{ marginTop: 0, fontSize: "1rem" }}>Daily circulation (last {circ?.days ?? 30} days)</h2>
          <LineChart data={circ?.series ?? []} />
        </section>
        <section style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, padding: "1.25rem" }}>
          <h2 style={{ marginTop: 0, fontSize: "1rem" }}>Loans by weekday</h2>
          <BarChart colour="#0e7490"
                    data={(peak?.by_weekday ?? []).map((d: any) => ({ label: d.day, value: d.count }))} />
        </section>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.25rem" }}>
        <section style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, padding: "1.25rem" }}>
          <h2 style={{ marginTop: 0, fontSize: "1rem" }}>Subject mix</h2>
          <BarChart colour="#7c3aed"
                    data={(subj?.subjects ?? []).slice(0, 15).map((s: any) => ({ label: s.subject, value: s.count }))} />
        </section>
        <section style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, padding: "1.25rem" }}>
          <h2 style={{ marginTop: 0, fontSize: "1rem" }}>Top borrowed titles</h2>
          <div style={{ maxHeight: 260, overflowY: "auto" }}>
            {(top?.titles ?? []).map((t: any) => (
              <div key={t.id} style={{ display: "flex", justifyContent: "space-between",
                                        padding: "0.4rem 0", borderBottom: "1px solid #f1f5f9", fontSize: "0.85rem" }}>
                <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "80%" }}>{t.title}</span>
                <span style={{ fontWeight: 700, color: "#1e3a8a" }}>{t.loans}</span>
              </div>
            ))}
          </div>
        </section>
      </div>

      <style>{`
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
