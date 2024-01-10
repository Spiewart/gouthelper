# Generated by Django 4.2.6 on 2024-01-10 21:00

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("labs", "0003_historicallab_user_historicalurate_user_lab_user"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="historicallab",
            name="history_user",
        ),
        migrations.RemoveField(
            model_name="historicallab",
            name="user",
        ),
        migrations.RemoveField(
            model_name="historicalurate",
            name="history_user",
        ),
        migrations.RemoveField(
            model_name="historicalurate",
            name="user",
        ),
        migrations.DeleteModel(
            name="HistoricalBaselineCreatinine",
        ),
        migrations.DeleteModel(
            name="HistoricalLab",
        ),
        migrations.DeleteModel(
            name="HistoricalUrate",
        ),
    ]
