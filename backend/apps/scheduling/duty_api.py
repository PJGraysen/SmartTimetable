"""
Duty Roster API (Session 3, weekly rotation).

Each week (Mon–Sun) has exactly two teachers:
  * DAY   one teacher covers 06:00–18:00 for the whole week
  * NIGHT one teacher covers 18:00–06:00 for the whole week

DutyAssignment.date stores the Monday of the week.

Eligibility: Teacher.duty_eligible (defaults True; admins set False for
librarian, principal, deputy, etc.).

Preference: Teacher.duty_preference — DAY_ONLY teachers never get night slots.

Rotation: /auto-rotate picks the least-used eligible teacher for each slot,
so over a term every teacher gets 2–3 duties.
"""
from datetime import date as _date, datetime, timedelta

from django.db import transaction
from django.db.models import Count
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from apps.users.models import Teacher, DutyPreference
from apps.scheduling.models import DutyAssignment, DutyShift


def _monday(d):
    return d - timedelta(days=d.weekday())


def _payload(d):
    return {
        "id": str(d.id),
        "week_start": d.date.isoformat(),
        "week_end": (d.date + timedelta(days=6)).isoformat(),
        "shift": d.shift,
        "teacher_id": str(d.teacher_id),
        "teacher_name": f"{d.teacher.first_name} {d.teacher.last_name}".strip(),
        "teacher_code": d.teacher.employee_code,
        "notes": d.notes,
        "is_active": d.is_active,
    }


def _eligible_qs():
    return Teacher.objects.filter(is_active=True, duty_eligible=True)


@api_view(["GET"])
@permission_classes([IsAdminUser])
def duty_roster(request):
    ws = request.query_params.get("week_start")
    try:
        num_weeks = int(request.query_params.get("weeks", "8"))
    except ValueError:
        num_weeks = 8
    num_weeks = max(1, min(num_weeks, 26))

    if ws:
        try:
            d = datetime.strptime(ws, "%Y-%m-%d").date()
        except ValueError:
            d = _date.today()
    else:
        d = _date.today()
    start = _monday(d)
    end = start + timedelta(days=7 * num_weeks - 1)

    rows = (
        DutyAssignment.objects
        .filter(date__gte=start, date__lte=end, is_active=True)
        .select_related("teacher")
    )
    by_week = {}
    for r in rows:
        by_week.setdefault(r.date.isoformat(), {})[r.shift] = _payload(r)

    weeks = []
    cursor = start
    for _ in range(num_weeks):
        key = cursor.isoformat()
        weeks.append({
            "week_start": key,
            "week_end": (cursor + timedelta(days=6)).isoformat(),
            "day": by_week.get(key, {}).get(DutyShift.DAY),
            "night": by_week.get(key, {}).get(DutyShift.NIGHT),
        })
        cursor += timedelta(days=7)

    eligible = [
        {
            "id": str(t.id),
            "code": t.employee_code,
            "name": f"{t.first_name} {t.last_name}".strip(),
            "preference": t.duty_preference,
            "day_ok": True,
            "night_ok": t.duty_preference != DutyPreference.DAY_ONLY,
        }
        for t in _eligible_qs().order_by("employee_code")
    ]

    return Response({
        "week_start": start.isoformat(),
        "week_end": end.isoformat(),
        "weeks": weeks,
        "eligible_teachers": eligible,
    })


@api_view(["POST"])
@permission_classes([IsAdminUser])
def duty_assign(request):
    ws = request.data.get("week_start")
    shift = (request.data.get("shift") or "").upper()
    tid = request.data.get("teacher_id")
    notes = (request.data.get("notes") or "")[:300]

    if not ws or shift not in {DutyShift.DAY, DutyShift.NIGHT} or not tid:
        return Response({"detail": "week_start, shift (DAY|NIGHT), teacher_id required"}, status=400)
    try:
        d = _monday(datetime.strptime(ws, "%Y-%m-%d").date())
    except ValueError:
        return Response({"detail": "week_start must be YYYY-MM-DD"}, status=400)
    try:
        t = Teacher.objects.get(id=tid)
    except Teacher.DoesNotExist:
        return Response({"detail": "teacher not found"}, status=404)
    if not t.duty_eligible:
        return Response({
            "detail": f"{t.first_name} {t.last_name} is not on the duty roster.",
        }, status=409)
    if shift == DutyShift.NIGHT and t.duty_preference == DutyPreference.DAY_ONLY:
        return Response({
            "detail": f"{t.first_name} {t.last_name} is day-shift only (lives off-campus).",
        }, status=409)

    clash = DutyAssignment.objects.filter(date=d, teacher=t, is_active=True).exclude(shift=shift)
    if clash.exists():
        return Response({
            "detail": f"{t.first_name} {t.last_name} already covers {clash.first().shift} that week.",
        }, status=409)

    with transaction.atomic():
        existing = DutyAssignment.objects.filter(date=d, shift=shift, is_active=True).first()
        if existing:
            existing.teacher = t
            existing.notes = notes
            existing.save(update_fields=["teacher", "notes", "updated_at"])
            return Response({"ok": True, "updated": True, "assignment": _payload(existing)})
        obj = DutyAssignment.objects.create(date=d, shift=shift, teacher=t, notes=notes, is_active=True)
    return Response({"ok": True, "created": True, "assignment": _payload(obj)})


