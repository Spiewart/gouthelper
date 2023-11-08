# Generated by Django 4.2.6 on 2023-11-04 20:11

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields
import rules.contrib.models
import simple_history.models
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Ethnicity",
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
                (
                    "value",
                    models.CharField(
                        choices=[
                            ("African American", "African American"),
                            ("Caucasian American", "Caucasian American"),
                            ("East African", "East African"),
                            ("Han Chinese", "Han Chinese"),
                            ("Hispanic", "Hispanic"),
                            ("Hmong", "Hmong"),
                            ("Korean", "Korean"),
                            ("Native American", "Native American"),
                            ("Other", "Other"),
                            ("Pacific Islander", "Pacific Islander"),
                            ("Thai", "Thai"),
                        ],
                        help_text="Ethnicity sometimes matters for gout treatment.",
                        max_length=40,
                        verbose_name="Race",
                    ),
                ),
            ],
            bases=(rules.contrib.models.RulesModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name="HistoricalEthnicity",
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
                (
                    "value",
                    models.CharField(
                        choices=[
                            ("African American", "African American"),
                            ("Caucasian American", "Caucasian American"),
                            ("East African", "East African"),
                            ("Han Chinese", "Han Chinese"),
                            ("Hispanic", "Hispanic"),
                            ("Hmong", "Hmong"),
                            ("Korean", "Korean"),
                            ("Native American", "Native American"),
                            ("Other", "Other"),
                            ("Pacific Islander", "Pacific Islander"),
                            ("Thai", "Thai"),
                        ],
                        help_text="Ethnicity sometimes matters for gout treatment.",
                        max_length=40,
                        verbose_name="Race",
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
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "historical ethnicity",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": "history_date",
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.AddConstraint(
            model_name="ethnicity",
            constraint=models.CheckConstraint(
                check=models.Q(
                    (
                        "value__in",
                        [
                            "African American",
                            "Caucasian American",
                            "East African",
                            "Han Chinese",
                            "Hispanic",
                            "Hmong",
                            "Korean",
                            "Native American",
                            "Other",
                            "Pacific Islander",
                            "Thai",
                        ],
                    )
                ),
                name="ethnicitys_ethnicity_value_check",
            ),
        ),
    ]
