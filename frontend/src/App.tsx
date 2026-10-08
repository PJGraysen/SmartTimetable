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
import { RequireModule } from "./auth/RequireModule";
import PageBar from "./layouts/PageBar";
import ErrorBoundary from "./components/ErrorBoundary";
import { HUB_NAV, STUDENT_HUB, STUDENT_LIBRARY_NAV, STUDENT_TIMETABLE_NAV, STUDENT_ACADEMICS_NAV, MODULE_NAV, MODULE_LABELS, moduleForPath, roleCanSee } from "./navigation";
import { PUBLIC_ROUTES, PROTECTED_ROUTES } from "./routes";
import NotificationBell from "./components/NotificationBell";
import { ThemeProvider, useTheme } from "./theme/ThemeContext";

function Sidebar({ isOpen }: { isOpen: boolean }) {
  const { user, logout, modules, hasModule, role } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const currentModule = moduleForPath(location.pathname);
  const inModule = currentModule !== null;
  // eslint-disable-next-line no-console
  console.log("[Sidebar] path=", location.pathname,
              "currentModule=", currentModule,
              "modules=", modules,
              "hasModule(current)=", currentModule ? hasModule(currentModule) : "n/a");

  // Which items to show
  let items = [] as { to: string; label: string; icon: any; end?: boolean }[];
  let heading = "MAIN";

  if (inModule) {
    if (hasModule(currentModule as string)) {
      // Student-specific sub-navs — a student never sees the full module nav.
      if (role === "STUDENT") {
        if (currentModule === "library") {
          items = STUDENT_LIBRARY_NAV;
          heading = "My Library";
        } else if (currentModule === "scheduling") {
          items = STUDENT_TIMETABLE_NAV;
          heading = "My Timetable";
        } else if (currentModule === "academics") {
          items = STUDENT_ACADEMICS_NAV;
          heading = "My Academics";
        } else {
          items = (MODULE_NAV[currentModule as string] || []).filter((i) => roleCanSee(i, role));
          heading = MODULE_LABELS[currentModule as string] || (currentModule as string).toUpperCase();
        }
      } else {
        items = (MODULE_NAV[currentModule as string] || []).filter((i) => roleCanSee(i, role));
        heading = MODULE_LABELS[currentModule as string] || (currentModule as string).toUpperCase();
      }
    } else {
      items = [];
      heading = "RESTRICTED";
    }
  } else {
    const hubList = role === "STUDENT" ? STUDENT_HUB : HUB_NAV;
    items = hubList.filter((i) => {
      const m = moduleForPath(i.to);
      if (!m) return true;
      if (!hasModule(m)) return false;
      return roleCanSee(i, role);
    });
  }

  // Available modules for the switcher (only when user has more than one)
  const isSuper = modules.includes("*");
  const STUDENT_MODULES = new Set(["library", "academics", "scheduling", "aichat"]);
  const availableModules = (isSuper
    ? Object.keys(MODULE_NAV)
    : Object.keys(MODULE_NAV).filter((m) => modules.includes(m))
  ).filter((m) => !(role === "STUDENT" && !STUDENT_MODULES.has(m)));
  const showSwitcher = availableModules.length > 1;

  async function handleSignOut() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <aside className="sidebar" data-collapsed={!isOpen}>
      <nav className="sidebar-nav">
        {inModule && isOpen && (
          <button
            type="button"
            className="nav-link"
            onClick={() => navigate("/home")}
            style={{
              background: "transparent",
              border: "none",
              cursor: "pointer",
              width: "100%",
              textAlign: "left",
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              marginBottom: "0.5rem",
              color: "#6fcffb",
              fontWeight: 700,
            }}
            title="Back to modules"
          >
            <span style={{ fontSize: 18 }}>{"\u2302"}</span>
            {isOpen && <span>All Modules</span>}
          </button>
        )}

        {isOpen && <div className="nav-section-title">{heading}</div>}

        {items.map(({ to, label, icon: Icon, end }) => (
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

        {showSwitcher && isOpen && (
          <>
            <div className="nav-section-title" style={{ marginTop: "0.85rem" }}>
              MODULES
            </div>
            {availableModules.map((m) => (
              <NavLink
                key={m}
                to={
                  m === "academics"
                    ? "/academics"
                    : m === "library"
                    ? "/library"
                    : m === "inventory"
                    ? "/inventory/dashboard"
                    : m === "scheduling"
                    ? "/timetables"
                    : m === "platform"
                    ? "/admin"
                    : m === "aichat"
                    ? "/ai"
                    : "/home"
                }
                className="nav-link"
                title={MODULE_LABELS[m] || m}
              >
                <span style={{ width: 19, textAlign: "center", fontWeight: 800 }}>
                  {m[0].toUpperCase()}
                </span>
                <span>{MODULE_LABELS[m] || m}</span>
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

        <NotificationBell />

        <ThemeToggleButton />

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


function ThemeToggleButton() {
  const { prefs, setPref, resolvedTheme } = useTheme();
  const next = prefs.theme === "system" ? "light" : prefs.theme === "light" ? "dark" : "system";
  const label =
    prefs.theme === "system"
      ? `System (${resolvedTheme})`
      : prefs.theme[0].toUpperCase() + prefs.theme.slice(1);
  const icon = resolvedTheme === "dark" ? "\uD83C\uDF19" : "\u2600";
  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={() => setPref("theme", next)}
      title={`Theme: ${label}. Click to switch to ${next}.`}
      aria-label="Toggle theme"
    >
      <span style={{ fontSize: 15 }}>{icon}</span>
    </button>
  );
}

export default function App() {
  return (
    <ThemeProvider>
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
          {PROTECTED_ROUTES.map((r) => {
            const m = moduleForPath(r.path);
            const el = m ? (
              <RequireModule name={m}>{r.element}</RequireModule>
            ) : (
              r.element
            );
            return <Route key={r.path} path={r.path} element={el} />;
          })}
          </Route>
        </Routes>
      </ErrorBoundary>
    </ThemeProvider>
  );
}