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
        ("labs", "0001_initial"),
        ("genders", "0001_initial"),
        ("medallergys", "0001_initial"),
        ("dateofbirths", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("ethnicitys", "0001_initial"),
        ("medhistorys", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="UltAid",
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
                ("decisionaid", models.JSONField(blank=True, default=dict)),
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
                    "ethnicity",
                    models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to="ethnicitys.ethnicity"),
                ),
                (
                    "gender",
                    models.OneToOneField(
                        blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="genders.gender"
                    ),
                ),
                (
                    "hlab5801",
                    models.OneToOneField(
                        blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="labs.hlab5801"
                    ),
                ),
                ("medallergys", models.ManyToManyField(to="medallergys.medallergy")),
                ("medhistorys", models.ManyToManyField(to="medhistorys.medhistory")),
            ],
            options={
                "abstract": False,
            },
            bases=(rules.contrib.models.RulesModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name="HistoricalUltAid",
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
                ("decisionaid", models.JSONField(blank=True, default=dict)),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField()),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")], max_length=1),
                ),
                (
                    "dateofbirth",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="dateofbirths.dateofbirth",
                    ),
                ),
                (
                    "ethnicity",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="ethnicitys.ethnicity",
                    ),
                ),
                (
                    "gender",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="genders.gender",
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
                    "hlab5801",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="labs.hlab5801",
                    ),
                ),
            ],
            options={
                "verbose_name": "historical ult aid",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": "history_date",
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
    ]
