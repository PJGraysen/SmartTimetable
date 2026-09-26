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
