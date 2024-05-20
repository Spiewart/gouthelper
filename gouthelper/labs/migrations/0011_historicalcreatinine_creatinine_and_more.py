# Generated by Django 4.2.6 on 2024-05-12 23:22

from decimal import Decimal
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import django_extensions.db.fields
import rules.contrib.models
import simple_history.models
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("akis", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("labs", "0010_alter_hlab5801_user"),
    ]

    operations = [
        migrations.CreateModel(
            name="HistoricalCreatinine",
            fields=[
                (
                    "created",
                    django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name="created"),
                ),
                (
                    "modified",
                    django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name="modified"),
                ),
                ("id", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False)),
                ("lower_limit", models.DecimalField(decimal_places=2, default=Decimal("0.74"), max_digits=4)),
                (
                    "units",
                    models.CharField(
                        choices=[("MGDL", "mg/dL (milligrams per deciliter)")],
                        default="MGDL",
                        max_length=10,
                        verbose_name="Units",
                    ),
                ),
                ("upper_limit", models.DecimalField(decimal_places=2, default=Decimal("1.35"), max_digits=4)),
                ("value", models.DecimalField(decimal_places=2, max_digits=4)),
                (
                    "date_drawn",
                    models.DateTimeField(
                        blank=True, default=django.utils.timezone.now, help_text="What day was this lab drawn?"
                    ),
                ),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField()),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")], max_length=1),
                ),
                (
                    "aki",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="akis.aki",
                    ),
                ),
                (
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "historical creatinine",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": "history_date",
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name="Creatinine",
            fields=[
                (
                    "created",
                    django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name="created"),
                ),
                (
                    "modified",
                    django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name="modified"),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True
                    ),
                ),
                ("lower_limit", models.DecimalField(decimal_places=2, default=Decimal("0.74"), max_digits=4)),
                (
                    "units",
                    models.CharField(
                        choices=[("MGDL", "mg/dL (milligrams per deciliter)")],
                        default="MGDL",
                        max_length=10,
                        verbose_name="Units",
                    ),
                ),
                ("upper_limit", models.DecimalField(decimal_places=2, default=Decimal("1.35"), max_digits=4)),
                ("value", models.DecimalField(decimal_places=2, max_digits=4)),
                (
                    "date_drawn",
                    models.DateTimeField(
                        blank=True, default=django.utils.timezone.now, help_text="What day was this lab drawn?"
                    ),
                ),
                (
                    "aki",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to="akis.aki"
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
            bases=(rules.contrib.models.RulesModelMixin, models.Model),
        ),
        migrations.AddConstraint(
            model_name="creatinine",
            constraint=models.CheckConstraint(
                check=models.Q(("lower_limit", Decimal("0.74")), ("units", "MGDL"), ("upper_limit", Decimal("1.35"))),
                name="labs_creatinine_units_upper_lower_limits_valid",
            ),
        ),
    ]