"""
Cascade is_active across the academic hierarchy.

Rule:
    flipping parent.is_active (TeachingGroup / Subject / Teacher)
    cascades to every child IG / LR.

Bidirectional:
    - parent OFF -> children OFF (removed from solver & analytics)
    - parent ON  -> children ON  (restored to solver & analytics)

Idempotent: uses .exclude(is_active=X).update(is_active=X) so a save
without a flag change is a no-op.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.academics.models import (
    TeachingGroup, InstructionalGroup, LessonRequirement, Subject,
)
from apps.users.models import Teacher


@receiver(post_save, sender=TeachingGroup, dispatch_uid="cascade_tg_active")
def cascade_teaching_group(sender, instance, created, **kwargs):
    if created:
        return
    target = instance.is_active
    # Cascade to IGs
    InstructionalGroup.objects.filter(
        teaching_group=instance,
    ).exclude(is_active=target).update(is_active=target)
    # Cascade to LRs through the IGs
    LessonRequirement.objects.filter(
        instructional_group__teaching_group=instance,
    ).exclude(is_active=target).update(is_active=target)


@receiver(post_save, sender=Subject, dispatch_uid="cascade_subject_active")
def cascade_subject(sender, instance, created, **kwargs):
    if created:
        return
    target = instance.is_active
    LessonRequirement.objects.filter(
        subject=instance,
    ).exclude(is_active=target).update(is_active=target)


@receiver(post_save, sender=Teacher, dispatch_uid="cascade_teacher_active")
def cascade_teacher(sender, instance, created, **kwargs):
    if created:
        return
    target = instance.is_active
    LessonRequirement.objects.filter(
        teacher=instance,
    ).exclude(is_active=target).update(is_active=target)
