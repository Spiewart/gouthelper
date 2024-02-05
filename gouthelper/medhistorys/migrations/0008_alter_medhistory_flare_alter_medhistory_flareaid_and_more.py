# Generated by Django 4.2.6 on 2024-01-29 01:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("ppxs", "0004_remove_ppx_labs_remove_ppx_medhistorys"),
        ("ults", "0004_remove_ult_medhistorys"),
        ("ppxaids", "0004_remove_ppxaid_medallergys_remove_ppxaid_medhistorys"),
        ("flareaids", "0005_remove_flareaid_medallergys_and_more"),
        ("ultaids", "0004_remove_ultaid_medallergys_remove_ultaid_medhistorys"),
        ("goalurates", "0004_remove_goalurate_medhistorys"),
        ("flares", "0008_alter_historicalflare_urate_alter_flare_urate_and_more"),
        ("medhistorys", "0007_medhistory_medhistorys_medhistory_user_aid_exclusive"),
    ]

    operations = [
        migrations.AlterField(
            model_name="medhistory",
            name="flare",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s",
                to="flares.flare",
            ),
        ),
        migrations.AlterField(
            model_name="medhistory",
            name="flareaid",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s",
                to="flareaids.flareaid",
            ),
        ),
        migrations.AlterField(
            model_name="medhistory",
            name="goalurate",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s",
                to="goalurates.goalurate",
            ),
        ),
        migrations.AlterField(
            model_name="medhistory",
            name="ppx",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s",
                to="ppxs.ppx",
            ),
        ),
        migrations.AlterField(
            model_name="medhistory",
            name="ppxaid",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s",
                to="ppxaids.ppxaid",
            ),
        ),
        migrations.AlterField(
            model_name="medhistory",
            name="ult",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s",
                to="ults.ult",
            ),
        ),
        migrations.AlterField(
            model_name="medhistory",
            name="ultaid",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s",
                to="ultaids.ultaid",
            ),
        ),
    ]