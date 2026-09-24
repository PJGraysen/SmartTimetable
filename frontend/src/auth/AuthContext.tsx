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
  loading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<PlatformUser | null>(null);
  const [applications, setApplications] = useState<PlatformApplication[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await platformApi.getMe();
      setUser(data.user);
      setApplications(data.applications);
      setError(null);
    } catch (err) {
      setUser(null);
      setApplications([]);
      setError(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const login = useCallback(async (username: string, password: string) => {
    const data = await platformApi.login(username, password);
    setUser(data.user);
    setApplications(data.applications);
    setError(null);
  }, []);

  const logout = useCallback(async () => {
    try {
      await platformApi.logout();
    } finally {
      setUser(null);
      setApplications([]);
    }
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      user,
      applications,
      loading,
      error,
      login,
      logout,
      refresh,
    }),
    [user, applications, loading, error, login, logout, refresh],
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
