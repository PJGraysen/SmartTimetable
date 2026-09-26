import type { ReactElement } from "react";
import ReservationsPage from "./pages/library/ReservationsPage";
import AnalyticsPage from "./pages/library/AnalyticsPage";
import StudentPortalPage from "./pages/library/StudentPortalPage";
import AuditsPage from "./pages/library/AuditsPage";
import BookReaderPage from "./pages/library/BookReaderPage";
import LibraryShell from "./components/library/LibraryShell";
import ResourcesPage from "./pages/library/ResourcesPage";
import ResourceViewerPage from "./pages/library/ResourceViewerPage";

import LoginPage from "./pages/LoginPage";
import HomeHub from "./pages/HomeHub";
import Dashboard from "./pages/Dashboard";
import Placeholder from "./pages/Placeholder";
import AIAssistant from "./pages/AIAssistant";
import Scheduling from "./Scheduling";
import AcademicsManagement from "./pages/AcademicsManagement";
import Timetable from "./pages/Timetable";

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
import StreamSummaryPage from "./pages/academics/StreamSummaryPage";
import BulkReportsPage from "./pages/academics/BulkReportsPage";
import AuditTrailPage from "./pages/academics/AuditTrailPage";
import CommentsPage from "./pages/academics/CommentsPage";
import GradingSchemePage from "./pages/academics/GradingSchemePage";
import RankingPage from "./pages/academics/RankingPage";

import AdminConsole from "./pages/AdminConsole";
import ErrorLogsPage from "./pages/admin/ErrorLogsPage";
import TeachersAdminPage from "./pages/admin/TeachersAdminPage";
import InventoryDashboard from "./pages/inventory/Dashboard";
import InventoryDepartments from "./pages/inventory/Departments";
import InventoryLocations from "./pages/inventory/Locations";
import InventoryCategories from "./pages/inventory/Categories";
import InventorySuppliers from "./pages/inventory/Suppliers";
import InventoryItems from "./pages/inventory/Items";
import InventoryAssets from "./pages/inventory/Assets";
import InventoryStock from "./pages/inventory/Stock";
import InventoryMovements from "./pages/inventory/Movements";
import InventoryMaintenance from "./pages/inventory/Maintenance";
import InventoryAudits from "./pages/inventory/Audits";
import InventoryReports from "./pages/inventory/Reports";

export type AppRoute = {
  path: string;
  element: ReactElement;
};

export const PUBLIC_ROUTES: AppRoute[] = [
  { path: "/login", element: <LoginPage /> },
];

export const PROTECTED_ROUTES: AppRoute[] = [
  { path: "/home", element: <HomeHub /> },
  { path: "/", element: <Dashboard /> },
  { path: "/timetables", element: <Timetable /> },
  { path: "/scheduling", element: <Scheduling /> },

  // Inventory & Assets
  { path: "/inventory/dashboard", element: <InventoryDashboard /> },
  { path: "/inventory/departments", element: <InventoryDepartments /> },
  { path: "/inventory/locations", element: <InventoryLocations /> },
  { path: "/inventory/categories", element: <InventoryCategories /> },
  { path: "/inventory/suppliers", element: <InventorySuppliers /> },
  { path: "/inventory/items", element: <InventoryItems /> },
  { path: "/inventory/assets", element: <InventoryAssets /> },
  { path: "/inventory/stock", element: <InventoryStock /> },
  { path: "/inventory/movements", element: <InventoryMovements /> },
  { path: "/inventory/maintenance", element: <InventoryMaintenance /> },
  { path: "/inventory/audits", element: <InventoryAudits /> },
  { path: "/inventory/reports", element: <InventoryReports /> },

  { path: "/academics", element: <AcademicsManagement initialTab="groups" /> },
  { path: "/academics/students", element: <StudentsPage /> },
  { path: "/academics/students/:id/analysis", element: <StudentAnalysisPage /> },
  { path: "/academics/students/:id/report-card", element: <ReportCardPage /> },
  { path: "/academics/students/:id/report-form", element: <ReportFormPage /> },
  { path: "/academics/analysis", element: <AnalysisDashboard /> },
  { path: "/academics/assessments", element: <AssessmentsPage /> },
  { path: "/academics/marks", element: <MarksEntryPage /> },
  { path: "/academics/classes", element: <ClassComparisonPage /> },
  { path: "/academics/stream-report", element: <StreamSummaryPage /> },
  { path: "/academics/bulk-reports", element: <BulkReportsPage /> },
  { path: "/academics/audit", element: <AuditTrailPage /> },
  { path: "/academics/comments", element: <CommentsPage /> },
  { path: "/academics/grading", element: <GradingSchemePage /> },
  { path: "/academics/ranking", element: <RankingPage /> },

  { path: "/teachers", element: <TeachersAdminPage /> },
  { path: "/subjects", element: <AcademicsManagement initialTab="subjects" /> },
  { path: "/rooms", element: <AcademicsManagement initialTab="rooms" /> },

  { path: "/academic-analysis", element: <AnalysisDashboard /> },

  { path: "/library", element: <LibraryShell><LibraryDashboard /></LibraryShell> },
  { path: "/library/catalogue", element: <LibraryShell><CataloguePage /></LibraryShell> },
  { path: "/library/catalogue/new", element: <LibraryShell><BookFormPage /></LibraryShell> },
  { path: "/library/catalogue/:id", element: <LibraryShell><BookDetailPage /></LibraryShell> },
  { path: "/library/read/:bookId", element: <LibraryShell><BookReaderPage /></LibraryShell> },
  { path: "/library/members", element: <LibraryShell><MembersPage /></LibraryShell> },
  { path: "/library/members/new", element: <LibraryShell><MemberFormPage /></LibraryShell> },
  { path: "/library/members/:id", element: <LibraryShell><MemberDetailPage /></LibraryShell> },
  { path: "/library/circulation", element: <LibraryShell><CirculationPage /></LibraryShell> },
  { path: "/library/loans", element: <LibraryShell><LoansPage /></LibraryShell> },
  { path: "/library/reservations", element: <LibraryShell><ReservationsPage /></LibraryShell> },
  { path: "/library/reports", element: <LibraryShell><ReportsPage /></LibraryShell> },
  { path: "/library/audits", element: <LibraryShell><AuditsPage /></LibraryShell> },
  { path: "/library/analytics", element: <LibraryShell><AnalyticsPage /></LibraryShell> },
  { path: "/library/my", element: <LibraryShell><StudentPortalPage /></LibraryShell> },
  { path: "/library/resources", element: <LibraryShell><ResourcesPage /></LibraryShell> },
  { path: "/library/resources/:id", element: <LibraryShell><ResourceViewerPage /></LibraryShell> },
  { path: "/library/settings", element: <LibraryShell><LoanRulesPage /></LibraryShell> },

  { path: "/validation", element: <Placeholder title="Validation" /> },
  { path: "/settings", element: <Placeholder title="Settings" /> },

  { path: "/ai", element: <AIAssistant /> },

  { path: "/admin", element: <AdminConsole /> },
  { path: "/admin/errors", element: <ErrorLogsPage /> },
  { path: "/admin/teachers", element: <TeachersAdminPage /> },
];