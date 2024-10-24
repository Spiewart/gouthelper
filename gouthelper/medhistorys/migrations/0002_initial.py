# Generated by Django 4.2.6 on 2024-07-29 15:15

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("medhistorys", "0001_initial"),
        ("ppxs", "0001_initial"),
        ("ppxaids", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="medhistory",
            name="ppx",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="ppxs.ppx"
            ),
        ),
        migrations.AddField(
            model_name="medhistory",
            name="ppxaid",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="ppxaids.ppxaid"
            ),
        ),
    ]
