"""Wire admin + all teachers + all students into library Members,
creating User accounts where missing and setting a shared default password."""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.library.models import Member


User = get_user_model()


class Command(BaseCommand):
    help = "Create Library Members for admin/teachers/students and set passwords."

    def add_arguments(self, parser):
        parser.add_argument("--password", default="SmartLib@2026",
                            help="Default password for newly created users.")
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args, **opts):
        password = opts["password"]
        dry = opts["dry_run"]
        created_members = 0
        created_users = 0
        updated_passwords = 0

        # ---- Admin ----
        admins = User.objects.filter(is_superuser=True, is_active=True)
        for u in admins:
            if not Member.objects.filter(user=u).exists():
                if not dry:
                    Member.objects.create(
                        user=u, member_number=f"ADM-{u.username[:12]}",
                        full_name=(u.get_full_name() or u.username),
                        email=u.email or "",
                        member_type=Member.MemberType.STAFF,
                    )
                    if not u.has_usable_password():
                        u.set_password(password)
                        u.save(update_fields=["password"])
                        updated_passwords += 1
                created_members += 1
                self.stdout.write(f"  ADMIN  {u.username} -> Member created")

        # ---- Teachers ----
        from apps.users.models import Teacher
        for t in Teacher.objects.filter(is_active=True).select_related("user"):
            u = t.user
            if u is None:
                continue
            if not Member.objects.filter(teacher=t).exists():
                if not dry:
                    full = f"{t.first_name} {t.last_name}".strip() or t.employee_code
                    Member.objects.create(
                        teacher=t, user=u,
                        member_number=f"TCH-{t.employee_code}",
                        full_name=full,
                        email=getattr(u, "email", "") or "",
                        member_type=Member.MemberType.TEACHER,
                    )
                    if not u.check_password(password):
                        pass  # don't touch existing teacher passwords
                created_members += 1
                self.stdout.write(f"  TEACH  {t.employee_code} -> Member created")

        # ---- Librarians (via Librarian group) ----
        librarian_users = User.objects.filter(
            groups__name="Librarian", is_active=True
        ).distinct()
        for u in librarian_users:
            if not Member.objects.filter(user=u).exists():
                if not dry:
                    Member.objects.create(
                        user=u, member_number=f"LIB-{u.username[:12]}",
                        full_name=(u.get_full_name() or u.username),
                        email=u.email or "",
                        member_type=Member.MemberType.LIBRARIAN,
                    )
                created_members += 1
                self.stdout.write(f"  LIBRN  {u.username} -> Member created")

        # ---- Students ----
        from apps.academics.models import Student
        import secrets
        for s in Student.objects.filter(is_active=True):
            u = s.user
            if u is None:
                if dry:
                    created_users += 1
                    created_members += 1
                    continue
                username = f"stu_{s.admission_number}".lower()
                # ensure unique
                base = username
                n = 1
                while User.objects.filter(username=username).exists():
                    n += 1
                    username = f"{base}{n}"
                u = User.objects.create_user(
                    username=username, password=password,
                    first_name=s.first_name or "", last_name=s.last_name or "",
                    email=getattr(s, "email", "") or "",
                )
                s.user = u
                s.save(update_fields=["user"])
                created_users += 1
            if not Member.objects.filter(student=s).exists():
                if not dry:
                    Member.objects.create(
                        student=s, user=u,
                        member_number=f"STU-{s.admission_number}",
                        full_name=s.full_name or f"{s.first_name} {s.last_name}".strip(),
                        email=getattr(u, "email", "") or "",
                        member_type=Member.MemberType.STUDENT,
                    )
                created_members += 1

        self.stdout.write(
            f"\nDone. created_users={created_users} "
            f"created_members={created_members} "
            f"password_resets={updated_passwords}"
        )
        self.stdout.write(f"Default password used: {password}")
