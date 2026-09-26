"""
Finance services — post charges and payments, keeping FeeAccount.balance
consistent with the ledger sum.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from apps.finance.models import FeeAccount, LedgerEntry


def get_or_create_account(member) -> FeeAccount:
    account, _ = FeeAccount.objects.get_or_create(member=member)
    return account


def _recompute(account: FeeAccount) -> FeeAccount:
    total = Decimal("0.00")
    for e in account.entries.all():
        total += e.signed_amount()
    account.balance = total
    account.save(update_fields=["balance", "updated_at"])
    return account


@transaction.atomic
def post_charge(*, member, amount: Decimal, source: str = "OTHER",
                description: str = "", reference_type: str = "",
                reference_id: str = "", by_user=None) -> LedgerEntry:
    account = get_or_create_account(member)
    entry = LedgerEntry.objects.create(
        account=account, kind=LedgerEntry.Kind.CHARGE, source=source,
        amount=amount, description=description,
        reference_type=reference_type, reference_id=reference_id,
        recorded_by=by_user,
    )
    _recompute(account)
    return entry


@transaction.atomic
def post_payment(*, member, amount: Decimal, source: str = "OTHER",
                 description: str = "", reference_type: str = "",
                 reference_id: str = "", by_user=None) -> LedgerEntry:
    account = get_or_create_account(member)
    entry = LedgerEntry.objects.create(
        account=account, kind=LedgerEntry.Kind.PAYMENT, source=source,
        amount=amount, description=description,
        reference_type=reference_type, reference_id=reference_id,
        recorded_by=by_user,
    )
    _recompute(account)
    return entry


@transaction.atomic
def post_waiver(*, member, amount: Decimal, source: str = "OTHER",
                description: str = "", by_user=None) -> LedgerEntry:
    account = get_or_create_account(member)
    entry = LedgerEntry.objects.create(
        account=account, kind=LedgerEntry.Kind.WAIVER, source=source,
        amount=amount, description=description, recorded_by=by_user,
    )
    _recompute(account)
    return entry


@transaction.atomic
def post_library_fine(*, loan, amount: Decimal, by_user=None) -> LedgerEntry:
    """Hook called from library when a fine is accrued."""
    return post_charge(
        member=loan.member, amount=amount, source=LedgerEntry.Source.LIBRARY,
        description=f"Library fine for loan {loan.id}",
        reference_type="library.Loan", reference_id=str(loan.id),
        by_user=by_user,
    )


@transaction.atomic
def post_library_payment(*, loan, amount: Decimal, by_user=None) -> LedgerEntry:
    return post_payment(
        member=loan.member, amount=amount, source=LedgerEntry.Source.LIBRARY,
        description=f"Library fine payment for loan {loan.id}",
        reference_type="library.Loan", reference_id=str(loan.id),
        by_user=by_user,
    )
