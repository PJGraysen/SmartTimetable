from django.core.management.base import BaseCommand
from apps.inventory.models import (
    Department, Location, Category, Supplier, Item, Asset, StockLevel,
)


DEPARTMENTS = [
    ("SCI", "Science Department", "Chemistry, Physics, Biology labs"),
    ("CS", "Computer Studies", "ICT and computer lab"),
    ("ADMIN", "Administration", "Front office and management"),
    ("SPORT", "Sports Department", "Games and athletics"),
    ("LIB", "Library", "Library and reading rooms"),
    ("MAINT", "Maintenance", "Facilities and repairs"),
]

LOCATIONS = [
    ("CHEM-LAB", "Chemistry Laboratory", "LAB", "SCI"),
    ("PHY-LAB", "Physics Laboratory", "LAB", "SCI"),
    ("BIO-LAB", "Biology Laboratory", "LAB", "SCI"),
    ("COMP-LAB", "Computer Laboratory", "LAB", "CS"),
    ("LIB-MAIN", "Main Library", "LIBRARY", "LIB"),
    ("SPORT-EQ", "Sports Equipment Store", "STORE", "SPORT"),
    ("GEN-STORE", "General Store", "STORE", "MAINT"),
    ("ADMIN-OFF", "Administration Office", "OFFICE", "ADMIN"),
]

CATEGORIES = [
    ("LAB-EQ", "Lab Equipment", False),
    ("GLASS", "Glassware", True),
    ("CHEM", "Chemicals", True),
    ("ELEC", "Electronics", False),
    ("ICT", "ICT Equipment", False),
    ("FURN", "Furniture", False),
    ("BOOK", "Books", False),
    ("SPORT", "Sports Gear", False),
    ("STN", "Stationery", True),
    ("TOOL", "Tools", False),
]

SUPPLIERS = [
    ("SUP-SCI", "Scientific Supplies Ltd", "sales@sci.co.ke", "0700-000-001"),
    ("SUP-ICT", "TechMart Solutions", "orders@techmart.co.ke", "0700-000-002"),
    ("SUP-GEN", "General Traders", "info@gtraders.co.ke", "0700-000-003"),
]

ITEMS = [
    # (code, name, category, unit, tracking, min_stock, cost)
    ("MICRO-BIN", "Binocular Microscope", "LAB-EQ", "pcs", "INDIVIDUAL", 0, 25000),
    ("BEAKER-250", "Beaker 250ml", "GLASS", "pcs", "QUANTITY", 20, 150),
    ("BEAKER-500", "Beaker 500ml", "GLASS", "pcs", "QUANTITY", 15, 250),
    ("TEST-TUBE", "Test Tube", "GLASS", "pcs", "QUANTITY", 100, 30),
    ("HCL-1L", "Hydrochloric Acid 1L", "CHEM", "bottle", "QUANTITY", 5, 400),
    ("NAOH-1KG", "Sodium Hydroxide 1kg", "CHEM", "kg", "QUANTITY", 5, 800),
    ("MICROSKOP", "Digital Microscope", "LAB-EQ", "pcs", "INDIVIDUAL", 0, 45000),
    ("LAPTOP", "Student Laptop", "ICT", "pcs", "INDIVIDUAL", 0, 65000),
    ("PRINTER", "Laser Printer", "ICT", "pcs", "INDIVIDUAL", 0, 32000),
    ("CHAIR", "Classroom Chair", "FURN", "pcs", "INDIVIDUAL", 0, 3500),
    ("DESK", "Student Desk", "FURN", "pcs", "INDIVIDUAL", 0, 8000),
    ("BALL-SOC", "Football (Size 5)", "SPORT", "pcs", "QUANTITY", 5, 1500),
    ("BOOK-PHY", "Physics Textbook", "BOOK", "pcs", "QUANTITY", 20, 900),
    ("MARKER", "Whiteboard Marker", "STN", "pcs", "QUANTITY", 30, 50),
    ("MULTIMETER", "Digital Multimeter", "ELEC", "pcs", "INDIVIDUAL", 0, 3500),
    ("HAMMER", "Hammer", "TOOL", "pcs", "INDIVIDUAL", 0, 800),
]


class Command(BaseCommand):
    help = "Seed inventory with demo departments, locations, categories, items"

    def handle(self, *a, **kw):
        for code, name, desc in DEPARTMENTS:
            Department.objects.get_or_create(code=code, defaults={"name": name, "description": desc})
        print(f"Departments: {Department.objects.count()}")

        dept_map = {d.code: d for d in Department.objects.all()}
        for code, name, ltype, dept_code in LOCATIONS:
            Location.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "location_type": ltype,
                    "department": dept_map.get(dept_code),
                },
            )
        print(f"Locations: {Location.objects.count()}")

        for code, name, consumable in CATEGORIES:
            Category.objects.get_or_create(
                code=code,
                defaults={"name": name, "is_consumable": consumable},
            )
        print(f"Categories: {Category.objects.count()}")

        for code, name, email, phone in SUPPLIERS:
            Supplier.objects.get_or_create(
                code=code,
                defaults={"name": name, "email": email, "phone": phone},
            )
        print(f"Suppliers: {Supplier.objects.count()}")

        cat_map = {c.code: c for c in Category.objects.all()}
        sup = Supplier.objects.filter(code="SUP-SCI").first()
        for code, name, cat_code, unit, mode, min_stock, cost in ITEMS:
            Item.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "category": cat_map[cat_code],
                    "unit": unit,
                    "tracking_mode": mode,
                    "min_stock": min_stock,
                    "unit_cost": cost,
                    "default_supplier": sup,
                },
            )
        print(f"Items: {Item.objects.count()}")
        print()
        print("Inventory demo seeded.")
