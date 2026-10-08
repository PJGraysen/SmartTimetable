"""
Book request workflow.

Student request → Subject teacher approval → Librarian approval → Book assigned.
All notifications go through apps.core.notifications.notify().
"""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.core.notifications import notify, notify_many, users_in_role
from apps.library.models import Book, Member, Reservation, Copy

User = get_user_model()


class RequestError(Exception):
    pass


def _member_for_user(user):
    """Return the library Member linked to this user, or None.

    A Member can be linked three ways:
      1. Member.user == user
      2. Member.student.user == user
      3. Member.teacher.user == user
    We try all three.
    """
    if not user or not user.is_authenticated:
        return None

    # Fast: direct user FK
    m = Member.objects.filter(user=user).first()
    if m:
        return m

    # Indirect via student
    from apps.academics.models import Student
    s = Student.objects.filter(user=user).first()
    if s:
        m = Member.objects.filter(student=s).first()
        if m:
            # Opportunistically heal the direct link
            if m.user_id != user.id:
                m.user = user
                m.save(update_fields=["user"])
            return m

    # Indirect via teacher
    from apps.users.models import Teacher
    t = Teacher.objects.filter(user=user).first()
    if t:
        m = Member.objects.filter(teacher=t).first()
        if m:
            if m.user_id != user.id:
                m.user = user
                m.save(update_fields=["user"])
            return m

    return None


def _subject_teacher_for(book):
    """Find the Teacher who teaches the primary subject of this book."""
    # Book.subjects is M2M to Subject
    subj = book.subjects.first()
    if not subj:
        return None
    # Look for any active LessonRequirement for this subject
    from apps.academics.models import LessonRequirement
    lr = (
        LessonRequirement.objects
        .filter(subject=subj, is_active=True, teacher__isnull=False)
        .select_related("teacher", "teacher__user")
        .first()
    )
    return lr.teacher if lr else None


def request_book(user, book_id) -> Reservation:
    """Create a book request. Auto-assigns the subject teacher."""
    member = _member_for_user(user)
    if member is None:
        raise RequestError(
            "You don't have a library membership. Contact the librarian."
        )

    book = Book.objects.filter(id=book_id, is_active=True).first()
    if not book:
        raise RequestError("Book not found or unavailable.")

    # Prevent duplicate pending requests
    existing = Reservation.objects.filter(
        book=book, member=member,
        approval_stage__in=("PENDING_TEACHER", "PENDING_LIBRARIAN"),
    ).first()
    if existing:
        raise RequestError("You already have a pending request for this book.")

    teacher = _subject_teacher_for(book)

    with transaction.atomic():
        res = Reservation.objects.create(
            book=book,
            member=member,
            status="PENDING",
            approval_stage="PENDING_TEACHER",
            subject_teacher=teacher,
            requested_at=timezone.now(),
            notes="",
        )

        if teacher and teacher.user:
            notify(
                teacher.user,
                title=f"Book request: {book.title}",
                body=f"{member.full_name} requests this book. Approve or reject.",
                kind="APPROVAL",
                url="/library/book-requests",
            )
        else:
            # No subject teacher found — go straight to librarian
            res.approval_stage = "PENDING_LIBRARIAN"
            res.save(update_fields=["approval_stage"])
            _notify_librarians(res)

    return res


def _notify_librarians(res):
    qs = users_in_role("LIBRARIAN")
    if qs.exists():
        notify_many(
            qs,
            title=f"Book request: {res.book.title}",
            body=f"{res.member.full_name} — ready for librarian approval.",
            kind="APPROVAL",
            url="/library/book-requests",
        )


def teacher_approve(res: Reservation, by_user, note: str = "") -> Reservation:
    """Move request to librarian stage."""
    if res.approval_stage != "PENDING_TEACHER":
        raise RequestError("This request is not awaiting teacher approval.")

    res.approval_stage = "PENDING_LIBRARIAN"
    res.teacher_approved_by = by_user
    res.teacher_approved_at = timezone.now()
    res.teacher_note = note
    res.save(update_fields=[
        "approval_stage", "teacher_approved_by",
        "teacher_approved_at", "teacher_note",
    ])

    _notify_librarians(res)
    notify(
        res.member.user,
        title=f"Teacher approved: {res.book.title}",
        body="Awaiting librarian confirmation.",
        kind="INFO",
        url="/library/my",
    )
    return res


def teacher_reject(res: Reservation, by_user, reason: str = "") -> Reservation:
    if res.approval_stage != "PENDING_TEACHER":
        raise RequestError("This request is not awaiting teacher approval.")

    res.approval_stage = "REJECTED"
    res.status = "CANCELLED"
    res.teacher_approved_by = by_user
    res.teacher_approved_at = timezone.now()
    res.teacher_note = reason
    res.rejection_reason = reason
    res.save(update_fields=[
        "approval_stage", "status", "teacher_approved_by",
        "teacher_approved_at", "teacher_note", "rejection_reason",
    ])
    notify(
        res.member.user,
        title=f"Book request declined: {res.book.title}",
        body=reason or "Your request was declined by the subject teacher.",
        kind="REJECTED",
        url="/library/my",
    )
    return res


