from __future__ import annotations

import uuid
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q

from apps.academics.models import Subject


class LibraryBase(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Author(LibraryBase):
    name = models.CharField(max_length=200)
    sort_name = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["sort_name", "name"]

    def __str__(self):
        return self.name


class Publisher(LibraryBase):
    name = models.CharField(max_length=200, unique=True)
    address = models.TextField(blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Category(LibraryBase):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=30, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Shelf(LibraryBase):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    location_hint = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Book(LibraryBase):
    isbn = models.CharField(max_length=20, blank=True, db_index=True)
    title = models.CharField(max_length=300)
    subtitle = models.CharField(max_length=300, blank=True)
    edition = models.CharField(max_length=50, blank=True)
    language = models.CharField(max_length=40, default="English")
    description = models.TextField(blank=True)
    publisher = models.ForeignKey(
        Publisher, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="books",
    )
    published_year = models.PositiveSmallIntegerField(null=True, blank=True)
    cover_url = models.URLField(blank=True)
    authors = models.ManyToManyField(Author, related_name="books", blank=True)
    categories = models.ManyToManyField(Category, related_name="books", blank=True)
    subjects = models.ManyToManyField(Subject, related_name="library_books", blank=True)
    is_active = models.BooleanField(default=True)
    ddc = models.CharField(max_length=32, blank=True, default="")
    lcc = models.CharField(max_length=32, blank=True, default="")
    page_count = models.PositiveIntegerField(null=True, blank=True)
    toc = models.TextField(blank=True, default="")
    source = models.CharField(max_length=20, blank=True, default="MANUAL")
    source_id = models.CharField(max_length=64, blank=True, default="")
    marc21 = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["title"]
        permissions = [
            ("import_catalogue", "Can bulk-import catalogue records"),
        ]

    def __str__(self):
        return self.title


class Copy(LibraryBase):
    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        ISSUED = "ISSUED", "Issued"
        RESERVED = "RESERVED", "Reserved"
        LOST = "LOST", "Lost"
        DAMAGED = "DAMAGED", "Damaged"
        REPAIR = "REPAIR", "In repair"

    class Condition(models.TextChoices):
        NEW = "NEW", "New"
        GOOD = "GOOD", "Good"
        FAIR = "FAIR", "Fair"
        WORN = "WORN", "Worn"

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="copies")
    barcode = models.CharField(max_length=60, unique=True, db_index=True)
    accession_number = models.CharField(max_length=60, unique=True)
    shelf = models.ForeignKey(
        Shelf, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="copies",
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.AVAILABLE,
        db_index=True,
    )
    condition = models.CharField(
        max_length=16, choices=Condition.choices, default=Condition.GOOD,
    )
    acquired_at = models.DateField(null=True, blank=True)
    acquisition_cost = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
    )
    replacement_cost = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
    )
    inventory_asset = models.ForeignKey(
        "inventory.Asset", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="library_copies",
        help_text="Linked inventory asset (created via register_copy_in_inventory).",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["barcode"]
        verbose_name_plural = "copies"

    def __str__(self):
        return f"{self.barcode} - {self.book.title}"


class Member(LibraryBase):
    class MemberType(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        TEACHER = "TEACHER", "Teacher"
        STAFF = "STAFF", "Staff"
        EXTERNAL = "EXTERNAL", "External"

    member_number = models.CharField(max_length=40, unique=True)
    user = models.OneToOneField(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="library_member",
    )
    student = models.OneToOneField(
        "academics.Student", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="library_member",
        help_text="Set when this Member represents an academic student.",
    )
    teacher = models.OneToOneField(
        "users.Teacher", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="library_member",
        help_text="Set when this Member represents a teacher or staff member.",
    )
    full_name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    member_type = models.CharField(
        max_length=16, choices=MemberType.choices, db_index=True,
    )
    is_active = models.BooleanField(default=True, db_index=True)
    joined_at = models.DateField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["member_number"]

    def __str__(self):
        return f"{self.member_number} - {self.full_name}"


class LoanRule(LibraryBase):
    member_type = models.CharField(
        max_length=16, choices=Member.MemberType.choices, unique=True,
    )
    max_concurrent_loans = models.PositiveSmallIntegerField(default=2)
    loan_days = models.PositiveSmallIntegerField(default=14)
    max_renewals = models.PositiveSmallIntegerField(default=2)
    fine_per_day = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal("0.00"),
    )
    grace_days = models.PositiveSmallIntegerField(default=0)
    max_fine = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
    )

    class Meta:
        permissions = [
            ("manage_settings", "Can manage library settings"),
        ]

    def __str__(self):
        return f"{self.get_member_type_display()} rule"


