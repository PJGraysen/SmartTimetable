from django.apps import AppConfig


class AcademicsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.academics"

    def ready(self):
        from apps.academics import signals  # noqa: F401
