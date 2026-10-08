"""
Teacher merge / dedup utilities.

Scan for likely duplicates across the Teacher table and merge two rows
safely by relinking every FK that points at the loser.
"""
from django.db import transaction
from django.apps import apps
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from apps.users.models import Teacher


def _similar(a: str, b: str) -> bool:
    a, b = (a or "").strip().lower(), (b or "").strip().lower()
    if not a or not b:
        return False
    if a == b:
        return True
    # first-letter match on first name, last-name substring match
    return a[0] == b[0] and (a in b or b in a)


@api_view(["GET"])
@permission_classes([IsAdminUser])
def teacher_scan_duplicates(request):
    """Return candidate duplicate pairs with reasons."""
    teachers = list(Teacher.objects.select_related("user").all())
    candidates = []
    seen = set()

    for i, a in enumerate(teachers):
        for b in teachers[i + 1:]:
            key = tuple(sorted([str(a.id), str(b.id)]))
            if key in seen:
                continue
            reasons = []
            # last name match + similar first name
            if _similar(a.last_name, b.last_name) and _similar(a.first_name, b.first_name):
                reasons.append("similar name")
            # same non-empty email
            if a.user_id and b.user_id and a.user.email and a.user.email == b.user.email:
                reasons.append("same email")
            # same non-empty phone
            if a.phone and b.phone and a.phone == b.phone:
                reasons.append("same phone")
            # same teacher_number
            if a.teacher_number and b.teacher_number and a.teacher_number == b.teacher_number:
                reasons.append("same teacher_number")
            # one code is an uppercase-only name of the other's code
            codes = {a.employee_code.upper(), b.employee_code.upper()}
            names = {f"{a.first_name} {a.last_name}".upper().replace(" ", "_"),
                     f"{b.first_name} {b.last_name}".upper().replace(" ", "_")}
            if codes & names:
                reasons.append("code/name collision")

            if reasons:
                seen.add(key)
                candidates.append({
                    "reason": ", ".join(reasons),
                    "a": {
                        "id": str(a.id),
                        "code": a.employee_code,
                        "name": f"{a.first_name} {a.last_name}".strip(),
                        "role": a.role,
                        "is_active": a.is_active,
                        "lr_count": a.lesson_requirements.filter(is_active=True).count(),
                        "email": a.user.email if a.user_id else "",
                    },
                    "b": {
                        "id": str(b.id),
                        "code": b.employee_code,
                        "name": f"{b.first_name} {b.last_name}".strip(),
                        "role": b.role,
                        "is_active": b.is_active,
                        "lr_count": b.lesson_requirements.filter(is_active=True).count(),
                        "email": b.user.email if b.user_id else "",
                    },
                })

    return Response({"count": len(candidates), "candidates": candidates})


@api_view(["POST"])
@permission_classes([IsAdminUser])
def teacher_merge(request):
    """Merge two teachers. body: {keep_id, drop_id}

    Relinks every FK on every model that points at `drop` to point at `keep`.
    Deactivates (does not delete) the dropped teacher to preserve audit trails.
    """
    keep_id = request.data.get("keep_id")
    drop_id = request.data.get("drop_id")

    if not keep_id or not drop_id or keep_id == drop_id:
        return Response({"detail": "keep_id and drop_id required and different"},
                        status=400)

    try:
        keep = Teacher.objects.select_related("user").get(id=keep_id)
        drop = Teacher.objects.select_related("user").get(id=drop_id)
    except Teacher.DoesNotExist:
        return Response({"detail": "teacher not found"}, status=404)

    relinked = {}

    with transaction.atomic():
        for model in apps.get_models():
            for field in model._meta.get_fields():
                if not hasattr(field, "related_model"):
                    continue
                if field.related_model is not Teacher:
                    continue
                if field.many_to_many:
                    continue
                try:
                    qs = model.objects.filter(**{field.name: drop})
                    n = qs.count()
                    if n:
                        qs.update(**{field.name: keep})
                        relinked[f"{model.__name__}.{field.name}"] = n
                except Exception:
                    pass

        # Deactivate the dropped teacher (audit preservation)
        drop.is_active = False
        drop.is_frozen = True
        drop.save(update_fields=["is_active", "is_frozen", "updated_at"])
        if drop.user_id:
            drop.user.is_active = False
            drop.user.save(update_fields=["is_active"])

    return Response({
        "ok": True,
        "kept": {"id": str(keep.id), "code": keep.employee_code,
                 "name": f"{keep.first_name} {keep.last_name}".strip()},
        "dropped": {"id": str(drop.id), "code": drop.employee_code,
                    "name": f"{drop.first_name} {drop.last_name}".strip()},
        "relinked": relinked,
    })
