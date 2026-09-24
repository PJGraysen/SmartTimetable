from django.urls import path
urlpatterns = []



# --- Student API registration (added 2026-09-16) ---
from rest_framework.routers import DefaultRouter as _StudentDefaultRouter
from apps.academics.views import StudentViewSet as _StudentViewSet

_student_router = _StudentDefaultRouter()
_student_router.register(r"students", _StudentViewSet, basename="student")
urlpatterns += _student_router.urls
