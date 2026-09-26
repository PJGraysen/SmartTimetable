"""Mobile inventory audit — service layer."""
from __future__ import annotations
from django.db import transaction
from django.utils import timezone
from apps.library.models import Copy, InventoryAudit, InventoryAuditLine


@transaction.atomic
def start_audit(*, scope="FULL", shelf=None, user=None):
    audit = InventoryAudit.objects.create(scope=scope, shelf=shelf, started_by=user)
    qs = Copy.objects.all()
    if scope == "SHELF" and shelf is not None:
        qs = qs.filter(shelf=shelf)
    lines = []
    for c in qs.select_related("shelf"):
        lines.append(InventoryAuditLine(
            audit=audit, copy=c, barcode_scanned="",
            expected_shelf=(c.shelf.code if c.shelf else ""),
            result=InventoryAuditLine.Result.MISSING,
        ))
    InventoryAuditLine.objects.bulk_create(lines)
    audit.total_expected = len(lines)
    audit.save(update_fields=["total_expected"])
    return audit


@transaction.atomic
def scan_barcode(*, audit, barcode, user=None):
    barcode = (barcode or "").strip()
    copy = Copy.objects.filter(barcode=barcode).select_related("shelf").first()
    now = timezone.now()
    if copy is None:
        return InventoryAuditLine.objects.create(
            audit=audit, copy=None, barcode_scanned=barcode,
            scanned_at=now, result=InventoryAuditLine.Result.UNKNOWN,
        )
    line = audit.lines.filter(copy=copy).first()
    expected = copy.shelf.code if copy.shelf else ""
    result = InventoryAuditLine.Result.MATCH
    if audit.scope == "SHELF" and audit.shelf and copy.shelf_id != audit.shelf_id:
        result = InventoryAuditLine.Result.MISPLACED
    if line is None:
        return InventoryAuditLine.objects.create(
            audit=audit, copy=copy, barcode_scanned=barcode,
            expected_shelf=expected, scanned_at=now, result=result,
        )
    line.barcode_scanned = barcode
    line.scanned_at = now
    line.result = result
    line.save(update_fields=["barcode_scanned", "scanned_at", "result"])
    return line


@transaction.atomic
def finish_audit(*, audit, user=None):
    audit.status = InventoryAudit.Status.FINISHED
    audit.finished_at = timezone.now()
    audit.total_scanned = audit.lines.exclude(scanned_at=None).count()
    audit.total_missing = audit.lines.filter(result=InventoryAuditLine.Result.MISSING).count()
    audit.total_misplaced = audit.lines.filter(result=InventoryAuditLine.Result.MISPLACED).count()
    audit.save(update_fields=[
        "status", "finished_at", "total_scanned",
        "total_missing", "total_misplaced",
    ])
    return audit
