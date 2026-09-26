"""
Finance — student/staff fee accounts and a simple ledger.

Library fines post here via apps.finance.services.post_charge().
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from django.db import models


class FeeAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member = models.OneToOneField(
        "library.Member", on_delete=models.CASCADE, related_name="fee_account",
    )
    balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"),
        help_text="Running balance: positive = owed by member.",
    )
    currency = models.CharField(max_length=8, default="KES")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "finance_fee_account"

    def __str__(self):
        return f"Account {self.member.member_number} ({self.balance} {self.currency})"


class LedgerEntry(models.Model):
    class Kind(models.TextChoices):
        CHARGE = "CHARGE", "Charge"
        PAYMENT = "PAYMENT", "Payment"
        WAIVER = "WAIVER", "Waiver"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"

    class Source(models.TextChoices):
        LIBRARY = "LIBRARY", "Library"
        FEES = "FEES", "School fees"
        UNIFORM = "UNIFORM", "Uniform"
        TRANSPORT = "TRANSPORT", "Transport"
        OTHER = "OTHER", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(
        FeeAccount, on_delete=models.CASCADE, related_name="entries",
    )
    kind = models.CharField(max_length=12, choices=Kind.choices, db_index=True)
    source = models.CharField(
        max_length=12, choices=Source.choices, default=Source.OTHER, db_index=True,
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference_type = models.CharField(max_length=60, blank=True, default="")
    reference_id = models.CharField(max_length=64, blank=True, default="")
    description = models.TextField(blank=True, default="")
    recorded_by = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="finance_entries",
    )
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "finance_ledger_entry"
        ordering = ["-recorded_at"]

    def signed_amount(self) -> Decimal:
        if self.kind == self.Kind.CHARGE:
            return self.amount
        return -self.amount

    def __str__(self):
        return f"{self.kind} {self.amount} [{self.source}] {self.account_id}"
