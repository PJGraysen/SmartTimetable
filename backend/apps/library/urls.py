from django.urls import include, path

urlpatterns = [
    path("", include("apps.library.api.urls")),
]
