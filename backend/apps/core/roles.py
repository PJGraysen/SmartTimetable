"""
Canonical roles, modules, and group -> module mapping.

This is the SINGLE SOURCE OF TRUTH for RBAC. Backend permission classes
and the frontend module filters both derive from these constants.
"""

# ----- Roles (must match the values Django Groups are named with) -----
class Role:
    SUPER_ADMIN = "SUPER_ADMIN"
    PRINCIPAL   = "PRINCIPAL"
    ADMIN       = "ADMIN"
    SECRETARY   = "SECRETARY"
    DEPT_HEAD   = "DEPT_HEAD"
    TEACHER     = "TEACHER"
    LIBRARIAN   = "LIBRARIAN"
    STUDENT     = "STUDENT"
    STAFF       = "STAFF"
    GUEST       = "GUEST"


ALL_ROLES = [
    Role.SUPER_ADMIN, Role.PRINCIPAL, Role.ADMIN, Role.SECRETARY,
    Role.DEPT_HEAD, Role.TEACHER, Role.LIBRARIAN, Role.STUDENT,
    Role.STAFF, Role.GUEST,
]

ROLE_LABELS = {
    Role.SUPER_ADMIN: "Super Administrator",
    Role.PRINCIPAL:   "Principal / Rector",
    Role.ADMIN:       "School Administrator",
    Role.SECRETARY:   "Secretary",
    Role.DEPT_HEAD:   "Department Head",
    Role.TEACHER:     "Teacher",
    Role.LIBRARIAN:   "Librarian",
    Role.STUDENT:     "Student",
    Role.STAFF:       "Staff",
    Role.GUEST:       "Guest",
}


# ----- Modules (one per top-level app section) -----
class Module:
    CORE       = "core"
    ACADEMICS  = "academics"
    LIBRARY    = "library"
    INVENTORY  = "inventory"
    SCHEDULING = "scheduling"
    FINANCE    = "finance"
    PLATFORM   = "platform"
    AICHAT     = "aichat"
    REPORTS    = "reports"


ALL_MODULES = [
    Module.CORE, Module.ACADEMICS, Module.LIBRARY, Module.INVENTORY,
    Module.SCHEDULING, Module.FINANCE, Module.PLATFORM, Module.AICHAT,
    Module.REPORTS,
]

MODULE_LABELS = {
    Module.CORE:       "Core / Home",
    Module.ACADEMICS:  "Academics",
    Module.LIBRARY:    "Library",
    Module.INVENTORY:  "Inventory",
    Module.SCHEDULING: "Scheduling",
    Module.FINANCE:    "Finance",
    Module.PLATFORM:   "Platform Admin",
    Module.AICHAT:     "AI Assistant",
    Module.REPORTS:    "Reports",
}


# ----- Group -> module access -----
# SUPER_ADMIN bypasses this map (sees every module).
GROUP_MODULES = {
    Role.PRINCIPAL: {
        Module.CORE, Module.ACADEMICS, Module.LIBRARY, Module.INVENTORY,
        Module.SCHEDULING, Module.FINANCE, Module.AICHAT, Module.REPORTS,
        Module.PLATFORM,
    },
    Role.ADMIN: {
        Module.CORE, Module.ACADEMICS, Module.LIBRARY, Module.INVENTORY,
        Module.SCHEDULING, Module.FINANCE, Module.AICHAT, Module.REPORTS,
        Module.PLATFORM,
    },
    Role.DEPT_HEAD: {
        Module.CORE, Module.ACADEMICS, Module.INVENTORY, Module.SCHEDULING,
        Module.AICHAT, Module.REPORTS,
    },
    Role.TEACHER: {
        Module.CORE, Module.ACADEMICS, Module.LIBRARY, Module.INVENTORY,
        Module.SCHEDULING, Module.AICHAT,
    },
    Role.LIBRARIAN: {
        Module.CORE, Module.LIBRARY, Module.REPORTS,
    },
    Role.STUDENT: {
        Module.CORE, Module.LIBRARY, Module.ACADEMICS, Module.SCHEDULING,
        Module.AICHAT,
    },
    Role.SECRETARY: {
        Module.CORE, Module.ACADEMICS, Module.REPORTS, Module.PLATFORM,
    },
    Role.STAFF: {
        Module.CORE,
    },
    Role.GUEST: set(),
}


# ----- Legacy group name aliases -----
# Groups created before the role enum was formalised. Users still in these
# groups keep their access. New assignments should use the canonical names.
LEGACY_GROUP_ALIASES = {
    "Principal": Role.PRINCIPAL,
    "Rector": Role.PRINCIPAL,
    "Secretary": Role.SECRETARY,
    "Administrator": Role.ADMIN,
    "Teacher": Role.TEACHER,
    "Librarian": Role.LIBRARIAN,
    "Library Administrator": Role.LIBRARIAN,
    "Library Assistant": Role.LIBRARIAN,
    "Viewer": Role.GUEST,
}


def _canonical_role_name(name: str) -> str:
    """Return the canonical role name for a (possibly legacy) group name."""
    if name in GROUP_MODULES:
        return name
    return LEGACY_GROUP_ALIASES.get(name, name)


def modules_for_user(user) -> set:
    """Return the set of modules a user can access."""
    if not user or not user.is_authenticated:
        return set()
    if user.is_superuser:
        return {"*"}
    modules = set()
    for g in user.groups.all():
        canonical = _canonical_role_name(g.name)
        modules |= GROUP_MODULES.get(canonical, set())
    return modules


def primary_role(user) -> str:
    """Return the user's primary role for display/UI decisions."""
    if not user or not user.is_authenticated:
        return Role.GUEST
    if user.is_superuser:
        return Role.SUPER_ADMIN
    for name in (Role.PRINCIPAL, Role.ADMIN, Role.SECRETARY, Role.DEPT_HEAD,
                 Role.LIBRARIAN, Role.TEACHER, Role.STUDENT, Role.STAFF):
        if user.groups.filter(name=name).exists():
            return name
    # Check legacy group names too
    for legacy, canonical in LEGACY_GROUP_ALIASES.items():
        if user.groups.filter(name=legacy).exists():
            return canonical
    return Role.GUEST
