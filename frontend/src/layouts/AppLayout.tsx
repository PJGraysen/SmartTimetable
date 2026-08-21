import { NavLink, Outlet } from "react-router-dom";
import {
  CalendarDays,
  ClipboardList,
  GraduationCap,
  LayoutDashboard,
  Settings,
  Users,
} from "lucide-react";

const navigation = [
  { label: "Dashboard", path: "/dashboard", icon: LayoutDashboard },
  { label: "Timetable", path: "/timetable", icon: CalendarDays },
  { label: "Scheduling Runs", path: "/scheduling", icon: ClipboardList },
];

const management = [
  { label: "Academics", icon: GraduationCap },
  { label: "Teachers", icon: Users },
];

export default function AppLayout() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">ST</div>
          <div>
            <strong>SmartTimetable</strong>
            <span>Pro</span>
          </div>
        </div>

        <nav className="navigation">
          <p className="nav-heading">MAIN</p>

          {navigation.map(({ label, path, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              className={({ isActive }) =>
                `nav-link ${isActive ? "active" : ""}`
              }
            >
              <Icon size={19} />
              <span>{label}</span>
            </NavLink>
          ))}

          <p className="nav-heading">MANAGEMENT</p>

          {management.map(({ label, icon: Icon }) => (
            <button key={label} className="nav-link disabled-link">
              <Icon size={19} />
              <span>{label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <button className="nav-link">
            <Settings size={19} />
            <span>Settings</span>
          </button>
          <div className="school-info">
            <strong>Queen of Apostles Seminary</strong>
            <span>Senior School</span>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <span className="topbar-label">TIMETABLE MANAGEMENT</span>
          </div>
          <div className="user-area">
            <div className="status-dot" />
            <span>System Online</span>
            <div className="avatar">IT</div>
          </div>
        </header>

        <section className="page-content">
          <Outlet />
        </section>
      </main>
    </div>
  );
}
