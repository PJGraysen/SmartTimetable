import { Navigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import LibraryShell from "../components/library/LibraryShell";
import LibraryDashboard from "./library/LibraryDashboard";

export default function LibraryEntry() {
  const { role } = useAuth();

  // Students never see the admin library dashboard — send them to catalogue.
  if (role === "STUDENT") {
    return <Navigate to="/library/catalogue" replace />;
  }

  return (
    <LibraryShell>
      <LibraryDashboard />
    </LibraryShell>
  );
}
