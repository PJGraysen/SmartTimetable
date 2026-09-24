"""
AI gateway.

  POST /api/ai/chat/
    body: { messages: [{role, content}, ...] }
          or { message: "..." }
          optional: mode = "chat" | "code"
          optional: model = "<explicit model name>"

  - mode "chat"  → general chat model (qwen2.5:3b).  Any authenticated user.
  - mode "code"  → code assistance model (deepseek-coder:1.3b).  Admin only.

Every "code" call is written to the academic audit trail so we know who
ran what and when.
"""
import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .ai_service import deepseek_service


def _is_admin(request) -> bool:
    u = getattr(request, "user", None)
    return bool(
        u
        and getattr(u, "is_authenticated", False)
        and (u.is_staff or u.is_superuser)
    )


def _audit(request, mode, model, prompt_preview, ok):
    try:
        from apps.academics.audit_util import log_event
        log_event(
            request,
            action="UPDATE",
            entity_type="AIRequest",
            entity_label=f"{mode} · {model} · {'ok' if ok else 'error'}",
            meta={
                "mode": mode,
                "model": model,
                "prompt_preview": (prompt_preview or "")[:180],
                "ok": ok,
            },
        )
    except Exception:
        # audit is best-effort — never let it break the AI call
        pass


@csrf_exempt
@require_POST
def chat(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse(
            {"success": False, "error": "Request body must contain valid JSON."},
            status=400,
        )

    mode = payload.get("mode") or "chat"
    if mode not in ("chat", "code"):
        return JsonResponse(
            {"success": False, "error": "mode must be 'chat' or 'code'."},
            status=400,
        )

    # Code mode requires admin. Chat mode requires authentication.
    if mode == "code" and not _is_admin(request):
        return JsonResponse(
            {"success": False, "error": "Code mode requires administrator access."},
            status=403,
        )

    messages = payload.get("messages")

    if not messages:
        single = payload.get("message")
        if not isinstance(single, str) or not single.strip():
            return JsonResponse(
                {"success": False, "error": "Provide either 'message' or 'messages'."},
                status=400,
            )
        messages = [{"role": "user", "content": single.strip()}]

    if not isinstance(messages, list) or not messages:
        return JsonResponse(
            {"success": False, "error": "'messages' must be a non-empty array."},
            status=400,
        )

    # Non-admin: strip any system prompt they tried to inject so teachers
    # can't impersonate admin context. Admin keeps full control.
    if not _is_admin(request):
        messages = [m for m in messages if m.get("role") != "system"]

    # Pick the model
    explicit_model = payload.get("model")
    chosen_model = explicit_model or deepseek_service.model_for(mode)

    # Preview for the audit trail
    user_msgs = [m for m in messages if m.get("role") == "user"]
    preview = user_msgs[-1].get("content") if user_msgs else ""

    try:
        result = deepseek_service.chat(
            messages=messages,
            model=chosen_model,
            mode=mode,
        )
        choices = result.get("choices") or []
        if not choices:
            raise RuntimeError("AI endpoint returned no choices.")

        assistant_message = choices[0].get("message") or {}
        content = assistant_message.get("content", "")

        if mode == "code":
            _audit(request, mode, chosen_model, preview, ok=True)

        return JsonResponse({
            "success": True,
            "mode": mode,
            "model": result.get("model") or chosen_model,
            "content": content,
            "response": result,
        })

    except Exception as exc:
        if mode == "code":
            _audit(request, mode, chosen_model, preview, ok=False)
        return JsonResponse({"success": False, "error": str(exc)}, status=502)