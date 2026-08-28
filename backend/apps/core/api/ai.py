import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .ai_service import deepseek_service


@csrf_exempt
@require_POST
def chat(request):
    """POST /api/ai/chat/."""

    try:
        payload = json.loads(
            request.body.decode("utf-8")
        )
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse(
            {
                "success": False,
                "error": "Request body must contain valid JSON.",
            },
            status=400,
        )

    messages = payload.get("messages")

    if not messages:
        message = payload.get("message")

        if not isinstance(message, str) or not message.strip():
            return JsonResponse(
                {
                    "success": False,
                    "error": (
                        "Provide either 'message' or "
                        "'messages'."
                    ),
                },
                status=400,
            )

        messages = [
            {
                "role": "user",
                "content": message.strip(),
            }
        ]

    if not isinstance(messages, list) or not messages:
        return JsonResponse(
            {
                "success": False,
                "error": "'messages' must be a non-empty array.",
            },
            status=400,
        )

    try:
        result = deepseek_service.chat(
            messages=messages,
            model=payload.get("model"),
        )

        choices = result.get("choices") or []

        if not choices:
            raise RuntimeError(
                "DeepSeek returned no choices."
            )

        assistant_message = choices[0].get("message") or {}

        return JsonResponse(
            {
                "success": True,
                "model": result.get("model"),
                "conversation_id": result.get(
                    "conversation_id"
                ),
                "content": assistant_message.get(
                    "content",
                    "",
                ),
                "response": result,
            }
        )

    except Exception as exc:
        return JsonResponse(
            {
                "success": False,
                "error": str(exc),
            },
            status=502,
        )
