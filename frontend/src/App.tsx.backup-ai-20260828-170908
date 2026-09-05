import { useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import {
  CalendarDays,
  ClipboardCheck,
  GraduationCap,
  LayoutDashboard,
  Settings,
  Users,
  BookOpen,
  DoorOpen,
  PlayCircle,
  Menu,
} from "lucide-react";
import "./index.css";
import api from "./api";
import Scheduling from "./Scheduling";
import AcademicsManagement from "./pages/AcademicsManagement";
import Timetable from "./pages/Timetable";
import { getAcademicTerms } from "./services/core";

function Sidebar({ isOpen }: { isOpen: boolean }) {
  const links = [
    { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
    { to: "/timetables", label: "Timetables", icon: CalendarDays },
    { to: "/scheduling", label: "Scheduling", icon: PlayCircle },
    { to: "/academics", label: "Academics", icon: GraduationCap },
    { to: "/teachers", label: "Teachers", icon: Users },
    { to: "/subjects", label: "Subjects", icon: BookOpen },
    { to: "/rooms", label: "Rooms", icon: DoorOpen },
    { to: "/validation", label: "Validation", icon: ClipboardCheck },
  ];

  return (
    <aside className="sidebar" data-collapsed={!isOpen}>
      <div className="brand">
        <div className="brand-mark">
          <CalendarDays size={24} />
        </div>

        {isOpen && (
          <div>
            <div className="brand-title">SmartTimetable</div>
            <div className="brand-subtitle">Pro</div>
          </div>
        )}
      </div>

      <nav className="sidebar-nav">
        {isOpen && <div className="nav-section-title">MAIN</div>}

        {links.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `nav-link ${isActive ? "active" : ""}`
            }
            title={isOpen ? undefined : label}
          >
            <Icon size={19} />
            {isOpen && <span>{label}</span>}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            `nav-link ${isActive ? "active" : ""}`
          }
          title={isOpen ? undefined : "Settings"}
        >
          <Settings size={19} />
          {isOpen && <span>Settings</span>}
        </NavLink>

        <div className="system-status">
          <span className="status-dot" />
          {isOpen && <span>System Online</span>}
        </div>
      </div>
    </aside>
  );
}

function Header({ onToggleSidebar }: { onToggleSidebar: () => void }) {
  const [activeTerm, setActiveTerm] = useState<{
    academic_year_name: string;
    name: string;
  } | null>(null);

  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    getAcademicTerms()
      .then((terms) => {
        const term = terms.find((item) => item.is_active);

        setActiveTerm(
          term
            ? {
                academic_year_name: term.academic_year_name,
                name: term.name,
              }
            : null,
        );
      })
      .catch(() => {
        setActiveTerm(null);
      });
  }, []);

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

        <div>
          <div className="school-name">
            Queen of Apostles Seminary Senior School
          </div>

          <div className="school-context">SmartTimetable Pro</div>
        </div>
      </div>

      <div className="header-actions">
        <div className="current-time">
          <span className="time-display">
            {currentTime.toLocaleTimeString()}
          </span>
          <span className="date-display">
            {currentTime.toLocaleDateString()}
          </span>
        </div>

        <div className="current-term">
          <span className="term-label">Current Term</span>

          <strong>
            {activeTerm
              ? `${activeTerm.academic_year_name} ${activeTerm.name}`
              : "--"}
          </strong>
        </div>

        <div className="user-avatar">IT</div>
      </div>
    </header>
  );
}

