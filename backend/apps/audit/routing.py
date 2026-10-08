from django.urls import path

from apps.audit.consumers import LiveActivityConsumer

websocket_urlpatterns = [
    path("ws/live/", LiveActivityConsumer.as_asgi()),
]