@api_view(["DELETE"])
@permission_classes([IsAdminUser])
def duty_unassign(request, pk):
    try:
        obj = DutyAssignment.objects.get(id=pk)
    except DutyAssignment.DoesNotExist:
        return Response({"detail": "not found"}, status=404)
    obj.is_active = False
    obj.save(update_fields=["is_active", "updated_at"])
    return Response({"ok": True})


@api_view(["GET", "PUT", "PATCH"])
@permission_classes([IsAdminUser])
def teacher_duty_preference(request, teacher_id):
    try:
        t = Teacher.objects.get(id=teacher_id)
    except Teacher.DoesNotExist:
        return Response({"detail": "teacher not found"}, status=404)
    if request.method == "GET":
        return Response({"teacher_id": str(t.id), "preference": t.duty_preference})
    pref = str(request.data.get("preference") or "").upper()
    valid = {c for c, _ in DutyPreference.choices}
    if pref not in valid:
        return Response({"detail": f"invalid. valid: {sorted(valid)}"}, status=400)
    t.duty_preference = pref
    t.save(update_fields=["duty_preference"])
    return Response({"ok": True, "preference": t.duty_preference})


@api_view(["POST"])
@permission_classes([IsAdminUser])
def duty_auto_rotate(request):
    """Fair rotation proposal. body: {start, weeks, apply?}."""
    start_str = request.data.get("start")
    try:
        weeks_n = int(request.data.get("weeks") or 0)
    except (TypeError, ValueError):
        return Response({"detail": "weeks must be a number"}, status=400)
    apply_ = bool(request.data.get("apply"))

    if not start_str or weeks_n <= 0:
        return Response({"detail": "start and weeks > 0 required"}, status=400)
    try:
        start = _monday(datetime.strptime(start_str, "%Y-%m-%d").date())
    except ValueError:
        return Response({"detail": "start must be YYYY-MM-DD"}, status=400)

    teachers = list(_eligible_qs())
    if len(teachers) < 2:
        return Response({"detail": "need at least 2 eligible teachers"}, status=400)

    # History: how many duties each teacher already has on record
    history = {t.id: 0 for t in teachers}
    for tid, n in (
        DutyAssignment.objects.filter(teacher__in=teachers, is_active=True)
        .values_list("teacher_id").annotate(n=Count("id"))
    ):
        history[tid] = n

    def pick(exclude_ids, shift):
        pool = [
            t for t in teachers
            if t.id not in exclude_ids
            and (shift != DutyShift.NIGHT or t.duty_preference != DutyPreference.DAY_ONLY)
        ]
        if not pool:
            return None
        pool.sort(key=lambda t: (history[t.id], t.employee_code))
        return pool[0]

    plan = []
    cursor = start
    for _ in range(weeks_n):
        day_t = pick(set(), DutyShift.DAY)
        night_t = pick({day_t.id} if day_t else set(), DutyShift.NIGHT)
        if not day_t or not night_t:
            break
        plan.append({
            "week_start": cursor.isoformat(),
            "week_end": (cursor + timedelta(days=6)).isoformat(),
            "day": {"id": str(day_t.id), "code": day_t.employee_code,
                    "name": f"{day_t.first_name} {day_t.last_name}".strip()},
            "night": {"id": str(night_t.id), "code": night_t.employee_code,
                      "name": f"{night_t.first_name} {night_t.last_name}".strip()},
        })
        history[day_t.id] += 1
        history[night_t.id] += 1
        cursor += timedelta(days=7)

    if apply_:
        with transaction.atomic():
            cursor = start
            for row in plan:
                for shift_key, key_upper in (("day", "DAY"), ("night", "NIGHT")):
                    DutyAssignment.objects.update_or_create(
                        date=cursor, shift=key_upper,
                        defaults={"teacher_id": row[shift_key]["id"], "is_active": True},
                    )
                cursor += timedelta(days=7)

    return Response({
        "plan": plan,
        "counts": {str(k): v for k, v in history.items()},
        "applied": apply_,
    })
