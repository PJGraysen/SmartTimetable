import { useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";
import http from "../services/http";

// ---------------------------------------------------------------------
// HeartbeatProvider
// Pings /api/audit/heartbeat/ every 15s while the app is open, plus on
// every route change so admins see the current page. Failures are silent
// but retried on the next tick.
// ---------------------------------------------------------------------
export default function HeartbeatProvider({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  const lastPathRef = useRef<string>("");

  useEffect(() => {
    let stopped = false;

    async function ping(force = false) {
      if (stopped) return;
      // Skip duplicate ping for the same path in rapid succession
      if (!force && lastPathRef.current === location.pathname) return;
      lastPathRef.current = location.pathname;
      try {
        await http.post("/audit/heartbeat/", { path: location.pathname });
      } catch {
        // reset so next tick retries
        lastPathRef.current = "";
      }
    }

    // Immediate + interval
    ping(true);
    const id = window.setInterval(() => ping(true), 15000);

    // Piggyback on visibility events
    function onVis() {
      if (document.visibilityState === "visible") ping(true);
    }
    document.addEventListener("visibilitychange", onVis);
    window.addEventListener("focus", onVis);

    return () => {
      stopped = true;
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", onVis);
      window.removeEventListener("focus", onVis);
    };
  }, [location.pathname]);

  return <>{children}</>;
}
