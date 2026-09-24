from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.library.models import Copy, Reservation
from apps.library.services.audit import log_library_action


class ReservationError(Exception):
    pass


def _next_position(book) -> int:
    from django.db.models import Max
    current = Reservation.objects.filter(
        book=book, status=Reservation.Status.WAITING,
    ).aggregate(m=Max("position")).get("m")
    return (current or 0) + 1


@transaction.atomic
def create_reservation(*, book, member, by_user) -> Reservation:
    if not member.is_active:
        raise ReservationError("Member is inactive.")
    if Reservation.objects.filter(
        book=book, member=member, status=Reservation.Status.WAITING,
    ).exists():
        raise ReservationError("Member already has a waiting reservation for this book.")

    reservation = Reservation.objects.create(
        book=book,
        member=member,
        status=Reservation.Status.WAITING,
        position=_next_position(book),
    )
    log_library_action(
        user=by_user,
        action="library.resv.create",
        entity_type="Reservation",
        entity_id=str(reservation.id),
        description=f"Reserved {book.title} for {member.member_number}",
    )
    return reservation


@transaction.atomic
def cancel_reservation(*, reservation: Reservation, by_user) -> Reservation:
    reservation.status = Reservation.Status.CANCELLED
    reservation.save(update_fields=["status", "updated_at"])
    log_library_action(
        user=by_user,
        action="library.resv.cancel",
        entity_type="Reservation",
        entity_id=str(reservation.id),
        description=f"Cancelled reservation for {reservation.book.title}",
    )
    return reservation


@transaction.atomic
def promote_next_waiting(*, book, by_user=None) -> Reservation | None:
    """
    When a copy becomes available, promote the oldest WAITING reservation
    to READY and set a pickup deadline.
    """
    waiting = (
        Reservation.objects
        .filter(book=book, status=Reservation.Status.WAITING)
        .order_by("position", "requested_at")
        .first()
    )
    if waiting is None:
        return None
    waiting.status = Reservation.Status.READY
    waiting.notified_at = timezone.now()
    waiting.expires_at = timezone.now() + timedelta(days=3)
    waiting.save(update_fields=["status", "notified_at", "expires_at", "updated_at"])
    return waiting
