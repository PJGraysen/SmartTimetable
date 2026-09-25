
from datetime import timedelta

from django.db.models import Sum, Count, F, Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.inventory.models import (
    Item, Asset, Location, Category, Department, StockLevel, Movement, MaintenanceLog,
)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def reports_low_stock(request):
    rows = []
    for sl in StockLevel.objects.select_related("item", "location"):
        if not sl.item.min_stock:
            continue
        if (sl.quantity or 0) < sl.item.min_stock:
            rows.append({
                "item_code": sl.item.code,
                "item_name": sl.item.name,
                "location_code": sl.location.code,
                "location_name": sl.location.name,
                "quantity": float(sl.quantity or 0),
                "min_stock": float(sl.item.min_stock),
                "reorder_stock": float(sl.item.reorder_stock or 0),
                "unit": sl.item.unit,
                "shortfall": float(sl.item.min_stock - (sl.quantity or 0)),
            })
    rows.sort(key=lambda r: -r["shortfall"])
    return Response({"rows": rows, "count": len(rows)})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def reports_expiring_soon(request):
    days = int(request.query_params.get("days", 90))
    cutoff = timezone.now().date() + timedelta(days=days)
    today = timezone.now().date()
    rows = []
    for sl in StockLevel.objects.select_related("item", "location"):
        if sl.expiry_date and today <= sl.expiry_date <= cutoff:
            rows.append({
                "item_code": sl.item.code,
                "item_name": sl.item.name,
                "location_code": sl.location.code,
                "quantity": float(sl.quantity or 0),
                "unit": sl.item.unit,
                "batch_number": sl.batch_number,
                "expiry_date": str(sl.expiry_date),
                "days_left": (sl.expiry_date - today).days,
            })
    rows.sort(key=lambda r: r["days_left"])
    return Response({"rows": rows, "count": len(rows), "window_days": days})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def reports_valuation(request):
    by_category = list(
        Item.objects.filter(is_active=True)
        .values("category__name")
        .annotate(total=Sum(F("unit_cost") * 1), count=Count("id"))
        .values("category__name", "total", "count")
    )
    asset_by_dept = list(
        Asset.objects.filter(is_active=True)
        .values("current_location__department__name")
        .annotate(value=Sum("purchase_cost"), count=Count("id"))
        .values("current_location__department__name", "value", "count")
    )
    total_asset_value = Asset.objects.filter(is_active=True).aggregate(v=Sum("purchase_cost"))["v"] or 0
    total_items = Item.objects.filter(is_active=True).count()
    total_assets = Asset.objects.filter(is_active=True).count()

    return Response({
        "total_asset_value": float(total_asset_value),
        "total_items": total_items,
        "total_assets": total_assets,
        "items_by_category": by_category,
        "assets_by_department": asset_by_dept,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def reports_movement_summary(request):
    days = int(request.query_params.get("days", 30))
    since = timezone.now() - timedelta(days=days)
    qs = Movement.objects.filter(occurred_at__gte=since)

    by_type = list(
        qs.values("movement_type")
        .annotate(count=Count("id"), total_qty=Sum("quantity"))
        .values("movement_type", "count", "total_qty")
    )
    top_items = list(
        qs.values("item__code", "item__name")
        .annotate(count=Count("id"), total_qty=Sum("quantity"))
        .order_by("-count")[:20]
    )
    top_destinations = list(
        qs.filter(to_location__isnull=False)
        .values("to_location__code", "to_location__name")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
    return Response({
        "window_days": days,
        "by_type": by_type,
        "top_items": top_items,
        "top_destinations": top_destinations,
    })
