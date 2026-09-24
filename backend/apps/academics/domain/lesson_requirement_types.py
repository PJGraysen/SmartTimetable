from __future__ import annotations

from django.db import models


class LessonRequirementType(models.TextChoices):
    """
    Structural classification of a curriculum lesson requirement.

    STANDALONE:
        Ordinary subject teaching requirement.

    BLOCK:
        Subject teaching that participates in a synchronized elective
        / parallel curriculum block.

    PRACTICAL:
        Stream-specific practical allocation for a subject which may
        simultaneously participate in a synchronized elective block.
    """

    STANDALONE = "STANDALONE", "Standalone"
    BLOCK = "BLOCK", "Block"
    PRACTICAL = "PRACTICAL", "Practical"
