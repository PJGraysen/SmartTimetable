from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("books", views.BookViewSet, basename="book")
router.register("copies", views.CopyViewSet, basename="copy")
router.register("authors", views.AuthorViewSet, basename="author")
router.register("publishers", views.PublisherViewSet, basename="publisher")
router.register("categories", views.CategoryViewSet, basename="category")
router.register("shelves", views.ShelfViewSet, basename="shelf")
router.register("members", views.MemberViewSet, basename="member")
router.register("rules", views.LoanRuleViewSet, basename="loanrule")
router.register("loans", views.LoanViewSet, basename="loan")
router.register("reservations", views.ReservationViewSet, basename="reservation")
router.register("fines", views.FinePaymentViewSet, basename="fine")
router.register("reading-lists", views.ReadingListViewSet, basename="readinglist")

urlpatterns = router.urls + [
    path("dashboard/", views.DashboardView.as_view(), name="library-dashboard"),
    path("members/<uuid:pk>/detail/", views.MemberDetailView.as_view()),
    path("import/", views.BulkImportView.as_view()),
    path("reports/circulation/", views.CirculationReportView.as_view()),
    path("reports/overdue/", views.OverdueReportView.as_view()),
    path("reports/inventory/", views.InventoryReportView.as_view()),
    path("reports/top-borrowers/", views.TopBorrowersReportView.as_view()),
    path("reports/student-loans/<uuid:member_id>/", views.StudentLoansReportView.as_view()),
    path("reports/book-loans/<uuid:book_id>/", views.BookLoansReportView.as_view()),
    path("reports/by-subject/", views.SubjectBreakdownReportView.as_view()),
    path("reports/by-category/", views.CategoryBreakdownReportView.as_view()),
    path("reports/activity-feed/", views.ActivityFeedView.as_view()),
    path("reports/popular-titles/", views.PopularTitlesReportView.as_view()),
    path("reports/acquisitions/", views.AcquisitionReportView.as_view()),
    path("reports/damage/", views.DamageReportView.as_view()),
    path("reports/blocked-members/", views.BlockedMembersReportView.as_view()),
]

from apps.library.api.views import book_lookup as _book_lookup_view

urlpatterns += [
    path("catalogue/lookup/", _book_lookup_view, name="library-book-lookup"),
]
