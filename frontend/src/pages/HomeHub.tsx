import { useNavigate } from "react-router-dom";
import {
  BookOpen,
  CalendarDays,
  GraduationCap,
  LogOut,
  LayoutGrid,
} from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import CalendarWidget from "../components/CalendarWidget";

function iconFor(name: string) {
  switch (name) {
    case "calendar":
      return CalendarDays;
    case "graduation-cap":
      return GraduationCap;
    case "book-open":
      return BookOpen;
    default:
      return LayoutGrid;
  }
}

const CARD_STYLE: React.CSSProperties = {
  position: "relative",
  overflow: "hidden",
  border: "1px solid #7a4e2a",
  borderRadius: "16px",
  padding: "1.75rem",
  textAlign: "left",
  background: "linear-gradient(135deg, #2b1a0f 0%, #5a3a1e 100%)",
  color: "#f5eee2",
  cursor: "pointer",
  boxShadow: "0 6px 20px rgba(10, 18, 29, 0.14)",
  transition:
    "transform 340ms cubic-bezier(.16,1,.3,1), box-shadow 340ms cubic-bezier(.16,1,.3,1), border-color 260ms ease, background 420ms ease",
};

const CARD_HOVER_STYLE: React.CSSProperties = {
  transform: "translateY(-6px) scale(1.02)",
  boxShadow: "0 14px 32px rgba(61,40,23,0.35), 0 0 0 2px rgba(34,180,240,0.5)",
  borderColor: "#22b4f0",
  background: "linear-gradient(135deg, #3d2817 0%, #7a4e2a 100%)",
};

const ICON_STYLE: React.CSSProperties = {
  width: "56px",
  height: "56px",
  borderRadius: "14px",
  background: "linear-gradient(135deg, #22b4f0, #0b5d8c)",
  color: "#fff",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  marginBottom: "1.1rem",
  boxShadow: "0 8px 20px rgba(34,180,240,0.4)",
  transition: "transform 340ms cubic-bezier(.34,1.56,.64,1), box-shadow 320ms ease",
};

const TITLE_STYLE: React.CSSProperties = {
  fontWeight: 700,
  fontSize: "1.15rem",
  color: "#ffffff",
  margin: "0 0 0.35rem 0",
};

const DESC_STYLE: React.CSSProperties = {
  color: "#e8d9c2",
  fontSize: "0.9rem",
  lineHeight: 1.45,
  margin: "0 0 1rem 0",
};

const OPEN_STYLE: React.CSSProperties = {
  color: "#6fcffb",
  fontSize: "0.78rem",
  fontWeight: 800,
  letterSpacing: "0.1em",
  display: "inline-flex",
  alignItems: "center",
  gap: "0.4rem",
};

export default function HomeHub() {
  const { user, applications, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <div style={{ padding: "2rem", maxWidth: "1200px", margin: "0 auto" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "2rem",
          flexWrap: "wrap",
          gap: "1rem",
        }}
      >
        <div>
          <div
            style={{
              fontSize: "0.75rem",
              letterSpacing: "0.16em",
              color: "#5a3a1e",
              fontWeight: 800,
            }}
          >
            SMARTSCHOOLPRO
          </div>
          <h1
            style={{
              marginTop: "0.35rem",
              fontSize: "2.1rem",
              color: "#1e2e40",
              fontWeight: 800,
              letterSpacing: "-0.015em",
            }}
          >
            Welcome{user ? `, ${user.display_name}` : ""}
          </h1>
          <p style={{ color: "#748095", marginTop: "0.35rem" }}>
            Choose an application to continue.
          </p>
        </div>
        <button type="button" onClick={handleLogout} className="secondary-button">
          <LogOut size={16} /> Sign out
        </button>
      </div>


      <h2
        style={{
          color: "#1e2e40",
          marginBottom: "1rem",
          fontSize: "1.1rem",
          letterSpacing: "0.02em",
        }}
      >
        Your Applications
      </h2>

      <section style={{ marginBottom: "2rem" }}>
        <h2
          style={{
            color: "#1e2e40",
            marginBottom: "1rem",
            fontSize: "1.1rem",
            letterSpacing: "0.02em",
          }}
        >
          Academics
        </h2>
        <button
          type="button"
          onClick={() => navigate("/academics/students")}
          style={{
            position: "relative",
            overflow: "hidden",
            border: "1px solid #7a4e2a",
            borderRadius: "16px",
            padding: "1.75rem",
            textAlign: "left",
            background: "linear-gradient(135deg, #2b1a0f 0%, #5a3a1e 100%)",
            color: "#f5eee2",
            cursor: "pointer",
            boxShadow: "0 6px 20px rgba(10, 18, 29, 0.14)",
            maxWidth: "360px",
          }}
        >
          <div
            style={{
              width: "56px",
              height: "56px",
              borderRadius: "14px",
              background: "linear-gradient(135deg, #22b4f0, #0b5d8c)",
              color: "#fff",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              marginBottom: "1.1rem",
              boxShadow: "0 8px 20px rgba(34,180,240,0.4)",
            }}
          >
            <GraduationCap size={26} />
          </div>
          <h3 style={{ fontWeight: 700, fontSize: "1.15rem", color: "#ffffff", margin: "0 0 0.35rem 0" }}>
            Students
          </h3>
          <p style={{ color: "#e8d9c2", fontSize: "0.9rem", lineHeight: 1.45, margin: "0 0 1rem 0" }}>
            View, edit and manage student records.
          </p>
          <span style={{ color: "#6fcffb", fontSize: "0.78rem", fontWeight: 800, letterSpacing: "0.1em" }}>
            OPEN →
          </span>
        </button>
      </section>
      {applications.length === 0 ? (
        <div
          style={{
            padding: "3rem 1rem",
            textAlign: "center",
            color: "#748095",
            border: "1px dashed #d1d5db",
            borderRadius: "10px",
          }}
        >
          No applications are available for your account.
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
            gap: "1.25rem",
          }}
        >
          {applications.map((app) => {
            const Icon = iconFor(app.icon);
            return (
              <button
                key={app.slug}
                type="button"
                onClick={() => navigate(app.entry_path)}
                style={CARD_STYLE}
                onMouseEnter={(e) => Object.assign(e.currentTarget.style, CARD_HOVER_STYLE)}
                onMouseLeave={(e) => Object.assign(e.currentTarget.style, CARD_STYLE)}
              >
                <div style={ICON_STYLE}>
                  <Icon size={26} />
                </div>
                <h3 style={TITLE_STYLE}>{app.name}</h3>
                <p style={DESC_STYLE}>{app.description}</p>
                <span style={OPEN_STYLE}>OPEN →</span>
              </button>
            );
          })}
        </div>
      )}

      <section style={{ marginTop: "2.5rem" }}>
        <CalendarWidget />
      </section>

    </div>
  );
}
