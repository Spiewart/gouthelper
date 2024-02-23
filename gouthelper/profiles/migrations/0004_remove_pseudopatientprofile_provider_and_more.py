# Generated by Django 4.2.6 on 2024-02-21 22:31

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("profiles", "0003_remove_adminprofile_organization_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="pseudopatientprofile",
            name="provider",
        ),
        migrations.RemoveField(
            model_name="pseudopatientprofile",
            name="user",
        ),
        migrations.AlterField(
            model_name="patientprofile",
            name="provider",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="patient_profiles",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.DeleteModel(
            name="HistoricalPseudopatientProfile",
        ),
        migrations.DeleteModel(
            name="PseudopatientProfile",
        ),
    ]
