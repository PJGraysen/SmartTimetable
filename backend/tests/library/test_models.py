import pytest
from decimal import Decimal

from apps.library.models import (
    Author, Book, Category, Copy, LoanRule, Member, Publisher, Shelf,
)


@pytest.mark.django_db
def test_book_minimal_creation():
    b = Book.objects.create(title="Test Book")
    assert b.id is not None
    assert b.is_active is True


@pytest.mark.django_db
def test_copy_barcode_unique():
    b = Book.objects.create(title="Test Book")
    Copy.objects.create(book=b, barcode="X1", accession_number="A1")
    from django.db import IntegrityError
    with pytest.raises(IntegrityError):
        Copy.objects.create(book=b, barcode="X1", accession_number="A2")


@pytest.mark.django_db
def test_copy_accession_unique():
    b = Book.objects.create(title="Test Book")
    Copy.objects.create(book=b, barcode="X1", accession_number="A1")
    from django.db import IntegrityError
    with pytest.raises(IntegrityError):
        Copy.objects.create(book=b, barcode="X2", accession_number="A1")


@pytest.mark.django_db
def test_loan_rule_unique_per_member_type():
    LoanRule.objects.create(member_type=Member.MemberType.STUDENT)
    from django.db import IntegrityError
    with pytest.raises(IntegrityError):
        LoanRule.objects.create(member_type=Member.MemberType.STUDENT)


@pytest.mark.django_db
def test_member_number_unique():
    Member.objects.create(member_number="M1", full_name="A", member_type="STUDENT")
    from django.db import IntegrityError
    with pytest.raises(IntegrityError):
        Member.objects.create(member_number="M1", full_name="B", member_type="STUDENT")
