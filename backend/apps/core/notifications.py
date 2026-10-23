"""
Notification helper. All notifications go through notify() so future
routing (email, SMS, push) plugs in one place.
"""
from typing import Iterable, Optional

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from apps.core.models import Notification, ApprovalRequest
from apps.core.roles import Role


User = get_user_model()


def notify(
    recipient,
    *,
    title: str,
    body: str = "",
    kind: str = Notification.Kind.INFO,
    url: str = "",
    sender=None,
    parent=None,
    attachment=None,
    attachment_name: str = "",
) -> Optional[Notification]:
    """Create a single notification. Returns the row (or None for anonymous)."""
    if not recipient or not getattr(recipient, "pk", None):
        return None
    return Notification.objects.create(
        recipient=recipient,
        sender=sender,
        parent=parent,
        kind=kind,
        title=title,
        body=body,
        url=url,
        attachment=attachment,
        attachment_name=attachment_name,
    )


def notify_many(recipients, *, title, body="", kind=Notification.Kind.INFO, url=""):
    """Fan-out helper. Accepts a queryset or iterable of users."""
    if isinstance(recipients, QuerySet):
        recipients = list(recipients)
    created = []
    for u in recipients or []:
        n = notify(u, title=title, body=body, kind=kind, url=url)
        if n:
            created.append(n)
    return created


def users_in_role(role_name: str):
    """All active users whose group is the given role."""
    return User.objects.filter(groups__name=role_name, is_active=True).distinct()


def principals():
    """Principals first; fall back to ADMIN if no PRINCIPAL exists."""
    qs = users_in_role(Role.PRINCIPAL)
    if qs.exists():
        return qs
    return users_in_role(Role.ADMIN)


def create_approval(
    *,
    kind: str,
    title: str,
    requested_by,
    assigned_to,
    body: str = "",
    target_type: str = "",
    target_id: str = "",
    payload: dict | None = None,
) -> ApprovalRequest:
    """Create an ApprovalRequest and notify the assignee."""
    req = ApprovalRequest.objects.create(
        kind=kind,
        title=title,
        body=body,
        requested_by=requested_by,
        assigned_to=assigned_to,
        target_type=target_type,
        target_id=target_id,
        payload=payload or {},
    )
    notify(
        assigned_to,
        title=f"Approval needed: {title}",
        body=body,
        kind=Notification.Kind.APPROVAL,
        url="/library/book-requests",
    )
    return req


def resolve_approval(req: ApprovalRequest, *, approved: bool, by_user, note: str = ""):
    """Finalise an approval: set status, notify the requester."""
    if approved:
        req.approve(by_user, note)
        notify(
            req.requested_by,
            title=f"Approved: {req.title}",
            body=note or "Your request has been approved.",
            kind=Notification.Kind.APPROVED,
            url="/library/book-requests",
        )
    else:
        req.reject(by_user, note)
        notify(
            req.requested_by,
            title=f"Rejected: {req.title}",
            body=note or "Your request was rejected.",
            kind=Notification.Kind.REJECTED,
            url="/library/book-requests",
        )
    return req
