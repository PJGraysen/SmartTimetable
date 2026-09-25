from rest_framework import serializers
from apps.inventory.models import (
    Department, Location, Category, Supplier, Item, Asset,
    StockLevel, Movement, MaintenanceLog, AuditSession, AuditLine,
)


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = "__all__"


class LocationSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    class Meta:
        model = Location
        fields = "__all__"


class CategorySerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name", read_only=True)
    class Meta:
        model = Category
        fields = "__all__"


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = "__all__"


class ItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    supplier_name = serializers.CharField(source="default_supplier.name", read_only=True)
    class Meta:
        model = Item
        fields = "__all__"


class AssetSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)
    item_code = serializers.CharField(source="item.code", read_only=True)
    location_code = serializers.CharField(source="current_location.code", read_only=True)
    location_name = serializers.CharField(source="current_location.name", read_only=True)
    class Meta:
        model = Asset
        fields = "__all__"


class StockLevelSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)
    item_code = serializers.CharField(source="item.code", read_only=True)
    unit = serializers.CharField(source="item.unit", read_only=True)
    location_code = serializers.CharField(source="location.code", read_only=True)
    class Meta:
        model = StockLevel
        fields = "__all__"


class MovementSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)
    item_code = serializers.CharField(source="item.code", read_only=True)
    asset_tag = serializers.CharField(source="asset.tag", read_only=True)
    from_code = serializers.CharField(source="from_location.code", read_only=True)
    to_code = serializers.CharField(source="to_location.code", read_only=True)
    actor_name = serializers.CharField(source="actor.username", read_only=True)
    class Meta:
        model = Movement
        fields = "__all__"


class MaintenanceLogSerializer(serializers.ModelSerializer):
    asset_tag = serializers.CharField(source="asset.tag", read_only=True)
    class Meta:
        model = MaintenanceLog
        fields = "__all__"


class AuditLineSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)
    item_code = serializers.CharField(source="item.code", read_only=True)
    class Meta:
        model = AuditLine
        fields = "__all__"


class AuditSessionSerializer(serializers.ModelSerializer):
    location_code = serializers.CharField(source="location.code", read_only=True)
    lines = AuditLineSerializer(many=True, read_only=True)
    class Meta:
        model = AuditSession
        fields = "__all__"
