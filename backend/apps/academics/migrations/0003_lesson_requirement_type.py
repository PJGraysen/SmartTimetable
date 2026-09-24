from django.db import migrations, models


def classify_existing_lesson_requirements(apps, schema_editor):
    LessonRequirement = apps.get_model(
        "academics",
        "LessonRequirement",
    )

    grade10_block_codes = {
        "BIO",
        "MUS",
        "FRE",
        "CHEM",
        "PHY",
        "LIT",
        "GEO",
        "HIS",
        "CS",
        "BUS",
        "AGR",
    }

    LessonRequirement.objects.filter(
        instructional_group__code__in=("10E", "10W"),
        subject__code__in=grade10_block_codes,
    ).update(
        requirement_type="BLOCK",
    )

    LessonRequirement.objects.filter(
        instructional_group__code__in=("10E", "10W"),
    ).exclude(
        subject__code__in=grade10_block_codes,
    ).update(
        requirement_type="STANDALONE",
    )


class Migration(migrations.Migration):

    dependencies = [
        (
            "academics",
            "0002_instructionalgroup_alter_lessonrequirement_options_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="lessonrequirement",
            name="requirement_type",
            field=models.CharField(
                choices=[
                    ("STANDALONE", "Standalone"),
                    ("BLOCK", "Block"),
                    ("PRACTICAL", "Practical"),
                ],
                default="STANDALONE",
                max_length=16,
            ),
        ),
        migrations.RemoveConstraint(
            model_name="lessonrequirement",
            name=(
                "uq_lesson_requirement_term_instructional_group_subject"
            ),
        ),
        migrations.AddConstraint(
            model_name="lessonrequirement",
            constraint=models.UniqueConstraint(
                fields=(
                    "term",
                    "instructional_group",
                    "subject",
                    "requirement_type",
                ),
                name="uq_lesson_requirement_term_group_subject_type",
            ),
        ),
        migrations.AddConstraint(
            model_name="lessonrequirement",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    requirement_type__in=(
                        "STANDALONE",
                        "BLOCK",
                        "PRACTICAL",
                    )
                ),
                name="ck_lesson_requirement_type_valid",
            ),
        ),
        migrations.RunPython(
            classify_existing_lesson_requirements,
            migrations.RunPython.noop,
        ),
    ]
