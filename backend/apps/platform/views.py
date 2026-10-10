from __future__ import annotations
from apps.core.roles import modules_for_user, primary_role

from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import throttle_classes

from apps.core.throttles import LoginRateThrottle
from apps.audit.models import (
    LoginAttempt, LoginOutcome, UserSecurity, security_for,
)

from .applications import applications_for_user


def _serialize_user(user) -> dict | None:
    if user is None or not getattr(user, "is_authenticated", False):
        return None

    # Prefer the real name from the linked Teacher or Student record, since
    # User.first_name / last_name are often empty for imported accounts.
    real_first = user.first_name or ""
    real_last = user.last_name or ""

    if not (real_first or real_last):
        try:
            t = getattr(user, "teacher_profile", None)
            if t is None:
                from apps.users.models import Teacher
                t = Teacher.objects.filter(user=user).first()
            if t:
                real_first = t.first_name or ""
                real_last = t.last_name or ""
        except Exception:
            pass

    if not (real_first or real_last):
        try:
            from apps.academics.models import Student
            s = Student.objects.filter(user=user).first()
            if s:
                real_first = getattr(s, "first_name", "") or ""
                real_last = getattr(s, "last_name", "") or ""
        except Exception:
            pass

    full_name = f"{real_first} {real_last}".strip()
    display_name = full_name or user.get_username()
    return {
        "id": user.id,
        "username": user.get_username(),
        "display_name": display_name,
        "is_superuser": bool(user.is_superuser),
    }


def _serialize_applications(user) -> list[dict]:
    return [a.to_dict() for a in applications_for_user(user)]


# ---------------------------------------------------------------------
# Login security helpers
# ---------------------------------------------------------------------
LOCKOUT_THRESHOLD = 3
LOCKOUT_MINUTES = 15
CODE_TTL_MINUTES = 15


def _client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") or None


def _log_attempt(request, username, outcome, user=None, details=None):
    try:
        LoginAttempt.objects.create(
            username_attempted=(username or "-")[:150],
            user=user,
            outcome=outcome,
            ip_address=_client_ip(request),
            user_agent=(request.META.get("HTTP_USER_AGENT") or "")[:500],
            details=details or {},
        )
    except Exception:
        import logging
        logging.getLogger(__name__).exception("LoginAttempt log failed")


def _generate_code():
    import secrets
    return "".join(secrets.choice("0123456789") for _ in range(6))


def _send_code(user, code, security):
    """Send verification code by email or console. Never raises."""
    from django.core.mail import send_mail
    from django.conf import settings as _s

    # Dev convenience: always write to a well-known file so the code can be
    # retrieved with a single shell command during local testing.
    try:
        import os as _os
        from django.conf import settings as _s2
        base = Path = None  # noqa
        from pathlib import Path as _P
        base = _P(_s2.BASE_DIR)
        log = base / "last_verify_code.txt"
        log.write_text(
            f"user={user.username}\ncode={code}\n",
            encoding="utf-8",
        )
    except Exception:
        pass

    to_email = (getattr(user, "email", "") or "").strip()
    if not to_email:
        # No email: print to console so admin can read from logs
        print(f"[LOGIN-VERIFY] user={user.username} code={code}")
        return "console"

    try:
        send_mail(
            subject="Your SmartTimetable verification code",
            message=f"Your verification code is: {code}\n\nIt expires in {CODE_TTL_MINUTES} minutes.",
            from_email=getattr(_s, "DEFAULT_FROM_EMAIL", None) or "no-reply@smarttimetable.local",
            recipient_list=[to_email],
            fail_silently=True,
        )
        return "email"
    except Exception:
        print(f"[LOGIN-VERIFY] user={user.username} code={code}")
        return "console"


