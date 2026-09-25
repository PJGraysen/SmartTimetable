
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum, Count, Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.inventory.models import (
    Item, Asset, Location, Department, Category, Supplier,
    StockLevel, Movement, MaintenanceLog, AuditSession,
)


# ---------------- Asset detail + history ----------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def asset_detail(request, pk):
    try:
        a = Asset.objects.select_related(
            "item__category", "current_location__department",
            "supplier", "custodian",
        ).get(pk=pk)
    except Asset.DoesNotExist:
        return Response({"detail": "not found"}, status=404)
    movements = list(
        Movement.objects.filter(asset=a)
        .order_by("-occurred_at")[:50]
        .values("id", "movement_type", "occurred_at", "from_location__code",
                "to_location__code", "notes", "actor__username")
    )
    maint = list(
        MaintenanceLog.objects.filter(asset=a)
        .order_by("-performed_at")[:50]
        .values("id", "performed_at", "performed_by", "description",
                "cost", "next_due")
    )
    return Response({
        "asset": {
            "id": a.id, "tag": a.tag, "serial_number": a.serial_number,
            "item_id": a.item_id, "item_code": a.item.code, "item_name": a.item.name,
            "category": a.item.category.name if a.item.category else None,
            "location_id": a.current_location_id if a.current_location else None,
            "location_code": a.current_location.code if a.current_location else None,
            "location_name": a.current_location.name if a.current_location else None,
            "department": (a.current_location.department.name
                           if a.current_location and a.current_location.department else None),
            "condition": a.condition, "status": a.status,
            "purchase_date": str(a.purchase_date) if a.purchase_date else None,
            "purchase_cost": float(a.purchase_cost or 0),
            "supplier": a.supplier.name if a.supplier else None,
            "warranty_expiry": str(a.warranty_expiry) if a.warranty_expiry else None,
            "notes": a.notes, "is_active": a.is_active,
        },
        "movements": movements,
        "maintenance": maint,
    })


# ---------------- Item detail + stock + usage ----------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def item_detail(request, pk):
    try:
        it = Item.objects.select_related("category", "default_supplier").get(pk=pk)
    except Item.DoesNotExist:
        return Response({"detail": "not found"}, status=404)
    stock = list(
        StockLevel.objects.filter(item=it)
        .values("id", "location__code", "location__name", "quantity",
                "batch_number", "expiry_date")
    )
    total_qty = sum((s["quantity"] or 0) for s in stock)
    assets = list(
        Asset.objects.filter(item=it, is_active=True)[:200]
        .values("id", "tag", "current_location__code", "condition", "status")
    )
    usage = list(
        Movement.objects.filter(item=it)
        .order_by("-occurred_at")[:50]
        .values("id", "movement_type", "occurred_at", "quantity",
                "from_location__code", "to_location__code", "recipient", "notes")
    )
    return Response({
        "item": {
            "id": it.id, "code": it.code, "name": it.name,
            "category_id": it.category_id,
            "category_name": it.category.name if it.category else None,
            "unit": it.unit, "tracking_mode": it.tracking_mode,
            "unit_cost": float(it.unit_cost or 0),
            "min_stock": float(it.min_stock or 0),
            "reorder_stock": float(it.reorder_stock or 0),
            "supplier_id": it.default_supplier_id if it.default_supplier else None,
            "supplier_name": it.default_supplier.name if it.default_supplier else None,
            "description": it.description, "is_active": it.is_active,
        },
        "stock": stock,
        "total_quantity": float(total_qty),
        "assets": assets,
        "assets_count": len(assets),
        "usage": usage,
    })


# ---------------- Location contents ----------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def location_contents(request, pk):
    try:
        loc = Location.objects.select_related("department", "parent").get(pk=pk)
    except Location.DoesNotExist:
        return Response({"detail": "not found"}, status=404)
    assets = list(
        Asset.objects.filter(current_location=loc, is_active=True)
        .values("id", "tag", "item__name", "condition", "status")[:500]
    )
    stock = list(
        StockLevel.objects.filter(location=loc)
        .values("id", "item__code", "item__name", "quantity",
                "item__unit", "batch_number", "expiry_date")
    )
    total_value = sum(
        float((a.purchase_cost or 0))
        for a in Asset.objects.filter(current_location=loc, is_active=True)
    )
    return Response({
        "location": {
            "id": loc.id, "code": loc.code, "name": loc.name,
            "location_type": loc.location_type,
            "department": loc.department.name if loc.department else None,
            "parent": loc.parent.name if loc.parent else None,
        },
        "assets": assets, "assets_count": len(assets),
        "stock": stock, "stock_count": len(stock),
        "total_value": total_value,
    })


