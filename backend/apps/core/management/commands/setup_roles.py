"""
Idempotent role setup. Creates/updates the 8 Django Groups and assigns
each one the model-level permissions its role needs.

Safe to run on every deploy. Never deletes users or their group memberships;
only ensures the groups exist with the right permissions.
"""
from django.apps import apps
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from apps.core.roles import ALL_ROLES, Role


# ---- Per-role permission grants (app_label.model: [actions]) ----
# "*" means all CRUD on that model.
ROLE_GRANTS = {
    Role.SUPER_ADMIN: "*",  # everything
    # PRINCIPAL: same model perms as ADMIN; the difference is UI gating
    Role.PRINCIPAL: {
        "core": "*", "academics": "*", "library": "*", "inventory": "*",
        "scheduling": "*", "users": "*", "finance": "*", "audit": "*",
    },
    # SECRETARY: view + add/change academics records; no delete
    Role.SECRETARY: {
        "core": ["view"],
        "academics": ["view", "add", "change"],
        "scheduling": ["view"],
    },
    Role.ADMIN: {
        "core": "*", "academics": "*", "library": "*", "inventory": "*",
        "scheduling": "*", "users": "*", "finance": "*", "audit": "*",
    },
    Role.DEPT_HEAD: {
        "core": ["view"],
        "academics": ["view", "add", "change"],
        "inventory": ["view", "add", "change"],
        "scheduling": ["view"],
        "library": ["view"],
    },
    Role.TEACHER: {
        "core": ["view"],
        "academics": ["view", "add", "change"],
        "library": ["view"],
        "inventory": ["view", "add", "change"],
        "scheduling": ["view"],
    },
    Role.LIBRARIAN: {
        "core": ["view"],
        "library": ["view", "add", "change", "delete"],
    },
    Role.STUDENT: {
        "core": ["view"],
        "academics": ["view"],
        "library": ["view"],
        "scheduling": ["view"],
    },
    Role.STAFF: {
        "core": ["view"],
    },
    Role.GUEST: {},
}


ACTION_TO_PERM = {
    "view":   "view",
    "add":    "add",
    "change": "change",
    "delete": "delete",
}


class Command(BaseCommand):
    help = "Create/update role groups with correct permissions (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--show", action="store_true",
                            help="Only print the current group membership counts.")

    def handle(self, *args, **opts):
        if opts["show"]:
            for g in Group.objects.order_by("name"):
                print(f"  {g.name:14}  members={g.user_set.count():3}  perms={g.permissions.count():3}")
            return

        for role in ALL_ROLES:
            group, created = Group.objects.get_or_create(name=role)
            tag = "created" if created else "updated"

            grants = ROLE_GRANTS.get(role, set())
            perms_to_set = set()

            if grants == "*":
                perms_to_set = set(Permission.objects.all())
            else:
                for app_label, actions in grants.items():
                    if actions == "*":
                        actions = ["view", "add", "change", "delete"]
                    if not isinstance(actions, (list, tuple)):
                        actions = [actions]
                    for action in actions:
                        codename_prefix = ACTION_TO_PERM.get(action, action)
                        for ct in ContentType.objects.filter(app_label=app_label):
                            for p in Permission.objects.filter(
                                content_type=ct,
                                codename__startswith=f"{codename_prefix}_",
                            ):
                                perms_to_set.add(p)

            group.permissions.set(perms_to_set)
            print(f"  [{tag}] {role:14}  permissions={len(perms_to_set)}")

        print()
        print("Final state:")
        for g in Group.objects.order_by("name"):
            print(f"  {g.name:14}  members={g.user_set.count():3}  perms={g.permissions.count():3}")
