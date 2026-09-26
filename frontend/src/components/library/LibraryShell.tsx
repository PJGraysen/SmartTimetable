import type { ReactNode } from "react";
import LibraryTabs from "./LibraryTabs";
import NotificationBell from "./NotificationBell";

export default function LibraryShell({ children }: { children: ReactNode }) {
  return (
    <div className="lib-shell" style={{ position: "relative", minHeight: "100vh" }}>
      <div className="lib-shelf-bg" aria-hidden="true" />
      <div className="lib-shell-content" style={{ position: "relative", zIndex: 1 }}>
        <div style={{ display: "flex", justifyContent: "flex-end", padding: "0 0 0.25rem" }}>
          <NotificationBell />
        </div>
        <LibraryTabs />
        {children}
      </div>
      <style>{`
        .lib-shelf-bg {
          position: fixed;
          inset: 0;
          z-index: 0;
          pointer-events: none;
          background:
            linear-gradient(180deg,
              transparent 0%,
              transparent 27.5%,
              rgba(120,53,15,0.22) 28%,
              rgba(120,53,15,0.34) 29%,
              transparent 30%,
              transparent 60.5%,
              rgba(120,53,15,0.22) 61%,
              rgba(120,53,15,0.34) 62%,
              transparent 63%,
              transparent 93.5%,
              rgba(120,53,15,0.22) 94%,
              rgba(120,53,15,0.34) 95%,
              transparent 96%),
            repeating-linear-gradient(90deg,
              rgba(30,58,138,0.10)  0px,  rgba(30,58,138,0.10)  10px,
              rgba(14,116,144,0.12) 10px,  rgba(14,116,144,0.12) 22px,
              rgba(124,58,237,0.10) 22px,  rgba(124,58,237,0.10) 34px,
              rgba(180,83,9,0.10)   34px,  rgba(180,83,9,0.10)   48px,
              rgba(21,128,61,0.10)  48px,  rgba(21,128,61,0.10)  62px,
              rgba(190,24,93,0.09)  62px,  rgba(190,24,93,0.09)  74px),
            linear-gradient(180deg, #fbfaf7 0%, #f4f1ea 100%);
          opacity: 0.95;
        }
        .lib-shelf-bg::after {
          content: "";
          position: absolute;
          inset: 0;
          background: linear-gradient(180deg,
            rgba(255,255,255,0.86) 0%,
            rgba(255,255,255,0.55) 25%,
            rgba(255,255,255,0.40) 55%,
            rgba(255,255,255,0.55) 100%);
        }
        .lib-shell-content > * { position: relative; z-index: 1; }
      `}</style>
    </div>
  );
}
