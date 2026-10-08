import { useAuth } from "../auth/AuthContext";
import StudentAcademicsPage from "./StudentAcademicsPage";
import TeacherAnalyticsPage from "./TeacherAnalyticsPage";

export default function AcademicsEntry() {
  const { role } = useAuth();
  if (role === "STUDENT") return <StudentAcademicsPage />;
  // Teachers, dept heads AND the principal all get the analytics page.
  // The principal additionally sees the "School" tab (whole-school view)
  // because TeacherAnalyticsPage checks authRole at render time.
  if (
    role === "TEACHER" ||
    role === "DEPT_HEAD" ||
    role === "PRINCIPAL"
  ) {
    return <TeacherAnalyticsPage />;
  }
  // Pure administrators (ADMIN / SUPER_ADMIN / SECRETARY) still see the
  // school-wide analytics page directly.
  return <TeacherAnalyticsPage />;
}
