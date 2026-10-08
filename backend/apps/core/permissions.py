"""
DRF permission classes for module-level access control.

Every API view that belongs to a module sets `permission_classes` to the
matching HasXxxAccess class. SUPER_ADMIN bypasses all checks.

Design:
    class HasAcademicsAccess(HasModuleAccess):
        MODULE = Module.ACADEMICS
"""
from rest_framework.permissions import BasePermission

from apps.core.roles import Module, modules_for_user


class HasModuleAccess(BasePermission):
    MODULE = None
    message = "You do not have access to this module."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return self.MODULE in modules_for_user(request.user)


def _make(module, name):
    return type(name, (HasModuleAccess,), {"MODULE": module})


HasCoreAccess       = _make(Module.CORE,       "HasCoreAccess")
HasAcademicsAccess  = _make(Module.ACADEMICS,  "HasAcademicsAccess")
HasLibraryAccess    = _make(Module.LIBRARY,    "HasLibraryAccess")
HasInventoryAccess  = _make(Module.INVENTORY,  "HasInventoryAccess")
HasSchedulingAccess = _make(Module.SCHEDULING, "HasSchedulingAccess")
HasFinanceAccess    = _make(Module.FINANCE,    "HasFinanceAccess")
HasPlatformAccess   = _make(Module.PLATFORM,   "HasPlatformAccess")
HasAIChatAccess     = _make(Module.AICHAT,     "HasAIChatAccess")
HasReportsAccess    = _make(Module.REPORTS,    "HasReportsAccess")


class IsSuperAdmin(BasePermission):
    message = "Super administrator access required."
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)


class IsAdminOrSuperAdmin(BasePermission):
    message = "Administrator access required."
    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        if u.is_superuser:
            return True
        return u.groups.filter(name__in=("ADMIN", "SUPER_ADMIN")).exists()
