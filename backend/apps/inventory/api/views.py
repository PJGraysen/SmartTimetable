from rest_framework import viewsets, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Count, Sum, Q, F
from django.utils import timezone
from datetime import timedelta

from apps.inventory.models import (
    Department, Location, Category, Supplier, Item, Asset,
    StockLevel, Movement, MaintenanceLog, AuditSession, AuditLine,
)
from apps.inventory.api.serializers import (
    DepartmentSerializer, LocationSerializer, CategorySerializer,
    SupplierSerializer, ItemSerializer, AssetSerializer,
    StockLevelSerializer, MovementSerializer, MaintenanceLogSerializer,
    AuditSessionSerializer, AuditLineSerializer,
)


class _BaseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    ordering = ["-id"]


class DepartmentViewSet(_BaseViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    search_fields = ["code", "name"]


class LocationViewSet(_BaseViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    search_fields = ["code", "name"]


class CategoryViewSet(_BaseViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    search_fields = ["code", "name"]


class SupplierViewSet(_BaseViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    search_fields = ["code", "name", "contact_person"]


class ItemViewSet(_BaseViewSet):
    queryset = Item.objects.select_related("category", "default_supplier").all()
    serializer_class = ItemSerializer
    search_fields = ["code", "name"]
    filterset_fields = ["category", "tracking_mode", "is_active"]


class AssetViewSet(_BaseViewSet):
    queryset = Asset.objects.select_related("item", "current_location").all()
    serializer_class = AssetSerializer
    search_fields = ["tag", "serial_number", "item__name", "item__code"]
    filterset_fields = ["item", "current_location", "condition", "status", "is_active"]


class StockLevelViewSet(_BaseViewSet):
    queryset = StockLevel.objects.select_related("item", "location").all()
    serializer_class = StockLevelSerializer
    search_fields = ["item__name", "item__code", "batch_number"]
    filterset_fields = ["item", "location"]


class MovementViewSet(_BaseViewSet):
    queryset = Movement.objects.select_related(
        "item", "asset", "from_location", "to_location", "actor",
    ).all()
    serializer_class = MovementSerializer
    search_fields = ["item__name", "item__code", "reference", "recipient"]
    filterset_fields = ["movement_type", "item", "asset", "to_location"]


class MaintenanceLogViewSet(_BaseViewSet):
    queryset = MaintenanceLog.objects.select_related("asset").all()
    serializer_class = MaintenanceLogSerializer
    filterset_fields = ["asset"]


class AuditSessionViewSet(_BaseViewSet):
    queryset = AuditSession.objects.prefetch_related("lines").all()
    serializer_class = AuditSessionSerializer
    search_fields = ["reference", "location__code"]
    filterset_fields = ["status", "location"]


class AuditLineViewSet(_BaseViewSet):
    queryset = AuditLine.objects.select_related("session", "item").all()
    serializer_class = AuditLineSerializer
    filterset_fields = ["session", "item"]


# ------------------ Dashboard ------------------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def inventory_dashboard(request):
    today = timezone.now().date()
    in_30 = today + timedelta(days=30)

    total_items = Item.objects.filter(is_active=True).count()
    total_assets = Asset.objects.filter(is_active=True).count()
    total_locations = Location.objects.filter(is_active=True).count()
    total_departments = Department.objects.filter(is_active=True).count()
    total_suppliers = Supplier.objects.filter(is_active=True).count()

    asset_value = Asset.objects.filter(is_active=True).aggregate(
        v=Sum("purchase_cost")
    )["v"] or 0

    by_condition = dict(
        Asset.objects.filter(is_active=True)
        .values_list("condition")
        .annotate(c=Count("id"))
        .values_list("condition", "c")
    )
    by_status = dict(
        Asset.objects.filter(is_active=True)
        .values_list("status")
        .annotate(c=Count("id"))
        .values_list("status", "c")
    )

    low_stock = []
    for sl in StockLevel.objects.select_related("item", "location"):
        if sl.item.min_stock and sl.quantity < sl.item.min_stock:
            low_stock.append({
                "item_code": sl.item.code,
                "item_name": sl.item.name,
                "location": sl.location.code,
                "quantity": float(sl.quantity),
                "min_stock": float(sl.item.min_stock),
                "unit": sl.item.unit,
            })

    warranty_due = list(
        Asset.objects.filter(
            is_active=True,
            warranty_expiry__gte=today,
            warranty_expiry__lte=in_30,
        ).values("tag", "item__name", "warranty_expiry")[:20]
    )

    maintenance_due = list(
        MaintenanceLog.objects.filter(
            next_due__gte=today,
            next_due__lte=in_30,
        ).values("asset__tag", "asset__item__name", "next_due")[:20]
    )

    by_department = list(
        Location.objects.filter(is_active=True)
        .values("department__name")
        .annotate(c=Count("assets"))
        .values("department__name", "c")
    )

    by_category = list(
        Item.objects.filter(is_active=True)
        .values("category__name")
        .annotate(c=Count("id"))
        .values("category__name", "c")
    )

    recent_movements = list(
        Movement.objects.select_related("item", "to_location", "from_location")
        .order_by("-occurred_at")[:10]
        .values("movement_type", "item__name", "item__code",
                "from_location__code", "to_location__code",
                "quantity", "occurred_at")
    )

    return Response({
        "totals": {
            "items": total_items,
            "assets": total_assets,
            "locations": total_locations,
            "departments": total_departments,
            "suppliers": total_suppliers,
            "asset_value": float(asset_value),
        },
        "assets_by_condition": by_condition,
        "assets_by_status": by_status,
        "assets_by_department": by_department,
        "items_by_category": by_category,
        "low_stock": low_stock,
        "warranty_due_30d": warranty_due,
        "maintenance_due_30d": maintenance_due,
        "recent_movements": recent_movements,
    })
