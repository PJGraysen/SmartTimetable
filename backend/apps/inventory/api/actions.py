
from decimal import Decimal

from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.inventory.models import Item, Asset, Location, StockLevel, Movement


def _qty(value):
    try:
        return Decimal(str(value))
    except Exception:
        return None


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def receive_stock(request):
    item_id = request.data.get("item")
    location_id = request.data.get("location")
    qty = _qty(request.data.get("quantity"))
    batch = request.data.get("batch_number") or ""
    notes = request.data.get("notes") or ""
    reference = request.data.get("reference") or ""

    if not all([item_id, location_id]) or qty is None or qty <= 0:
        return Response({"detail": "item, location, positive quantity required"}, status=400)

    with transaction.atomic():
        item = Item.objects.get(pk=item_id)
        location = Location.objects.get(pk=location_id)
        sl, _ = StockLevel.objects.get_or_create(
            item=item, location=location, batch_number=batch,
            defaults={"quantity": Decimal("0")},
        )
        sl.quantity = (sl.quantity or Decimal("0")) + qty
        sl.save(update_fields=["quantity"])
        Movement.objects.create(
            movement_type="RECEIPT", item=item, to_location=location,
            quantity=qty, actor=request.user, reference=reference, notes=notes,
        )
    return Response({"ok": True, "new_quantity": float(sl.quantity)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def issue_stock(request):
    item_id = request.data.get("item")
    location_id = request.data.get("location")
    qty = _qty(request.data.get("quantity"))
    batch = request.data.get("batch_number") or ""
    recipient = request.data.get("recipient") or ""
    notes = request.data.get("notes") or ""

    if not all([item_id, location_id]) or qty is None or qty <= 0:
        return Response({"detail": "item, location, positive quantity required"}, status=400)

    with transaction.atomic():
        item = Item.objects.get(pk=item_id)
        location = Location.objects.get(pk=location_id)
        sl = StockLevel.objects.filter(
            item=item, location=location, batch_number=batch,
        ).first()
        have = float(sl.quantity) if sl and sl.quantity else 0
        if sl is None or (sl.quantity or 0) < qty:
            return Response(
                {"detail": f"insufficient stock (have {have}, need {float(qty)})"},
                status=400,
            )
        sl.quantity = sl.quantity - qty
        sl.save(update_fields=["quantity"])
        Movement.objects.create(
            movement_type="ISSUE", item=item, from_location=location,
            quantity=qty, actor=request.user, recipient=recipient, notes=notes,
        )
    return Response({"ok": True, "new_quantity": float(sl.quantity)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def transfer_stock(request):
    item_id = request.data.get("item")
    from_id = request.data.get("from_location")
    to_id = request.data.get("to_location")
    qty = _qty(request.data.get("quantity"))
    batch = request.data.get("batch_number") or ""
    notes = request.data.get("notes") or ""

    if not all([item_id, from_id, to_id]) or qty is None or qty <= 0:
        return Response({"detail": "item, from_location, to_location, positive quantity required"}, status=400)
    if str(from_id) == str(to_id):
        return Response({"detail": "source and destination must differ"}, status=400)

    with transaction.atomic():
        item = Item.objects.get(pk=item_id)
        src = Location.objects.get(pk=from_id)
        dst = Location.objects.get(pk=to_id)
        sl_src = StockLevel.objects.filter(
            item=item, location=src, batch_number=batch,
        ).first()
        if sl_src is None or (sl_src.quantity or 0) < qty:
            return Response({"detail": "insufficient stock at source"}, status=400)
        sl_src.quantity = sl_src.quantity - qty
        sl_src.save(update_fields=["quantity"])
        sl_dst, _ = StockLevel.objects.get_or_create(
            item=item, location=dst, batch_number=batch,
            defaults={"quantity": Decimal("0")},
        )
        sl_dst.quantity = (sl_dst.quantity or Decimal("0")) + qty
        sl_dst.save(update_fields=["quantity"])
        Movement.objects.create(
            movement_type="TRANSFER", item=item,
            from_location=src, to_location=dst,
            quantity=qty, actor=request.user, notes=notes,
        )
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def move_asset(request):
    asset_id = request.data.get("asset")
    to_id = request.data.get("to_location")
    notes = request.data.get("notes") or ""

    if not all([asset_id, to_id]):
        return Response({"detail": "asset, to_location required"}, status=400)

    with transaction.atomic():
        asset = Asset.objects.select_related("current_location").get(pk=asset_id)
        dst = Location.objects.get(pk=to_id)
        old = asset.current_location
        asset.current_location = dst
        asset.save(update_fields=["current_location"])
        Movement.objects.create(
            movement_type="TRANSFER", item=asset.item, asset=asset,
            from_location=old, to_location=dst, quantity=Decimal("1"),
            actor=request.user, notes=notes,
        )
    return Response({"ok": True})
