from __future__ import annotations

from decimal import Decimal

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from apps.library.api.permissions import LibraryModelPermissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.library.models import (
    Author, Book, Category, Copy, Loan, LoanRule, Member, Publisher, Shelf,
)
from apps.library.services.audit import log_library_action
from apps.library.services.loans import LoanError, issue_loan, renew_loan, return_loan
from apps.library.api import serializers as s


def _require(request, codename):
    if not request.user.has_perm(codename):
        raise PermissionDenied(f"Missing permission: {codename}")


class BaseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, LibraryModelPermissions]


class BookViewSet(BaseViewSet):
    queryset = Book.objects.all()
    serializer_class = s.BookSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(
                Q(title__icontains=q) | Q(isbn__icontains=q) | Q(authors__name__icontains=q)
            )
        subject = self.request.query_params.get("subject")
        if subject:
            qs = qs.filter(subjects__code=subject)
        return qs.distinct()

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])

    @action(detail=True, methods=["get", "post"])
    def copies(self, request, pk=None):
        book = self.get_object()
        if request.method == "GET":
            qs = book.copies.all()
            return Response(s.CopySerializer(qs, many=True).data)
        _require(request, "library.add_book")
        ser = s.CopySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        copy = ser.save(book=book)
        log_library_action(
            user=request.user,
            action="library.copy.create",
            entity_type="Copy",
            entity_id=str(copy.id),
            description=f"Added copy {copy.barcode} to book {book.title}",
        )
        return Response(s.CopySerializer(copy).data, status=201)


class AuthorViewSet(BaseViewSet):
    queryset = Author.objects.all()
    serializer_class = s.AuthorSerializer


class PublisherViewSet(BaseViewSet):
    queryset = Publisher.objects.all()
    serializer_class = s.PublisherSerializer


class CategoryViewSet(BaseViewSet):
    queryset = Category.objects.all()
    serializer_class = s.CategorySerializer


class ShelfViewSet(BaseViewSet):
    queryset = Shelf.objects.all()
    serializer_class = s.ShelfSerializer


class CopyViewSet(BaseViewSet):
    queryset = Copy.objects.all()
    serializer_class = s.CopySerializer

    def get_queryset(self):
        qs = super().get_queryset()
        st = self.request.query_params.get("status")
        if st:
            qs = qs.filter(status=st)
        book = self.request.query_params.get("book")
        if book:
            qs = qs.filter(book_id=book)
        return qs

    @action(detail=False, methods=["get"], url_path=r"by-barcode/(?P<barcode>[^/]+)")
    def by_barcode(self, request, barcode=None):
        copy = get_object_or_404(Copy, barcode=barcode)
        return Response(s.CopySerializer(copy).data)


class MemberViewSet(BaseViewSet):
    queryset = Member.objects.all()
    serializer_class = s.MemberSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(
                Q(full_name__icontains=q)
                | Q(member_number__icontains=q)
                | Q(email__icontains=q)
            )
        t = self.request.query_params.get("type")
        if t:
            qs = qs.filter(member_type=t)
        return qs

    @action(detail=True, methods=["get"])
    def loans(self, request, pk=None):
        member = self.get_object()
        return Response(s.LoanSerializer(member.loans.all().order_by("-issued_at"), many=True).data)

    @action(detail=True, methods=["post"])
    def disable(self, request, pk=None):
        _require(request, "library.change_member")
        member = self.get_object()
        member.is_active = False
        member.save(update_fields=["is_active", "updated_at"])
        return Response(s.MemberSerializer(member).data)


class LoanRuleViewSet(BaseViewSet):
    queryset = LoanRule.objects.all()
    serializer_class = s.LoanRuleSerializer


