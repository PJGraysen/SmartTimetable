import type { ComponentType } from "react";
import {
  AlertCircle, Award, BarChart3, BookOpen, Bot, CalendarDays,
  ClipboardCheck, ClipboardEdit, ClipboardList, DoorOpen, FileStack,
  FileText, GraduationCap, Home as HomeIcon, Layers, LayoutDashboard,
  MessageSquare, Package, PlayCircle, ScrollText, Trophy, UserCheck, UserCog, Users,
} from "lucide-react";

export type Role = "admin" | "teacher";

export type NavItem = {
  to: string;
  label: string;
  icon: ComponentType<{ size?: number }>;
  end?: boolean;
  roles?: Role[];
};

export const MAIN_NAV: NavItem[] = [
  { to: "/home", label: "Home", icon: HomeIcon },
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/ai", label: "AI Assistant", icon: Bot },
  { to: "/timetables", label: "Timetables", icon: CalendarDays },
  { to: "/scheduling", label: "Scheduling", icon: PlayCircle, roles: ["admin"] },

  { to: "/academics", label: "Academics", icon: GraduationCap, roles: ["admin"] },
  { to: "/academics/students", label: "Students", icon: Users },
  { to: "/academics/analysis", label: "Analysis", icon: BarChart3 },
  { to: "/academics/marks", label: "Marks Entry", icon: ClipboardEdit },
  { to: "/academics/classes", label: "Class Comparison", icon: Layers },
  { to: "/academics/stream-report", label: "Stream Report", icon: FileText },
  { to: "/academics/comments", label: "Comments", icon: MessageSquare },

  { to: "/academics/assessments", label: "Assessments", icon: ClipboardList, roles: ["admin"] },
  { to: "/academics/bulk-reports", label: "Bulk Reports", icon: FileStack, roles: ["admin"] },
  { to: "/academics/audit", label: "Audit Trail", icon: ScrollText, roles: ["admin"] },
  { to: "/academics/grading", label: "Grading", icon: Award, roles: ["admin"] },
  { to: "/academics/ranking", label: "Ranking", icon: Trophy, roles: ["admin"] },

  { to: "/teachers", label: "Teachers", icon: Users, roles: ["admin"] },
  { to: "/subjects", label: "Subjects", icon: BookOpen, roles: ["admin"] },
  { to: "/rooms", label: "Rooms", icon: DoorOpen, roles: ["admin"] },
  { to: "/validation", label: "Validation", icon: ClipboardCheck, roles: ["admin"] },
  { to: "/inventory/dashboard", label: "Inventory", icon: Package, roles: ["admin"] },
];

export const ADMIN_NAV: NavItem[] = [
  { to: "/admin", label: "Admin Console", icon: UserCog },
  { to: "/admin/teachers", label: "Teachers", icon: UserCheck },
  { to: "/admin/errors", label: "Error Logs", icon: AlertCircle },
];