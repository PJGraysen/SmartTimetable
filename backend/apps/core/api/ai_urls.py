from django.urls import path

from .ai import chat


urlpatterns = [
    path(
        "chat/",
        chat,
        name="ai-chat",
    ),
]
