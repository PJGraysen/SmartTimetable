import { NavLink } from "react-router-dom";

const TABS = [
  { to: "/library", label: "Dashboard", end: true },
  { to: "/library/catalogue", label: "Catalogue" },
  { to: "/library/resources", label: "Resources" },
  { to: "/library/circulation", label: "Circulation" },
  { to: "/library/members", label: "Members" },
  { to: "/library/loans", label: "Loans" },
  { to: "/library/reservations", label: "Reservations" },
  { to: "/library/reports", label: "Reports" },
  { to: "/library/rules", label: "Loan Rules" },
];

export default function LibraryTabs() {
  return (
    <nav className="lib-tabs" style={{
      display: "flex", gap: "0.25rem", flexWrap: "wrap",
      borderBottom: "1px solid #e5e7eb", marginBottom: "1.25rem",
      background: "#fff", borderRadius: "8px 8px 0 0", padding: "0 0.5rem",
    }}>
      {TABS.map((t) => (
        <NavLink
          key={t.to}
          to={t.to}
          end={t.end as boolean | undefined}
          className={({ isActive }) => "lib-tab" + (isActive ? " is-active" : "")}
          style={({ isActive }) => ({
            display: "inline-block",
            padding: "0.7rem 0.9rem",
            fontSize: "0.83rem",
            fontWeight: 700,
            color: isActive ? "#1e3a8a" : "#64748b",
            borderBottom: isActive ? "2px solid #1e3a8a" : "2px solid transparent",
            textDecoration: "none",
            marginBottom: "-1px",
            transition: "color 120ms ease, border-color 120ms ease",
          })}
        >
          {t.label}
        </NavLink>
      ))}
    </nav>
  );
}
