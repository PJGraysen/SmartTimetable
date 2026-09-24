import { useEffect, useState } from "react";
import {
  NavLink,
  Outlet,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";
import AIAssistant from "./pages/AIAssistant";
import {
  BookOpen,
  BarChart3,
  CalendarDays,
  ClipboardCheck,
  ClipboardEdit,
  ClipboardList,
  DoorOpen,
  GraduationCap,
  Home as HomeIcon,
  Layers,
  FileStack,
  ScrollText,
  MessageSquare,
  Award,
  Trophy,
  LayoutDashboard,
  LogOut,
  Menu,
  PlayCircle,
  Settings,
  Sparkles,
  Users,
} from "lucide-react";
import "./index.css";
import api from "./api";
import Scheduling from "./Scheduling";
import AcademicsManagement from "./pages/AcademicsManagement";
import Timetable from "./pages/Timetable";
import LoginPage from "./pages/LoginPage";
import HomeHub from "./pages/HomeHub";
import { getAcademicTerms } from "./services/core";
import { useAuth } from "./auth/AuthContext";
import { RequireAuth } from "./auth/RequireAuth";
import PageBar from "./layouts/PageBar";
import LibraryDashboard from "./pages/library/LibraryDashboard";
import CataloguePage from "./pages/library/CataloguePage";
import BookDetailPage from "./pages/library/BookDetailPage";
import BookFormPage from "./pages/library/BookFormPage";
import MembersPage from "./pages/library/MembersPage";
import MemberDetailPage from "./pages/library/MemberDetailPage";
import MemberFormPage from "./pages/library/MemberFormPage";
import CirculationPage from "./pages/library/CirculationPage";
import LoansPage from "./pages/library/LoansPage";
import ReportsPage from "./pages/library/ReportsPage";
import LoanRulesPage from "./pages/library/LoanRulesPage";
import StudentsPage from "./pages/academics/StudentsPage";
import AnalysisDashboard from "./pages/academics/AnalysisDashboard";
import StudentAnalysisPage from "./pages/academics/StudentAnalysisPage";
import AssessmentsPage from "./pages/academics/AssessmentsPage";
import MarksEntryPage from "./pages/academics/MarksEntryPage";
import ReportCardPage from "./pages/academics/ReportCardPage";
import ReportFormPage from "./pages/academics/ReportFormPage";
import ClassComparisonPage from "./pages/academics/ClassComparisonPage";
import BulkReportsPage from "./pages/academics/BulkReportsPage";
import AuditTrailPage from "./pages/academics/AuditTrailPage";
import ErrorBoundary from "./components/ErrorBoundary";
import CommentsPage from "./pages/academics/CommentsPage";
import GradingSchemePage from "./pages/academics/GradingSchemePage";
import RankingPage from "./pages/academics/RankingPage";

function Sidebar({ isOpen }: { isOpen: boolean }) {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const links = [
    { to: "/home", label: "Home", icon: HomeIcon },
    { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
    { to: "/timetables", label: "Timetables", icon: CalendarDays },
    { to: "/scheduling", label: "Scheduling", icon: PlayCircle },
    { to: "/academics", label: "Academics", icon: GraduationCap },
    { to: "/academics/students", label: "Students", icon: Users },
    { to: "/academics/analysis", label: "Analysis", icon: BarChart3 },
    { to: "/academics/classes", label: "Class Comparison", icon: Layers },
    { to: "/academics/bulk-reports", label: "Bulk Reports", icon: FileStack },
    { to: "/academics/audit", label: "Audit Trail", icon: ScrollText },
    { to: "/academics/comments", label: "Comments", icon: MessageSquare },
    { to: "/academics/grading", label: "Grading", icon: Award },
    { to: "/academics/ranking", label: "Ranking", icon: Trophy },
    { to: "/academics/assessments", label: "Assessments", icon: ClipboardList },
    { to: "/academics/marks", label: "Marks Entry", icon: ClipboardEdit },
    { to: "/teachers", label: "Teachers", icon: Users },
    { to: "/subjects", label: "Subjects", icon: BookOpen },
    { to: "/rooms", label: "Rooms", icon: DoorOpen },
    { to: "/validation", label: "Validation", icon: ClipboardCheck },
  ];

  async function handleSignOut() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <aside className="sidebar" data-collapsed={!isOpen}>
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

  const initials = (user?.display_name || user?.username || "?")
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
          <div className="school-name">
            Queen of Apostles Seminary Senior School
          </div>
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
          <span
            className="time-display"
            style={{ color: "#6fcffb", fontWeight: 700, fontSize: "0.95rem" }}
          >
            {currentTime.toLocaleTimeString()}
          </span>
          <span
            className="date-display"
            style={{ color: "#e8d9c2", fontSize: "0.72rem", letterSpacing: "0.04em" }}
          >
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

        <div className="user-avatar" title={user?.display_name || ""}>
          {initials}
        </div>
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
          teachingGroups: Array.isArray(teachingGroups.data) ? teachingGroups.data.length : 0,
          teachers: Array.isArray(teachers.data) ? teachers.data.length : 0,
          subjects: Array.isArray(subjects.data) ? subjects.data.length : 0,
          rooms: Array.isArray(rooms.data) ? rooms.data.length : 0,
        });
      } catch {
        setCounts({ teachingGroups: 0, teachers: 0, subjects: 0, rooms: 0 });
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
          <div className="stat-icon"><GraduationCap size={21} /></div>
          <div>
            <div className="stat-label">Teaching Groups</div>
            <div className="stat-value">{counts.teachingGroups}</div>
            <div className="stat-note">From academic data</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon"><Users size={21} /></div>
          <div>
            <div className="stat-label">Teachers</div>
            <div className="stat-value">{counts.teachers}</div>
            <div className="stat-note">Teacher assignments</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon"><BookOpen size={21} /></div>
          <div>
            <div className="stat-label">Subjects</div>
            <div className="stat-value">{counts.subjects}</div>
            <div className="stat-note">Active subjects</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon"><DoorOpen size={21} /></div>
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
              <p>Run the scheduling engine to generate a new timetable.</p>
            </div>
          </div>

          <div className="generation-panel">
            <div className="generation-icon"><PlayCircle size={32} /></div>
            <div className="generation-content">
              <h3>Ready to generate</h3>
              <p>
                The scheduling engine will enforce teacher clashes, room
                clashes, availability, lesson requirements and teacher
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
          <NavLink to="/scheduling" className="text-button">View all</NavLink>
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
    <div className="ssp-placeholder">
      <div className="ssp-placeholder-icon">
        <Sparkles size={28} />
      </div>
      <h1>{title}</h1>
      <p>This module is ready for implementation.</p>
    </div>
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

function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        <Route
          element={
            <RequireAuth>
              <AppShell />
            </RequireAuth>
          }
        >
          <Route path="/home" element={<HomeHub />} />
          <Route path="/" element={<Dashboard />} />
          <Route path="/timetables" element={<Timetable />} />
          <Route path="/scheduling" element={<Scheduling />} />
          <Route
            path="/academics"
            element={<AcademicsManagement initialTab="groups" />}
          />
          <Route path="/academics/students" element={<StudentsPage />} />
          <Route path="/academics/analysis" element={<AnalysisDashboard />} />
          <Route path="/academics/assessments" element={<AssessmentsPage />} />
          <Route path="/academics/marks" element={<MarksEntryPage />} />
          <Route
            path="/academics/students/:id/analysis"
            element={<StudentAnalysisPage />}
          />
          <Route
            path="/academics/students/:id/report-card"
            element={<ReportCardPage />}
          />
          <Route path="/academics/classes" element={<ClassComparisonPage />} />
          <Route path="/academics/bulk-reports" element={<BulkReportsPage />} />
          <Route path="/academics/audit" element={<AuditTrailPage />} />
          <Route path="/academics/comments" element={<CommentsPage />} />
          <Route path="/academics/grading" element={<GradingSchemePage />} />
          <Route path="/academics/ranking" element={<RankingPage />} />
          <Route path="/academics/students/:id/report-form" element={<ReportFormPage />} />
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
            path="/academic-analysis"
            element={<AnalysisDashboard />}
          />
          <Route path="/library" element={<LibraryDashboard />} />
          <Route path="/library/catalogue" element={<CataloguePage />} />
          <Route path="/library/catalogue/new" element={<BookFormPage />} />
          <Route path="/library/catalogue/:id" element={<BookDetailPage />} />
          <Route path="/library/members" element={<MembersPage />} />
          <Route path="/library/members/new" element={<MemberFormPage />} />
          <Route path="/library/members/:id" element={<MemberDetailPage />} />
          <Route path="/library/circulation" element={<CirculationPage />} />
          <Route path="/library/loans" element={<LoansPage />} />
          <Route path="/library/reports" element={<ReportsPage />} />
          <Route path="/library/settings" element={<LoanRulesPage />} />
          <Route
            path="/validation"
            element={<Placeholder title="Validation" />}
          />
          <Route
            path="/settings"
            element={<Placeholder title="Settings" />}
          />
          <Route path="/ai" element={<AIAssistant />} />
        </Route>
      </Routes>
    </ErrorBoundary>
  );
}

export default App;