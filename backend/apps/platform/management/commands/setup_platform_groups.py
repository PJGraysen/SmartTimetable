from __future__ import annotations

from decimal import Decimal

from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

from apps.library.models import LoanRule, Member


LIBRARY_GROUPS = {
    "Library Administrator": [
        "library.view_book", "library.add_book", "library.change_book",
        "library.delete_book", "library.import_catalogue",
        "library.view_author", "library.add_author", "library.change_author", "library.delete_author",
        "library.view_publisher", "library.add_publisher", "library.change_publisher", "library.delete_publisher",
        "library.view_category", "library.add_category", "library.change_category", "library.delete_category",
        "library.view_shelf", "library.add_shelf", "library.change_shelf", "library.delete_shelf",
        "library.view_copy", "library.add_copy", "library.change_copy", "library.delete_copy",
        "library.view_member", "library.add_member", "library.change_member", "library.delete_member",
        "library.view_loan", "library.add_loan", "library.change_loan", "library.delete_loan",
        "library.issue_loan", "library.return_loan", "library.renew_loan",
        "library.manage_fines", "library.view_reports",
        "library.view_loanrule", "library.add_loanrule", "library.change_loanrule", "library.delete_loanrule",
        "library.manage_settings",
    ],
    "Librarian": [
        "library.view_book", "library.add_book", "library.change_book",
        "library.import_catalogue",
        "library.view_author", "library.add_author", "library.change_author",
        "library.view_publisher", "library.add_publisher", "library.change_publisher",
        "library.view_category", "library.add_category", "library.change_category",
        "library.view_shelf", "library.add_shelf", "library.change_shelf",
        "library.view_copy", "library.add_copy", "library.change_copy",
        "library.view_member", "library.change_member",
        "library.view_loan", "library.issue_loan", "library.return_loan",
        "library.renew_loan", "library.view_reports",
    ],
    "Library Assistant": [
        "library.view_book",
        "library.view_copy",
        "library.view_member",
        "library.view_loan", "library.issue_loan", "library.return_loan",
    ],
}


DEFAULT_LOAN_RULES = [
    # member_type, max_concurrent, loan_days, max_renewals, fine_per_day, grace_days, max_fine
    ("STUDENT",  2, 14, 2, Decimal("5.00"), 1, Decimal("500.00")),
    ("TEACHER",  5, 30, 3, Decimal("5.00"), 1, Decimal("500.00")),
    ("STAFF",    3, 21, 2, Decimal("5.00"), 1, Decimal("500.00")),
    ("EXTERNAL", 1,  7, 1, Decimal("10.00"), 0, Decimal("500.00")),
]


class Command(BaseCommand):
    help = "Seed platform groups, library permissions, and default loan rules."

    def handle(self, *args, **options):
        created_groups = 0
        missing = []

        for group_name, codenames in LIBRARY_GROUPS.items():
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                created_groups += 1
            group.permissions.clear()
            for codename in codenames:
                perm = Permission.objects.filter(codename=codename.split(".", 1)[1]).filter(
                    content_type__app_label=codename.split(".", 1)[0]
                ).first()
                if perm is None:
                    missing.append(codename)
                    continue
                group.permissions.add(perm)
            self.stdout.write(f"  group {group_name!r}: {group.permissions.count()} permissions")

        self.stdout.write(f"  groups created: {created_groups}")
        if missing:
            self.stdout.write(self.style.WARNING(
                f"  {len(missing)} permissions missing (run 'migrate library' first): "
                f"{missing[:5]}{'...' if len(missing) > 5 else ''}"
            ))

        created_rules = 0
        for (mtype, mx, days, renews, fine, grace, cap) in DEFAULT_LOAN_RULES:
            _, created = LoanRule.objects.get_or_create(
                member_type=mtype,
                defaults={
                    "max_concurrent_loans": mx,
                    "loan_days": days,
                    "max_renewals": renews,
                    "fine_per_day": fine,
                    "grace_days": grace,
                    "max_fine": cap,
                },
            )
            if created:
                created_rules += 1

        self.stdout.write(f"  loan rules created: {created_rules}")
        self.stdout.write(self.style.SUCCESS("setup_platform_groups complete."))
