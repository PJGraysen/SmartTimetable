import { useEffect, useRef, useState } from "react";

type Event = {
  id: string; kind: string; level: string; title: string;
  term: string | null; status: string; approved: boolean;
  at: string | null; message: string | null;
};

export default function NotificationsBanner() {
  const [events, setEvents] = useState<Event[]>([]);
  const lastRef = useRef<string | null>(null);

  useEffect(() => {
    let stopped = false;
    const tick = async () => {
      try {
        const url = "/api/scheduling/notifications/" +
          (lastRef.current ? `?since=${encodeURIComponent(lastRef.current)}` : "");
        const r = await fetch(url, { credentials: "include" });
        if (!r.ok) return;
        const data = await r.json();
        if (stopped) return;
        if (data.events?.length) {
          setEvents(prev => [...data.events, ...prev].slice(0, 5));
          lastRef.current = data.events[0].at;
        }
      } catch { /* network hiccup - retry next tick */ }
    };
    tick();
    const h = setInterval(tick, 5000);
    return () => { stopped = true; clearInterval(h); };
  }, []);

  if (!events.length) return null;

  return (
    <div style={{ position: "fixed", top: 12, right: 12, zIndex: 1000 }}>
      {events.map(e => (
        <div key={e.id + e.at} style={{
          background: e.level === "error" ? "#fee" :
                      e.level === "success" ? "#efe" : "#eef",
          border: "1px solid #ccc", borderRadius: 6,
          padding: "8px 12px", marginBottom: 8, minWidth: 260,
          boxShadow: "0 2px 6px rgba(0,0,0,0.1)",
        }}>
          <strong>{e.title}</strong>
          {e.term && <span style={{ marginLeft: 6, color: "#666" }}>({e.term})</span>}
          {e.message && <div style={{ fontSize: 12, color: "#a00", marginTop: 4 }}>{e.message}</div>}
        </div>
      ))}
    </div>
  );
}
