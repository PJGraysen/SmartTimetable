from django.contrib import admin

# Register your models here.


from apps.core.models import SchoolEvent as _SchoolEvent


@admin.register(_SchoolEvent)
class SchoolEventAdmin(admin.ModelAdmin):
    list_display = ("date", "end_date", "title", "kind", "is_active")
    list_filter = ("kind", "is_active")
    search_fields = ("title", "description")
    date_hierarchy = "date"