function Dashboard() {
  const [counts, setCounts] = useState({
    teachingGroups: 0,
    teachers: 0,
    subjects: 0,
    rooms: 0,
  });

  useEffect(() => {
    async function loadCounts() {
      try {
        const [teachingGroups, teachers, subjects, rooms] = await Promise.all([
          api.get("/academics/management/teaching-groups/"),
          api.get("/academics/management/teachers/"),
          api.get("/academics/management/subjects/"),
          api.get("/academics/management/rooms/"),
        ]);

        setCounts({
          teachingGroups: Array.isArray(teachingGroups.data)
            ? teachingGroups.data.length
            : 0,
          teachers: Array.isArray(teachers.data) ? teachers.data.length : 0,
          subjects: Array.isArray(subjects.data) ? subjects.data.length : 0,
          rooms: Array.isArray(rooms.data) ? rooms.data.length : 0,
        });
      } catch {
        setCounts({
          teachingGroups: 0,
          teachers: 0,
          subjects: 0,
          rooms: 0,
        });
      }
    }

    void loadCounts();
  }, []);

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Dashboard</h1>
          <p>Overview of timetable management and scheduling.</p>
        </div>

        <NavLink to="/scheduling" className="primary-button">
          <PlayCircle size={18} />
          Generate Timetable
        </NavLink>
      </div>

      <section className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon">
            <GraduationCap size={21} />
          </div>

          <div>
            <div className="stat-label">Teaching Groups</div>
            <div className="stat-value">{counts.teachingGroups}</div>
            <div className="stat-note">From academic data</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">
            <Users size={21} />
          </div>

          <div>
            <div className="stat-label">Teachers</div>
            <div className="stat-value">{counts.teachers}</div>
            <div className="stat-note">Teacher assignments</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">
            <BookOpen size={21} />
          </div>

          <div>
            <div className="stat-label">Subjects</div>
            <div className="stat-value">{counts.subjects}</div>
            <div className="stat-note">Active subjects</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">
            <DoorOpen size={21} />
          </div>

          <div>
            <div className="stat-label">Rooms</div>
            <div className="stat-value">{counts.rooms}</div>
            <div className="stat-note">Available rooms</div>
          </div>
        </div>
      </section>

      <section className="dashboard-grid">
        <div className="panel">
          <div className="panel-header">
            <div>
              <h2>Timetable Generation</h2>
              <p>
                Run the scheduling engine to generate a new timetable.
              </p>
            </div>
          </div>

          <div className="generation-panel">
            <div className="generation-icon">
              <PlayCircle size={32} />
            </div>

            <div className="generation-content">
              <h3>Ready to generate</h3>

              <p>
                The scheduling engine will enforce teacher clashes,
                room clashes, availability, lesson requirements and teacher
                free-afternoon constraints.
              </p>

              <NavLink to="/scheduling" className="secondary-button">
                Open Scheduling
              </NavLink>
            </div>
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <div>
              <h2>System Status</h2>
              <p>Core platform components.</p>
            </div>
          </div>

          <div className="status-list">
            <div className="status-row">
              <span>Backend API</span>
              <span className="status-badge ready">Ready</span>
            </div>

            <div className="status-row">
              <span>Scheduling Engine</span>
              <span className="status-badge ready">Ready</span>
            </div>

            <div className="status-row">
              <span>Validation Engine</span>
              <span className="status-badge ready">Ready</span>
            </div>

            <div className="status-row">
              <span>Database</span>
              <span className="status-badge ready">Ready</span>
            </div>
          </div>
        </div>
      </section>

      <section className="panel recent-panel">
        <div className="panel-header">
          <div>
            <h2>Recent Scheduling Runs</h2>
            <p>Generated timetable history will appear here.</p>
          </div>

          <NavLink to="/scheduling" className="text-button">
            View all
          </NavLink>
        </div>

        <div className="empty-state">
          <CalendarDays size={38} />

          <h3>No scheduling runs displayed yet</h3>

          <p>
            Once the UI is connected to the scheduling API, recent runs will
            appear here automatically.
          </p>
        </div>
      </section>
    </>
  );
}

function Placeholder({ title }: { title: string }) {
  return (
    <div className="page-header">
      <div>
        <h1>{title}</h1>
        <p>This module is ready for implementation.</p>
      </div>
    </div>
  );
}

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className="app-shell">
      <Sidebar isOpen={sidebarOpen} />

      <div className="main-area" data-sidebar-open={sidebarOpen}>
        <Header onToggleSidebar={() => setSidebarOpen(!sidebarOpen)} />

        <main className="content">
          <Routes>
            <Route path="/" element={<Dashboard />} />

            <Route path="/timetables" element={<Timetable />} />

            <Route path="/scheduling" element={<Scheduling />} />

            <Route
              path="/academics"
              element={<AcademicsManagement initialTab="groups" />}
            />

            <Route
              path="/teachers"
              element={<AcademicsManagement initialTab="teachers" />}
            />

            <Route
              path="/subjects"
              element={<AcademicsManagement initialTab="subjects" />}
            />

            <Route
              path="/rooms"
              element={<AcademicsManagement initialTab="rooms" />}
            />

            <Route
              path="/validation"
              element={<Placeholder title="Validation" />}
            />

            <Route
              path="/settings"
              element={<Placeholder title="Settings" />}
            />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default App;
