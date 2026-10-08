"""
WebSocket consumers for live activity (Layer 3B).

Only admin-like users can connect. On any broadcast, the payload is
forwarded to the client as JSON.
"""
import json

from channels.generic.websocket import AsyncWebsocketConsumer


GROUP = "live_activity"


class LiveActivityConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close()
            return
        if not (user.is_staff or user.is_superuser):
            await self.close()
            return

        await self.channel_layer.group_add(GROUP, self.channel_name)
        await self.accept()
        await self.send(text_data=json.dumps({
            "type": "hello",
            "message": "Connected to live activity stream.",
        }))

    async def disconnect(self, code):
        try:
            await self.channel_layer.group_discard(GROUP, self.channel_name)
        except Exception:
            pass

    async def broadcast(self, event):
        await self.send(text_data=json.dumps(event["payload"]))
