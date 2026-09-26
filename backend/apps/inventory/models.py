from __future__ import annotations

from django.conf import settings
from django.db import models


class Department(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    head = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="headed_departments",
    )
    assigned_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="inventory_departments",
        help_text="Staff member responsible for tracking this department inventory",
    )
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Location(models.Model):
    LOCATION_TYPES = [
        ("LAB", "Laboratory"), ("OFFICE", "Office"), ("STORE", "Store"),
        ("CLASSROOM", "Classroom"), ("LIBRARY", "Library"), ("HALL", "Hall"),
        ("SPORTS", "Sports Facility"), ("OTHER", "Other"),
    ]
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=160)
    location_type = models.CharField(max_length=20, choices=LOCATION_TYPES, default="OTHER")
    department = models.ForeignKey(
        Department, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="locations",
    )
    parent = models.ForeignKey(
        "self", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="children",
    )
    custodian = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="custodian_locations",
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Category(models.Model):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=120)
    parent = models.ForeignKey(
        "self", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="children",
    )
    description = models.TextField(blank=True)
    is_consumable = models.BooleanField(default=False)
    custom_fields = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Supplier(models.Model):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    whatsapp = models.CharField(max_length=40, blank=True)
    payment_terms = models.CharField(max_length=120, blank=True)
    lead_time_days = models.IntegerField(default=7)
    rating = models.DecimalField(
        max_digits=3, decimal_places=2, default=0,
        help_text="0-5 quality rating",
    )
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Item(models.Model):
    TRACKING_CHOICES = [
        ("INDIVIDUAL", "Track individually (serialized asset)"),
        ("QUANTITY", "Track by quantity (bulk stock)"),
    ]
    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="items")
    department = models.ForeignKey(
        Department, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="owned_items",
        help_text="Owning department",
    )
    unit = models.CharField(max_length=20, default="pcs")
    tracking_mode = models.CharField(max_length=20, choices=TRACKING_CHOICES, default="INDIVIDUAL")
    description = models.TextField(blank=True)
    min_stock = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reorder_stock = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    default_supplier = models.ForeignKey(
        Supplier, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="items",
    )
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    specs = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    is_retired = models.BooleanField(default=False, db_index=True)
    retired_at = models.DateTimeField(null=True, blank=True)
    retired_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="retired_items",
    )
    retirement_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Asset(models.Model):
    CONDITION_CHOICES = [
        ("NEW", "New"), ("GOOD", "Good"), ("FAIR", "Fair"),
        ("POOR", "Poor"), ("DAMAGED", "Damaged"), ("DISPOSED", "Disposed"),
    ]
    STATUS_CHOICES = [
        ("AVAILABLE", "Available"), ("IN_USE", "In Use"),
        ("MAINTENANCE", "Under Maintenance"), ("LOANED", "Loaned Out"),
        ("LOST", "Lost"), ("DISPOSED", "Disposed"),
    ]
    tag = models.CharField(max_length=40, unique=True)
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="assets")
    serial_number = models.CharField(max_length=120, blank=True)
    current_location = models.ForeignKey(
        Location, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="assets",
    )
    custodian = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="custodian_assets",
    )
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default="NEW")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="AVAILABLE")
    purchase_date = models.DateField(null=True, blank=True)
    purchase_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    supplier = models.ForeignKey(
        Supplier, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="assets",
    )
    warranty_expiry = models.DateField(null=True, blank=True)
    useful_life_months = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tag} - {self.item.name}"


class StockLevel(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="stock_levels")
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="stock_levels")
    quantity = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    batch_number = models.CharField(max_length=60, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    last_counted_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [("item", "location", "batch_number")]
        ordering = ["item__name", "location__name"]

    def __str__(self):
        return f"{self.item.name} @ {self.location.code} = {self.quantity} {self.item.unit}"


class Movement(models.Model):
    MOVEMENT_TYPES = [
        ("RECEIPT", "Receipt"), ("ISSUE", "Issue"), ("TRANSFER", "Transfer"),
        ("RETURN", "Return"), ("DISPOSAL", "Disposal"), ("ADJUSTMENT", "Stock Adjustment"),
        ("MAINTENANCE_OUT", "Sent for Maintenance"),
        ("MAINTENANCE_IN", "Returned from Maintenance"),
    ]
    movement_type = models.CharField(max_length=30, choices=MOVEMENT_TYPES)
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="movements")
    asset = models.ForeignKey(
        Asset, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="movements",
    )
    from_location = models.ForeignKey(
        Location, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="movements_out",
    )
    to_location = models.ForeignKey(
        Location, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="movements_in",
    )
    quantity = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="inventory_movements",
    )
    recipient = models.CharField(max_length=120, blank=True)
    reference = models.CharField(max_length=60, blank=True)
    reason = models.TextField(blank=True, help_text="Why this action is being taken")
    notes = models.TextField(blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_at"]

    def __str__(self):
        return f"{self.movement_type} {self.item.code} x{self.quantity}"


class MaintenanceLog(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending Approval"), ("APPROVED", "Approved"),
        ("IN_PROGRESS", "In Progress"), ("COMPLETED", "Completed"),
        ("REJECTED", "Rejected"),
    ]
    PRIORITY_CHOICES = [
        ("LOW", "Low"), ("NORMAL", "Normal"),
        ("HIGH", "High"), ("CRITICAL", "Critical"),
    ]
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="maintenance_logs")
    performed_by = models.CharField(max_length=120, blank=True)
    description = models.TextField(help_text="What is faulty")
    remedy = models.TextField(blank=True, help_text="Proposed remedy")
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="NORMAL")
    approval_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="reported_maintenance",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="approved_maintenance",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approval_note = models.TextField(blank=True)
    performed_at = models.DateField(null=True, blank=True)
    next_due = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.asset.tag} [{self.approval_status}] {self.description[:40]}"


class AuditSession(models.Model):
    STATUS_CHOICES = [("OPEN", "Open"), ("CLOSED", "Closed")]
    reference = models.CharField(max_length=60, unique=True)
    location = models.ForeignKey(Location, on_delete=models.PROTECT, related_name="audit_sessions")
    started_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="OPEN")
    conducted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="conducted_audits",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.reference} @ {self.location.code}"


class AuditLine(models.Model):
    session = models.ForeignKey(AuditSession, on_delete=models.CASCADE, related_name="lines")
    item = models.ForeignKey(Item, on_delete=models.PROTECT)
    expected_quantity = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    counted_quantity = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    variance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["item__name"]

    def __str__(self):
        return f"{self.item.code}: {self.counted_quantity} (var {self.variance})"
