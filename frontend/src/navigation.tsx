import type { ComponentType } from "react";
import {
  AlertCircle,
  Award,
  BarChart3,
  BookOpen,
  Bot,
  CalendarDays,
  ClipboardCheck,
  ClipboardEdit,
  ClipboardList,
  DoorOpen,
  FileStack,
  FileText,
  GraduationCap,
  Home as HomeIcon,
  Layers,
  LayoutDashboard,
  MessageSquare,
  Package,
  PlayCircle,
  ScrollText,
  Trophy,
  UserCheck,
  UserCog,
  Users,
  LineChart,
  ListChecks,
  FileSpreadsheet,
  TrendingUp as TrendingUpIcon,
  Activity,
  GitMerge,
} from "lucide-react";;;;;;

export type RoleName =
  | "SUPER_ADMIN" | "PRINCIPAL" | "ADMIN" | "SECRETARY"
  | "DEPT_HEAD" | "TEACHER" | "LIBRARIAN" | "STUDENT" | "STAFF" | "GUEST";

export type NavItem = {
  to: string;
  label: string;
  icon: ComponentType<{ size?: number }>;
  end?: boolean;
  // If set, only these roles see the item. Absent = anyone with module access.
  requires?: RoleName[];
};

// ----- Role groups (reusable shortcuts) -----
export const ALL_STAFF: RoleName[] = [
  "SUPER_ADMIN", "PRINCIPAL", "ADMIN", "SECRETARY",
  "DEPT_HEAD", "TEACHER", "LIBRARIAN", "STAFF",
];
export const TEACHING_STAFF: RoleName[] = [
  "SUPER_ADMIN", "PRINCIPAL", "ADMIN", "DEPT_HEAD", "TEACHER",
];
export const ACADEMIC_ADMINS: RoleName[] = [
  "SUPER_ADMIN", "PRINCIPAL", "ADMIN", "SECRETARY",
];
export const ADMINS_ONLY: RoleName[] = [
  "SUPER_ADMIN", "PRINCIPAL", "ADMIN",
];
export const SUPER_ONLY: RoleName[] = ["SUPER_ADMIN"];

export const LIBRARY_ADMINS: RoleName[] = [
  "SUPER_ADMIN", "PRINCIPAL", "ADMIN", "LIBRARIAN",
];
export const TEACHING_AND_ADMIN: RoleName[] = [
  "SUPER_ADMIN", "PRINCIPAL", "ADMIN", "SECRETARY",
  "DEPT_HEAD", "TEACHER",
];
export const STUDENT_ONLY: RoleName[] = ["STUDENT"];

export function roleCanSee(item: NavItem, role: string | null | undefined): boolean {
  if (!item.requires) return true;
  if (!role) return false;
  return item.requires.includes(role as RoleName);
}

// Module keys must match the backend MODULE names exactly.
export const MODULE_LABELS: Record<string, string> = {
  academics: "Academics",
  library: "Library",
  inventory: "Inventory",
  scheduling: "Scheduling",
  platform: "Platform Admin",
  aichat: "AI Assistant",
  reports: "Reports",
  finance: "Finance",
  core: "Home",
};

