import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { setToastHandler } from "../services/http";
import { AlertCircle, CheckCircle2, Info, X, XCircle } from "lucide-react";

export type ToastType = "success" | "error" | "warning" | "info";

export type ToastItem = {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  mitigation?: string;
  ttlMs?: number;
};

type ToastCtxType = {
  push: (t: Omit<ToastItem, "id">) => void;
};

const ToastCtx = createContext<ToastCtxType>({ push: () => {} });
export function useToast() { return useContext(ToastCtx); }

const STYLES: Record<ToastType, {
  bg: string; border: string; fg: string;
  icon: React.ComponentType<{ size?: number; color?: string }>;
}> = {
  success: { bg: "#f0fdf4", border: "#86efac", fg: "#166534", icon: CheckCircle2 },
  error:   { bg: "#fef2f2", border: "#fecaca", fg: "#991b1b", icon: XCircle },
  warning: { bg: "#fffbeb", border: "#fde68a", fg: "#92400e", icon: AlertCircle },
  info:    { bg: "#eff6ff", border: "#bfdbfe", fg: "#1e40af", icon: Info },
};

function ToastCard({ t, onClose }: { t: ToastItem; onClose: () => void }) {
  const s = STYLES[t.type];
  const Icon = s.icon;
  return (
    <div style={{
      display: "flex", gap: "10px",
      padding: "0.75rem 0.9rem",
      background: s.bg, border: `1px solid ${s.border}`,
      borderRadius: "10px", boxShadow: "0 8px 24px rgba(10,18,29,0.14)",
      color: s.fg, fontSize: "0.85rem", lineHeight: 1.45,
    }}>
      <Icon size={18} />
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 700, marginBottom: "2px" }}>{t.title}</div>
        {t.message && <div style={{ opacity: 0.9, fontSize: "0.82rem" }}>{t.message}</div>}
        {t.mitigation && (
          <div style={{
            marginTop: "6px", padding: "5px 8px",
            background: "rgba(255,255,255,0.6)", borderRadius: "6px",
            fontSize: "0.78rem", fontStyle: "italic",
          }}>
            <strong style={{ fontStyle: "normal" }}>What to do:</strong> {t.mitigation}
          </div>
        )}
      </div>
      <button type="button" onClick={onClose} style={{
        background: "transparent", border: "none", color: s.fg,
        cursor: "pointer", padding: 0, alignSelf: "flex-start",
      }}>
        <X size={15} />
      </button>
    </div>
  );
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const push = useCallback((t: Omit<ToastItem, "id">) => {
    const id = Math.random().toString(36).slice(2);
    const now = Date.now();

    setItems((prev) => {
      // Dedupe: identical (type+title+message) within 2s is a repeat,
      // not a new notification. Prevents stacked duplicates from retry
      // loops and parallel axios failures.
      const dup = prev.some(
        (x) =>
          x.type === t.type &&
          x.title === t.title &&
          (x.message ?? "") === (t.message ?? "") &&
          (x as any).__seen &&
          now - (x as any).__seen < 2000,
      );
      if (dup) return prev;

      // Cap visible toasts at 4. Oldest drops on overflow.
      const next = [
        ...prev,
        { ...t, id, __seen: now } as ToastItem,
      ];
      return next.length > 4 ? next.slice(next.length - 4) : next;
    });

    const ttl = t.ttlMs ?? (
      t.type === "error"   ? 12000 :
      t.type === "warning" ? 6000  :
      t.type === "success" ? 3000  :
                             4000
    );
    window.setTimeout(() => {
      setItems((prev) => prev.filter((x) => x.id !== id));
    }, ttl);
  }, []);

  // Bridge: give axios a way to push toasts from anywhere
  useEffect(() => {
    setToastHandler((t) => push(t));
  }, [push]);

  return (
    <ToastCtx.Provider value={{ push }}>
      {children}
      <div style={{
        position: "fixed", top: "1rem", right: "1rem",
        zIndex: 9999, display: "grid", gap: "0.6rem",
        maxWidth: "420px", width: "calc(100vw - 2rem)",
        pointerEvents: "none",
      }}>
        {items.map((t) => (
          <div key={t.id} style={{ pointerEvents: "auto" }}>
            <ToastCard t={t} onClose={() => setItems((prev) => prev.filter((x) => x.id !== t.id))} />
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}