
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.inventory.models import (
    Item, Asset, Location, StockLevel, Movement, MaintenanceLog,
)


class Command(BaseCommand):
    help = "Seed real assets, stock levels, movements for demo"

    def handle(self, *a, **kw):
        today = date.today()

        items = {i.code: i for i in Item.objects.all()}
        locs = {l.code: l for l in Location.objects.all()}

        def _tag(prefix, n):
            return f"{prefix}-{n:04d}"

        # ---- Serialized assets ----
        ASSETS = [
            ("MICRO-BIN", "CHEM-LAB", 6, "GOOD", "IN_USE"),
            ("MICROSKOP", "BIO-LAB", 4, "NEW", "AVAILABLE"),
            ("LAPTOP", "COMP-LAB", 12, "GOOD", "IN_USE"),
            ("PRINTER", "COMP-LAB", 2, "FAIR", "IN_USE"),
            ("MULTIMETER", "PHY-LAB", 8, "GOOD", "IN_USE"),
            ("CHAIR", "GEN-STORE", 40, "GOOD", "AVAILABLE"),
            ("DESK", "GEN-STORE", 40, "GOOD", "AVAILABLE"),
            ("HAMMER", "GEN-STORE", 6, "GOOD", "AVAILABLE"),
        ]
        created_assets = 0
        with transaction.atomic():
            for item_code, loc_code, count, cond, status in ASSETS:
                item = items.get(item_code)
                loc = locs.get(loc_code)
                if not item or not loc:
                    continue
                for i in range(1, count + 1):
                    tag = _tag(item_code[:4].upper(), i)
                    if Asset.objects.filter(tag=tag).exists():
                        continue
                    Asset.objects.create(
                        tag=tag, item=item, current_location=loc,
                        serial_number=f"SN-{item_code}-{i:04d}",
                        condition=cond, status=status,
                        purchase_date=today - timedelta(days=180),
                        purchase_cost=item.unit_cost,
                        supplier=item.default_supplier,
                        warranty_expiry=today + timedelta(days=365),
                        useful_life_months=60,
                    )
                    created_assets += 1
        print(f"Created {created_assets} assets")

        # ---- Bulk stock levels ----
        STOCK = [
            ("BEAKER-250", "CHEM-LAB", 45),
            ("BEAKER-500", "CHEM-LAB", 30),
            ("TEST-TUBE",  "CHEM-LAB", 180),
            ("HCL-1L",     "CHEM-LAB", 4),      # below min -> triggers low stock
            ("NAOH-1KG",   "CHEM-LAB", 12),
            ("BALL-SOC",   "SPORT-EQ", 6),
            ("BOOK-PHY",   "LIB-MAIN", 25),
            ("MARKER",     "GEN-STORE", 18),
        ]
        created_stock = 0
        with transaction.atomic():
            for item_code, loc_code, qty in STOCK:
                item = items.get(item_code)
                loc = locs.get(loc_code)
                if not item or not loc:
                    continue
                sl, created = StockLevel.objects.get_or_create(
                    item=item, location=loc, batch_number="",
                    defaults={"quantity": Decimal(str(qty))},
                )
                if created:
                    created_stock += 1
                    Movement.objects.create(
                        movement_type="RECEIPT", item=item, to_location=loc,
                        quantity=Decimal(str(qty)), notes="Initial seed",
                    )
        print(f"Created {created_stock} stock rows")

        # ---- Movements (issue + transfer history) ----
        sample_moves = 0
        with transaction.atomic():
            for item_code, loc_code in [("BEAKER-250", "CHEM-LAB"), ("MARKER", "GEN-STORE")]:
                item = items.get(item_code)
                loc = locs.get(loc_code)
                if not item or not loc:
                    continue
                Movement.objects.create(
                    movement_type="ISSUE", item=item, from_location=loc,
                    quantity=Decimal("2"), recipient="Lab Assistant",
                    notes="Weekly practicals",
                )
                sample_moves += 1
        print(f"Created {sample_moves} sample movements")

        # ---- One maintenance log ----
        first_asset = Asset.objects.filter(status="IN_USE").first()
        if first_asset:
            MaintenanceLog.objects.get_or_create(
                asset=first_asset,
                performed_at=today - timedelta(days=20),
                defaults={
                    "performed_by": "Technician",
                    "description": "Routine service and calibration",
                    "cost": Decimal("1500"),
                    "next_due": today + timedelta(days=90),
                },
            )
            print("Created maintenance log")

        print()
        print("Done. Dashboard now shows real data.")
