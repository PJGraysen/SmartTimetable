import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { AlertTriangle, CheckCircle2, HelpCircle, X, XCircle } from "lucide-react";

export type ConfirmVariant = "danger" | "warning" | "primary" | "info";

export type ConfirmOptions = {
  title: string;
  message: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: ConfirmVariant;
};

type Resolver = (v: boolean) => void;
type ConfirmCtxType = { ask: (o: ConfirmOptions) => Promise<boolean> };

const ConfirmCtx = createContext<ConfirmCtxType>({ ask: async () => false });
export function useConfirm() { return useContext(ConfirmCtx); }

const STYLE: Record<ConfirmVariant, { accent: string; icon: any; bg: string }> = {
  danger:  { accent: "#dc2626", icon: XCircle,       bg: "#fef2f2" },
  warning: { accent: "#d97706", icon: AlertTriangle, bg: "#fffbeb" },
  primary: { accent: "#2b1a0f", icon: HelpCircle,    bg: "#f5eee2" },
  info:    { accent: "#0284c7", icon: CheckCircle2,  bg: "#eff6ff" },
};

export function ConfirmProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<{
    open: boolean; opts: ConfirmOptions; resolve: Resolver | null;
  }>({ open: false, opts: { title: "", message: "" }, resolve: null });

  const ask = useCallback((opts: ConfirmOptions) => {
    return new Promise<boolean>((resolve) => {
      setState({ open: true, opts, resolve });
    });
  }, []);

  const close = (v: boolean) => {
    state.resolve?.(v);
    setState((s) => ({ ...s, open: false, resolve: null }));
  };

  const variant = state.opts.variant ?? "primary";
  const s = STYLE[variant];
  const Icon = s.icon;

  return (
    <ConfirmCtx.Provider value={{ ask }}>
      {children}
      {state.open && createPortal(
        <div
          onClick={() => close(false)}
          style={{
            position: "fixed", inset: 0, zIndex: 10000,
            background: "rgba(10,18,29,0.45)",
            backdropFilter: "blur(4px)",
            display: "grid", placeItems: "center",
            animation: "cfd-in 180ms ease",
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              width: 460, maxWidth: "calc(100vw - 2rem)",
              background: "#fff", borderRadius: 16,
              boxShadow: "0 24px 60px rgba(10,18,29,0.28), 0 0 0 1px rgba(10,18,29,0.05)",
              overflow: "hidden",
              animation: "cfd-scale 220ms cubic-bezier(0.16, 1, 0.3, 1)",
            }}
          >
            <div style={{ display: "flex", alignItems: "flex-start", gap: 14, padding: "1.25rem 1.5rem 0.75rem" }}>
              <div style={{
                width: 44, height: 44, borderRadius: 12,
                background: s.bg, color: s.accent,
                display: "grid", placeItems: "center", flexShrink: 0,
              }}>
                <Icon size={22} />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: "1.05rem", fontWeight: 800, color: "#1e2e40", marginBottom: 4 }}>
                  {state.opts.title}
                </div>
                <div style={{ fontSize: "0.88rem", color: "#64748b", lineHeight: 1.5 }}>
                  {state.opts.message}
                </div>
              </div>
              <button
                onClick={() => close(false)}
                style={{ background: "transparent", border: "none", cursor: "pointer", color: "#94a3b8", padding: 4, marginTop: -4 }}
              ><X size={16} /></button>
            </div>
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", padding: "0.9rem 1.5rem 1.25rem" }}>
              <button
                type="button"
                onClick={() => close(false)}
                style={{
                  padding: "0.55rem 1rem", borderRadius: 8,
                  border: "1px solid #e2e8f0", background: "#fff",
                  cursor: "pointer", fontSize: "0.85rem", fontWeight: 600, color: "#475569",
                }}
              >{state.opts.cancelLabel ?? "Cancel"}</button>
              <button
                type="button"
                autoFocus
                onClick={() => close(true)}
                style={{
                  padding: "0.55rem 1.1rem", borderRadius: 8,
                  border: "none", cursor: "pointer",
                  fontSize: "0.85rem", fontWeight: 700,
                  color: "#fff", background: s.accent,
                  boxShadow: "0 4px 12px " + s.accent + "55",
                }}
              >{state.opts.confirmLabel ?? "Confirm"}</button>
            </div>
          </div>
          <style>{"\n@keyframes cfd-in { from { opacity: 0 } to { opacity: 1 } }\n@keyframes cfd-scale { from { transform: scale(0.94); opacity: 0 } to { transform: scale(1); opacity: 1 } }\n"}</style>
        </div>,
        document.body,
      )}
    </ConfirmCtx.Provider>
  );
}
