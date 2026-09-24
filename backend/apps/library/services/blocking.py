"""
Member eligibility + penalties.

A member is considered BLOCKED from borrowing if they have any ACTIVE
loan past its due date. Blocking is computed, never stored — so the
state updates automatically the moment the loan is returned or a rule
is changed.
"""
from __future__ import annotations

from decimal import Decimal

from django.utils import timezone

from apps.library.models import Loan, Member


def overdue_loans(member: Member):
    now = timezone.now()
    return Loan.objects.filter(
        member=member,
        status=Loan.Status.ACTIVE,
        due_at__lt=now,
    )


def is_blocked(member: Member) -> bool:
    return overdue_loans(member).exists()


def overdue_count(member: Member) -> int:
    return overdue_loans(member).count()


def total_fines_owed(member: Member) -> Decimal:
    total = Decimal("0.00")
    for loan in Loan.objects.filter(member=member).exclude(fine_accrued=Decimal("0.00")):
        owed = (loan.fine_accrued or Decimal("0.00")) - (loan.fine_paid or Decimal("0.00"))
        if owed > 0:
            total += owed
    return total


def member_status(member: Member) -> dict:
    return {
        "is_blocked": is_blocked(member),
        "overdue_count": overdue_count(member),
        "fines_owed": str(total_fines_owed(member)),
    }
