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

from apps.library.api.views import subjects_list as _subjects_list_view
from apps.library.api.views import subject_summary as _subject_summary_view

urlpatterns += [
    path("catalogue/subjects/", _subjects_list_view, name="library-subjects-list"),
    path("catalogue/subject-summary/", _subject_summary_view, name="library-subject-summary"),
]

from apps.library.api.views import self_checkout as _self_checkout_view
from apps.library.api.views import bulk_return as _bulk_return_view
from apps.library.api.views import catalogue_search as _catalogue_search_view
from apps.library.api.views import export_report as _export_report_view

urlpatterns += [
    path("circulation/self-checkout/", _self_checkout_view, name="library-self-checkout"),
    path("circulation/bulk-return/", _bulk_return_view, name="library-bulk-return"),
    path("catalogue/search/", _catalogue_search_view, name="library-catalogue-search"),
    path("reports/<slug:report_name>/export/", _export_report_view, name="library-report-export"),
]

from apps.library.api.views import roster_eligible as _roster_eligible
from apps.library.api.views import roster_sync as _roster_sync
from apps.library.api.views import inventory_register_one as _inv_reg_one
from apps.library.api.views import inventory_register_all as _inv_reg_all
from apps.library.api.views import member_fee_account as _member_fee_acct
from apps.library.api.views import post_loan_fine as _post_loan_fine

urlpatterns += [
    path("roster/eligible/", _roster_eligible, name="library-roster-eligible"),
    path("roster/sync/", _roster_sync, name="library-roster-sync"),
    path("copies/<uuid:pk>/register-inventory/", _inv_reg_one, name="library-copy-inv-register"),
    path("copies/register-all-inventory/", _inv_reg_all, name="library-copies-inv-register-all"),
    path("members/<uuid:member_id>/fee-account/", _member_fee_acct, name="library-member-fee-account"),
    path("loans/<uuid:loan_id>/post-fine/", _post_loan_fine, name="library-loan-post-fine"),
]

from apps.library.api.views import dam_resources as _dam_resources
from apps.library.api.views import dam_resource_detail as _dam_detail
from apps.library.api.views import dam_view_stream as _dam_view_stream
from apps.library.api.views import dam_download_stream as _dam_download_stream
from apps.library.api.views import dam_delete as _dam_delete

urlpatterns += [
    path("resources/", _dam_resources, name="library-resources"),
    path("resources/<uuid:pk>/", _dam_detail, name="library-resource-detail"),
    path("resources/<uuid:pk>/view/", _dam_view_stream, name="library-resource-view"),
    path("resources/<uuid:pk>/download/", _dam_download_stream, name="library-resource-download"),
    path("resources/<uuid:pk>/delete/", _dam_delete, name="library-resource-delete"),
]

from apps.library.api.views import audits as _audits
from apps.library.api.views import audit_detail as _audit_detail
from apps.library.api.views import audit_scan as _audit_scan
from apps.library.api.views import audit_finish as _audit_finish
from apps.library.api.views import portal_me as _portal_me
from apps.library.api.views import portal_recommendations as _portal_recs
from apps.library.api.views import analytics_circulation as _ana_circ
from apps.library.api.views import analytics_subject_mix as _ana_subj
from apps.library.api.views import analytics_peak_periods as _ana_peak
from apps.library.api.views import analytics_top_titles as _ana_titles

urlpatterns += [
    path("audits/", _audits, name="library-audits"),
    path("audits/<uuid:pk>/", _audit_detail, name="library-audit-detail"),
    path("audits/<uuid:pk>/scan/", _audit_scan, name="library-audit-scan"),
    path("audits/<uuid:pk>/finish/", _audit_finish, name="library-audit-finish"),
    path("portal/me/", _portal_me, name="library-portal-me"),
    path("portal/recommendations/", _portal_recs, name="library-portal-recommendations"),
    path("analytics/circulation/", _ana_circ, name="library-analytics-circulation"),
    path("analytics/subject-mix/", _ana_subj, name="library-analytics-subject-mix"),
    path("analytics/peak-periods/", _ana_peak, name="library-analytics-peak-periods"),
    path("analytics/top-titles/", _ana_titles, name="library-analytics-top-titles"),
]

from apps.library.api.views import notifications_me as _notifications_me
from apps.library.api.views import notification_mark_read as _notification_read
from apps.library.api.views import notifications_scan as _notifications_scan

urlpatterns += [
    path("notifications/me/", _notifications_me, name="library-notifications-me"),
    path("notifications/<uuid:pk>/read/", _notification_read, name="library-notification-read"),
    path("notifications/scan/", _notifications_scan, name="library-notifications-scan"),
]

from apps.library.api.views import catalogue_marc_lookup as _catalogue_marc_lookup

urlpatterns += [
    path("catalogue/marc-lookup/", _catalogue_marc_lookup, name="library-catalogue-marc-lookup"),
]

from apps.library.api.views import rules_ensure_defaults as _rules_ensure

urlpatterns += [
    path("rules/ensure-defaults/", _rules_ensure, name="library-rules-ensure"),
]
