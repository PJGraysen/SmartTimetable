from django.contrib import admin
from apps.library.models import (
    Author, Book, Category, Copy, Loan, LoanRule, Member, Publisher, Shelf,
)


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("name", "sort_name")
    search_fields = ("name", "sort_name")


@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    search_fields = ("name", "code")


@admin.register(Shelf)
class ShelfAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "location_hint")


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "isbn", "publisher", "is_active")
    search_fields = ("title", "isbn")
    list_filter = ("is_active",)
    filter_horizontal = ("authors", "categories", "subjects")


@admin.register(Copy)
class CopyAdmin(admin.ModelAdmin):
    list_display = ("barcode", "book", "status", "condition", "shelf")
    search_fields = ("barcode", "accession_number", "book__title")
    list_filter = ("status", "condition")


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ("member_number", "full_name", "member_type", "is_active")
    search_fields = ("member_number", "full_name", "email")
    list_filter = ("member_type", "is_active")


@admin.register(LoanRule)
class LoanRuleAdmin(admin.ModelAdmin):
    list_display = (
        "member_type", "max_concurrent_loans", "loan_days",
        "max_renewals", "fine_per_day", "grace_days",
    )


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ("copy", "member", "issued_at", "due_at", "returned_at", "status")
    search_fields = ("copy__barcode", "member__member_number", "member__full_name")
    list_filter = ("status",)
    date_hierarchy = "issued_at"
