"""Notification engine — email via Django mail, SMS/push stubs."""
from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from apps.library.models import Loan, Notification, Reservation


def _channel_for(member):
    """Choose best channel: EMAIL if member has email, else IN_APP."""
    if member.email:
        return Notification.Channel.EMAIL
    return Notification.Channel.IN_APP


@transaction.atomic
def notify_member(*, member, kind, subject, body, ref_type="", ref_id="",
                  channel=None) -> Notification:
    ch = channel or _channel_for(member)
    n = Notification.objects.create(
        member=member, kind=kind, channel=ch,
        subject=subject[:200], body=body,
        reference_type=ref_type, reference_id=ref_id,
        status=Notification.Status.PENDING,
    )
    delivered = _deliver(n)
    return delivered


def _deliver(n: Notification) -> Notification:
    try:
        if n.channel == Notification.Channel.EMAIL and n.member.email:
            send_mail(
                subject=n.subject or "Library notification",
                message=n.body,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL",
                                   "library@smarttimetable.local"),
                recipient_list=[n.member.email],
                fail_silently=True,
            )
            n.status = Notification.Status.SENT
            n.sent_at = timezone.now()
        elif n.channel == Notification.Channel.SMS:
            # TODO: plug in SMS provider (Africa's Talking, Twilio)
            n.status = Notification.Status.SENT
            n.sent_at = timezone.now()
        elif n.channel == Notification.Channel.PUSH:
            # TODO: plug in Web Push provider
            n.status = Notification.Status.SENT
            n.sent_at = timezone.now()
        else:
            # In-app — mark sent immediately; UI reads it
            n.status = Notification.Status.SENT
            n.sent_at = timezone.now()
    except Exception:
        n.status = Notification.Status.FAILED
    n.save(update_fields=["status", "sent_at"])
    return n


# ---------------- Event hooks ----------------

def on_fine_accrued(loan: Loan):
    if not loan.fine_accrued or loan.fine_accrued <= 0:
        return None
    body = (
        f"Hello {loan.member.full_name},\n\n"
        f"A fine of {loan.fine_accrued} has been accrued on your loan of "
        f"'{loan.copy.book.title if loan.copy and loan.copy.book else 'a book'}'.\n"
        f"Please settle it at the circulation desk.\n\n"
        f"— Library, SmartTimetable Pro"
    )
    return notify_member(
        member=loan.member, kind=Notification.Kind.FINE_ACCRUED,
        subject="Library fine accrued",
        body=body, ref_type="library.Loan", ref_id=str(loan.id),
    )


def on_hold_ready(reservation: Reservation):
    body = (
        f"Hello {reservation.member.full_name},\n\n"
        f"Your hold on '{reservation.book.title}' is ready for pickup.\n"
        f"Please collect it within 3 days.\n\n— Library"
    )
    return notify_member(
        member=reservation.member, kind=Notification.Kind.HOLD_READY,
        subject=f"Hold ready: {reservation.book.title}",
        body=body, ref_type="library.Reservation", ref_id=str(reservation.id),
    )


def scan_due_and_overdue(*, due_soon_days: int = 3) -> dict:
    """Daily command: emit DUE_SOON and OVERDUE notifications."""
    now = timezone.now()
    horizon = now + timedelta(days=due_soon_days)
    sent = {"due_soon": 0, "overdue": 0}

    for loan in Loan.objects.filter(status=Loan.Status.ACTIVE).select_related(
        "member", "copy__book"
    ):
        title = loan.copy.book.title if loan.copy and loan.copy.book else "your book"
        if loan.due_at < now:
            body = (
                f"Hello {loan.member.full_name},\n\n"
                f"'{title}' was due on {loan.due_at:%d %b %Y} and is now overdue.\n"
                f"Please return it promptly to stop further fines.\n\n— Library"
            )
            notify_member(
                member=loan.member, kind=Notification.Kind.OVERDUE,
                subject=f"Overdue: {title}", body=body,
                ref_type="library.Loan", ref_id=str(loan.id),
            )
            sent["overdue"] += 1
        elif loan.due_at <= horizon:
            body = (
                f"Hello {loan.member.full_name},\n\n"
                f"Reminder: '{title}' is due on {loan.due_at:%d %b %Y}.\n"
                f"Please return or renew it.\n\n— Library"
            )
            notify_member(
                member=loan.member, kind=Notification.Kind.DUE_SOON,
                subject=f"Due soon: {title}", body=body,
                ref_type="library.Loan", ref_id=str(loan.id),
            )
            sent["due_soon"] += 1

    return sent
