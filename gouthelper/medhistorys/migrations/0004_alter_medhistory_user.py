# Generated by Django 4.2.6 on 2023-12-28 01:19

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("medhistorys", "0003_historicalmedhistory_user_medhistory_user"),
    ]

    operations = [
        migrations.AlterField(
            model_name="medhistory",
            name="user",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL
            ),
        ),
    ]