class LoanViewSet(BaseViewSet):
    queryset = Loan.objects.all()
    serializer_class = s.LoanSerializer

    def get_permissions(self):
        if self.action in ("issue", "do_return", "renew", "waive_fine", "pay_fine"):
            return [IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        st = self.request.query_params.get("status")
        if st:
            qs = qs.filter(status=st)
        member = self.request.query_params.get("member")
        if member:
            qs = qs.filter(member_id=member)
        return qs

    @action(detail=False, methods=["post"])
    def issue(self, request):
        _require(request, "library.issue_loan")
        copy_id = request.data.get("copy")
        member_id = request.data.get("member")
        copy = get_object_or_404(Copy, id=copy_id)
        member = get_object_or_404(Member, id=member_id)
        try:
            loan = issue_loan(copy=copy, member=member, issued_by=request.user)
        except LoanError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(s.LoanSerializer(loan).data, status=201)

    @action(detail=True, methods=["post"], url_path="return")
    def do_return(self, request, pk=None):
        _require(request, "library.return_loan")
        loan = self.get_object()
        try:
            loan = return_loan(loan=loan, received_by=request.user)
        except LoanError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(s.LoanSerializer(loan).data)

    @action(detail=True, methods=["post"])
    def renew(self, request, pk=None):
        _require(request, "library.renew_loan")
        loan = self.get_object()
        try:
            loan = renew_loan(loan=loan, by_user=request.user)
        except LoanError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(s.LoanSerializer(loan).data)

    @action(detail=True, methods=["post"], url_path="waive-fine")
    def waive_fine(self, request, pk=None):
        _require(request, "library.manage_fines")
        loan = self.get_object()
        loan.fine_paid = loan.fine_accrued
        loan.save(update_fields=["fine_paid", "updated_at"])
        log_library_action(
            user=request.user,
            action="library.fine.waive",
            entity_type="Loan",
            entity_id=str(loan.id),
            description=f"Waived fine {loan.fine_accrued}",
        )
        return Response(s.LoanSerializer(loan).data)

    @action(detail=True, methods=["post"], url_path="pay-fine")
    def pay_fine(self, request, pk=None):
        _require(request, "library.manage_fines")
        loan = self.get_object()
        amount = Decimal(str(request.data.get("amount") or 0))
        loan.fine_paid = loan.fine_paid + amount
        loan.save(update_fields=["fine_paid", "updated_at"])
        log_library_action(
            user=request.user,
            action="library.fine.pay",
            entity_type="Loan",
            entity_id=str(loan.id),
            description=f"Recorded payment {amount}",
        )
        return Response(s.LoanSerializer(loan).data)


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        return Response({
            "total_books": Book.objects.filter(is_active=True).count(),
            "total_copies": Copy.objects.count(),
            "available_copies": Copy.objects.filter(status=Copy.Status.AVAILABLE).count(),
            "issued_copies": Copy.objects.filter(status=Copy.Status.ISSUED).count(),
            "active_loans": Loan.objects.filter(status=Loan.Status.ACTIVE).count(),
            "overdue_loans": Loan.objects.filter(
                status=Loan.Status.ACTIVE, due_at__lt=now,
            ).count(),
            "active_members": Member.objects.filter(is_active=True).count(),
        })


class CirculationReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from datetime import timedelta
        since = timezone.now() - timedelta(days=30)
        loans = Loan.objects.filter(issued_at__gte=since)
        return Response({
            "period_days": 30,
            "loans_issued": loans.count(),
            "loans_returned": loans.filter(returned_at__isnull=False).count(),
        })


class OverdueReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        qs = Loan.objects.filter(
            status=Loan.Status.ACTIVE, due_at__lt=now,
        ).order_by("due_at")
        return Response(s.LoanSerializer(qs, many=True).data)


class InventoryReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        by_status = Copy.objects.values("status").annotate(count=Count("id"))
        return Response({"by_status": list(by_status)})


class TopBorrowersReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Member.objects.annotate(
            loan_count=Count("loans"),
        ).order_by("-loan_count")[:20]
        return Response([
            {
                "id": str(m.id),
                "member_number": m.member_number,
                "full_name": m.full_name,
                "loan_count": m.loan_count,
            }
            for m in qs
        ])


# =========================================================================
# PHASE 2 views
# =========================================================================
from apps.library.models import (
    FinePayment as _FinePayment,
    ReadingList as _ReadingList,
    Reservation as _Reservation,
)
from apps.library.services import fines as _fines
from apps.library.services import reservations as _res
from apps.library.api.serializers import (
    FinePaymentSerializer,
    MemberWithStatusSerializer,
    ReadingListSerializer,
    ReservationSerializer,
)


class ReservationViewSet(BaseViewSet):
    queryset = _Reservation.objects.all()
    serializer_class = ReservationSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        st = self.request.query_params.get("status")
        if st:
            qs = qs.filter(status=st)
        member = self.request.query_params.get("member")
        if member:
            qs = qs.filter(member_id=member)
        return qs

    @action(detail=False, methods=["post"])
    def create_for(self, request):
        _require(request, "library.manage_reservations")
        book = get_object_or_404(Book, id=request.data.get("book"))
        member = get_object_or_404(Member, id=request.data.get("member"))
        try:
            r = _res.create_reservation(book=book, member=member, by_user=request.user)
        except _res.ReservationError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(ReservationSerializer(r).data, status=201)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        _require(request, "library.manage_reservations")
        r = self.get_object()
        r = _res.cancel_reservation(reservation=r, by_user=request.user)
        return Response(ReservationSerializer(r).data)

    @action(detail=True, methods=["post"])
    def fulfill(self, request, pk=None):
        _require(request, "library.fulfill_reservation")
        r = self.get_object()
        r.status = _Reservation.Status.FULFILLED
        r.save(update_fields=["status", "updated_at"])
        return Response(ReservationSerializer(r).data)


class FinePaymentViewSet(BaseViewSet):
    queryset = _FinePayment.objects.all()
    serializer_class = FinePaymentSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        loan = self.request.query_params.get("loan")
        if loan:
            qs = qs.filter(loan_id=loan)
        return qs

    @action(detail=False, methods=["post"])
    def record(self, request):
        _require(request, "library.record_fine_payment")
        loan = get_object_or_404(Loan, id=request.data.get("loan"))
        amount = Decimal(str(request.data.get("amount") or 0))
        kind = str(request.data.get("kind") or "PAYMENT").upper()
        reason = str(request.data.get("reason") or "")
        try:
            if kind == "WAIVER":
                p = _fines.waive_remaining(loan=loan, by_user=request.user, reason=reason)
            else:
                p = _fines.record_payment(loan=loan, amount=amount, by_user=request.user, reason=reason)
        except _fines.FineError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(FinePaymentSerializer(p).data, status=201)


class ReadingListViewSet(BaseViewSet):
    queryset = _ReadingList.objects.all()
    serializer_class = ReadingListSerializer


class MemberDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        member = get_object_or_404(Member, id=pk)
        return Response(MemberWithStatusSerializer(member).data)


class BulkImportView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        _require(request, "library.import_catalogue")
        upload = request.FILES.get("file")
        if upload is None:
            return Response({"detail": "No file uploaded."}, status=400)
        import tempfile, os, subprocess, sys
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            for chunk in upload.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name
        dry = str(request.data.get("dry_run", "")).lower() in ("1", "true", "yes")
        try:
            from io import StringIO
            from django.core.management import call_command
            buf = StringIO()
            args = [tmp_path]
            if dry:
                args.append("--dry-run")
            call_command("import_catalogue", *args, stdout=buf, stderr=buf)
            output = buf.getvalue()
        finally:
            try: os.unlink(tmp_path)
            except Exception: pass
        return Response({"output": output})


# ---------- Extra reports ----------
class StudentLoansReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, member_id):
        member = get_object_or_404(Member, id=member_id)
        loans = Loan.objects.filter(member=member).order_by("-issued_at")
        return Response(s.LoanSerializer(loans, many=True).data)


class BookLoansReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, book_id):
        book = get_object_or_404(Book, id=book_id)
        loans = Loan.objects.filter(copy__book=book).order_by("-issued_at")
        return Response(s.LoanSerializer(loans, many=True).data)


class SubjectBreakdownReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Count
        rows = (
            Book.objects
            .filter(is_active=True)
            .values("subjects__code", "subjects__name")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        return Response([
            {"subject_code": r["subjects__code"], "subject_name": r["subjects__name"], "count": r["count"]}
            for r in rows
        ])


class CategoryBreakdownReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Count
        rows = (
            Book.objects
            .filter(is_active=True)
            .values("categories__name", "categories__code")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        return Response([
            {"category_code": r["categories__code"], "category_name": r["categories__name"], "count": r["count"]}
            for r in rows
        ])


class ActivityFeedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.audit.models import AuditLog
        logs = (
            AuditLog.objects
            .filter(action__startswith="library.")
            .select_related("user")
            .order_by("-created_at")[:30]
        )
        return Response([
            {
                "id": str(l.id),
                "action": l.action,
                "description": l.description,
                "user": l.user.get_username() if l.user else None,
                "created_at": l.created_at,
            }
            for l in logs
        ])


class PopularTitlesReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Count
        rows = (
            Book.objects
            .annotate(loan_count=Count("copies__loans"))
            .filter(loan_count__gt=0)
            .order_by("-loan_count")[:20]
        )
        return Response([
            {"id": str(b.id), "title": b.title, "loan_count": b.loan_count}
            for b in rows
        ])


class AcquisitionReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models.functions import TruncMonth
        from django.db.models import Count, Sum
        rows = (
            Copy.objects
            .filter(acquired_at__isnull=False)
            .annotate(month=TruncMonth("acquired_at"))
            .values("month")
            .annotate(count=Count("id"), total_cost=Sum("acquisition_cost"))
            .order_by("-month")
        )
        return Response([
            {"month": r["month"], "count": r["count"], "total_cost": str(r["total_cost"] or 0)}
            for r in rows
        ])


class DamageReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Copy.objects.filter(status__in=[Copy.Status.DAMAGED, Copy.Status.LOST, Copy.Status.REPAIR]).select_related("book")
        return Response([
            {"id": str(c.id), "barcode": c.barcode, "book": c.book.title, "status": c.status, "condition": c.condition}
            for c in qs
        ])


class BlockedMembersReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.library.services.blocking import is_blocked, overdue_count, total_fines_owed
        blocked = []
        for m in Member.objects.filter(is_active=True):
            if is_blocked(m):
                blocked.append({
                    "id": str(m.id),
                    "member_number": m.member_number,
                    "full_name": m.full_name,
                    "overdue_count": overdue_count(m),
                    "fines_owed": str(total_fines_owed(m)),
                })
        return Response(blocked)


# ---- Cataloguing: ISBN lookup ----
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status as _status

from apps.library.services.book_lookup import lookup_by_isbn


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def book_lookup(request):
    """GET /api/library/catalogue/lookup/?isbn=XXXX"""
    isbn = request.query_params.get("isbn", "").strip()
    if not isbn:
        return Response({"error": "isbn query parameter required"}, status=_status.HTTP_400_BAD_REQUEST)
    result = lookup_by_isbn(isbn)
    if not result:
        return Response({"found": False, "isbn": isbn}, status=_status.HTTP_200_OK)
    return Response({"found": True, **result.to_dict()}, status=_status.HTTP_200_OK)


# ---- Cataloguing: subjects (learning categories) ----
from apps.academics.models import Subject as _Subject
from apps.library.models import Book as _Book


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def subjects_list(request):
    """GET /api/library/catalogue/subjects/ - active subjects for form dropdowns."""
    qs = _Subject.objects.filter(is_active=True).order_by("name")
    return Response({
        "subjects": [
            {"id": str(s.id), "name": s.name, "code": s.code}
            for s in qs
        ]
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def subject_summary(request):
    """GET /api/library/catalogue/subject-summary/

    Per-subject book counts for the library dashboard "Learning Categories".
    """
    rows = []
    for s in _Subject.objects.filter(is_active=True).order_by("name"):
        book_count = _Book.objects.filter(subjects=s, is_active=True).count()
        # Count distinct available copies across those books
        available = 0
        try:
            available = _Book.objects.filter(
                subjects=s, is_active=True, copies__status="AVAILABLE"
            ).distinct().count()
        except Exception:
            available = 0
        rows.append({
            "id": str(s.id),
            "name": s.name,
            "code": s.code,
            "book_count": book_count,
            "available_copies": available,
        })
    return Response({"subjects": rows})


# =====================================================================
# L2 — Circulation quick actions
# =====================================================================
from apps.library.services.loans import issue_loan as _issue_loan
from apps.library.services.loans import return_loan as _return_loan_service


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def self_checkout(request):
    """POST /api/library/circulation/self-checkout/
    Body: { "barcode": "BK-000123", "member_number": "STU-001" }
    """
    barcode = (request.data.get("barcode") or "").strip()
    member_number = (request.data.get("member_number") or "").strip()
    if not barcode or not member_number:
        return Response({"error": "barcode and member_number are required"},
                        status=400)
    copy = Copy.objects.filter(barcode=barcode).select_related("book").first()
    if not copy:
        return Response({"error": f"No copy with barcode {barcode}"}, status=404)
    member = Member.objects.filter(member_number=member_number).first()
    if not member:
        return Response({"error": f"No member with number {member_number}"}, status=404)
    try:
        loan = _issue_loan(copy=copy, member=member, issued_by=request.user)
    except Exception as e:
        return Response({"error": str(e)}, status=409)
    return Response({
        "ok": True,
        "loan_id": str(loan.id),
        "book_title": copy.book.title,
        "member_name": member.full_name,
        "due_at": loan.due_at,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def bulk_return(request):
    """POST /api/library/circulation/bulk-return/
    Body: { "barcodes": ["BK-000123", "BK-000124"] }
    """
    barcodes = request.data.get("barcodes") or []
    if not isinstance(barcodes, list) or not barcodes:
        return Response({"error": "barcodes must be a non-empty list"}, status=400)
    results = []
    for raw in barcodes:
        barcode = str(raw).strip()
        entry = {"barcode": barcode, "ok": False, "error": ""}
        try:
            copy = Copy.objects.filter(barcode=barcode).first()
            if not copy:
                entry["error"] = "copy not found"
                results.append(entry); continue
            loan = Loan.objects.filter(copy=copy, status=Loan.Status.ACTIVE).first()
            if not loan:
                entry["error"] = "no active loan"
                results.append(entry); continue
            _return_loan_service(loan=loan, received_by=request.user)
            entry["ok"] = True
        except Exception as e:
            entry["error"] = str(e)
        results.append(entry)
    ok_count = sum(1 for r in results if r["ok"])
    return Response({"processed": len(results), "succeeded": ok_count, "results": results})


# =====================================================================
# L5 — Catalogue search (facets)
# =====================================================================
from django.db.models import Q as _Q


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def catalogue_search(request):
    """GET /api/library/catalogue/search/
    params: q, subject, author, year_from, year_to, availability
    """
    qs = Book.objects.filter(is_active=True).prefetch_related(
        "authors", "categories", "subjects",
    ).select_related("publisher")

    q = (request.query_params.get("q") or "").strip()
    if q:
        qs = qs.filter(
            _Q(title__icontains=q) | _Q(subtitle__icontains=q) |
            _Q(isbn__icontains=q) | _Q(authors__name__icontains=q) |
            _Q(publisher__name__icontains=q)
        ).distinct()

    subject = (request.query_params.get("subject") or "").strip()
    if subject:
        qs = qs.filter(subjects__code__iexact=subject).distinct()

    author = (request.query_params.get("author") or "").strip()
    if author:
        qs = qs.filter(authors__name__icontains=author).distinct()

    year_from = request.query_params.get("year_from")
    if year_from and str(year_from).isdigit():
        qs = qs.filter(published_year__gte=int(year_from))
    year_to = request.query_params.get("year_to")
    if year_to and str(year_to).isdigit():
        qs = qs.filter(published_year__lte=int(year_to))

    availability = (request.query_params.get("availability") or "").strip().lower()
    if availability == "available":
        qs = qs.filter(copies__status=Copy.Status.AVAILABLE).distinct()

    qs = qs.order_by("title")[:200]

    rows = []
    for b in qs:
        rows.append({
            "id": str(b.id),
            "title": b.title,
            "subtitle": b.subtitle,
            "isbn": b.isbn,
            "published_year": b.published_year,
            "cover_url": b.cover_url,
            "authors": [{"id": str(a.id), "name": a.name} for a in b.authors.all()],
            "subjects": [{"id": str(s.id), "name": s.name, "code": s.code} for s in b.subjects.all()],
            "publisher": b.publisher.name if b.publisher else "",
            "copy_count": b.copies.count(),
            "available_copy_count": b.copies.filter(status=Copy.Status.AVAILABLE).count(),
        })
    return Response({"results": rows, "count": len(rows)})


# =====================================================================
# L7 — Report export (CSV / JSON)
# =====================================================================
import csv as _csv
from django.http import HttpResponse as _HttpResponse
import json as _json


_EXPORT_HANDLERS = {
    "circulation": lambda: _report_circulation_rows(),
    "overdue":     lambda: _report_overdue_rows(),
    "inventory":   lambda: _report_inventory_rows(),
    "popular":     lambda: _report_popular_rows(),
}


def _report_circulation_rows():
    rows = [["loan_id", "issued_at", "due_at", "returned_at", "status",
             "member_number", "member_name", "book_title", "copy_barcode"]]
    for loan in Loan.objects.select_related("member", "copy__book").order_by("-issued_at")[:2000]:
        rows.append([
            str(loan.id), str(loan.issued_at), str(loan.due_at),
            str(loan.returned_at or ""), loan.status,
            loan.member.member_number, loan.member.full_name,
            loan.copy.book.title if loan.copy and loan.copy.book else "",
            loan.copy.barcode if loan.copy else "",
        ])
    return rows


def _report_overdue_rows():
    from django.utils import timezone as _tz
    now = _tz.now()
    rows = [["loan_id", "due_at", "days_overdue", "member_number",
             "member_name", "book_title", "copy_barcode"]]
    for loan in Loan.objects.filter(status=Loan.Status.ACTIVE, due_at__lt=now)                             .select_related("member", "copy__book").order_by("due_at"):
        days = (now - loan.due_at).days
        rows.append([
            str(loan.id), str(loan.due_at), str(days),
            loan.member.member_number, loan.member.full_name,
            loan.copy.book.title if loan.copy and loan.copy.book else "",
            loan.copy.barcode if loan.copy else "",
        ])
    return rows


def _report_inventory_rows():
    rows = [["barcode", "accession_number", "title", "shelf", "status", "condition"]]
    for c in Copy.objects.select_related("book", "shelf").order_by("barcode"):
        rows.append([
            c.barcode, c.accession_number, c.book.title if c.book else "",
            c.shelf.code if c.shelf else "", c.status, c.condition,
        ])
    return rows


def _report_popular_rows():
    from django.db.models import Count as _Count
    rows = [["book_id", "title", "loan_count"]]
    qs = Book.objects.annotate(loan_count=_Count("copies__loans")).order_by("-loan_count")[:100]
    for b in qs:
        rows.append([str(b.id), b.title, str(b.loan_count)])
    return rows


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export_report(request, report_name):
    """GET /api/library/reports/<name>/export/?format=csv|json"""
    handler = _EXPORT_HANDLERS.get(report_name)
    if not handler:
        return Response({"error": f"unknown report: {report_name}"}, status=404)
    rows = handler()
    fmt = (request.query_params.get("format") or "csv").lower()
    if fmt == "json":
        header = rows[0]
        data = [dict(zip(header, r)) for r in rows[1:]]
        return Response({"rows": data, "count": len(data)})
    resp = _HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = f"attachment; filename=library-{report_name}.csv"
    writer = _csv.writer(resp)
    for row in rows:
        writer.writerow(row)
    return resp


# =====================================================================
# L3a — Roster sync
# =====================================================================
from apps.library.services.roster import (
    sync_roster as _sync_roster,
    eligible_people as _eligible_people,
)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def roster_eligible(request):
    """GET /api/library/roster/eligible/ — students/teachers not yet members."""
    return Response(_eligible_people())


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def roster_sync(request):
    """POST /api/library/roster/sync/ — create Member rows from roster."""
    return Response(_sync_roster())


# =====================================================================
# L3c — Inventory link
# =====================================================================
from apps.library.services.inventory_link import (
    register_copy_in_inventory as _register_copy_in_inventory,
    register_all_copies as _register_all_copies,
)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def inventory_register_one(request, pk):
    """POST /api/library/copies/<id>/register-inventory/"""
    copy = Copy.objects.filter(id=pk).first()
    if not copy:
        return Response({"error": "copy not found"}, status=404)
    asset, created = _register_copy_in_inventory(copy)
    return Response({
        "ok": True, "asset_id": str(asset.id), "asset_tag": asset.tag,
        "created": created,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def inventory_register_all(request):
    """POST /api/library/copies/register-all-inventory/"""
    return Response(_register_all_copies())


# =====================================================================
# L3b — Fee account + ledger
# =====================================================================
from apps.finance.services import post_library_fine as _post_fine
from apps.finance.services import post_library_payment as _post_payment
from apps.finance.models import FeeAccount as _FeeAccount


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def member_fee_account(request, member_id):
    """GET /api/library/members/<id>/fee-account/"""
    member = Member.objects.filter(id=member_id).first()
    if not member:
        return Response({"error": "member not found"}, status=404)
    acct, _ = _FeeAccount.objects.get_or_create(member=member)
    entries = [
        {
            "id": str(e.id), "kind": e.kind, "source": e.source,
            "amount": str(e.amount), "description": e.description,
            "recorded_at": e.recorded_at,
        }
        for e in acct.entries.all()[:200]
    ]
    return Response({
        "member_id": str(member.id),
        "member_number": member.member_number,
        "member_name": member.full_name,
        "balance": str(acct.balance),
        "currency": acct.currency,
        "entries": entries,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def post_loan_fine(request, loan_id):
    """POST /api/library/loans/<id>/post-fine/ — body {amount, reason}"""
    from apps.library.models import Loan as _Loan
    loan = _Loan.objects.filter(id=loan_id).first()
    if not loan:
        return Response({"error": "loan not found"}, status=404)
    amount_raw = request.data.get("amount")
    if not amount_raw:
        return Response({"error": "amount required"}, status=400)
    try:
        from decimal import Decimal as _D
        amount = _D(str(amount_raw))
    except Exception:
        return Response({"error": "invalid amount"}, status=400)
    entry = _post_fine(loan=loan, amount=amount, by_user=request.user)
    return Response({
        "ok": True, "entry_id": str(entry.id), "balance_after": str(entry.account.balance),
    })


# =====================================================================
# L4 — DAM
# =====================================================================
from apps.library.models import DigitalAsset as _DA
from apps.library.services.dam import (
    save_asset as _save_asset,
    serve_asset as _serve_asset,
    DAMError as _DAMError,
)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def dam_resources(request):
    """GET  list  | POST upload"""
    if request.method == "GET":
        qs = _DA.objects.filter(is_active=True).select_related("subject", "book", "uploaded_by")
        cat = (request.query_params.get("category") or "").strip()
        if cat: qs = qs.filter(category=cat)
        subj = (request.query_params.get("subject") or "").strip()
        if subj: qs = qs.filter(subject__code__iexact=subj)
        q = (request.query_params.get("q") or "").strip()
        if q: qs = qs.filter(title__icontains=q)
        qs = qs.order_by("-created_at")[:300]
        rows = [{
            "id": str(a.id), "title": a.title, "description": a.description,
            "format": a.format, "category": a.category,
            "size_bytes": a.size_bytes, "subject": (
                {"id": str(a.subject.id), "name": a.subject.name, "code": a.subject.code}
                if a.subject else None
            ),
            "book_id": str(a.book.id) if a.book else None,
            "allow_download": a.allow_download, "read_only": a.read_only,
            "watermark_text": a.watermark_text,
            "view_count": a.view_count, "download_count": a.download_count,
            "uploaded_by": str(a.uploaded_by) if a.uploaded_by else "",
            "created_at": a.created_at,
        } for a in qs]
        return Response({"resources": rows})

    # POST upload
    file = request.FILES.get("file")
    title = (request.data.get("title") or "").strip()
    if not file or not title:
        return Response({"error": "file and title are required"}, status=400)
    subject_id = request.data.get("subject_id") or None
    book_id = request.data.get("book_id") or None
    category = (request.data.get("category") or "OTHER").strip()
    desc = (request.data.get("description") or "").strip()
    allow_dl = str(request.data.get("allow_download") or "false").lower() in ("1", "true", "yes")
    allow_pr = str(request.data.get("allow_print") or "false").lower() in ("1", "true", "yes")
    wm = (request.data.get("watermark_text") or "").strip()
    expires = request.data.get("expires_at") or None

    subj_obj = None; book_obj = None
    if subject_id:
        from apps.academics.models import Subject as _S
        subj_obj = _S.objects.filter(id=subject_id).first()
    if book_id:
        book_obj = Book.objects.filter(id=book_id).first()

    try:
        asset = _save_asset(
            file=file, title=title, description=desc, category=category,
            subject=subj_obj, book=book_obj,
            allow_download=allow_dl, allow_print=allow_pr,
            watermark_text=wm, by_user=request.user,
        )
    except _DAMError as e:
        return Response({"error": str(e)}, status=400)
    return Response({"ok": True, "id": str(asset.id), "format": asset.format,
                     "size_bytes": asset.size_bytes})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dam_resource_detail(request, pk):
    a = _DA.objects.filter(id=pk).first()
    if not a:
        return Response({"error": "not found"}, status=404)
    return Response({
        "id": str(a.id), "title": a.title, "description": a.description,
        "format": a.format, "category": a.category, "size_bytes": a.size_bytes,
        "subject": ({"id": str(a.subject.id), "code": a.subject.code, "name": a.subject.name}
                    if a.subject else None),
        "allow_download": a.allow_download, "allow_print": a.allow_print,
        "read_only": a.read_only, "watermark_text": a.watermark_text,
        "view_count": a.view_count, "download_count": a.download_count,
        "uploaded_by": str(a.uploaded_by) if a.uploaded_by else "",
        "created_at": a.created_at,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dam_view_stream(request, pk):
    a = _DA.objects.filter(id=pk, is_active=True).first()
    if not a:
        return Response({"error": "not found"}, status=404)
    try:
        return _serve_asset(a, user=request.user, action="view", request=request)
    except _DAMError as e:
        return Response({"error": str(e)}, status=403)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dam_download_stream(request, pk):
    a = _DA.objects.filter(id=pk, is_active=True).first()
    if not a:
        return Response({"error": "not found"}, status=404)
    try:
        return _serve_asset(a, user=request.user, action="download", request=request)
    except _DAMError as e:
        return Response({"error": str(e)}, status=403)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def dam_delete(request, pk):
    a = _DA.objects.filter(id=pk).first()
    if not a:
        return Response({"error": "not found"}, status=404)
    a.is_active = False
    a.save(update_fields=["is_active", "updated_at"])
    return Response({"ok": True})


# =====================================================================
# L6 — Audits
# =====================================================================
from apps.library.models import InventoryAudit as _IA, InventoryAuditLine as _IAL
from apps.library.services.inventory_audit import (
    start_audit as _start_audit, scan_barcode as _scan_barcode, finish_audit as _finish_audit,
)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def audits(request):
    if request.method == "GET":
        qs = _IA.objects.order_by("-started_at")[:60]
        return Response({"audits": [{
            "id": str(a.id), "scope": a.scope, "status": a.status,
            "started_at": a.started_at, "finished_at": a.finished_at,
            "total_expected": a.total_expected, "total_scanned": a.total_scanned,
            "total_missing": a.total_missing, "total_misplaced": a.total_misplaced,
            "shelf": ({"id": str(a.shelf.id), "code": a.shelf.code} if a.shelf else None),
        } for a in qs]})
    scope = (request.data.get("scope") or "FULL").upper()
    shelf_id = request.data.get("shelf_id") or None
    shelf = None
    if scope == "SHELF" and shelf_id:
        from apps.library.models import Shelf as _S
        shelf = _S.objects.filter(id=shelf_id).first()
    audit = _start_audit(scope=scope, shelf=shelf, user=request.user)
    return Response({"ok": True, "id": str(audit.id), "total_expected": audit.total_expected})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def audit_detail(request, pk):
    a = _IA.objects.filter(id=pk).first()
    if not a: return Response({"error": "not found"}, status=404)
    lines = a.lines.select_related("copy__book").order_by("-scanned_at", "barcode_scanned")[:300]
    return Response({
        "id": str(a.id), "scope": a.scope, "status": a.status,
        "started_at": a.started_at, "finished_at": a.finished_at,
        "total_expected": a.total_expected, "total_scanned": a.total_scanned,
        "total_missing": a.total_missing, "total_misplaced": a.total_misplaced,
        "lines": [{
            "id": str(l.id), "barcode": l.barcode_scanned or (l.copy.barcode if l.copy else ""),
            "book_title": (l.copy.book.title if l.copy and l.copy.book else ""),
            "expected_shelf": l.expected_shelf, "result": l.result, "scanned_at": l.scanned_at,
        } for l in lines],
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def audit_scan(request, pk):
    a = _IA.objects.filter(id=pk).first()
    if not a: return Response({"error": "not found"}, status=404)
    if a.status != _IA.Status.OPEN: return Response({"error": "audit is not open"}, status=409)
    barcode = (request.data.get("barcode") or "").strip()
    if not barcode: return Response({"error": "barcode required"}, status=400)
    line = _scan_barcode(audit=a, barcode=barcode, user=request.user)
    return Response({
        "ok": True, "line_id": str(line.id), "result": line.result,
        "barcode": line.barcode_scanned,
        "book_title": (line.copy.book.title if line.copy and line.copy.book else ""),
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def audit_finish(request, pk):
    a = _IA.objects.filter(id=pk).first()
    if not a: return Response({"error": "not found"}, status=404)
    _finish_audit(audit=a, user=request.user)
    return Response({"ok": True, "status": a.status, "total_expected": a.total_expected,
                     "total_scanned": a.total_scanned, "total_missing": a.total_missing,
                     "total_misplaced": a.total_misplaced})


# =====================================================================
# Student portal
# =====================================================================
def _resolve_member_for_user(user):
    if not user or not getattr(user, "is_authenticated", False):
        return None
    m = Member.objects.filter(user=user).first()
    if m: return m
    t = getattr(user, "teacher_profile", None)
    if t is not None:
        return Member.objects.filter(teacher=t).first()
    s = getattr(user, "student_profile", None)
    if s is not None:
        return Member.objects.filter(student=s).first()
    return None


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def portal_me(request):
    member = _resolve_member_for_user(request.user)
    if not member:
        return Response({"linked": False, "message": "Your account is not yet linked to a library membership."})
    from django.utils import timezone
    now = timezone.now()
    active = Loan.objects.filter(member=member, status=Loan.Status.ACTIVE).select_related("copy__book").order_by("due_at")
    history = Loan.objects.filter(member=member).exclude(status=Loan.Status.ACTIVE).select_related("copy__book").order_by("-returned_at")[:50]
    return Response({
        "linked": True,
        "member": {"id": str(member.id), "member_number": member.member_number,
                   "full_name": member.full_name, "member_type": member.member_type},
        "active_loans": [{
            "id": str(l.id), "book_title": l.copy.book.title if l.copy and l.copy.book else "",
            "copy_barcode": l.copy.barcode if l.copy else "",
            "issued_at": l.issued_at, "due_at": l.due_at,
            "overdue_days": max(0, (now - l.due_at).days) if l.due_at < now else 0,
            "renewals_used": l.renewal_count,
        } for l in active],
        "history": [{
            "id": str(l.id), "book_title": l.copy.book.title if l.copy and l.copy.book else "",
            "issued_at": l.issued_at, "returned_at": l.returned_at, "status": l.status,
        } for l in history],
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def portal_recommendations(request):
    member = _resolve_member_for_user(request.user)
    if not member or not member.student_id:
        return Response({"recommendations": []})
    from apps.academics.models import StudentEnrollment as _SE, LessonRequirement as _LR
    enr = _SE.objects.filter(student=member.student, is_active=True).select_related("instructional_group").first()
    codes = set()
    if enr and enr.instructional_group:
        codes = {lr.subject.code for lr in _LR.objects.filter(
            instructional_group=enr.instructional_group, is_active=True).select_related("subject") if lr.subject}
    qs = Book.objects.filter(is_active=True, subjects__code__in=codes).distinct()[:24]
    return Response({"recommendations": [{
        "id": str(b.id), "title": b.title, "cover_url": b.cover_url,
        "subjects": [s.code for s in b.subjects.all()],
    } for b in qs]})


# =====================================================================
# Analytics
# =====================================================================
from django.db.models import Count as _Count
from django.db.models.functions import TruncDate as _TruncDate, ExtractWeekDay as _EWD
from datetime import timedelta as _td
from django.utils import timezone as _tz


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def analytics_circulation(request):
    days = max(7, min(int(request.query_params.get("days") or 30), 180))
    start = _tz.now() - _td(days=days)
    qs = (Loan.objects.filter(issued_at__gte=start)
          .annotate(d=_TruncDate("issued_at")).values("d").annotate(n=_Count("id")).order_by("d"))
    return Response({"days": days, "series": [{"date": r["d"].isoformat(), "count": r["n"]} for r in qs]})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def analytics_subject_mix(request):
    from apps.academics.models import Subject as _S
    rows = [{"subject": s.code, "name": s.name,
             "count": Book.objects.filter(subjects=s, is_active=True).count()}
            for s in _S.objects.filter(is_active=True)]
    rows = [r for r in rows if r["count"] > 0]
    rows.sort(key=lambda r: -r["count"])
    return Response({"subjects": rows})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def analytics_peak_periods(request):
    start = _tz.now() - _td(days=90)
    qs = (Loan.objects.filter(issued_at__gte=start)
          .annotate(d=_EWD("issued_at")).values("d").annotate(n=_Count("id")).order_by("d"))
    names = {1: "Sun", 2: "Mon", 3: "Tue", 4: "Wed", 5: "Thu", 6: "Fri", 7: "Sat"}
    return Response({"by_weekday": [{"day": names.get(r["d"], str(r["d"])), "count": r["n"]} for r in qs]})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def analytics_top_titles(request):
    qs = Book.objects.annotate(loans_n=_Count("copies__loans")).filter(loans_n__gt=0).order_by("-loans_n")[:20]
    return Response({"titles": [{"id": str(b.id), "title": b.title, "loans": b.loans_n} for b in qs]})


# =====================================================================
# Notifications
# =====================================================================
from apps.library.models import Notification as _Notif


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def notifications_me(request):
    member = _resolve_member_for_user(request.user)
    if not member:
        return Response({"notifications": [], "unread": 0})
    qs = _Notif.objects.filter(member=member).order_by("-created_at")[:50]
    unread = _Notif.objects.filter(member=member).exclude(status=_Notif.Status.READ).count()
    return Response({
        "unread": unread,
        "notifications": [{
            "id": str(n.id), "kind": n.kind, "subject": n.subject, "body": n.body,
            "status": n.status, "created_at": n.created_at, "read_at": n.read_at,
        } for n in qs],
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def notification_mark_read(request, pk):
    member = _resolve_member_for_user(request.user)
    if not member:
        return Response({"error": "not linked"}, status=404)
    n = _Notif.objects.filter(id=pk, member=member).first()
    if not n:
        return Response({"error": "not found"}, status=404)
    from django.utils import timezone as _tz
    n.status = _Notif.Status.READ
    n.read_at = _tz.now()
    n.save(update_fields=["status", "read_at"])
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def notifications_scan(request):
    """Trigger due/overdue scan (usually run by cron)."""
    from apps.library.services.notifications import scan_due_and_overdue
    return Response(scan_due_and_overdue())
