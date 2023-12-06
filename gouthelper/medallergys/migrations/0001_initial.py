# Generated by Django 4.2.6 on 2023-12-05 19:33

from django.db import migrations, models
import django_extensions.db.fields
import rules.contrib.models
import simple_history.models
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="HistoricalMedAllergy",
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
                    "treatment",
                    models.CharField(
                        choices=[
                            ("ALLOPURINOL", "Allopurinol"),
                            ("CELECOXIB", "Celecoxib"),
                            ("COLCHICINE", "Colchicine"),
                            ("DICLOFENAC", "Diclofenac"),
                            ("FEBUXOSTAT", "Febuxostat"),
                            ("IBUPROFEN", "Ibuprofen"),
                            ("INDOMETHACIN", "Indomethacin"),
                            ("MELOXICAM", "Meloxicam"),
                            ("METHYLPREDNISOLONE", "Methylprednisolone"),
                            ("NAPROXEN", "Naproxen"),
                            ("PREDNISONE", "Prednisone"),
                            ("PROBENECID", "Probenecid"),
                        ],
                        help_text="Medication the allergy is for.",
                        max_length=20,
                        verbose_name="Treatment Type",
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
                "verbose_name": "historical med allergy",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": "history_date",
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name="MedAllergy",
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
                    "treatment",
                    models.CharField(
                        choices=[
                            ("ALLOPURINOL", "Allopurinol"),
                            ("CELECOXIB", "Celecoxib"),
                            ("COLCHICINE", "Colchicine"),
                            ("DICLOFENAC", "Diclofenac"),
                            ("FEBUXOSTAT", "Febuxostat"),
                            ("IBUPROFEN", "Ibuprofen"),
                            ("INDOMETHACIN", "Indomethacin"),
                            ("MELOXICAM", "Meloxicam"),
                            ("METHYLPREDNISOLONE", "Methylprednisolone"),
                            ("NAPROXEN", "Naproxen"),
                            ("PREDNISONE", "Prednisone"),
                            ("PROBENECID", "Probenecid"),
                        ],
                        help_text="Medication the allergy is for.",
                        max_length=20,
                        verbose_name="Treatment Type",
                    ),
                ),
            ],
            bases=(rules.contrib.models.RulesModelMixin, models.Model),
        ),
        migrations.AddConstraint(
            model_name="medallergy",
            constraint=models.CheckConstraint(
                check=models.Q(
                    (
                        "treatment__in",
                        [
                            "ALLOPURINOL",
                            "CELECOXIB",
                            "COLCHICINE",
                            "DICLOFENAC",
                            "FEBUXOSTAT",
                            "IBUPROFEN",
                            "INDOMETHACIN",
                            "MELOXICAM",
                            "METHYLPREDNISOLONE",
                            "NAPROXEN",
                            "PREDNISONE",
                            "PROBENECID",
                        ],
                    )
                ),
                name="medallergys_medallergy_treatment_valid",
            ),
        ),
    ]
