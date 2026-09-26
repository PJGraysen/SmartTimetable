"""Seed emoji icons + colours for subjects."""
from django.core.management.base import BaseCommand
from apps.academics.models import Subject

EMOJI = {
    "AGR": ("🌾", "#92400e"),
    "ARAB": ("🕌", "#0f766e"),
    "ART": ("🎨", "#a21caf"),
    "AVI": ("✈️", "#0369a1"),
    "BIO": ("🧬", "#15803d"),
    "BIOPRAC": ("🔬", "#15803d"),
    "BLD": ("🏗️", "#78350f"),
    "BUS": ("💼", "#1e40af"),
    "CAS": ("🎭", "#b45309"),
    "CHEM": ("🧪", "#0e7490"),
    "CHEMPRAC": ("🧫", "#0e7490"),
    "COMP": ("💻", "#1e3a8a"),
    "CS": ("🖥️", "#1e40af"),
    "CRE": ("✝️", "#7c2d12"),
    "EMCM": ("📐", "#4c1d95"),
    "ENG": ("📖", "#1d4ed8"),
    "FRE": ("🇫🇷", "#0891b2"),
    "GEO": ("🌍", "#065f46"),
    "HIS": ("🏛️", "#7c2d12"),
    "ICT": ("🖥️", "#0f766e"),
    "INTSCI": ("🔬", "#15803d"),
    "IRE": ("☪️", "#065f46"),
    "KIS": ("📚", "#b91c1c"),
    "LIT": ("📜", "#7c3aed"),
    "MAT": ("🧮", "#1e3a8a"),
    "MUS": ("🎵", "#9333ea"),
    "MUSD": ("🎼", "#7e22ce"),
    "PE": ("🏃", "#0284c7"),
    "PHY": ("⚛️", "#0e7490"),
    "PHYPRAC": ("🔭", "#0e7490"),
    "PPI": ("🙏", "#7c2d12"),
    "SOCIAL": ("🗺️", "#065f46"),
    "SST": ("🌐", "#0f766e"),
}
DEFAULT = ("📕", "#475569")


class Command(BaseCommand):
    help = "Seed emoji icons + colours for subjects that lack them."
    def add_arguments(self, parser):
        parser.add_argument("--overwrite", action="store_true")

    def handle(self, *args, **opts):
        n = 0
        for s in Subject.objects.all():
            if not opts["overwrite"] and (s.icon and s.colour):
                continue
            emoji, colour = EMOJI.get(s.code.upper(), DEFAULT)
            s.icon = emoji
            s.colour = colour
            s.save(update_fields=["icon", "colour", "updated_at"])
            n += 1
        print(f"Updated {n} subjects.")
