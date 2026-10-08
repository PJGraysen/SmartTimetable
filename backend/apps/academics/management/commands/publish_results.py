"""Publish or unpublish results for a term (locks teacher marks entry)."""
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.academics.models import ResultPublication
from apps.core.models import Term


class Command(BaseCommand):
    help = "Publish results for a term (locks teacher marks entry) or reopen."

    def add_arguments(self, parser):
        parser.add_argument("--term", type=str, help="Term name or id")
        parser.add_argument("--open", action="store_true",
                            help="Set is_published=False (reopen for editing)")

    def handle(self, *args, **opts):
        term = None
        if opts["term"]:
            term = Term.objects.filter(name=opts["term"]).first() or \
                   Term.objects.filter(id=opts["term"]).first()
        else:
            term = Term.objects.filter(is_active=True).first()
        if not term:
            self.stderr.write("Term not found.")
            return

        pub, _ = ResultPublication.objects.get_or_create(term=term)

        if opts["open"]:
            pub.is_published = False
            pub.published_at = None
            pub.published_by = None
            self.stdout.write(self.style.WARNING(f"REOPENED {term}"))
        else:
            pub.is_published = True
            pub.published_at = timezone.now()
            self.stdout.write(self.style.SUCCESS(f"PUBLISHED {term}"))

        pub.save()
