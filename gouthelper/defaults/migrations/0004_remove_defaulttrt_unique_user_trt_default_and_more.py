# Generated by Django 4.2.6 on 2023-11-10 13:28

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        (
            "defaults",
            "0003_remove_defaultmedhistory_defaults_defaultmedhistory_unique_user_sideeffect_default_and_more",
        ),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="defaulttrt",
            name="unique_user_trt_default",
        ),
        migrations.AddConstraint(
            model_name="defaulttrt",
            constraint=models.UniqueConstraint(
                fields=("user", "treatment", "trttype"), name="defaults_defaulttrt_user_trt"
            ),
        ),
    ]