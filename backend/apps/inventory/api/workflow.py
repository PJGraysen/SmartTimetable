
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum, Count, Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.inventory.models import (
    Item, Asset, Location, Department, Category, Supplier,
    StockLevel, Movement, MaintenanceLog, AuditSession, AuditLine,
)


# ================= RETIRE / UNRETIRE ITEMS =================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def retire_item(request, pk):
    try:
        it = Item.objects.get(pk=pk)
    except Item.DoesNotExist:
        return Response({"detail": "not found"}, status=404)
    reason = request.data.get("reason") or "Retired"
    it.is_retired = True
    it.retired_at = timezone.now()
    it.retired_by = request.user
    it.retirement_reason = reason
    it.save(update_fields=["is_retired", "retired_at", "retired_by", "retirement_reason"])
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def unretire_item(request, pk):
    try:
        it = Item.objects.get(pk=pk)
    except Item.DoesNotExist:
        return Response({"detail": "not found"}, status=404)
    it.is_retired = False
    it.retired_at = None
    it.retired_by = None
    it.retirement_reason = ""
    it.save(update_fields=["is_retired", "retired_at", "retired_by", "retirement_reason"])
    return Response({"ok": True})


# ================= QUICK-ADD ITEM (auto asset for INDIVIDUAL) =================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def quick_add_item(request):
    data = request.data
    code = (data.get("code") or "").strip()
    name = (data.get("name") or "").strip()
    if not code or not name:
        return Response({"detail": "code and name required"}, status=400)
    if Item.objects.filter(code=code).exists():
        return Response({"detail": "code already exists"}, status=409)

    category_id = data.get("category")
    department_id = data.get("department")
    tracking = data.get("tracking_mode") or "INDIVIDUAL"
    unit = data.get("unit") or "pcs"
    unit_cost = data.get("unit_cost") or 0
    min_stock = data.get("min_stock") or 0
    reorder_stock = data.get("reorder_stock") or 0
    description = data.get("description") or ""
    supplier_id = data.get("default_supplier")
    location_id = data.get("initial_location")
    quantity = int(data.get("initial_quantity") or 0)
    tag_prefix = data.get("tag_prefix") or code[:4].upper()

    with transaction.atomic():
        item = Item.objects.create(
            code=code, name=name,
            category_id=category_id,
            department_id=department_id or None,
            tracking_mode=tracking,
            unit=unit, unit_cost=unit_cost,
            min_stock=min_stock, reorder_stock=reorder_stock,
            description=description,
            default_supplier_id=supplier_id or None,
            is_active=True,
        )
        created_assets = 0
        created_stock = 0

        if tracking == "INDIVIDUAL" and location_id and quantity > 0:
            for i in range(1, quantity + 1):
                tag = f"{tag_prefix}-{i:04d}"
                if Asset.objects.filter(tag=tag).exists():
                    continue
                Asset.objects.create(
                    tag=tag, item=item,
                    current_location_id=location_id,
                    condition="NEW", status="AVAILABLE",
                    purchase_date=timezone.now().date(),
                    purchase_cost=unit_cost,
                    supplier_id=supplier_id or None,
                )
                created_assets += 1

        elif tracking == "QUANTITY" and location_id and quantity > 0:
            StockLevel.objects.create(
                item=item, location_id=location_id,
                quantity=Decimal(str(quantity)),
            )
            created_stock = 1
            Movement.objects.create(
                movement_type="RECEIPT", item=item,
                to_location_id=location_id,
                quantity=Decimal(str(quantity)),
                actor=request.user, reason="Initial stock on item creation",
            )

    return Response({
        "ok": True, "item_id": item.id,
        "assets_created": created_assets,
        "stock_created": created_stock,
    })


# ================= QUICK-ADD STOCK =================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def quick_add_stock(request):
    data = request.data
    item_id = data.get("item")
    location_id = data.get("location")
    qty = data.get("quantity")
    batch = data.get("batch_number") or ""
    expiry = data.get("expiry_date") or None
    reason = data.get("reason") or "Initial stock"

    if not item_id or not location_id or not qty:
        return Response({"detail": "item, location, quantity required"}, status=400)

    with transaction.atomic():
        item = Item.objects.get(pk=item_id)
        loc = Location.objects.get(pk=location_id)
        sl, created = StockLevel.objects.get_or_create(
            item=item, location=loc, batch_number=batch,
            defaults={"quantity": Decimal(str(qty))},
        )
        if not created:
            sl.quantity = (sl.quantity or Decimal("0")) + Decimal(str(qty))
            sl.save(update_fields=["quantity"])
        if expiry:
            sl.expiry_date = expiry
            sl.save(update_fields=["expiry_date"])
        Movement.objects.create(
            movement_type="RECEIPT", item=item, to_location=loc,
            quantity=Decimal(str(qty)), actor=request.user, reason=reason,
        )
    return Response({"ok": True, "stock_id": sl.id, "quantity": float(sl.quantity)})


