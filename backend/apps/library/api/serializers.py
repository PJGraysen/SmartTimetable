from __future__ import annotations

from django.utils import timezone
from rest_framework import serializers

from apps.library.models import (
    Author, Book, Category, Copy, Loan, LoanRule, Member, Publisher, Shelf,
)


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ["id", "name", "sort_name"]


class PublisherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publisher
        fields = ["id", "name", "address", "contact_email", "contact_phone"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "code", "description"]


class ShelfSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shelf
        fields = ["id", "code", "name", "description", "location_hint"]


class BookSerializer(serializers.ModelSerializer):
    authors = AuthorSerializer(many=True, read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    publisher = PublisherSerializer(read_only=True)
    copy_count = serializers.SerializerMethodField()
    available_copy_count = serializers.SerializerMethodField()
    read_asset = serializers.SerializerMethodField()

    # --- L1 pro cataloguing: convenience fields ---
    authors_text = serializers.CharField(
        write_only=True, required=False, allow_blank=True,
        help_text="Comma-separated author names. Auto-creates Author rows.",
    )
    publisher_name = serializers.CharField(
        write_only=True, required=False, allow_blank=True,
        help_text="Publisher name. Auto-creates Publisher row.",
    )

    class Meta:
        model = Book
        fields = [
            "id", "isbn", "title", "subtitle", "edition", "language",
            "description", "publisher", "published_year", "cover_url",
            "authors", "categories", "is_active",
            "ddc", "lcc", "toc", "page_count", "source", "source_id", "marc21",
            "authors_text", "publisher_name",
            "copy_count", "available_copy_count", "read_asset",
            "created_at", "updated_at",
        ]

    def get_copy_count(self, obj):
        return obj.copies.count()

    def get_available_copy_count(self, obj):
        return obj.copies.filter(status=Copy.Status.AVAILABLE).count()



    def get_read_asset(self, obj):
        """Return a compact descriptor of the book's readable digital asset, if any."""
        asset = obj.digital_assets.filter(is_active=True).order_by("-created_at").first()
        if not asset:
            return None
        return {
            "id": str(asset.id),
            "title": asset.title,
            "format": asset.format,
            "allow_download": asset.allow_download,
            "allow_print": asset.allow_print,
            "read_only": asset.read_only,
            "watermark_text": asset.watermark_text,
        }

    def create(self, validated_data):
        authors_text = validated_data.pop("authors_text", "") or ""
        publisher_name = (validated_data.pop("publisher_name", "") or "").strip()

        if publisher_name:
            pub, _ = Publisher.objects.get_or_create(name=publisher_name)
            validated_data["publisher"] = pub

        book = super().create(validated_data)

        names = [n.strip() for n in authors_text.split(",") if n.strip()]
        for name in names:
            a, _ = Author.objects.get_or_create(name=name, defaults={"sort_name": name})
            book.authors.add(a)
        return book

    def update(self, instance, validated_data):
        authors_text = validated_data.pop("authors_text", None)
        publisher_name = validated_data.pop("publisher_name", None)

        if publisher_name is not None:
            publisher_name = (publisher_name or "").strip()
            if publisher_name:
                pub, _ = Publisher.objects.get_or_create(name=publisher_name)
                validated_data["publisher"] = pub
            else:
                validated_data["publisher"] = None

        book = super().update(instance, validated_data)

        if authors_text is not None:
            names = [n.strip() for n in authors_text.split(",") if n.strip()]
            authors = []
            for name in names:
                a, _ = Author.objects.get_or_create(name=name, defaults={"sort_name": name})
                authors.append(a)
            book.authors.set(authors)
        return book


class CopySerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)

    class Meta:
        model = Copy
        fields = [
            "id", "book", "book_title", "barcode", "accession_number",
            "shelf", "status", "condition", "acquired_at",
            "acquisition_cost", "replacement_cost", "notes",
            "created_at", "updated_at",
        ]


class MemberSerializer(serializers.ModelSerializer):
    class_name = serializers.SerializerMethodField()
    active_loan_count = serializers.SerializerMethodField()
    total_borrowed = serializers.SerializerMethodField()
    fines_due = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = [
            "id", "member_number", "user", "full_name", "email", "phone",
            "member_type", "is_active", "joined_at", "notes",
            "class_name", "active_loan_count", "total_borrowed", "fines_due",
            "created_at", "updated_at",
        ]

    def get_class_name(self, obj):
        student = getattr(obj, 'student', None)
        if student is None:
            return None
        for attr in ('class_name', 'grade', 'class_display', 'klass_name'):
            val = getattr(student, attr, None)
            if val:
                return str(val)
        klass = getattr(student, 'klass', None) or getattr(student, 'current_class', None)
        if klass is not None:
            return str(klass)
        return None

    def get_active_loan_count(self, obj):
        from apps.library.models import Loan
        return Loan.objects.filter(member=obj, status="ACTIVE").count()

    def get_total_borrowed(self, obj):
        from apps.library.models import Loan
        return Loan.objects.filter(member=obj).exclude(status="ACTIVE").count()

    def get_fines_due(self, obj):
        from apps.library.models import Loan
        from django.db.models import Sum, F, Value
        from django.db.models.functions import Coalesce
        rows = Loan.objects.filter(member=obj).annotate(
            net=Coalesce(F("fine_accrued"), Value(0)) - Coalesce(F("fine_paid"), Value(0))
        ).filter(net__gt=0)
        total = rows.aggregate(s=Sum("net"))["s"] or 0
        return float(total)


class LoanRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanRule
        fields = [
            "id", "member_type", "max_concurrent_loans", "loan_days",
            "max_renewals", "fine_per_day", "grace_days", "max_fine",
        ]


class LoanSerializer(serializers.ModelSerializer):
    copy_barcode = serializers.CharField(source="copy.barcode", read_only=True)
    book_title = serializers.CharField(source="copy.book.title", read_only=True)
    member_number = serializers.CharField(source="member.member_number", read_only=True)
    member_name = serializers.CharField(source="member.full_name", read_only=True)
    is_overdue = serializers.SerializerMethodField()
    overdue_days = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = [
            "id", "copy", "copy_barcode", "book_title",
            "member", "member_number", "member_name",
            "issued_at", "due_at", "returned_at", "status",
            "renewal_count", "fine_accrued", "fine_paid",
            "is_overdue", "overdue_days", "notes",
            "issued_by", "received_by",
            "created_at", "updated_at",
        ]

    def get_is_overdue(self, obj):
        if obj.status != Loan.Status.ACTIVE:
            return False
        return obj.due_at < timezone.now()

    def get_overdue_days(self, obj):
        if obj.status != Loan.Status.ACTIVE:
            return 0
        return max(0, (timezone.now() - obj.due_at).days)


# =========================================================================
# PHASE 2 serializers
# =========================================================================
from apps.library.models import (
    FinePayment as _FinePayment,
    ReadingList as _ReadingList,
    ReadingListItem as _ReadingListItem,
    Reservation as _Reservation,
)
from apps.library.services.blocking import member_status as _member_status


class MemberStatusMixin:
    def get_status(self, obj):
        return _member_status(obj)


class ReservationSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)
    member_number = serializers.CharField(source="member.member_number", read_only=True)
    member_name = serializers.CharField(source="member.full_name", read_only=True)

    class Meta:
        model = _Reservation
        fields = [
            "id", "book", "book_title",
            "member", "member_number", "member_name",
            "status", "position",
            "requested_at", "notified_at", "expires_at", "notes",
        ]


class FinePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = _FinePayment
        fields = [
            "id", "loan", "amount", "kind", "reason",
            "recorded_by", "recorded_at",
        ]


class ReadingListItemSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(source="book.title", read_only=True)

    class Meta:
        model = _ReadingListItem
        fields = ["id", "book", "book_title", "position", "notes"]


class ReadingListSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True, allow_null=True)
    items = ReadingListItemSerializer(many=True, read_only=True)

    class Meta:
        model = _ReadingList
        fields = [
            "id", "name", "subject", "subject_name",
            "description", "is_active", "items",
            "created_at", "updated_at",
        ]


# Extend MemberSerializer by redefining (django rest framework lets us
# add SerializerMethodFields by declaring a subclass)
class MemberWithStatusSerializer(MemberSerializer):
    library_status = serializers.SerializerMethodField()

    class Meta(MemberSerializer.Meta):
        fields = MemberSerializer.Meta.fields + ["library_status"]

    def get_library_status(self, obj):
        return _member_status(obj)


class BookLookupPreviewSerializer(serializers.Serializer):
    isbn = serializers.CharField()
    title = serializers.CharField(allow_blank=True)
    subtitle = serializers.CharField(allow_blank=True)
    authors = serializers.ListField(child=serializers.CharField(), required=False)
    publisher = serializers.CharField(allow_blank=True)
    published_year = serializers.IntegerField(allow_null=True, required=False)
    edition = serializers.CharField(allow_blank=True)
    language = serializers.CharField(allow_blank=True)
    description = serializers.CharField(allow_blank=True)
    cover_url = serializers.CharField(allow_blank=True)
    page_count = serializers.IntegerField(allow_null=True, required=False)
    ddc = serializers.CharField(allow_blank=True)
    lcc = serializers.CharField(allow_blank=True)
    toc = serializers.CharField(allow_blank=True)
    source = serializers.CharField(allow_blank=True)
    source_id = serializers.CharField(allow_blank=True)
