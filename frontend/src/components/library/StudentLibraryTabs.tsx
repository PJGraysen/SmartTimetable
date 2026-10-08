import { NavLink } from "react-router-dom";
import {
  BookOpen, LayoutDashboard, FileText, FileStack,
  CalendarDays, BarChart3, ClipboardCheck,
} from "lucide-react";

// Student-safe tabs. NO circulation, members, audits, analytics, settings.
const TABS = [
  { to: "/library/catalogue",    label: "Catalogue",     icon: BookOpen },
  { to: "/library/my",           label: "My Library",    icon: LayoutDashboard },
  { to: "/library/resources",    label: "Digital Resources", icon: FileText },
  { to: "/library/loans",        label: "My Loans",      icon: FileStack },
  { to: "/library/reservations", label: "Reservations",  icon: CalendarDays },
  { to: "/library/rules",        label: "Loan Rules",    icon: ClipboardCheck },
  { to: "/library/my-reports",   label: "My Reports",    icon: BarChart3 },
];

export default function StudentLibraryTabs() {
  return (
    <nav className="lib-tabs student-lib-tabs" aria-label="Library">
      {TABS.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === "/library/catalogue"}
          className={({ isActive }) => "lib-tab" + (isActive ? " active" : "")}
        >
          <Icon size={16} />
          <span>{label}</span>
        </NavLink>
      ))}
      <style>{`
        .student-lib-tabs {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
          padding: 10px 12px;
          margin: 8px 0 14px;
          background: #fff;
          border: 1px solid var(--border, #e2e8f0);
          border-radius: 12px;
          box-shadow: 0 2px 8px rgba(15,23,42,.05);
        }
        .student-lib-tabs .lib-tab {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 8px 14px;
          border-radius: 8px;
          font-size: 0.82rem;
          font-weight: 700;
          color: var(--text-muted, #64748b);
          text-decoration: none;
          border: 1px solid transparent;
          transition: background 180ms ease, color 180ms ease, transform 180ms ease;
        }
        .student-lib-tabs .lib-tab:hover {
          background: var(--bg-subtle, #f8fafc);
          color: var(--text, #172033);
          transform: translateY(-1px);
        }
        .student-lib-tabs .lib-tab.active {
          background: var(--accent, #244b72);
          color: #fff;
        }
        [data-theme="dark"] .student-lib-tabs {
          background: #1e293b;
          border-color: #334155;
        }
      `}</style>
    </nav>
  );
}
