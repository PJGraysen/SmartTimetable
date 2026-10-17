import { useEffect, useRef, useState } from "react";

type Event = {
  id: string; kind: string; level: string; title: string;
  term: string | null; status: string; approved: boolean;
  at: string | null; message: string | null;
};

export default function NotificationsBanner() {
  const [events, setEvents] = useState<Event[]>([]);
  const lastRef = useRef<string | null>(null);

  const seenRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    let stopped = false;
    const tick = async () => {
      // Skip when the tab is hidden — background polls would only
      // accumulate stale notifications the user never asked to see.
      if (document.hidden) return;
      try {
        const url = "/api/scheduling/notifications/" +
          (lastRef.current ? `?since=${encodeURIComponent(lastRef.current)}` : "");
        const r = await fetch(url, { credentials: "include" });
        if (!r.ok) return;
        const data = await r.json();
        if (stopped) return;
        if (data.events?.length) {
          // Dedupe by id: the same event never renders twice, even if the
          // backend returns it again on a follow-up poll.
          const fresh = (data.events as Event[]).filter(
            (e) => !seenRef.current.has(e.id),
          );
          if (fresh.length) {
            fresh.forEach((e) => seenRef.current.add(e.id));
            setEvents(prev => [...fresh, ...prev].slice(0, 3));
            // Auto-dismiss each new batch after 5 seconds.
            const ids = fresh.map((e) => e.id);
            window.setTimeout(() => {
              setEvents(prev => prev.filter((x) => !ids.includes(x.id)));
            }, 5000);
          }
          lastRef.current = data.events[0].at;
        }
      } catch { /* network hiccup - retry next tick */ }
    };
    tick();
    const h = setInterval(tick, 5000);
    const onVis = () => { if (!document.hidden) tick(); };
    document.addEventListener("visibilitychange", onVis);
    return () => {
      stopped = true;
      clearInterval(h);
      document.removeEventListener("visibilitychange", onVis);
    };
  }, []);

  if (!events.length) return null;

  return (
    <div style={{ position: "fixed", bottom: 12, right: 12, zIndex: 1000 }}>
      {events.map(e => (
        <div key={e.id} style={{
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
