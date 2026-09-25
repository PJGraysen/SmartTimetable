from django.urls import path, include
from rest_framework.routers import DefaultRouter
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
    path("", include(router.urls)),
]