# ================= MAINTENANCE WORKFLOW =================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def maintenance_report(request):
    data = request.data
    asset_id = data.get("asset")
    description = data.get("description")
    remedy = data.get("remedy") or ""
    cost = data.get("cost") or 0
    priority = data.get("priority") or "NORMAL"
    if not asset_id or not description:
        return Response({"detail": "asset and description required"}, status=400)
    try:
        asset = Asset.objects.get(pk=asset_id)
    except Asset.DoesNotExist:
        return Response({"detail": "asset not found"}, status=404)

    log = MaintenanceLog.objects.create(
        asset=asset,
        description=description,
        remedy=remedy,
        cost=cost,
        priority=priority,
        approval_status="PENDING",
        reported_by=request.user,
        performed_by=(request.user.get_full_name() or request.user.username),
    )
    return Response({"ok": True, "log_id": log.id})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def maintenance_approve(request, pk):
    try:
        log = MaintenanceLog.objects.get(pk=pk)
    except MaintenanceLog.DoesNotExist:
        return Response({"detail": "not found"}, status=404)
    note = request.data.get("note") or ""
    log.approval_status = "APPROVED"
    log.approved_by = request.user
    log.approved_at = timezone.now()
    log.approval_note = note
    log.save(update_fields=["approval_status", "approved_by", "approved_at", "approval_note"])

    # Mark asset as under maintenance
    asset = log.asset
    asset.status = "MAINTENANCE"
    asset.save(update_fields=["status"])
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def maintenance_reject(request, pk):
    try:
        log = MaintenanceLog.objects.get(pk=pk)
    except MaintenanceLog.DoesNotExist:
        return Response({"detail": "not found"}, status=404)
    note = request.data.get("note") or ""
    log.approval_status = "REJECTED"
    log.approved_by = request.user
    log.approved_at = timezone.now()
    log.approval_note = note
    log.save(update_fields=["approval_status", "approved_by", "approved_at", "approval_note"])
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def maintenance_complete(request, pk):
    try:
        log = MaintenanceLog.objects.get(pk=pk)
    except MaintenanceLog.DoesNotExist:
        return Response({"detail": "not found"}, status=404)
    log.approval_status = "COMPLETED"
    log.performed_at = timezone.now().date()
    log.save(update_fields=["approval_status", "performed_at"])
    asset = log.asset
    asset.status = "AVAILABLE"
    asset.condition = "GOOD"
    asset.save(update_fields=["status", "condition"])
    return Response({"ok": True})


# ================= NOTIFICATIONS FOR DASHBOARD =================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def notifications(request):
    today = timezone.now().date()
    soon = today + timedelta(days=30)
    out = []

    # Low stock
    for sl in StockLevel.objects.select_related("item", "location"):
        if sl.item.min_stock and (sl.quantity or 0) < sl.item.min_stock:
            out.append({
                "type": "LOW_STOCK", "severity": "HIGH",
                "title": f"Low stock: {sl.item.name}",
                "message": f"{sl.location.code} has {sl.quantity} {sl.item.unit} (min {sl.item.min_stock})",
                "link": "/inventory/reports",
            })

    # Pending maintenance
    pend = MaintenanceLog.objects.filter(approval_status="PENDING").count()
    if pend:
        out.append({
            "type": "MAINTENANCE", "severity": "MEDIUM",
            "title": f"{pend} maintenance request(s) pending approval",
            "message": "Review and approve or reject",
            "link": "/inventory/maintenance",
        })

    # Warranty expiring
    war = Asset.objects.filter(
        is_active=True, warranty_expiry__gte=today, warranty_expiry__lte=soon,
    ).count()
    if war:
        out.append({
            "type": "WARRANTY", "severity": "LOW",
            "title": f"{war} warranty expiring in 30 days",
            "message": "Review warranties",
            "link": "/inventory/assets",
        })

    # Expiring stock
    exp = StockLevel.objects.filter(expiry_date__gte=today, expiry_date__lte=soon).count()
    if exp:
        out.append({
            "type": "EXPIRING", "severity": "MEDIUM",
            "title": f"{exp} batch(es) expiring in 30 days",
            "message": "Review expiring stock",
            "link": "/inventory/reports",
        })

    return Response({"notifications": out, "count": len(out)})


# ================= COMPREHENSIVE REPORT =================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def comprehensive_report(request):
    """One payload with everything for the Reports page."""
    depts = list(Department.objects.filter(is_active=True).values("id", "code", "name"))
    cat_summary = list(
        Item.objects.filter(is_active=True, is_retired=False)
        .values("category__name")
        .annotate(count=Count("id"), value=Sum("unit_cost"))
        .values("category__name", "count", "value")
    )
    dept_summary = list(
        Asset.objects.filter(is_active=True, current_location__department__isnull=False)
        .values("current_location__department__id", "current_location__department__name")
        .annotate(assets=Count("id"), value=Sum("purchase_cost"))
        .values("current_location__department__id", "current_location__department__name",
                "assets", "value")
    )
    supplier_summary = list(
        Item.objects.filter(default_supplier__isnull=False)
        .values("default_supplier__name")
        .annotate(items=Count("id"))
        .values("default_supplier__name", "items")
    )
    totals = {
        "items_active": Item.objects.filter(is_active=True, is_retired=False).count(),
        "items_retired": Item.objects.filter(is_retired=True).count(),
        "assets": Asset.objects.filter(is_active=True).count(),
        "assets_value": float(Asset.objects.filter(is_active=True).aggregate(v=Sum("purchase_cost"))["v"] or 0),
        "locations": Location.objects.filter(is_active=True).count(),
        "departments": Department.objects.filter(is_active=True).count(),
        "suppliers": Supplier.objects.filter(is_active=True).count(),
    }
    return Response({
        "totals": totals,
        "items_by_category": cat_summary,
        "assets_by_department": dept_summary,
        "items_by_supplier": supplier_summary,
        "departments": depts,
    })


# ================= SUPPLIER CONTACT LOG =================

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def supplier_log_contact(request, pk):
    try:
        s = Supplier.objects.get(pk=pk)
    except Supplier.DoesNotExist:
        return Response({"detail": "not found"}, status=404)
    method = request.data.get("method") or "note"
    note = request.data.get("note") or ""
    # Just log as a Movement-adjacent note. Store in supplier notes.
    stamp = timezone.now().strftime("%Y-%m-%d %H:%M")
    s.notes = (s.notes or "") + f"\n[{stamp} {method}] {note}"
    s.save(update_fields=["notes"])
    return Response({"ok": True})
