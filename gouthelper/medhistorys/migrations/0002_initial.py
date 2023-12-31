# Generated by Django 4.2.6 on 2023-12-05 19:33

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("medhistorys", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicalmedhistory",
            name="history_user",
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.CreateModel(
            name="Allopurinolhypersensitivity",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("medhistorys.medhistory",),
        ),
        migrations.CreateModel(
            name="Angina",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("medhistorys.medhistory",),
        ),
        migrations.CreateModel(
            name="Anticoagulation",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("medhistorys.medhistory",),
        ),
        migrations.CreateModel(
            name="Bleed",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("medhistorys.medhistory",),
        ),
        migrations.CreateModel(
            name="Cad",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("medhistorys.medhistory",),
        ),
        migrations.CreateModel(
            name="Chf",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("medhistorys.medhistory",),
        ),
        migrations.CreateModel(
            name="Ckd",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("medhistorys.medhistory",),
        ),
        migrations.CreateModel(
            name="Colchicineinteraction",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("medhistorys.medhistory",),
        ),
        migrations.CreateModel(
            name="Diabetes",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("medhistorys.medhistory",),
        ),
        migrations.CreateModel(
            name="Erosions",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("medhistorys.medhistory",),
        ),
        migrations.CreateModel(
            name="Febuxostathypersensitivity",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("medhistorys.medhistory",),
        ),
        migrations.CreateModel(
            name="Gastricbypass",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("medhistorys.medhistory",),
        ),
        migrations.CreateModel(
            name="Gout",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("medhistorys.medhistory",),
        ),
        migrations.CreateModel(
            name="Heartattack",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("medhistorys.medhistory",),
        ),
        migrations.CreateModel(
            name="Hypertension",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("medhistorys.medhistory",),
        ),
        migrations.CreateModel(
            name="Hyperuricemia",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("medhistorys.medhistory",),
        ),
        migrations.CreateModel(
            name="Ibd",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("medhistorys.medhistory",),
        ),
        migrations.CreateModel(
            name="Menopause",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("medhistorys.medhistory",),
        ),
        migrations.CreateModel(
            name="Organtransplant",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("medhistorys.medhistory",),
        ),
        migrations.CreateModel(
            name="Osteoporosis",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("medhistorys.medhistory",),
        ),
        migrations.CreateModel(
            name="Pvd",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("medhistorys.medhistory",),
        ),
        migrations.CreateModel(
            name="Stroke",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("medhistorys.medhistory",),
        ),
        migrations.CreateModel(
            name="Tophi",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("medhistorys.medhistory",),
        ),
        migrations.CreateModel(
            name="Uratestones",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("medhistorys.medhistory",),
        ),
        migrations.CreateModel(
            name="Xoiinteraction",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("medhistorys.medhistory",),
        ),
    ]