def librarian_approve(res: Reservation, by_user, note: str = "") -> Reservation:
    if res.approval_stage != "PENDING_LIBRARIAN":
        raise RequestError("This request is not awaiting librarian approval.")

    # Try to reserve an available copy
    copy = Copy.objects.filter(
        book=res.book, status="AVAILABLE",
    ).first()

    res.approval_stage = "APPROVED"
    res.status = "READY"
    res.librarian_approved_by = by_user
    res.librarian_approved_at = timezone.now()
    res.librarian_note = note
    if copy:
        copy.status = "RESERVED"
        copy.save(update_fields=["status"])
    res.save(update_fields=[
        "approval_stage", "status", "librarian_approved_by",
        "librarian_approved_at", "librarian_note",
    ])

    notify(
        res.member.user,
        title=f"Book ready: {res.book.title}",
        body="Your request is approved. Collect from the library.",
        kind="APPROVED",
        url="/library/my",
    )
    return res


def librarian_reject(res: Reservation, by_user, reason: str = "") -> Reservation:
    if res.approval_stage != "PENDING_LIBRARIAN":
        raise RequestError("This request is not awaiting librarian approval.")

    res.approval_stage = "REJECTED"
    res.status = "CANCELLED"
    res.librarian_approved_by = by_user
    res.librarian_approved_at = timezone.now()
    res.librarian_note = reason
    res.rejection_reason = reason
    res.save(update_fields=[
        "approval_stage", "status", "librarian_approved_by",
        "librarian_approved_at", "librarian_note", "rejection_reason",
    ])
    notify(
        res.member.user,
        title=f"Book request declined: {res.book.title}",
        body=reason or "Your request was declined by the librarian.",
        kind="REJECTED",
        url="/library/my",
    )
    return res


def cancel_request(res: Reservation, by_user) -> Reservation:
    if res.member.user_id != by_user.id and not by_user.is_superuser:
        raise RequestError("You can only cancel your own requests.")
    if res.approval_stage not in ("PENDING_TEACHER", "PENDING_LIBRARIAN"):
        raise RequestError("Only pending requests can be cancelled.")
    res.approval_stage = "CANCELLED"
    res.status = "CANCELLED"
    res.save(update_fields=["approval_stage", "status"])
    return res



def hold_request(res: Reservation, by_user, note: str = "") -> Reservation:
    """Park the request on hold — no state change to book or member."""
    if res.approval_stage not in ("PENDING_TEACHER", "PENDING_LIBRARIAN"):
        raise RequestError("Only pending requests can be put on hold.")
    if res.approval_stage == "PENDING_TEACHER":
        res.teacher_note = note or res.teacher_note
        res.teacher_approved_by = by_user
        res.teacher_approved_at = timezone.now()
    else:
        res.librarian_note = note or res.librarian_note
        res.librarian_approved_by = by_user
        res.librarian_approved_at = timezone.now()
    res.approval_stage = "HOLD"
    res.save()
    notify(
        res.member.user,
        title=f"Book request on hold: {res.book.title}",
        body=note or "Your request is being reviewed by the librarian.",
        kind="INFO",
        url="/library/my",
    )
    return res


def resume_request(res: Reservation, by_user) -> Reservation:
    """Bring a held request back to PENDING_TEACHER."""
    if res.approval_stage != "HOLD":
        raise RequestError("This request is not on hold.")
    res.approval_stage = "PENDING_TEACHER"
    res.save(update_fields=["approval_stage"])
    return res



def award_request(res: Reservation, by_user, note: str = "") -> Reservation:
    """Librarian confirms the physical book has been handed to the student."""
    if res.approval_stage != "APPROVED":
        raise RequestError("Only approved requests can be marked as awarded.")

    res.approval_stage = "AWARDED"
    res.status = "ISSUED"
    if note:
        existing = res.librarian_note or ""
        res.librarian_note = (existing + "\n" + note).strip()
    res.save()

    # Mark the reserved copy as ISSUED
    try:
        copy = Copy.objects.filter(book=res.book, status="RESERVED").first()
        if copy:
            copy.status = "ISSUED"
            copy.save(update_fields=["status"])
    except Exception:
        pass

    notify(
        res.member.user,
        title=f"Book awarded: {res.book.title}",
        body="Your book has been issued. Enjoy reading!",
        kind="APPROVED",
        url="/library/my",
    )

    # Also notify admins/principal for oversight
    try:
        admin_qs = users_in_role("ADMIN") | users_in_role("PRINCIPAL")
        if admin_qs.exists():
            notify_many(
                admin_qs,
                title=f"Book awarded: {res.book.title}",
                body=f"{res.member.full_name} received this book from the librarian.",
                kind="INFO",
                url="/library/book-requests",
            )
    except Exception:
        pass

    return res
