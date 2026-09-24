import { useEffect, useState } from "react";
import {
  NavLink,
  Outlet,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";
import { LogOut, Menu, Settings } from "lucide-react";
import "./index.css";
import "./styles/sidebar.css";
import { getAcademicTerms } from "./services/core";
import { useAuth } from "./auth/AuthContext";
import { RequireAuth } from "./auth/RequireAuth";
import PageBar from "./layouts/PageBar";
import ErrorBoundary from "./components/ErrorBoundary";
import { ToastProvider } from "./components/Toast";
import { MAIN_NAV, ADMIN_NAV, type Role } from "./navigation";
import { PUBLIC_ROUTES, PROTECTED_ROUTES } from "./routes";

type AuthUser = {
  display_name?: string;
  username?: string;
  is_staff?: boolean;
  is_superuser?: boolean;
  groups?: string[];
};

function determineRole(user: AuthUser | null): Role {
  if (!user) return "teacher";
  if (user.is_staff || user.is_superuser) return "admin";
  if (Array.isArray(user.groups) && user.groups.includes("Administrator")) return "admin";
  if (user.username === "admin") return "admin";
  return "teacher";
}

function Sidebar({ isOpen }: { isOpen: boolean }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const u = user as AuthUser | null;
  const role = determineRole(u);
  const isAdmin = role === "admin";

  const visibleMain = MAIN_NAV.filter((item) => !item.roles || item.roles.includes(role));

  async function handleSignOut() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <aside className="sidebar" data-collapsed={!isOpen}>
      <nav className="sidebar-nav">
        {isOpen && <div className="nav-section-title">MAIN</div>}
        {visibleMain.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
            title={isOpen ? undefined : label}
          >
            <Icon size={19} />
            {isOpen && <span>{label}</span>}
          </NavLink>
        ))}

        {isAdmin && (
          <>
            {isOpen && (
              <div className="nav-section-title" style={{ marginTop: "0.85rem" }}>
                ADMIN
              </div>
            )}
            {ADMIN_NAV.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
                title={isOpen ? undefined : label}
              >
                <Icon size={19} />
                {isOpen && <span>{label}</span>}
              </NavLink>
            ))}
          </>
        )}
      </nav>

      <div className="sidebar-footer">
        <NavLink
          to="/settings"
          className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
          title={isOpen ? undefined : "Settings"}
        >
          <Settings size={19} />
          {isOpen && <span>Settings</span>}
        </NavLink>

        <button
          type="button"
          onClick={handleSignOut}
          className="nav-link"
          style={{
            background: "transparent",
            border: "none",
            cursor: "pointer",
            width: "100%",
            textAlign: "left",
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
          }}
          title={isOpen ? undefined : "Sign out"}
        >
          <LogOut size={19} />
          {isOpen && <span>Sign out</span>}
        </button>

        <div className="system-status">
          <span className="status-dot" />
          {isOpen && <span>System Online</span>}
        </div>
      </div>
    </aside>
  );
}

function Header({ onToggleSidebar }: { onToggleSidebar: () => void }) {
  const { user } = useAuth();
  const [activeTerm, setActiveTerm] = useState<{ academic_year_name: string; name: string } | null>(null);
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    getAcademicTerms()
      .then((terms) => {
        const term = terms.find((item) => item.is_active);
        setActiveTerm(term ? { academic_year_name: term.academic_year_name, name: term.name } : null);
      })
      .catch(() => setActiveTerm(null));
  }, []);

  const initials =
    (user?.display_name || user?.username || "?")
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]!.toUpperCase())
      .join("") || "?";

  return (
    <header className="topbar">
      <div className="topbar-left">
        <button
          type="button"
          className="sidebar-toggle"
          onClick={onToggleSidebar}
          title="Toggle sidebar"
          aria-label="Toggle sidebar"
        >
          <Menu size={20} />
        </button>

        <img
          src="/logo.png"
          alt="SmartSchoolPro"
          className="ssp-logo"
          onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
        />

        <div className="ssp-brand-text">
          <div className="school-name">Queen of Apostles Seminary Senior School</div>
          <div className="school-context">SmartSchoolPro</div>
        </div>
      </div>

      <div className="header-actions">
        <div
          className="current-time ssp-clock"
          style={{
            background: "linear-gradient(135deg, #2b1a0f, #5a3a1e)",
            border: "1px solid #22b4f0",
            borderRadius: "10px",
            padding: "0.45rem 0.85rem",
            boxShadow: "0 4px 14px rgba(34, 180, 240, 0.25)",
            display: "flex",
            flexDirection: "column",
            alignItems: "flex-end",
            lineHeight: 1.15,
          }}
        >
          <span className="time-display" style={{ color: "#6fcffb", fontWeight: 700, fontSize: "0.95rem" }}>
            {currentTime.toLocaleTimeString()}
          </span>
          <span className="date-display" style={{ color: "#e8d9c2", fontSize: "0.72rem", letterSpacing: "0.04em" }}>
            {currentTime.toLocaleDateString()}
          </span>
        </div>

        <div className="current-term">
          <span className="term-label">Current Term</span>
          <strong>
            {activeTerm ? `${activeTerm.academic_year_name} ${activeTerm.name}` : "--"}
          </strong>
        </div>

        <div className="user-avatar" title={user?.display_name || ""}>
          {initials}
        </div>
      </div>
    </header>
  );
}

function AppShell() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const location = useLocation();

  return (
    <div className="app-shell">
      <Sidebar isOpen={sidebarOpen} />
      <div className="main-area" data-sidebar-open={sidebarOpen}>
        <Header onToggleSidebar={() => setSidebarOpen(!sidebarOpen)} />
        <main className="content">
          <PageBar />
          <div key={location.pathname} className="ssp-page-transition">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <Routes>
        {PUBLIC_ROUTES.map((r) => (
          <Route key={r.path} path={r.path} element={r.element} />
        ))}

        <Route
          element={
            <RequireAuth>
              <AppShell />
            </RequireAuth>
          }
        >
          {PROTECTED_ROUTES.map((r) => (
            <Route key={r.path} path={r.path} element={r.element} />
          ))}
        </Route>
      </Routes>
    </ErrorBoundary>
  );
}