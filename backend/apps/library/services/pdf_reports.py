"""Pro PDF report generator (reportlab platypus)."""
from __future__ import annotations

from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)


BRAND_PRIMARY = colors.HexColor("#1e3a8a")
BRAND_ACCENT = colors.HexColor("#0e7490")
BRAND_SOFT = colors.HexColor("#f1f5f9")
BRAND_LINE = colors.HexColor("#cbd5e1")


def _page_decor(canvas, doc):
    canvas.saveState()
    # header band
    canvas.setFillColor(BRAND_PRIMARY)
    canvas.rect(0, A4[1] - 22*mm, A4[0], 22*mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawString(18*mm, A4[1] - 12*mm, "SmartTimetable Pro — Library")
    canvas.setFont("Helvetica", 9)
    canvas.drawString(18*mm, A4[1] - 18*mm, doc.title)
    # footer
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.setFont("Helvetica", 8)
    canvas.drawString(18*mm, 12*mm, f"Generated {datetime.now():%d %b %Y %H:%M}")
    canvas.drawRightString(A4[0] - 18*mm, 12*mm, f"Page {doc.page}")
    canvas.setStrokeColor(BRAND_LINE)
    canvas.line(18*mm, 15*mm, A4[0] - 18*mm, 15*mm)
    canvas.restoreState()


def _styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle(name="TitleX", parent=s["Title"], textColor=BRAND_PRIMARY,
                         fontSize=20, spaceAfter=6, alignment=0))
    s.add(ParagraphStyle(name="SubX", parent=s["Normal"], fontSize=10,
                         textColor=colors.HexColor("#475569"), spaceAfter=14))
    s.add(ParagraphStyle(name="SectionX", parent=s["Heading2"], textColor=BRAND_PRIMARY,
                         fontSize=12, spaceBefore=8, spaceAfter=6))
    return s


def _table(rows, col_widths=None, header=True):
    if not rows:
        return Paragraph("<i>No data available.</i>", _styles()["Normal"])
    t = Table(rows, colWidths=col_widths, repeatRows=1 if header else 0)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_PRIMARY) if header else ("BACKGROUND", (0, 0), (-1, -1), colors.white),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white) if header else ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("FONT", (0, 0), (-1, -1), "Helvetica", 8.5),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9) if header else ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1),
         [colors.white, BRAND_SOFT] if header else [colors.white, BRAND_SOFT]),
        ("GRID", (0, 0), (-1, -1), 0.25, BRAND_LINE),
    ]
    t.setStyle(TableStyle(style))
    return t


def _header_block(title, subtitle):
    s = _styles()
    return [Paragraph(title, s["TitleX"]), Paragraph(subtitle, s["SubX"])]


def build_general_report() -> bytes:
    from apps.library.models import Book, Copy, Loan, Member
    from apps.academics.models import Subject

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm,
                            topMargin=30*mm, bottomMargin=20*mm, title="General Library Report")
    elements = _header_block("General Library Report",
                             "Snapshot of catalogue, circulation, members and curriculum coverage.")

    # Summary cards
    total_books = Book.objects.filter(is_active=True).count()
    total_copies = Copy.objects.count()
    active_loans = Loan.objects.filter(status=Loan.Status.ACTIVE).count()
    overdue_loans = Loan.objects.filter(status=Loan.Status.ACTIVE).filter(due_at__lt=datetime.now()).count() if False else 0
    members = Member.objects.filter(is_active=True).count()
    subjects_total = Subject.objects.filter(is_active=True).count()
    subjects_with_books = Subject.objects.filter(is_active=True, library_books__isnull=False).distinct().count()

    summary = [
        ["Books (titles)", str(total_books)],
        ["Physical copies", str(total_copies)],
        ["Active loans", str(active_loans)],
        ["Active members", str(members)],
        ["Subjects supported", f"{subjects_with_books} / {subjects_total}"],
    ]
    elements.append(Paragraph("Summary", _styles()["SectionX"]))
    elements.append(_table([["Metric", "Value"]] + summary, col_widths=[90*mm, 40*mm]))
    elements.append(Spacer(1, 8*mm))

    # Top 10 most-borrowed
    from django.db.models import Count
    top = (Book.objects.annotate(n=Count("copies__loans"))
           .filter(n__gt=0).order_by("-n")[:10])
    elements.append(Paragraph("Top 10 most-borrowed titles", _styles()["SectionX"]))
    rows = [["Title", "Loans"]]
    for b in top:
        rows.append([b.title[:70], str(b.n)])
    elements.append(_table(rows, col_widths=[130*mm, 20*mm]))
    elements.append(Spacer(1, 8*mm))

    # Subject coverage
    elements.append(Paragraph("Subject coverage", _styles()["SectionX"]))
    rows = [["Code", "Subject", "Titles"]]
    for s in Subject.objects.filter(is_active=True).order_by("code"):
        n = Book.objects.filter(subjects=s, is_active=True).count()
        if n:
            rows.append([s.code, s.name[:50], str(n)])
    elements.append(_table(rows, col_widths=[25*mm, 100*mm, 25*mm]))

    doc.build(elements, onFirstPage=_page_decor, onLaterPages=_page_decor)
    return buf.getvalue()


def build_department_report() -> bytes:
    from apps.inventory.models import Department
    from apps.library.models import Book
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm,
                            topMargin=30*mm, bottomMargin=20*mm, title="Department Report")
    elements = _header_block("Library — Department Report",
                             "Books and inventory holdings grouped by owning department.")
    rows = [["Dept", "Total items", "Total books"]]
    for d in Department.objects.all().order_by("name"):
        items_n = getattr(d, "owned_items", None).count() if hasattr(d, "owned_items") else 0
        books_n = 0
        rows.append([d.name[:50], str(items_n), str(books_n)])
    elements.append(_table(rows, col_widths=[100*mm, 25*mm, 25*mm]))
    doc.build(elements, onFirstPage=_page_decor, onLaterPages=_page_decor)
    return buf.getvalue()


def build_category_report() -> bytes:
    from apps.library.models import Book, Category
    from django.db.models import Count
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm,
                            topMargin=30*mm, bottomMargin=20*mm, title="Category Report")
    elements = _header_block("Library — Category Report",
                             "Catalogue distribution by book category.")
    rows = [["Category", "Code", "Titles"]]
    for c in Category.objects.all().order_by("name"):
        n = Book.objects.filter(categories=c, is_active=True).count()
        rows.append([c.name[:50], c.code, str(n)])
    elements.append(_table(rows, col_widths=[100*mm, 25*mm, 25*mm]))
    doc.build(elements, onFirstPage=_page_decor, onLaterPages=_page_decor)
    return buf.getvalue()


def build_asset_report() -> bytes:
    from apps.inventory.models import Asset
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=18*mm, rightMargin=18*mm,
                            topMargin=30*mm, bottomMargin=20*mm, title="Asset Report")
    elements = _header_block("Library ↔ Inventory — Asset Report",
                             "Library copies linked to inventory assets.")
    rows = [["Tag", "Item", "Condition", "Status", "Location", "Cost"]]
    for a in Asset.objects.select_related("item", "current_location").all()[:500]:
        rows.append([
            a.tag[:24],
            (a.item.name if a.item else "")[:50],
            a.condition, a.status,
            (a.current_location.name if a.current_location else "")[:30],
            str(a.purchase_cost),
        ])
    elements.append(_table(rows, col_widths=[35*mm, 70*mm, 20*mm, 22*mm, 45*mm, 25*mm]))
    doc.build(elements, onFirstPage=_page_decor, onLaterPages=_page_decor)
    return buf.getvalue()
