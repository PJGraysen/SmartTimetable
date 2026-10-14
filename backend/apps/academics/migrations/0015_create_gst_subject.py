from django.db import migrations


def create_gst_subject(apps, schema_editor):
    Subject = apps.get_model("academics", "Subject")
    Subject.objects.get_or_create(
        code="GST",
        defaults={
            "name": "Guided Study Time",
            "is_active": True,
        },
    )


def remove_gst_subject(apps, schema_editor):
    Subject = apps.get_model("academics", "Subject")
    Subject.objects.filter(code="GST").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("academics", "0014_resultpublication"),
    ]

    operations = [
        migrations.RunPython(create_gst_subject, remove_gst_subject),
    ]
