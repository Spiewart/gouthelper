# Generated by Django 4.2.6 on 2023-12-20 19:50

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("profiles", "0002_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="adminprofile",
            name="organization",
        ),
        migrations.RemoveField(
            model_name="historicaladminprofile",
            name="organization",
        ),
        migrations.RemoveField(
            model_name="historicalpatientprofile",
            name="patient_id",
        ),
        migrations.RemoveField(
            model_name="historicalproviderprofile",
            name="organization",
        ),
        migrations.RemoveField(
            model_name="historicalproviderprofile",
            name="surrogate",
        ),
        migrations.RemoveField(
            model_name="historicalpseudopatientprofile",
            name="alias",
        ),
        migrations.RemoveField(
            model_name="patientprofile",
            name="patient_id",
        ),
        migrations.RemoveField(
            model_name="providerprofile",
            name="organization",
        ),
        migrations.RemoveField(
            model_name="providerprofile",
            name="surrogate",
        ),
        migrations.RemoveField(
            model_name="pseudopatientprofile",
            name="alias",
        ),
        migrations.AlterField(
            model_name="patientprofile",
            name="provider",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="patient_providers",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="pseudopatientprofile",
            name="provider",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="pseudopatient_providers",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
