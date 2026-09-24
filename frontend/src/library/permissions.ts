/**
 * Library permission hook.
 *
 * The platform /me endpoint does not currently expose per-permission
 * lists. This hook reads the current user's application visibility and
 * applies a lightweight client-side gate: if the user can see the
 * Library application at all, they are treated as able to browse. The
 * backend still enforces every write permission server-side.
 *
 * When /me grows a permissions array, this hook can be upgraded without
 * touching any consumer code.
 */
import { useAuth } from "../auth/AuthContext";

export function useLibraryAccess() {
  const { applications, user } = useAuth();

  const canAccessLibrary =
    !!user &&
    (user.is_superuser ||
      applications.some((a) => a.slug === "library"));

  return {
    canAccessLibrary,
    isSuperuser: !!user?.is_superuser,
  };
}
