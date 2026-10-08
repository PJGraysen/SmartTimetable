"""
Idempotent user-group sync. Assigns every Teacher's linked User to the
correct group based on teacher.role, and every Student's linked User to
STUDENT. Safe to run on every deploy.
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.users.models import Teacher
from apps.academics.models import Student


# Teacher.role -> Django group name
TEACHER_ROLE_TO_GROUP = {
    "SUPER_ADMIN": "SUPER_ADMIN",
    "PRINCIPAL":   "PRINCIPAL",
    "SECRETARY":   "SECRETARY",
    "DEPT_HEAD":   "DEPT_HEAD",
    "TEACHER":     "TEACHER",
    "LIBRARIAN":   "LIBRARIAN",
    "LAB_TECH":    "STAFF",     # lab tech: staff-level, not a full teacher
    "AUDITOR":     "STAFF",
    "PROCUREMENT": "STAFF",
    "BURSAR":      "STAFF",
    "OTHER":       "STAFF",
}


class Command(BaseCommand):
    help = "Sync users into role groups based on Teacher.role and Student records."

    def add_arguments(self, parser):
        parser.add_argument("--show", action="store_true",
                            help="Only print current group membership.")
        parser.add_argument("--dry-run", action="store_true",
                            help="Show what would be assigned without writing.")

    def handle(self, *args, **opts):
        if opts["show"]:
            self._show()
            return

        U = get_user_model()
        counts = {}
        dry = opts["dry_run"]

        # ----- Teachers -> role group -----
        for t in Teacher.objects.select_related("user").filter(user__isnull=False):
            # Special case: Rector (T001) is PRINCIPAL unless explicitly SUPER_ADMIN
            if t.employee_code == "T001" and t.role != "SUPER_ADMIN":
                group_name = "PRINCIPAL"
            else:
                group_name = TEACHER_ROLE_TO_GROUP.get(t.role, "TEACHER")
            counts[group_name] = counts.get(group_name, 0) + 1
            if dry:
                continue
            with transaction.atomic():
                g = Group.objects.get(name=group_name)
                # Remove from other role groups, then add to correct one
                for other in TEACHER_ROLE_TO_GROUP.values():
                    if other != group_name:
                        t.user.groups.remove(Group.objects.filter(name=other).first() or Group.objects.create(name=other))
                t.user.groups.add(g)
                # Teachers should be staff (Django admin access) but NOT superuser
                if not t.user.is_superuser:
                    t.user.is_staff = True
                    t.user.save(update_fields=["is_staff"])

        # ----- Students -> STUDENT group -----
        for s in Student.objects.select_related("user").filter(user__isnull=False):
            counts["STUDENT"] = counts.get("STUDENT", 0) + 1
            if dry:
                continue
            with transaction.atomic():
                g = Group.objects.get(name="STUDENT")
                s.user.groups.add(g)
                s.user.is_staff = False
                s.user.is_superuser = False
                s.user.save(update_fields=["is_staff", "is_superuser"])

        print()
        print("=== Assignment summary ===")
        for name, n in sorted(counts.items()):
            print(f"  {name:14}  {n:3}")

        print()
        self._show()

    def _show(self):
        U = get_user_model()
        print("=== Current group membership ===")
        for g in Group.objects.order_by("name"):
            print(f"  {g.name:14}  members={g.user_set.count():3}")
        print()
        print(f"  Users total:            {U.objects.count()}")
        print(f"  Users with no group:    {U.objects.filter(groups__isnull=True).count()}")
