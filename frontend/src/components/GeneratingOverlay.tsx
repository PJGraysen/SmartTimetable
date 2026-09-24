import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import "./GeneratingOverlay.css";

interface Props {
  visible: boolean;
  statusText?: string;
}

export function GeneratingOverlay({ visible, statusText }: Props) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!visible) { setElapsed(0); return; }
    const t0 = Date.now();
    const id = window.setInterval(() => {
      setElapsed(Math.floor((Date.now() - t0) / 1000));
    }, 1000);
    return () => window.clearInterval(id);
  }, [visible]);

  if (!visible) return null;

  const mm = String(Math.floor(elapsed / 60)).padStart(2, "0");
  const ss = String(elapsed % 60).padStart(2, "0");

  const node = (
    <div className="gen-overlay" role="alert" aria-live="polite">
      <div className="gen-card">
        <svg viewBox="0 0 120 120" className="gen-coffee" aria-hidden="true">
          <path className="gen-steam gen-s1" d="M 40 50 Q 34 38 40 26 T 40 6"
                fill="none" stroke="#94a3b8" strokeWidth="3" strokeLinecap="round" />
          <path className="gen-steam gen-s2" d="M 60 50 Q 54 38 60 26 T 60 6"
                fill="none" stroke="#94a3b8" strokeWidth="3" strokeLinecap="round" />
          <path className="gen-steam gen-s3" d="M 80 50 Q 74 38 80 26 T 80 6"
                fill="none" stroke="#94a3b8" strokeWidth="3" strokeLinecap="round" />
          <path d="M 22 55 L 28 95 Q 30 104 40 104 L 80 104 Q 90 104 92 95 L 98 55 Z"
                fill="#ffffff" stroke="#0f172a" strokeWidth="2.5" strokeLinejoin="round" />
          <ellipse cx="60" cy="57" rx="35" ry="4" fill="#78350f" />
          <path d="M 22 55 Q 60 64 98 55"
                fill="none" stroke="#0f172a" strokeWidth="2.5" />
          <path d="M 98 68 Q 116 68 116 82 Q 116 96 98 96"
                fill="none" stroke="#0f172a" strokeWidth="3" strokeLinecap="round" />
          <ellipse cx="60" cy="112" rx="52" ry="5"
                   fill="#e2e8f0" stroke="#cbd5e1" strokeWidth="1" />
        </svg>
        <div className="gen-title">SmartTimeTable Generating...</div>
        <div className="gen-sub">
          {statusText || "Please wait — grab a cup of coffee"}
        </div>
        <div className="gen-timer" aria-label="elapsed time">{mm}:{ss}</div>
        <div className="gen-dots"><span></span><span></span><span></span></div>
      </div>
    </div>
  );

  return createPortal(node, document.body);
}
