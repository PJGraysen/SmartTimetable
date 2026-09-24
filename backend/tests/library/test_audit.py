import pytest
from django.contrib.auth.models import User
from decimal import Decimal

from apps.audit.models import AuditLog
from apps.library.models import Book, Copy, LoanRule, Member
from apps.library.services.loans import issue_loan, return_loan


@pytest.fixture
def user(db):
    return User.objects.create_user(username="libaudit", password="x")


@pytest.fixture
def fixture_data(db):
    LoanRule.objects.create(
        member_type=Member.MemberType.STUDENT,
        loan_days=14,
        fine_per_day=Decimal("0.00"),
    )
    book = Book.objects.create(title="Audited")
    copy = Copy.objects.create(book=book, barcode="B1", accession_number="AC1")
    member = Member.objects.create(
        member_number="M1", full_name="Bob", member_type=Member.MemberType.STUDENT,
    )
    return book, copy, member


@pytest.mark.django_db
def test_issue_loan_creates_audit(user, fixture_data):
    _, copy, member = fixture_data
    before = AuditLog.objects.count()
    issue_loan(copy=copy, member=member, issued_by=user)
    assert AuditLog.objects.count() == before + 1
    log = AuditLog.objects.order_by("-created_at").first()
    assert log.action == "library.loan.issue"
    assert log.entity_type == "Loan"


@pytest.mark.django_db
def test_return_loan_creates_audit(user, fixture_data):
    _, copy, member = fixture_data
    loan = issue_loan(copy=copy, member=member, issued_by=user)
    before = AuditLog.objects.count()
    return_loan(loan=loan, received_by=user)
    assert AuditLog.objects.count() == before + 1
    log = AuditLog.objects.order_by("-created_at").first()
    assert log.action == "library.loan.return"
