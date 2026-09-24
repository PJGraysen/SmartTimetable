"""
Audit helper for academic mutations.

Usage from any view / serializer:

    from apps.academics.audit_util import log_event
    log_event(
        request,
        action="PUBLISH",
        entity_type="Assessment",
        entity_label=assessment.name,
        entity_id=assessment.id,
        meta={"from": "DRAFT", "to": "PUBLISHED"},
    )
"""
from apps.academics.models import AcademicAuditEvent


def log_event(
    request,
    action,
    entity_type,
    entity_label="",
    entity_id=None,
    meta=None,
):
    actor = None
    ip = None
    ua = ""
    if request is not None:
        user = getattr(request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            actor = user
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            ip = xff.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR") or None
        ua = (request.META.get("HTTP_USER_AGENT") or "")[:300]

    return AcademicAuditEvent.objects.create(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_label=entity_label,
        meta_json=meta or {},
        ip_address=ip,
        user_agent=ua,
    )