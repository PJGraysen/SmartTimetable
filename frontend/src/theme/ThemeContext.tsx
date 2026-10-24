import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type ThemeMode = "light" | "dark" | "system" | "classic";
export type Density = "comfortable" | "compact";
export type AccentKey = "blue" | "green" | "purple" | "amber" | "rose" | "teal";

export type Prefs = {
  theme: ThemeMode;
  accent: AccentKey;
  density: Density;
  sidebarCollapsed: boolean;
  notifySound: boolean;
  notifyBadgeMode: "count" | "dot";
  defaultTimetableView: "master" | "class" | "teacher";
  defaultPrintSize: "A3-landscape" | "A4-portrait";
};

const DEFAULT_PREFS: Prefs = {
  theme: "system",
  accent: "blue",
  density: "comfortable",
  sidebarCollapsed: false,
  notifySound: false,
  notifyBadgeMode: "count",
  defaultTimetableView: "master",
  defaultPrintSize: "A3-landscape",
};

const STORAGE_KEY = "stp.prefs.v1";

const ACCENTS: Record<AccentKey, { primary: string; hover: string; soft: string }> = {
  blue:   { primary: "#244b72", hover: "#1a3a5c", soft: "#e6eef6" },
  green:  { primary: "#166534", hover: "#0f4a24", soft: "#e5f5ec" },
  purple: { primary: "#5b21b6", hover: "#47168f", soft: "#ede9fe" },
  amber:  { primary: "#b45309", hover: "#8a3f07", soft: "#fef3c7" },
  rose:   { primary: "#9f1239", hover: "#7a0e2c", soft: "#ffe4e6" },
  teal:   { primary: "#0f766e", hover: "#0b5a54", soft: "#ccfbf1" },
};

function loadPrefs(): Prefs {
  if (typeof window === "undefined") return DEFAULT_PREFS;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_PREFS;
    return { ...DEFAULT_PREFS, ...JSON.parse(raw) };
  } catch {
    return DEFAULT_PREFS;
  }
}

type ThemeCtx = {
  prefs: Prefs;
  setPref: <K extends keyof Prefs>(key: K, value: Prefs[K]) => void;
  resetPrefs: () => void;
  resolvedTheme: "light" | "dark";
};

const Ctx = createContext<ThemeCtx | null>(null);

function systemTheme(): "light" | "dark" {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [prefs, setPrefs] = useState<Prefs>(loadPrefs);
  const [sysTheme, setSysTheme] = useState<"light" | "dark">(systemTheme);

  // Track OS theme changes
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = (e: MediaQueryListEvent) => setSysTheme(e.matches ? "dark" : "light");
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  const resolvedTheme: "light" | "dark" =
    prefs.theme === "system" ? sysTheme : prefs.theme;

  // Apply to <html>
  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute("data-theme", resolvedTheme);
    root.setAttribute("data-density", prefs.density);
    root.setAttribute("data-accent", prefs.accent);

    const a = ACCENTS[prefs.accent] || ACCENTS.blue;
    root.style.setProperty("--accent", a.primary);
    root.style.setProperty("--accent-hover", a.hover);
    root.style.setProperty("--accent-soft", a.soft);
  }, [resolvedTheme, prefs.density, prefs.accent]);

  // Persist
  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
    } catch { /* storage full or blocked */ }
  }, [prefs]);

  const setPref = useCallback(<K extends keyof Prefs>(key: K, value: Prefs[K]) => {
    setPrefs((prev) => ({ ...prev, [key]: value }));
  }, []);

  const resetPrefs = useCallback(() => setPrefs(DEFAULT_PREFS), []);

  const value = useMemo<ThemeCtx>(
    () => ({ prefs, setPref, resetPrefs, resolvedTheme }),
    [prefs, setPref, resetPrefs, resolvedTheme],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useTheme(): ThemeCtx {
  const v = useContext(Ctx);
  if (v === null) throw new Error("useTheme must be used within ThemeProvider");
  return v;
}

export { ACCENTS };
