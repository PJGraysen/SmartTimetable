from django.urls import path, include
from rest_framework.routers import DefaultRouter
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
    path("", include(router.urls)),
]
