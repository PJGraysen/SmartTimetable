import type { ReactElement } from "react";
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

  { path: "/library", element: <LibraryDashboard /> },
  { path: "/library/catalogue", element: <CataloguePage /> },
  { path: "/library/catalogue/new", element: <BookFormPage /> },
  { path: "/library/catalogue/:id", element: <BookDetailPage /> },
  { path: "/library/members", element: <MembersPage /> },
  { path: "/library/members/new", element: <MemberFormPage /> },
  { path: "/library/members/:id", element: <MemberDetailPage /> },
  { path: "/library/circulation", element: <CirculationPage /> },
  { path: "/library/loans", element: <LoansPage /> },
  { path: "/library/reports", element: <ReportsPage /> },
  { path: "/library/resources", element: <ResourcesPage /> },
  { path: "/library/resources/:id", element: <ResourceViewerPage /> },
  { path: "/library/settings", element: <LoanRulesPage /> },

  { path: "/validation", element: <Placeholder title="Validation" /> },
  { path: "/settings", element: <Placeholder title="Settings" /> },

  { path: "/ai", element: <AIAssistant /> },

  { path: "/admin", element: <AdminConsole /> },
  { path: "/admin/errors", element: <ErrorLogsPage /> },
  { path: "/admin/teachers", element: <TeachersAdminPage /> },
];