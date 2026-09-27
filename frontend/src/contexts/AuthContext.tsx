import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import http from "../services/http";

export type Role = "SUPER_ADMIN" | "LIBRARIAN" | "DEPT_HEAD" | "TEACHER" | "STAFF" | "STUDENT" | "GUEST";
export type Me = {
  authenticated: boolean;
  id?: number; username?: string; email?: string; full_name?: string;
  role: Role; is_superuser?: boolean; is_staff?: boolean;
  member_id?: string | null; landing_path?: string;
};
type Ctx = { me: Me | null; loading: boolean; refresh: () => Promise<void> };
const Ctx = createContext<Ctx>({ me: null, loading: true, refresh: async () => {} });

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  async function refresh() {
    try { const { data } = await http.get("/core/me/"); setMe(data as Me); }
    catch { setMe({ authenticated: false, role: "GUEST", landing_path: "/library/public" }); }
    finally { setLoading(false); }
  }
  useEffect(() => { void refresh(); }, []);
  return <Ctx.Provider value={{ me, loading, refresh }}>{children}</Ctx.Provider>;
}
export function useAuth() { return useContext(Ctx); }
