import pytest
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.utils import timezone

from apps.library.models import Book, Copy, Loan, LoanRule, Member
from apps.library.services.loans import LoanError, issue_loan, renew_loan, return_loan


@pytest.fixture
def user(db):
    return User.objects.create_user(username="librarian", password="x")


@pytest.fixture
def setup_library(db):
    rule = LoanRule.objects.create(
        member_type=Member.MemberType.STUDENT,
        max_concurrent_loans=2,
        loan_days=14,
        max_renewals=1,
        fine_per_day=Decimal("5.00"),
        grace_days=1,
        max_fine=Decimal("100.00"),
    )
    book = Book.objects.create(title="Test")
    copy = Copy.objects.create(book=book, barcode="X1", accession_number="A1")
    member = Member.objects.create(
        member_number="M1", full_name="Alice", member_type=Member.MemberType.STUDENT,
    )
    return rule, book, copy, member


@pytest.mark.django_db
def test_issue_loan_basic(user, setup_library):
    rule, book, copy, member = setup_library
    loan = issue_loan(copy=copy, member=member, issued_by=user)
    copy.refresh_from_db()
    assert loan.status == Loan.Status.ACTIVE
    assert copy.status == Copy.Status.ISSUED


@pytest.mark.django_db
def test_issue_loan_rejects_unavailable_copy(user, setup_library):
    rule, book, copy, member = setup_library
    copy.status = Copy.Status.LOST
    copy.save()
    with pytest.raises(LoanError, match="not available"):
        issue_loan(copy=copy, member=member, issued_by=user)


@pytest.mark.django_db
def test_issue_loan_respects_concurrent_cap(user, setup_library):
    rule, book, copy, member = setup_library
    rule.max_concurrent_loans = 1
    rule.save()
    issue_loan(copy=copy, member=member, issued_by=user)
    copy2 = Copy.objects.create(book=book, barcode="X2", accession_number="A2")
    with pytest.raises(LoanError, match="active loans"):
        issue_loan(copy=copy2, member=member, issued_by=user)


@pytest.mark.django_db
def test_return_loan_no_fine_when_early(user, setup_library):
    rule, book, copy, member = setup_library
    loan = issue_loan(copy=copy, member=member, issued_by=user)
    loan = return_loan(loan=loan, received_by=user)
    assert loan.status == Loan.Status.RETURNED
    assert loan.fine_accrued == Decimal("0.00")
    copy.refresh_from_db()
    assert copy.status == Copy.Status.AVAILABLE


@pytest.mark.django_db
def test_return_loan_accrues_fine_when_overdue(user, setup_library):
    rule, book, copy, member = setup_library
    loan = issue_loan(copy=copy, member=member, issued_by=user)
    # force overdue by 10 days (grace=1, so 9 chargeable days)
    loan.due_at = timezone.now() - timedelta(days=10)
    loan.save(update_fields=["due_at"])
    loan = return_loan(loan=loan, received_by=user)
    assert loan.fine_accrued == Decimal("5.00") * 9


@pytest.mark.django_db
def test_renew_loan_extends_due_date(user, setup_library):
    rule, book, copy, member = setup_library
    loan = issue_loan(copy=copy, member=member, issued_by=user)
    original_due = loan.due_at
    loan = renew_loan(loan=loan, by_user=user)
    assert loan.due_at > original_due
    assert loan.renewal_count == 1


@pytest.mark.django_db
def test_renew_loan_respects_max_renewals(user, setup_library):
    rule, book, copy, member = setup_library
    loan = issue_loan(copy=copy, member=member, issued_by=user)
    loan = renew_loan(loan=loan, by_user=user)
    with pytest.raises(LoanError, match="Maximum renewals"):
        renew_loan(loan=loan, by_user=user)


@pytest.mark.django_db
def test_renew_loan_rejects_overdue(user, setup_library):
    rule, book, copy, member = setup_library
    loan = issue_loan(copy=copy, member=member, issued_by=user)
    loan.due_at = timezone.now() - timedelta(days=1)
    loan.save(update_fields=["due_at"])
    with pytest.raises(LoanError, match="overdue"):
        renew_loan(loan=loan, by_user=user)