class Loan(LibraryBase):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        RETURNED = "RETURNED", "Returned"
        LOST = "LOST", "Lost"

    copy = models.ForeignKey(Copy, on_delete=models.PROTECT, related_name="loans")
    member = models.ForeignKey(Member, on_delete=models.PROTECT, related_name="loans")
    issued_at = models.DateTimeField(auto_now_add=True)
    due_at = models.DateTimeField()
    returned_at = models.DateTimeField(null=True, blank=True)
    issued_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="library_loans_issued",
    )
    received_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="library_loans_received",
    )
    renewal_count = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE,
        db_index=True,
    )
    fine_accrued = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("0.00"),
    )
    fine_paid = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal("0.00"),
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-issued_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["copy"],
                condition=Q(status="ACTIVE"),
                name="uq_active_loan_per_copy",
            ),
        ]
        permissions = [
            ("issue_loan", "Can issue loans"),
            ("return_loan", "Can return loans"),
            ("renew_loan", "Can renew loans"),
            ("manage_fines", "Can manage fines"),
            ("view_reports", "Can view library reports"),
        ]

    def __str__(self):
        return f"Loan {self.id} - {self.copy.barcode} -> {self.member.member_number}"


# =========================================================================
# PHASE 2 — Reservations, Fine Payments, Reading Lists
# =========================================================================


class Reservation(LibraryBase):
    class Status(models.TextChoices):
        WAITING = "WAITING", "Waiting"
        READY = "READY", "Ready for pickup"
        FULFILLED = "FULFILLED", "Fulfilled"
        CANCELLED = "CANCELLED", "Cancelled"
        EXPIRED = "EXPIRED", "Expired"

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="reservations")
    member = models.ForeignKey(Member, on_delete=models.PROTECT, related_name="reservations")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.WAITING, db_index=True)
    position = models.PositiveIntegerField(default=1)
    requested_at = models.DateTimeField(auto_now_add=True)
    notified_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["status", "position", "requested_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["book", "member"],
                condition=Q(status="WAITING"),
                name="uq_waiting_reservation_per_member_book",
            ),
        ]
        permissions = [
            ("manage_reservations", "Can manage reservations"),
            ("fulfill_reservation", "Can fulfill reservations"),
        ]

    def __str__(self):
        return f"Reservation {self.member.member_number} -> {self.book.title} ({self.status})"


class FinePayment(LibraryBase):
    class Kind(models.TextChoices):
        PAYMENT = "PAYMENT", "Payment"
        WAIVER = "WAIVER", "Waiver"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"

    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.PAYMENT)
    reason = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="library_fine_payments",
    )
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-recorded_at"]
        permissions = [
            ("record_fine_payment", "Can record fine payments"),
        ]

    def __str__(self):
        return f"{self.kind} {self.amount} on loan {self.loan_id}"


class ReadingList(LibraryBase):
    name = models.CharField(max_length=200)
    subject = models.ForeignKey(
        Subject, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reading_lists",
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        permissions = [
            ("manage_reading_lists", "Can manage reading lists"),
        ]

    def __str__(self):
        return self.name


class ReadingListItem(LibraryBase):
    reading_list = models.ForeignKey(ReadingList, on_delete=models.CASCADE, related_name="items")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="reading_list_items")
    position = models.PositiveSmallIntegerField(default=0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["position", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["reading_list", "book"],
                name="uq_reading_list_book",
            ),
        ]

    def __str__(self):
        return f"{self.reading_list.name}: {self.book.title}"
