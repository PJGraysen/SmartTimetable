from django.contrib import admin
from apps.inventory.models import (
    Department, Location, Category, Supplier, Item, Asset,
    StockLevel, Movement, MaintenanceLog, AuditSession, AuditLine,
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "head", "is_active")
    search_fields = ("code", "name")


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "location_type", "department", "is_active")
    list_filter = ("location_type", "department", "is_active")
    search_fields = ("code", "name")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "parent", "is_consumable", "is_active")
    list_filter = ("is_consumable", "is_active")


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "contact_person", "phone", "is_active")
    search_fields = ("code", "name", "contact_person")


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "category", "unit", "tracking_mode", "is_active")
    list_filter = ("category", "tracking_mode", "is_active")
    search_fields = ("code", "name")


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("tag", "item", "current_location", "condition", "status", "is_active")
    list_filter = ("condition", "status", "current_location")
    search_fields = ("tag", "serial_number", "item__name")


@admin.register(StockLevel)
class StockLevelAdmin(admin.ModelAdmin):
    list_display = ("item", "location", "quantity", "batch_number", "expiry_date")
    list_filter = ("location",)


@admin.register(Movement)
class MovementAdmin(admin.ModelAdmin):
    list_display = ("occurred_at", "movement_type", "item", "from_location", "to_location", "quantity")
    list_filter = ("movement_type",)
    search_fields = ("reference", "recipient", "item__name")


@admin.register(MaintenanceLog)
class MaintenanceLogAdmin(admin.ModelAdmin):
    list_display = ("asset", "performed_at", "performed_by", "cost", "next_due")


class AuditLineInline(admin.TabularInline):
    model = AuditLine
    extra = 0


@admin.register(AuditSession)
class AuditSessionAdmin(admin.ModelAdmin):
    list_display = ("reference", "location", "status", "started_at", "closed_at")
    list_filter = ("status", "location")
    inlines = [AuditLineInline]
