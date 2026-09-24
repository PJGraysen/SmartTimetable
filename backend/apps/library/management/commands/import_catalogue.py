"""
Bulk CSV catalogue import.

CSV columns (header row required, case-insensitive):
  isbn, title, subtitle, author, publisher, year, category, subject, copies

- author/publisher/category/subject: created on demand if missing
- copies: integer; creates that many copies with auto-generated barcodes
- Upsert by ISBN: if a book with the ISBN exists, updates fields.

Usage:
  python manage.py import_catalogue path/to/file.csv
  python manage.py import_catalogue path/to/file.csv --dry-run
"""
from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.academics.models import Subject
from apps.library.models import Author, Book, Category, Copy, Publisher, Shelf


class Command(BaseCommand):
    help = "Bulk-import books from a CSV file."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str)
        parser.add_argument("--dry-run", action="store_true")

    def _get_or_create(self, Model, *, name_field="name", **lookup):
        obj, _ = Model.objects.get_or_create(**lookup)
        return obj

    def handle(self, *args, **options):
        path = Path(options["csv_path"])
        dry = options["dry_run"]
        if not path.exists():
            self.stderr.write(f"File not found: {path}"); return

        created_books = 0
        updated_books = 0
        created_copies = 0
        errors = []

        with path.open(encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)

        self.stdout.write(f"  rows: {len(rows)}  dry_run: {dry}")

        with transaction.atomic():
            for i, row in enumerate(rows, start=2):
                try:
                    title = (row.get("title") or "").strip()
                    if not title:
                        errors.append((i, "missing title"))
                        continue

                    isbn = (row.get("isbn") or "").strip()
                    book = None
                    if isbn:
                        book = Book.objects.filter(isbn=isbn).first()

                    publisher = None
                    pname = (row.get("publisher") or "").strip()
                    if pname:
                        publisher = Publisher.objects.filter(name__iexact=pname).first() or \
                                    Publisher.objects.create(name=pname)

                    defaults = {
                        "title": title,
                        "subtitle": (row.get("subtitle") or "").strip(),
                        "publisher": publisher,
                        "published_year": int(row["year"]) if row.get("year") else None,
                    }

                    if book is None:
                        book = Book.objects.create(isbn=isbn, **defaults)
                        created_books += 1
                    else:
                        for k, v in defaults.items():
                            setattr(book, k, v)
                        book.save()
                        updated_books += 1

                    author_name = (row.get("author") or "").strip()
                    if author_name:
                        a = Author.objects.filter(name__iexact=author_name).first() or \
                            Author.objects.create(name=author_name)
                        book.authors.add(a)

                    cat = (row.get("category") or "").strip()
                    if cat:
                        c = Category.objects.filter(name__iexact=cat).first() or \
                            Category.objects.create(name=cat, code=cat.upper()[:30])
                        book.categories.add(c)

                    subj = (row.get("subject") or "").strip()
                    if subj:
                        s = Subject.objects.filter(code__iexact=subj).first()
                        if s is None:
                            s = Subject.objects.filter(name__iexact=subj).first()
                        if s is not None:
                            book.subjects.add(s)

                    copies_n = int(row.get("copies") or 0)
                    if copies_n > 0:
                        for _ in range(copies_n):
                            barcode = Copy.objects.model._meta.model_name  # placeholder
                            # auto-generate unique barcode
                            import uuid
                            bc = f"LIB-{uuid.uuid4().hex[:10].upper()}"
                            Copy.objects.create(
                                book=book,
                                barcode=bc,
                                accession_number=bc,
                            )
                            created_copies += 1

                except Exception as exc:
                    errors.append((i, f"{type(exc).__name__}: {exc}"))

            if dry:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING("  DRY RUN — rolled back."))

        self.stdout.write(f"  books created: {created_books}")
        self.stdout.write(f"  books updated: {updated_books}")
        self.stdout.write(f"  copies created: {created_copies}")
        if errors:
            self.stdout.write(self.style.ERROR(f"  {len(errors)} error(s):"))
            for line, msg in errors[:10]:
                self.stdout.write(f"    line {line}: {msg}")
        else:
            self.stdout.write(self.style.SUCCESS("  import OK"))
