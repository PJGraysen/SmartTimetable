"""
Thin wrapper around Channels group_send so sync code can broadcast.
Safely no-ops if Channels isn't configured.
"""
from asgiref.sync import async_to_sync


GROUP = "live_activity"


def broadcast(payload: dict) -> None:
    try:
        from channels.layers import get_channel_layer
        layer = get_channel_layer()
        if layer is None:
            return
        async_to_sync(layer.group_send)(
            GROUP,
            {"type": "broadcast", "payload": payload},
        )
    except Exception:
        import logging
        logging.getLogger(__name__).debug(
            "broadcast skipped", exc_info=True,
        )
