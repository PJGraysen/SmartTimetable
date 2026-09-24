from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from apps.library.models import FinePayment
from apps.library.services.audit import log_library_action


class FineError(Exception):
    pass


@transaction.atomic
def record_payment(*, loan, amount: Decimal, by_user, reason: str = "") -> FinePayment:
    if amount <= 0:
        raise FineError("Amount must be positive.")
    owed = (loan.fine_accrued or Decimal("0.00")) - (loan.fine_paid or Decimal("0.00"))
    if amount > owed:
        raise FineError(f"Amount exceeds outstanding balance {owed}.")

    payment = FinePayment.objects.create(
        loan=loan,
        amount=amount,
        kind=FinePayment.Kind.PAYMENT,
        reason=reason,
        recorded_by=by_user,
    )
    loan.fine_paid = (loan.fine_paid or Decimal("0.00")) + amount
    loan.save(update_fields=["fine_paid", "updated_at"])

    log_library_action(
        user=by_user,
        action="library.fine.pay",
        entity_type="Loan",
        entity_id=str(loan.id),
        description=f"Payment {amount}: {reason or 'no reason given'}",
    )
    return payment


@transaction.atomic
def waive_remaining(*, loan, by_user, reason: str = "") -> FinePayment:
    owed = (loan.fine_accrued or Decimal("0.00")) - (loan.fine_paid or Decimal("0.00"))
    if owed <= 0:
        raise FineError("Nothing to waive.")

    payment = FinePayment.objects.create(
        loan=loan,
        amount=owed,
        kind=FinePayment.Kind.WAIVER,
        reason=reason,
        recorded_by=by_user,
    )
    loan.fine_paid = loan.fine_accrued
    loan.save(update_fields=["fine_paid", "updated_at"])

    log_library_action(
        user=by_user,
        action="library.fine.waive",
        entity_type="Loan",
        entity_id=str(loan.id),
        description=f"Waived {owed}: {reason or 'no reason given'}",
    )
    return payment
