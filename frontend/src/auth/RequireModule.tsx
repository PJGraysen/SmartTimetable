import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./AuthContext";

// Paths a student must never see, even by direct URL.
// Backend enforces this too, but we redirect early for UX.
const STUDENT_BLOCKED_PATHS: string[] = [
  "/inventory",
  "/scheduling",
  "/validation",
  "/admin",
  "/academics/students",
  "/academics/marks",
  "/academics/classes",
  "/academics/stream-report",
  "/academics/comments",
  "/academics/assessments",
  "/academics/bulk-reports",
  "/academics/audit",
  "/academics/grading",
  "/academics/ranking",
  "/subjects",
  "/rooms",
  "/teachers",
  "/library/circulation",
  "/library/members",
  "/library/reports",
  "/library/audits",
  "/library/analytics",
  "/library/settings",
];

function isStudentBlocked(pathname: string, role: string | null | undefined): boolean {
  if (role !== "STUDENT") return false;
  return STUDENT_BLOCKED_PATHS.some((p) => pathname === p || pathname.startsWith(p + "/") || pathname.startsWith(p));
}

export function RequireModule({
  name,
  children,
}: {
  name: string;
  children: ReactNode;
}) {
  const { modules, loading, role } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div style={{ padding: "2rem", textAlign: "center", color: "#64748b" }}>
        Loading…
      </div>
    );
  }

  // Student path blocklist — hard gate before module check
  if (isStudentBlocked(location.pathname, role)) {
    return <Navigate to="/home?denied=1" replace state={{ from: location.pathname }} />;
  }

  const isSuper = modules.includes("*");
  const allowed = isSuper || modules.includes(name);
  // eslint-disable-next-line no-console
  console.log("[RequireModule] name=", name,
              "modules=", modules,
              "isSuper=", isSuper,
              "allowed=", allowed);

  if (!allowed) {
    return (
      <Navigate
        to={`/home?denied=${encodeURIComponent(name)}`}
        replace
        state={{ from: location.pathname }}
      />
    );
  }

  return <>{children}</>;
}