def _unlock_and_clear(user, security):
    """Clear lockout state and verification flag on success."""
    from django.utils import timezone
    security.failed_attempts = 0
    security.locked_until = None
    security.requires_verification = False
    security.verification_code_hash = ""
    security.verification_sent_at = None
    security.verification_purpose = ""
    security.last_successful_login_at = timezone.now()
    security.save(update_fields=[
        "failed_attempts", "locked_until", "requires_verification",
        "verification_code_hash", "verification_sent_at",
        "verification_purpose", "last_successful_login_at", "updated_at",
    ])



@csrf_exempt
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def login_view(request):
    from django.utils import timezone
    from django.contrib.auth import get_user_model
    from django.contrib.auth.hashers import make_password
    from datetime import timedelta

    U = get_user_model()

    username = str(request.data.get("username", "")).strip()
    password = str(request.data.get("password", ""))

    if not username or not password:
        return Response(
            {"detail": "Username and password are required.",
             "code": "MISSING_CREDENTIALS"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = U.objects.filter(username__iexact=username).first()

    if user is None:
        _log_attempt(request, username, LoginOutcome.NO_SUCH_USER)
        # Same message as bad password ? no user enumeration
        return Response(
            {"detail": "Invalid credentials.", "code": "BAD_CREDS"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    security = security_for(user)

    # Already locked?
    if security.is_locked():
        _log_attempt(request, username, LoginOutcome.LOCKED, user=user)
        remaining = int((security.locked_until - timezone.now()).total_seconds() / 60) + 1
        return Response(
            {
                "detail": f"Account locked. Try again in about {remaining} minute(s).",
                "code": "LOCKED",
                "retry_after_minutes": remaining,
            },
            status=423,
        )

    if not user.is_active:
        _log_attempt(request, username, LoginOutcome.INACTIVE, user=user)
        return Response(
            {"detail": "Account is inactive.", "code": "INACTIVE"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    authed = authenticate(request, username=user.username, password=password)
    if authed is None:
        security.failed_attempts += 1
        fields = ["failed_attempts", "updated_at"]

        if security.failed_attempts >= LOCKOUT_THRESHOLD:
            security.locked_until = timezone.now() + timedelta(minutes=LOCKOUT_MINUTES)
            security.requires_verification = True
            security.verification_purpose = "post_lockout"
            fields += ["locked_until", "requires_verification", "verification_purpose"]
            security.save(update_fields=fields)
            _log_attempt(request, username, LoginOutcome.LOCKED, user=user,
                         details={"failed_attempts": security.failed_attempts})
            return Response(
                {
                    "detail": (
                        f"Too many failed attempts. Account locked for "
                        f"{LOCKOUT_MINUTES} minutes. After unlocking you will "
                        "be asked to verify by email or phone."
                    ),
                    "code": "LOCKED",
                    "retry_after_minutes": LOCKOUT_MINUTES,
                },
                status=423,
            )

        security.save(update_fields=fields)
        _log_attempt(request, username, LoginOutcome.BAD_PASSWORD, user=user,
                     details={"failed_attempts": security.failed_attempts})
        remaining = LOCKOUT_THRESHOLD - security.failed_attempts
        return Response(
            {
                "detail": f"Invalid credentials. {remaining} attempt(s) left before lockout.",
                "code": "BAD_CREDS",
                "attempts_left": remaining,
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Correct password. Does this user still need verification?
    if security.requires_verification:
        code = _generate_code()
        security.verification_code_hash = make_password(code)
        security.verification_sent_at = timezone.now()
        security.save(update_fields=[
            "verification_code_hash", "verification_sent_at", "updated_at",
        ])
        channel = _send_code(user, code, security)
        _log_attempt(request, username, LoginOutcome.PENDING_VERIFY, user=user,
                     details={"channel": channel})
        return Response(
            {
                "detail": "Password accepted. Verification code required.",
                "code": "VERIFICATION_REQUIRED",
                "channel": channel,
            },
            status=202,
        )

    # Normal successful login
    login(request, user)
    _unlock_and_clear(user, security)
    _log_attempt(request, username, LoginOutcome.SUCCESS, user=user)
    return Response({
        "user": _serialize_user(user),
        "applications": _serialize_applications(user),
    })


@csrf_exempt
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def verify_login_view(request):
    """Second step after lockout: verify with a 6-digit code."""
    from django.utils import timezone
    from django.contrib.auth import get_user_model
    from django.contrib.auth.hashers import check_password
    from datetime import timedelta

    U = get_user_model()
    username = str(request.data.get("username", "")).strip()
    code = str(request.data.get("code", "")).strip()

    if not username or not code:
        return Response(
            {"detail": "username and code required.", "code": "MISSING"},
            status=400,
        )

    user = U.objects.filter(username__iexact=username).first()
    if user is None:
        _log_attempt(request, username, LoginOutcome.NO_SUCH_USER)
        return Response(
            {"detail": "Invalid credentials.", "code": "BAD_CREDS"},
            status=401,
        )

    security = security_for(user)

    if not security.verification_code_hash or not security.verification_sent_at:
        return Response(
            {"detail": "No pending verification for this account.", "code": "NO_CODE"},
            status=400,
        )

    if security.verification_sent_at + timedelta(minutes=CODE_TTL_MINUTES) < timezone.now():
        security.verification_code_hash = ""
        security.verification_sent_at = None
        security.save(update_fields=["verification_code_hash", "verification_sent_at", "updated_at"])
        _log_attempt(request, username, LoginOutcome.BAD_CODE, user=user)
        return Response(
            {"detail": "Verification code expired. Please request a new one.", "code": "CODE_EXPIRED"},
            status=401,
        )

    if not check_password(code, security.verification_code_hash):
        _log_attempt(request, username, LoginOutcome.BAD_CODE, user=user)
        return Response(
            {"detail": "Incorrect verification code.", "code": "BAD_CODE"},
            status=401,
        )

    # Success
    if not user.is_active:
        _log_attempt(request, username, LoginOutcome.INACTIVE, user=user)
        return Response({"detail": "Account is inactive.", "code": "INACTIVE"}, status=401)

    login(request, user)
    _unlock_and_clear(user, security)
    _log_attempt(request, username, LoginOutcome.SUCCESS, user=user,
                 details={"via": "verification"})
    return Response({
        "user": _serialize_user(user),
        "applications": _serialize_applications(user),
    })


@csrf_exempt
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def resend_code_view(request):
    """Regenerate and resend the verification code."""
    from django.utils import timezone
    from django.contrib.auth import get_user_model
    from django.contrib.auth.hashers import make_password

    U = get_user_model()
    username = str(request.data.get("username", "")).strip()
    if not username:
        return Response({"detail": "username required."}, status=400)

    user = U.objects.filter(username__iexact=username).first()
    if user is None:
        return Response({"detail": "Invalid credentials."}, status=401)

    security = security_for(user)
    if not security.requires_verification:
        return Response(
            {"detail": "No pending verification for this account.", "code": "NO_CODE"},
            status=400,
        )

    code = _generate_code()
    security.verification_code_hash = make_password(code)
    security.verification_sent_at = timezone.now()
    security.save(update_fields=["verification_code_hash", "verification_sent_at", "updated_at"])
    channel = _send_code(user, code, security)

    _log_attempt(request, username, LoginOutcome.PENDING_VERIFY, user=user,
                 details={"channel": channel, "resent": True})
    return Response({"detail": "Code sent.", "code": "RESENT", "channel": channel})


@csrf_exempt
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def logout_view(request):
    logout(request)
    return Response({"detail": "Signed out."})


@ensure_csrf_cookie
@api_view(["GET"])
@permission_classes([AllowAny])
def me_view(request):
    user = request.user if getattr(request.user, "is_authenticated", False) else None
    modules = sorted(modules_for_user(user)) if user else []
    role = primary_role(user) if user else "GUEST"
    return Response({
        "user": _serialize_user(user),
        "applications": _serialize_applications(user),
        "modules": modules,
        "role": role,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def applications_view(request):
    return Response({
        "applications": _serialize_applications(request.user),
    })
