import pytest
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.utils import timezone

from apps.library.models import (
    Book, Copy, FinePayment, Loan, LoanRule, Member, Reservation,
)
from apps.library.services.blocking import is_blocked, overdue_count, total_fines_owed
from apps.library.services.fines import record_payment, waive_remaining, FineError
from apps.library.services.loans import issue_loan, return_loan, LoanError
from apps.library.services.reservations import create_reservation, promote_next_waiting


@pytest.fixture
def user(db):
    return User.objects.create_user(username="p2", password="x")


@pytest.fixture
def env(db):
    LoanRule.objects.create(
        member_type=Member.MemberType.STUDENT,
        max_concurrent_loans=3, loan_days=14, max_renewals=2,
        fine_per_day=Decimal("10.00"), grace_days=0, max_fine=None,
    )
    book = Book.objects.create(title="Phase2")
    copy = Copy.objects.create(book=book, barcode="P2C1", accession_number="P2A1")
    member = Member.objects.create(member_number="P2M1", full_name="P2 Student", member_type="STUDENT")
    return book, copy, member


@pytest.mark.django_db
def test_blocked_when_overdue(user, env):
    book, copy, member = env
    loan = issue_loan(copy=copy, member=member, issued_by=user)
    assert not is_blocked(member)
    loan.due_at = timezone.now() - timedelta(days=1)
    loan.save(update_fields=["due_at"])
    assert is_blocked(member)
    assert overdue_count(member) == 1


@pytest.mark.django_db
def test_blocking_prevents_new_loans(user, env):
    book, copy, member = env
    loan = issue_loan(copy=copy, member=member, issued_by=user)
    loan.due_at = timezone.now() - timedelta(days=5)
    loan.save(update_fields=["due_at"])
    copy2 = Copy.objects.create(book=book, barcode="P2C2", accession_number="P2A2")
    with pytest.raises(LoanError, match="blocked"):
        issue_loan(copy=copy2, member=member, issued_by=user)


@pytest.mark.django_db
def test_unblocked_after_return(user, env):
    book, copy, member = env
    loan = issue_loan(copy=copy, member=member, issued_by=user)
    loan.due_at = timezone.now() - timedelta(days=5)
    loan.save(update_fields=["due_at"])
    assert is_blocked(member)
    return_loan(loan=loan, received_by=user)
    assert not is_blocked(member)


@pytest.mark.django_db
def test_fine_payment_recorded(user, env):
    book, copy, member = env
    loan = issue_loan(copy=copy, member=member, issued_by=user)
    loan.due_at = timezone.now() - timedelta(days=3)
    loan.save(update_fields=["due_at"])
    return_loan(loan=loan, received_by=user)
    loan.refresh_from_db()
    assert loan.fine_accrued == Decimal("30.00")

    record_payment(loan=loan, amount=Decimal("10.00"), by_user=user, reason="partial")
    loan.refresh_from_db()
    assert loan.fine_paid == Decimal("10.00")
    assert total_fines_owed(member) == Decimal("20.00")


@pytest.mark.django_db
def test_waiver_clears_balance(user, env):
    book, copy, member = env
    loan = issue_loan(copy=copy, member=member, issued_by=user)
    loan.due_at = timezone.now() - timedelta(days=3)
    loan.save(update_fields=["due_at"])
    return_loan(loan=loan, received_by=user)
    loan.refresh_from_db()
    waive_remaining(loan=loan, by_user=user, reason="goodwill")
    loan.refresh_from_db()
    assert loan.fine_paid == loan.fine_accrued


@pytest.mark.django_db
def test_reservation_fifo(user, env):
    book, copy, member = env
    member2 = Member.objects.create(member_number="P2M2", full_name="B", member_type="STUDENT")
    r1 = create_reservation(book=book, member=member, by_user=user)
    r2 = create_reservation(book=book, member=member2, by_user=user)
    assert r1.position == 1 and r2.position == 2

    promoted = promote_next_waiting(book=book, by_user=user)
    assert promoted is not None
    assert promoted.member_id == member.id
    assert promoted.status == Reservation.Status.READY
