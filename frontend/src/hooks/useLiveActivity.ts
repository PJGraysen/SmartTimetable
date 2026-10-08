import { useEffect, useRef, useState } from "react";

export type LiveEvent =
  | { type: "hello"; message: string }
  | { type: "heartbeat"; user_id: number; username: string;
      first_name: string; last_name: string; last_path: string;
      ip_address: string | null; last_seen: string }
  | { type: "audit"; id: string; created_at: string;
      user_username: string; user_name: string; action: string;
      entity_type: string; entity_id: string; description: string;
      ip_address: string | null };

type Status = "connecting" | "open" | "closed";

export function useLiveActivity(enabled: boolean) {
  const [status, setStatus] = useState<Status>("closed");
  const [last, setLast] = useState<LiveEvent | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    if (!enabled) return;

    let disposed = false;

    function connect() {
      if (disposed) return;

      const proto = window.location.protocol === "https:" ? "wss" : "ws";
      const url = `${proto}://${window.location.host}/ws/live/`;
      setStatus("connecting");
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        retryRef.current = 0;
        setStatus("open");
      };

      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data) as LiveEvent;
          setLast(data);
        } catch {
          // ignore bad frames
        }
      };

      ws.onclose = () => {
        setStatus("closed");
        if (disposed) return;
        retryRef.current += 1;
        const delay = Math.min(30000, 1000 * 2 ** Math.min(retryRef.current, 5));
        timerRef.current = window.setTimeout(connect, delay);
      };

      ws.onerror = () => {
        // onclose will fire next; nothing to do here
      };
    }

    connect();

    return () => {
      disposed = true;
      if (timerRef.current !== null) window.clearTimeout(timerRef.current);
      if (wsRef.current) {
        try { wsRef.current.close(); } catch { /* ignore */ }
      }
    };
  }, [enabled]);

  return { status, last };
}