# ---------------- Department summary ----------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def department_summary(request, pk):
    try:
        d = Department.objects.get(pk=pk)
    except Department.DoesNotExist:
        return Response({"detail": "not found"}, status=404)
    locs = Location.objects.filter(department=d)
    assets = Asset.objects.filter(current_location__department=d, is_active=True)
    by_condition = dict(
        assets.values_list("condition").annotate(c=Count("id")).values_list("condition", "c")
    )
    by_status = dict(
        assets.values_list("status").annotate(c=Count("id")).values_list("status", "c")
    )
    total_value = assets.aggregate(v=Sum("purchase_cost"))["v"] or 0
    return Response({
        "department": {"id": d.id, "code": d.code, "name": d.name,
                       "description": d.description, "is_active": d.is_active},
        "locations": list(locs.values("id", "code", "name", "location_type")),
        "asset_count": assets.count(),
        "asset_value": float(total_value),
        "by_condition": by_condition,
        "by_status": by_status,
    })


# ---------------- Bulk asset operations ----------------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bulk_transfer_assets(request):
    ids = request.data.get("asset_ids") or []
    to_id = request.data.get("to_location")
    notes = request.data.get("notes") or "Bulk transfer"
    if not ids or not to_id:
        return Response({"detail": "asset_ids and to_location required"}, status=400)
    try:
        dst = Location.objects.get(pk=to_id)
    except Location.DoesNotExist:
        return Response({"detail": "to_location not found"}, status=404)
    moved = 0
    with transaction.atomic():
        for a in Asset.objects.filter(pk__in=ids):
            old = a.current_location
            a.current_location = dst
            a.save(update_fields=["current_location"])
            Movement.objects.create(
                movement_type="TRANSFER", item=a.item, asset=a,
                from_location=old, to_location=dst,
                quantity=Decimal("1"), actor=request.user, notes=notes,
            )
            moved += 1
    return Response({"ok": True, "moved": moved})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bulk_status_assets(request):
    ids = request.data.get("asset_ids") or []
    status = request.data.get("status")
    condition = request.data.get("condition")
    if not ids:
        return Response({"detail": "asset_ids required"}, status=400)
    upd = 0
    with transaction.atomic():
        qs = Asset.objects.filter(pk__in=ids)
        if status:
            upd += qs.update(status=status)
        if condition:
            upd += qs.update(condition=condition)
    return Response({"ok": True, "updated": upd})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bulk_maintenance_assets(request):
    ids = request.data.get("asset_ids") or []
    description = request.data.get("description") or "Scheduled maintenance"
    cost = request.data.get("cost") or 0
    today = timezone.now().date()
    if not ids:
        return Response({"detail": "asset_ids required"}, status=400)
    created = 0
    with transaction.atomic():
        for a in Asset.objects.filter(pk__in=ids):
            MaintenanceLog.objects.create(
                asset=a, description=description,
                performed_at=today, cost=cost,
                performed_by=(request.user.get_full_name() or request.user.username),
            )
            a.status = "MAINTENANCE"
            a.save(update_fields=["status"])
            created += 1
    return Response({"ok": True, "created": created})


# ---------------- Extended dashboard ----------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_v2(request):
    today = timezone.now().date()

    total_assets = Asset.objects.filter(is_active=True).count()
    by_status = dict(
        Asset.objects.filter(is_active=True)
        .values_list("status").annotate(c=Count("id")).values_list("status", "c")
    )
    by_condition = dict(
        Asset.objects.filter(is_active=True)
        .values_list("condition").annotate(c=Count("id")).values_list("condition", "c")
    )
    asset_value = Asset.objects.filter(is_active=True).aggregate(v=Sum("purchase_cost"))["v"] or 0

    # Asset count by department (for clickthrough)
    by_dept = list(
        Asset.objects.filter(is_active=True)
        .values("current_location__department__id", "current_location__department__name")
        .annotate(count=Count("id"), value=Sum("purchase_cost"))
        .values("current_location__department__id", "current_location__department__name",
                "count", "value")
    )

    # Low stock
    low_stock = []
    for sl in StockLevel.objects.select_related("item", "location"):
        if sl.item.min_stock and (sl.quantity or 0) < sl.item.min_stock:
            low_stock.append({
                "item_id": sl.item_id,
                "item_code": sl.item.code,
                "item_name": sl.item.name,
                "location_code": sl.location.code,
                "quantity": float(sl.quantity or 0),
                "min_stock": float(sl.item.min_stock),
                "unit": sl.item.unit,
                "shortfall": float(sl.item.min_stock - (sl.quantity or 0)),
            })
    low_stock.sort(key=lambda r: -r["shortfall"])

    # Recent movements
    recent = list(
        Movement.objects.order_by("-occurred_at")[:12]
        .values("id", "movement_type", "item__code", "item__name",
                "from_location__code", "to_location__code",
                "quantity", "occurred_at", "actor__username")
    )

    return Response({
        "total_assets": total_assets,
        "by_status": by_status,
        "by_condition": by_condition,
        "asset_value": float(asset_value),
        "assets_by_department": by_dept,
        "low_stock": low_stock[:20],
        "low_stock_count": len(low_stock),
        "recent_movements": recent,
    })
