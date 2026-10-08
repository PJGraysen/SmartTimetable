import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import * as platformApi from "../services/platform";
import type {
  PlatformApplication,
  PlatformUser,
} from "../services/platform";

type AuthState = {
  user: PlatformUser | null;
  applications: PlatformApplication[];
  modules: string[];   // e.g. ["academics", "library"], or ["*"] for superadmin
  role: string;        // primary role name: SUPER_ADMIN / TEACHER / STUDENT ...
  loading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  hasModule: (name: string) => boolean;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<PlatformUser | null>(null);
  const [applications, setApplications] = useState<PlatformApplication[]>([]);
  const [modules, setModules] = useState<string[]>([]);
  const [role, setRole] = useState<string>("GUEST");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data: any = await platformApi.getMe();
      // eslint-disable-next-line no-console
      console.log("[Auth] /me response:", data);
      // eslint-disable-next-line no-console
      console.log("[Auth] modules =", data.modules, "  role =", data.role);
      setUser(data.user);
      setApplications(data.applications);
      setModules(Array.isArray(data.modules) ? data.modules : []);
      setRole(typeof data.role === "string" ? data.role : "GUEST");
      setError(null);
    } catch (err) {
      setUser(null);
      setApplications([]);
      setModules([]);
      setRole("GUEST");
      setError(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const login = useCallback(async (username: string, password: string) => {
    const data: any = await platformApi.login(username, password);
    setUser(data.user);
    setApplications(data.applications);
    setModules(Array.isArray(data.modules) ? data.modules : []);
    setRole(typeof data.role === "string" ? data.role : "GUEST");
    setError(null);
    // Ensure modules/role are always canonical: re-fetch from /me after login.
    try {
      const me: any = await platformApi.getMe();
      setUser(me.user);
      setApplications(me.applications);
      setModules(Array.isArray(me.modules) ? me.modules : []);
      setRole(typeof me.role === "string" ? me.role : "GUEST");
    } catch {
      /* login response already applied; /me is best-effort */
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await platformApi.logout();
    } finally {
      setUser(null);
      setApplications([]);
      setModules([]);
      setRole("GUEST");
    }
  }, []);

  const hasModule = useCallback(
    (name: string) => {
      if (!name) return true;
      if (modules.includes("*")) return true;
      return modules.includes(name);
    },
    [modules],
  );

  const value = useMemo<AuthState>(
    () => ({
      user,
      applications,
      modules,
      role,
      loading,
      error,
      login,
      logout,
      refresh,
      hasModule,
    }),
    [user, applications, modules, role, loading, error, login, logout, refresh, hasModule],
  );

  return (
    <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (ctx === null) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
