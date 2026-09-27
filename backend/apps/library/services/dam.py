"""
DAM — upload, serve, log. No PDF watermarking yet (pypdf pending install).
"""
from __future__ import annotations

import hashlib
import mimetypes
import os
from pathlib import Path

from django.http import StreamingHttpResponse
from django.utils import timezone

from apps.library.models import DigitalAsset, DigitalAssetView


ALLOWED_EXT = {
    ".pdf": DigitalAsset.Format.PDF,
    ".epub": DigitalAsset.Format.EPUB,
    ".docx": DigitalAsset.Format.DOCX,
    ".doc": DigitalAsset.Format.DOCX,
    ".pptx": DigitalAsset.Format.PPTX,
    ".ppt": DigitalAsset.Format.PPTX,
    ".mp3": DigitalAsset.Format.AUDIO,
    ".m4a": DigitalAsset.Format.AUDIO,
    ".wav": DigitalAsset.Format.AUDIO,
    ".mp4": DigitalAsset.Format.VIDEO,
    ".mov": DigitalAsset.Format.VIDEO,
}
MAX_BYTES = 100 * 1024 * 1024


class DAMError(Exception):
    pass


def detect_format(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    return ALLOWED_EXT.get(ext, DigitalAsset.Format.OTHER)


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def save_asset(*, file, title: str, description: str = "", category: str = "OTHER",
               subject=None, book=None, allow_download: bool = False,
               allow_print: bool = False, watermark_text: str = "",
               read_only: bool = True, expires_at=None, by_user=None) -> DigitalAsset:
    name = getattr(file, "name", "upload")
    ext = os.path.splitext(name)[1].lower()
    if ext not in ALLOWED_EXT:
        raise DAMError(f"Unsupported file type: {ext}")
    if getattr(file, "size", 0) > MAX_BYTES:
        raise DAMError("File exceeds 100 MB limit.")

    fmt = detect_format(name)
    asset = DigitalAsset(
        title=title[:220], description=description, format=fmt,
        category=category, subject=subject, book=book,
        allow_download=allow_download, allow_print=allow_print,
        watermark_text=watermark_text, read_only=read_only,
        expires_at=expires_at, uploaded_by=by_user,
    )
    asset.save()  # to get an id for upload_to
    asset.file = file
    asset.save()
    try:
        asset.size_bytes = os.path.getsize(asset.file.path)
        asset.checksum = _sha256(asset.file.path)
        asset.save(update_fields=["size_bytes", "checksum"])
    except Exception:
        pass
    return asset


def log_view(asset: DigitalAsset, *, user, action: str, request=None) -> DigitalAssetView:
    ip = None; ua = ""
    if request is not None:
        ua = (request.META.get("HTTP_USER_AGENT") or "")[:240]
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        ip = (xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")) or None
    entry = DigitalAssetView.objects.create(
        asset=asset, user=user if getattr(user, "is_authenticated", False) else None,
        action=action, ip_address=ip, user_agent=ua,
    )
    if action == DigitalAssetView.Action.VIEW:
        DigitalAsset.objects.filter(pk=asset.pk).update(view_count=asset.view_count + 1)
    elif action == DigitalAssetView.Action.DOWNLOAD:
        DigitalAsset.objects.filter(pk=asset.pk).update(download_count=asset.download_count + 1)
    return entry


def _file_chunks(path, chunk=65536):
    with open(path, "rb") as fh:
        while True:
            data = fh.read(chunk)
            if not data:
                break
            yield data




def _watermark_pdf(path: str, text: str):
    """Return watermarked PDF bytes, or None."""
    if not text:
        return None
    try:
        from io import BytesIO
        from pypdf import PdfReader, PdfWriter
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
    except Exception:
        return None
    try:
        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        c.saveState()
        c.setFont("Helvetica-Bold", 48)
        try:
            c.setFillAlpha(0.14)
        except Exception:
            pass
        c.setFillColorRGB(0.4, 0.15, 0.15)
        c.translate(280, 420)
        c.rotate(40)
        c.drawString(-220, 0, text[:80])
        c.restoreState()
        c.save()
        buf.seek(0)
        overlay = PdfReader(buf)

        reader = PdfReader(path)
        writer = PdfWriter()
        overlay_page = overlay.pages[0] if overlay.pages else None
        for page in reader.pages:
            if overlay_page is not None:
                page.merge_page(overlay_page)
            writer.add_page(page)
        writer.add_metadata({"/Watermark": text, "/Producer": "SmartTimetable Pro Library"})
        out = BytesIO()
        writer.write(out)
        return out.getvalue()
    except Exception:
        return None




# --- Stream auth: iframes cannot send Authorization headers,
# so we accept a ?token= query param (JWT or DRF token).
def _authenticate_stream_token(request):
    from django.contrib.auth.models import AnonymousUser
    token = request.GET.get("token")
    if not token:
        return request.user  # fall back to normal auth
    # Try JWT
    try:
        from rest_framework_simplejwt.authentication import JWTAuthentication
        from rest_framework_simplejwt.tokens import AccessToken
        from django.contrib.auth import get_user_model
        validated = AccessToken(token)
        uid = validated.get("user_id")
        if uid:
            return get_user_model().objects.filter(pk=uid).first() or request.user
    except Exception:
        pass
    # Try DRF TokenAuthentication
    try:
        from rest_framework.authtoken.models import Token
        t = Token.objects.filter(key=token).select_related("user").first()
        if t:
            return t.user
    except Exception:
        pass
    return request.user


def serve_asset(asset: DigitalAsset, *, user, action: str, request=None):
    """
    Stream the asset. Enforces allow_download, read_only, expires_at.
    Logs the action. Returns StreamingHttpResponse (or raises DAMError).
    """
    if not asset.is_active:
        raise DAMError("Asset is not available.")
    if asset.expires_at and asset.expires_at < timezone.now():
        raise DAMError("Asset access has expired.")
    if action == "download" and not asset.allow_download:
        log_view(asset, user=user, action=DigitalAssetView.Action.DENIED, request=request)
        raise DAMError("Download is disabled for this asset.")

    try:
        path = asset.file.path
    except Exception:
        raise DAMError("Asset file is missing.")
    if not os.path.exists(path):
        raise DAMError("Asset file is missing on disk.")

    ctype, _ = mimetypes.guess_type(path)
    ctype = ctype or "application/octet-stream"
    disposition = "inline" if action == "view" else "attachment"
    filename = os.path.basename(path)

    body = None
    size = asset.size_bytes or os.path.getsize(path)
    if asset.watermark_text and path.lower().endswith(".pdf"):
        wm = _watermark_pdf(path, asset.watermark_text)
        if wm:
            body = wm
            size = len(wm)

    if body is not None:
        from django.http import HttpResponse as _HR
        resp = _HR(body, content_type=ctype)
    else:
        resp = StreamingHttpResponse(_file_chunks(path), content_type=ctype)
    resp["Content-Length"] = str(size)
    resp["Content-Disposition"] = f'{disposition}; filename="{filename}"'
    resp["X-DRM-ReadOnly"] = "1" if asset.read_only else "0"
    resp["X-DRM-Allow-Download"] = "1" if asset.allow_download else "0"
    resp["X-DRM-Allow-Print"] = "1" if asset.allow_print else "0"
    if asset.watermark_text:
        resp["X-DRM-Watermark"] = asset.watermark_text
    log_view(asset, user=user, action=(
        DigitalAssetView.Action.DOWNLOAD if action == "download"
        else DigitalAssetView.Action.VIEW
    ), request=request)
    return resp
