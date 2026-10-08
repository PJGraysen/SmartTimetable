

# ---------------------------------------------------------------------
# ErrorEnvelopeMiddleware  (Layer 1 ? global error handler)
# ---------------------------------------------------------------------
# Wraps every request. On an uncaught exception:
#   * writes an apps.audit.ErrorRecord
#   * returns a JSON envelope: {detail, code, hint, audit_id, status}
#   * the frontend http interceptor turns that into a toast
#
# Env override: ST_DEBUG_HTML=1  -> fall back to Django's debug page
# ---------------------------------------------------------------------
import os
import traceback
import uuid

from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin


class ErrorEnvelopeMiddleware(MiddlewareMixin):
    """Catch uncaught exceptions and return a JSON envelope."""

    def process_exception(self, request, exception):
        # Allow devs to fall back to Django's traceback page
        if os.environ.get("ST_DEBUG_HTML") == "1":
            return None

        audit_id = uuid.uuid4().hex[:12]

        # ---- record the error ----
        try:
            from apps.audit.models import (
                ErrorRecord, ErrorSeverity, ErrorStatus,
            )
            from apps.audit.services import record_error  # type: ignore
        except Exception:
            ErrorRecord = None

        if ErrorRecord is not None:
            try:
                user = getattr(request, "user", None)
                if user is not None and not getattr(user, "is_authenticated", False):
                    user = None

                xff = request.META.get("HTTP_X_FORWARDED_FOR")
                ip = (xff.split(",")[0].strip() if xff
                      else request.META.get("REMOTE_ADDR") or None)

                ErrorRecord.objects.create(
                    severity=ErrorSeverity.ERROR,
                    status=ErrorStatus.OPEN,
                    subsystem="http.request",
                    operation=f"{request.method} {request.path}",
                    error_code=audit_id,
                    message=str(exception)[:2000] or exception.__class__.__name__,
                    technical_exception=exception.__class__.__name__,
                    traceback="".join(traceback.format_exception(
                        type(exception), exception, exception.__traceback__,
                    ))[-8000:],
                    entity_type="HTTP",
                    entity_id=request.path[:100],
                    user=user,
                    details={
                        "audit_id": audit_id,
                        "method": request.method,
                        "path": request.path,
                        "query": dict(request.GET),
                        "ip": ip,
                        "user_agent": (request.META.get("HTTP_USER_AGENT") or "")[:300],
                    },
                )
            except Exception:
                # If the audit record fails, do not swallow the original error
                import logging
                logging.getLogger(__name__).exception(
                    "Failed to write ErrorRecord for %s", exception
                )

        # ---- JSON envelope ----
        payload = {
            "detail": "Something went wrong while processing your request.",
            "code": "INTERNAL_ERROR",
            "hint": (
                "Please try again. If this keeps happening, share the "
                f"reference ID with your administrator: {audit_id}"
            ),
            "audit_id": audit_id,
            "status": 500,
        }
        return JsonResponse(payload, status=500)


# ---------------------------------------------------------------------
# AuditMutationsMiddleware  (Layer 2 ? write AuditLog for every mutation)
# ---------------------------------------------------------------------
# After a successful unsafe request (POST/PUT/PATCH/DELETE, 2xx response),
# write an AuditLog row. Captures: user, action, inferred entity_type and
# entity_id, description, IP.
#
# Skips: /admin/, /api/schema/, /api/docs/, static, media, /api/audit/*
# Honors: header "X-Skip-Audit: 1" from the client
# ---------------------------------------------------------------------
import re as _re


_UUID_RE = _re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)

_SKIP_PATH_PREFIXES = (
    "/admin/",
    "/api/schema/",
    "/api/docs/",
    "/api/redoc/",
    "/api/audit/",
    "/static/",
    "/media/",
)


def _infer_entity_type(path: str) -> str:
    """Convert /api/academics/assessments/<uuid>/ to 'academics.assessments'."""
    parts = [p for p in path.split("/") if p]
    # Drop leading "api"
    if parts and parts[0] == "api":
        parts = parts[1:]
    # Drop UUID segments
    parts = [p for p in parts if not _UUID_RE.fullmatch(p)]
    if not parts:
        return "unknown"
    # Join everything except the last segment (usually the noun)
    if len(parts) == 1:
        return parts[0]
    return ".".join(parts)


def _infer_entity_id(path: str, response_body) -> str:
    """Extract UUID from URL or fall back to response body 'id'."""
    m = _UUID_RE.search(path)
    if m:
        return m.group(0)
    if isinstance(response_body, dict):
        for key in ("id", "pk", "uuid"):
            v = response_body.get(key)
            if v:
                return str(v)[:100]
    return ""


class AuditMutationsMiddleware(MiddlewareMixin):
    """Auto-audit every successful unsafe HTTP request."""

    def process_response(self, request, response):
        try:
            method = request.method.upper()
            if method not in ("POST", "PUT", "PATCH", "DELETE"):
                return response

            # Only successful mutations
            if response.status_code < 200 or response.status_code >= 300:
                return response

            # Skip opt-outs
            if request.META.get("HTTP_X_SKIP_AUDIT") == "1":
                return response

            path = request.path or ""
            for prefix in _SKIP_PATH_PREFIXES:
                if path.startswith(prefix):
                    return response

            # User (may be anonymous)
            user = getattr(request, "user", None)
            if user is None or not getattr(user, "is_authenticated", False):
                return response  # do not audit anonymous requests

            # Try to parse JSON body for id fallback
            body = None
            try:
                if (
                    hasattr(response, "data")
                    and isinstance(response.data, (dict, list))
                ):
                    body = response.data
                elif getattr(response, "content", None):
                    import json as _json
                    ct = response.get("Content-Type", "")
                    if "application/json" in ct and len(response.content) < 20000:
                        body = _json.loads(response.content.decode("utf-8"))
            except Exception:
                body = None

            # Action mapping
            if method == "POST":
                action = "CREATE"
            elif method == "DELETE":
                action = "DELETE"
            else:
                action = "UPDATE"

            entity_type = _infer_entity_type(path)[:100]
            entity_id = _infer_entity_id(path, body)[:100]

            # Description: method + path + short name/id hints
            desc_bits = [f"{method} {path}"]
            if isinstance(body, dict):
                for hint in ("name", "title", "label", "code"):
                    v = body.get(hint)
                    if v:
                        desc_bits.append(f"{hint}={str(v)[:60]}")
                        break
            description = " | ".join(desc_bits)[:1000]

            # IP
            xff = request.META.get("HTTP_X_FORWARDED_FOR")
            ip = (xff.split(",")[0].strip() if xff
                  else request.META.get("REMOTE_ADDR") or None)

            from apps.audit.models import AuditLog
            log = AuditLog.objects.create(
                user=user,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id or "-",
                description=description,
                ip_address=ip,
            )

            # Broadcast to admin live feed
            try:
                from apps.audit.broadcast import broadcast
                broadcast({
                    "type": "audit",
                    "id": str(log.id),
                    "created_at": log.created_at.isoformat(),
                    "user_username": user.username,
                    "user_name": (
                        f"{user.first_name} {user.last_name}".strip()
                        or user.username
                    ),
                    "action": action,
                    "entity_type": entity_type,
                    "entity_id": log.entity_id,
                    "description": description,
                    "ip_address": ip,
                })
            except Exception:
                pass
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                "AuditMutationsMiddleware failed for %s %s",
                request.method, request.path,
            )
        return response
