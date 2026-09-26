from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.library.models import Copy, Loan, LoanRule, Member
from apps.library.services.audit import log_library_action
from apps.library.services.blocking import is_blocked


class LoanError(Exception):
    pass


def _rule_for(member: Member) -> LoanRule:
    rule = LoanRule.objects.filter(member_type=member.member_type).first()
    if rule is None:
        raise LoanError(
            f"No LoanRule configured for member type {member.member_type}."
        )
    return rule


@transaction.atomic
def issue_loan(*, copy: Copy, member: Member, issued_by) -> Loan:
    if not member.is_active:
        raise LoanError("Member is inactive.")
    if is_blocked(member):
        raise LoanError(
            "Member is blocked from borrowing: one or more overdue loans."
        )
    if copy.status != Copy.Status.AVAILABLE:
        raise LoanError(
            f"Copy {copy.barcode} is not available (status={copy.status})."
        )
    rule = _rule_for(member)

    active = Loan.objects.filter(member=member, status=Loan.Status.ACTIVE).count()
    if active >= rule.max_concurrent_loans:
        raise LoanError(
            f"Member already has {active} active loans "
            f"(limit {rule.max_concurrent_loans})."
        )

    due_at = timezone.now() + timedelta(days=rule.loan_days)
    loan = Loan.objects.create(
        copy=copy,
        member=member,
        due_at=due_at,
        issued_by=issued_by,
    )
    copy.status = Copy.Status.ISSUED
    copy.save(update_fields=["status", "updated_at"])

    log_library_action(
        user=issued_by,
        action="library.loan.issue",
        entity_type="Loan",
        entity_id=str(loan.id),
        description=f"Issued {copy.barcode} to {member.member_number}; due {due_at.isoformat()}",
    )
    return loan


@transaction.atomic
def return_loan(*, loan: Loan, received_by, notes: str = "") -> Loan:
    if loan.status != Loan.Status.ACTIVE:
        raise LoanError(f"Loan is not active (status={loan.status}).")

    now = timezone.now()
    rule = LoanRule.objects.filter(member_type=loan.member.member_type).first()
    fine = Decimal("0.00")

    if rule is not None:
        overdue_days = max(0, (now - loan.due_at).days - rule.grace_days)
        if overdue_days > 0:
            fine = rule.fine_per_day * Decimal(overdue_days)
            if rule.max_fine is not None and fine > rule.max_fine:
                fine = rule.max_fine

    loan.returned_at = now
    loan.received_by = received_by
    loan.status = Loan.Status.RETURNED
    loan.fine_accrued = fine
    if notes:
        loan.notes = (loan.notes + "\n" + notes).strip()
    loan.save(update_fields=[
        "returned_at", "received_by", "status",
        "fine_accrued", "notes", "updated_at",
    ])

    copy = loan.copy
    if copy.status == Copy.Status.ISSUED:
        copy.status = Copy.Status.AVAILABLE
        copy.save(update_fields=["status", "updated_at"])

    log_library_action(
        user=received_by,
        action="library.loan.return",
        entity_type="Loan",
        entity_id=str(loan.id),
        description=f"Returned {copy.barcode}; fine_accrued={fine}",
    )

    # ---- Post fine to finance ledger if any ----
    if fine and fine > 0:
        try:
            from apps.finance.services import post_library_fine as _post_fine
            _post_fine(loan=loan, amount=fine, by_user=received_by)
        except Exception:
            pass
        # ---- Fire fine notification ----
        try:
            from apps.library.services.notifications import on_fine_accrued as _n
            _n(loan)
        except Exception:
            pass

    return loan


@transaction.atomic
def renew_loan(*, loan: Loan, by_user) -> Loan:
    if loan.status != Loan.Status.ACTIVE:
        raise LoanError(f"Loan is not active (status={loan.status}).")
    now = timezone.now()
    if loan.due_at < now:
        raise LoanError("Loan is overdue; cannot renew.")

    rule = _rule_for(loan.member)
    if loan.renewal_count >= rule.max_renewals:
        raise LoanError(
            f"Maximum renewals reached ({rule.max_renewals})."
        )

    old_due = loan.due_at
    loan.due_at = loan.due_at + timedelta(days=rule.loan_days)
    loan.renewal_count += 1
    loan.save(update_fields=["due_at", "renewal_count", "updated_at"])

    log_library_action(
        user=by_user,
        action="library.loan.renew",
        entity_type="Loan",
        entity_id=str(loan.id),
        description=f"Renewed {loan.copy.barcode}: {old_due.isoformat()} -> {loan.due_at.isoformat()}",
    )
    return loan
