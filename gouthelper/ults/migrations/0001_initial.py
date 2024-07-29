# Generated by Django 4.2.6 on 2024-07-29 15:15

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields
import gouthelper.utils.models
import rules.contrib.models
import simple_history.models
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("ultaids", "0001_initial"),
        ("dateofbirths", "0001_initial"),
        ("genders", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="HistoricalUlt",
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
                    "freq_flares",
                    models.IntegerField(
                        blank=True,
                        choices=[(1, "One or less"), (2, "Two or more")],
                        help_text="How many gout flares to you have per year?",
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(2),
                        ],
                        verbose_name="Flares per Year",
                    ),
                ),
                (
                    "indication",
                    models.IntegerField(
                        choices=[(0, "Not Indicated"), (1, "Conditionally Indicated"), (2, "Indicated")],
                        default=0,
                        help_text="Does the patient have an indication for ULT?",
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(2),
                        ],
                        verbose_name="Indication",
                    ),
                ),
                (
                    "num_flares",
                    models.IntegerField(
                        choices=[(0, "Zero"), (1, "One"), (2, "Two or more")],
                        help_text="How many gout flares have you had?",
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(2),
                        ],
                        verbose_name="Total Number of Flares",
                    ),
                ),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField()),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")], max_length=1),
                ),
            ],
            options={
                "verbose_name": "historical ult",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": "history_date",
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name="Ult",
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
                    "freq_flares",
                    models.IntegerField(
                        blank=True,
                        choices=[(1, "One or less"), (2, "Two or more")],
                        help_text="How many gout flares to you have per year?",
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(2),
                        ],
                        verbose_name="Flares per Year",
                    ),
                ),
                (
                    "indication",
                    models.IntegerField(
                        choices=[(0, "Not Indicated"), (1, "Conditionally Indicated"), (2, "Indicated")],
                        default=0,
                        help_text="Does the patient have an indication for ULT?",
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(2),
                        ],
                        verbose_name="Indication",
                    ),
                ),
                (
                    "num_flares",
                    models.IntegerField(
                        choices=[(0, "Zero"), (1, "One"), (2, "Two or more")],
                        help_text="How many gout flares have you had?",
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(2),
                        ],
                        verbose_name="Total Number of Flares",
                    ),
                ),
                (
                    "dateofbirth",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="dateofbirths.dateofbirth",
                    ),
                ),
                (
                    "gender",
                    models.OneToOneField(
                        blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="genders.gender"
                    ),
                ),
                (
                    "ultaid",
                    models.OneToOneField(
                        blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="ultaids.ultaid"
                    ),
                ),
            ],
            bases=(rules.contrib.models.RulesModelMixin, gouthelper.utils.models.GoutHelperBaseModel, models.Model),
        ),
    ]
