# Generated by Django 4.2.6 on 2024-05-12 23:28

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("flares", "0014_alter_flare_flareaid"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="flare",
            name="aki",
        ),
        migrations.RemoveField(
            model_name="historicalflare",
            name="aki",
        ),
    ]
