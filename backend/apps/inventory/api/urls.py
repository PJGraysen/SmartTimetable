from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.inventory.api.workflow import (
    retire_item, unretire_item, quick_add_item, quick_add_stock,
    maintenance_report, maintenance_approve, maintenance_reject, maintenance_complete,
    notifications as workflow_notifications,
    comprehensive_report, supplier_log_contact,
)
from apps.inventory.api.extras import (
    asset_detail, item_detail, location_contents, department_summary,
    bulk_transfer_assets, bulk_status_assets, bulk_maintenance_assets,
    dashboard_v2,
)
from apps.inventory.api.actions import (
    receive_stock, issue_stock, transfer_stock, move_asset,
)
from apps.inventory.api.reports import (
    reports_low_stock, reports_expiring_soon,
    reports_valuation, reports_movement_summary,
)
from apps.inventory.api.views import (
    DepartmentViewSet, LocationViewSet, CategoryViewSet,
    SupplierViewSet, ItemViewSet, AssetViewSet, StockLevelViewSet,
    MovementViewSet, MaintenanceLogViewSet,
    AuditSessionViewSet, AuditLineViewSet,
    inventory_dashboard,
)

router = DefaultRouter()
router.register(r"departments", DepartmentViewSet)
router.register(r"locations", LocationViewSet)
router.register(r"categories", CategoryViewSet)
router.register(r"suppliers", SupplierViewSet)
router.register(r"items", ItemViewSet)
router.register(r"assets", AssetViewSet)
router.register(r"stock", StockLevelViewSet)
router.register(r"movements", MovementViewSet)
router.register(r"maintenance", MaintenanceLogViewSet)
router.register(r"audits", AuditSessionViewSet)
router.register(r"audit-lines", AuditLineViewSet)

urlpatterns = [
    path("dashboard/", inventory_dashboard, name="inventory-dashboard"),

    # Quick actions
    path("actions/receive/", receive_stock, name="inventory-receive"),
    path("actions/issue/", issue_stock, name="inventory-issue"),
    path("actions/transfer/", transfer_stock, name="inventory-transfer"),
    path("actions/move-asset/", move_asset, name="inventory-move-asset"),

    # Reports
    path("reports/low-stock/", reports_low_stock, name="inventory-reports-low-stock"),
    path("reports/expiring/", reports_expiring_soon, name="inventory-reports-expiring"),
    path("reports/valuation/", reports_valuation, name="inventory-reports-valuation"),
    path("reports/movements/", reports_movement_summary, name="inventory-reports-movements"),

    # Dashboard v2
    path("dashboard/v2/", dashboard_v2, name="inventory-dashboard-v2"),

    # Detail + history
    path("assets/<int:pk>/detail/", asset_detail, name="inventory-asset-detail"),
    path("items/<int:pk>/detail/", item_detail, name="inventory-item-detail"),
    path("locations/<int:pk>/contents/", location_contents, name="inventory-location-contents"),
    path("departments/<int:pk>/summary/", department_summary, name="inventory-department-summary"),

    # Phase-2 workflow
    path("items/<int:pk>/retire/", retire_item, name="inventory-item-retire"),
    path("items/<int:pk>/unretire/", unretire_item, name="inventory-item-unretire"),
    path("items/quick-add/", quick_add_item, name="inventory-item-quick-add"),
    path("stock/quick-add/", quick_add_stock, name="inventory-stock-quick-add"),
    path("maintenance/report/", maintenance_report, name="inventory-maint-report"),
    path("maintenance/<int:pk>/approve/", maintenance_approve, name="inventory-maint-approve"),
    path("maintenance/<int:pk>/reject/", maintenance_reject, name="inventory-maint-reject"),
    path("maintenance/<int:pk>/complete/", maintenance_complete, name="inventory-maint-complete"),
    path("notifications/", workflow_notifications, name="inventory-notifications"),
    path("reports/comprehensive/", comprehensive_report, name="inventory-reports-comprehensive"),
    path("suppliers/<int:pk>/contact/", supplier_log_contact, name="inventory-supplier-contact"),

    # Bulk operations
    path("actions/bulk-transfer-assets/", bulk_transfer_assets, name="inventory-bulk-transfer-assets"),
    path("actions/bulk-status-assets/", bulk_status_assets, name="inventory-bulk-status-assets"),
    path("actions/bulk-maintenance-assets/", bulk_maintenance_assets, name="inventory-bulk-maintenance-assets"),
    path("", include(router.urls)),
]
