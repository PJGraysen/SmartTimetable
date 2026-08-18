"""
URL configuration for SmartTimetable Pro.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "api/scheduling/",
        include("apps.scheduling.api.urls"),
    ),
]