// ----- Per-module navigation -----
export const MODULE_NAV: Record<string, NavItem[]> = {
  academics: [
    // Landing — role-dependent (student / teacher / admin)
    { to: "/academics", label: "Academics", icon: GraduationCap, end: true },

    // ----- Analysis -----
    { to: "/academics/school",         label: "School Analytics",     icon: BarChart3,       requires: ADMINS_ONLY },
    { to: "/academics/classes",        label: "Class Comparison",     icon: Layers,          requires: TEACHING_STAFF },
    { to: "/academics/stream-report",  label: "Stream Report",        icon: LineChart,       requires: TEACHING_STAFF },
    { to: "/academics/analysis",       label: "Assessment Dashboard", icon: TrendingUpIcon,  requires: TEACHING_STAFF },

    // ----- Marks & Results -----
    { to: "/academics/assessments",    label: "Assessments",          icon: ClipboardCheck,  requires: ADMINS_ONLY },
    { to: "/academics/marks",          label: "Marks Entry",          icon: ClipboardEdit,   requires: TEACHING_STAFF },
    { to: "/academics/ranking",        label: "Ranking",              icon: Trophy,          requires: ACADEMIC_ADMINS },
    { to: "/academics/grading",        label: "Grading Scheme",       icon: ListChecks,      requires: ADMINS_ONLY },

    // ----- Reports -----
    { to: "/academics/bulk-reports",   label: "Bulk Reports",         icon: FileSpreadsheet, requires: TEACHING_STAFF },
    { to: "/academics/comments",       label: "Report Comments",      icon: MessageSquare,   requires: TEACHING_STAFF },

    // ----- Students -----
    { to: "/academics/students",       label: "Students",             icon: Users,           requires: TEACHING_STAFF },

    // ----- Compliance -----
    { to: "/academics/audit",          label: "Audit Trail",          icon: ScrollText,      requires: ADMINS_ONLY },

    // ----- CRUD -----
    { to: "/academics/manage",         label: "Academic Management",  icon: UserCog,         requires: ADMINS_ONLY },
    { to: "/academics/lesson-requirements", label: "Lesson Requirements", icon: ClipboardList, requires: ADMINS_ONLY },
  ],
  inventory: [
    { to: "/inventory/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { to: "/inventory/items", label: "Items", icon: Package },
    { to: "/inventory/assets", label: "Assets", icon: Award },
    { to: "/inventory/stock", label: "Stock", icon: Layers },
    { to: "/inventory/movements", label: "Movements", icon: FileStack },
    { to: "/inventory/maintenance", label: "Maintenance", icon: ClipboardCheck },
    { to: "/inventory/audits", label: "Audits", icon: ClipboardCheck },
    { to: "/inventory/reports", label: "Reports", icon: FileText },
    { to: "/inventory/departments", label: "Departments", icon: Users },
    { to: "/inventory/locations", label: "Locations", icon: DoorOpen },
    { to: "/inventory/categories", label: "Categories", icon: Layers },
    { to: "/inventory/suppliers", label: "Suppliers", icon: UserCheck },
  ],
  library: [
    { to: "/library", label: "Dashboard", icon: LayoutDashboard, end: true },
    { to: "/library/catalogue", label: "Catalogue", icon: BookOpen },
    { to: "/library/circulation", label: "Circulation", icon: ClipboardEdit, requires: LIBRARY_ADMINS },
    { to: "/library/loans", label: "Loans", icon: FileStack },
    { to: "/library/reservations", label: "Reservations", icon: CalendarDays },
    { to: "/library/members", label: "Members", icon: Users, requires: LIBRARY_ADMINS },
    { to: "/library/reports", label: "Reports", icon: FileText, requires: LIBRARY_ADMINS },
    { to: "/library/audits", label: "Audits", icon: ClipboardCheck, requires: LIBRARY_ADMINS },
    { to: "/library/analytics", label: "Analytics", icon: BarChart3, requires: LIBRARY_ADMINS },
  ],
  scheduling: [
    { to: "/timetables", label: "Master Timetable", icon: CalendarDays },  // everyone
    { to: "/scheduling", label: "Scheduling Runs", icon: PlayCircle, requires: ADMINS_ONLY },
    { to: "/validation", label: "Validation", icon: ClipboardCheck, requires: ADMINS_ONLY },
  ],
  platform: [
    { to: "/admin", label: "Admin Console", icon: UserCog },
    { to: "/admin/teachers", label: "Teachers", icon: UserCheck },
    { to: "/admin/teachers/merge", label: "Merge Teachers", icon: GitMerge, requires: ADMINS_ONLY },
    { to: "/admin/duty-roster", label: "Duty Roster", icon: CalendarDays, requires: ADMINS_ONLY },
    { to: "/teachers", label: "Teacher Profiles", icon: UserCheck },
    { to: "/admin/errors", label: "Error Logs", icon: AlertCircle },
    { to: "/admin/audit-trail", label: "Audit Trail", icon: ScrollText, requires: ADMINS_ONLY },
    { to: "/admin/live", label: "Live Activity", icon: Activity, requires: ADMINS_ONLY },],
  aichat: [
    { to: "/ai", label: "AI Assistant", icon: Bot },
  ],
};

// ----- Hub navigation (shown when not inside any module) -----
export const STUDENT_HUB: NavItem[] = [
  { to: "/home", label: "My Dashboard", icon: HomeIcon, end: true },
  { to: "/academics", label: "My Academics", icon: GraduationCap, end: true },
  { to: "/timetables", label: "My Timetable", icon: CalendarDays },
  { to: "/library/catalogue", label: "Library", icon: BookOpen },
  { to: "/ai", label: "AI Assistant", icon: Bot },
];

export const STUDENT_LIBRARY_NAV: NavItem[] = [
  { to: "/library/catalogue", label: "Catalogue", icon: BookOpen },
  { to: "/library/my", label: "My Library", icon: LayoutDashboard },
  { to: "/library/resources", label: "Digital Resources", icon: FileText },
  { to: "/library/loans", label: "My Loans", icon: FileStack },
  { to: "/library/reservations", label: "Reservations", icon: CalendarDays },
  { to: "/library/rules", label: "Loan Rules", icon: ClipboardCheck },
  { to: "/library/my-reports", label: "My Reports", icon: BarChart3 },
  { to: "/library/book-requests", label: "Book Requests", icon: ClipboardList, requires: ["SUPER_ADMIN", "PRINCIPAL", "ADMIN", "LIBRARIAN", "DEPT_HEAD", "TEACHER"] },
];

export const STUDENT_TIMETABLE_NAV: NavItem[] = [
  { to: "/timetables", label: "My Timetable", icon: CalendarDays },
];

export const STUDENT_ACADEMICS_NAV: NavItem[] = [
  { to: "/academics", label: "My Performance", icon: GraduationCap, end: true },
];

export const HUB_NAV: NavItem[] = [
  { to: "/home", label: "Home", icon: HomeIcon, end: true },
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/timetables", label: "Master Timetable", icon: CalendarDays },
  { to: "/ai", label: "AI Assistant", icon: Bot },
  { to: "/admin", label: "Admin Console", icon: UserCog, requires: ADMINS_ONLY },];

// ----- Which module does a URL belong to? -----
export function moduleForPath(pathname: string): string | null {
  if (!pathname) return null;
  if (pathname.startsWith("/academics")) return "academics";
  if (pathname.startsWith("/subjects")) return "academics";
  if (pathname.startsWith("/rooms")) return "academics";
  if (pathname.startsWith("/academic-analysis")) return "academics";
  if (pathname.startsWith("/inventory")) return "inventory";
  if (pathname.startsWith("/library")) return "library";
  if (pathname.startsWith("/scheduling")) return "scheduling";
  if (pathname.startsWith("/timetables")) return "scheduling";
  if (pathname.startsWith("/validation")) return "scheduling";
  if (pathname.startsWith("/admin")) return "platform";
  if (pathname.startsWith("/teachers")) return "platform";
  if (pathname.startsWith("/ai")) return "aichat";
  return null;
}


// The set of module paths a student is allowed to enter
export const STUDENT_MODULE_ALLOWED = new Set([
  "core", "library", "aichat", "scheduling", // scheduling = timetable view only
]);

export function isStudentAllowedInModule(moduleName: string | null): boolean {
  if (!moduleName) return true; // hub paths
  return STUDENT_MODULE_ALLOWED.has(moduleName);
}
