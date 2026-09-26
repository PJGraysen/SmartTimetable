"""
Link library copies to the inventory app.

Each Copy becomes an inventory Asset under the LIBRARY department, belonging
to an Item created per Book title. Barcode becomes the Asset tag.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction


def _ensure_department():
    from apps.inventory.models import Department
    dept, _ = Department.objects.get_or_create(
        code="LIBRARY",
        defaults={"name": "Library",
                  "description": "School library department"},
    )
    return dept


def _ensure_category():
    from apps.inventory.models import Category
    cat, _ = Category.objects.get_or_create(
        code="LIB-BOOK",
        defaults={"name": "Library Books", "is_consumable": False},
    )
    return cat


def _item_for_book(book, dept, cat):
    from apps.inventory.models import Item
    code = f"BOOK-{str(book.id)[:8]}"
    item, _ = Item.objects.get_or_create(
        code=code,
        defaults={
            "name": book.title[:200],
            "category": cat,
            "department": dept,
            "tracking_mode": "INDIVIDUAL",
            "unit": "copy",
            "unit_cost": Decimal("0.00"),
        },
    )
    return item


_COND = {"NEW": "NEW", "GOOD": "GOOD", "FAIR": "FAIR", "WORN": "POOR"}
_STATUS = {"AVAILABLE": "AVAILABLE", "ISSUED": "LOANED",
           "RESERVED": "IN_USE", "LOST": "LOST",
           "DAMAGED": "DAMAGED", "REPAIR": "MAINTENANCE"}


@transaction.atomic
def register_copy_in_inventory(copy):
    from apps.inventory.models import Asset
    dept = _ensure_department()
    cat = _ensure_category()
    item = _item_for_book(copy.book, dept, cat)
    asset, created = Asset.objects.get_or_create(
        tag=copy.barcode,
        defaults={
            "item": item,
            "serial_number": copy.accession_number,
            "condition": _COND.get(copy.condition, "GOOD"),
            "status": _STATUS.get(copy.status, "AVAILABLE"),
            "purchase_date": copy.acquired_at,
            "purchase_cost": copy.acquisition_cost or Decimal("0.00"),
        },
    )
    if copy.inventory_asset_id != asset.id:
        copy.inventory_asset = asset
        copy.save(update_fields=["inventory_asset", "updated_at"])
    return asset, created


@transaction.atomic
def register_all_copies() -> dict:
    from apps.library.models import Copy
    total = 0; created = 0; errors = 0
    for c in Copy.objects.filter(inventory_asset__isnull=True):
        total += 1
        try:
            _, was_new = register_copy_in_inventory(c)
            if was_new: created += 1
        except Exception:
            errors += 1
    return {"scanned": total, "created": created, "errors": errors,
            "total_copies": Copy.objects.count()}
