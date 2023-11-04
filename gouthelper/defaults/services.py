from ..medhistorys.dicts import historys_get_treatments_contras
from ..treatments.dicts import treatments_get_default_dosing


def create_or_update_default_settings(apps, schema_editor):
    """Method that creates or updates DefaultSettings, DefaultFlareTrtSettings,
    DefaultPpxTrtSettings, and DefaultUltTrtSettings Gouthelper default objects
    in the database."""
    DefaultFlareTrtSettings = apps.get_model("defaults", "DefaultFlareTrtSettings")
    DefaultPpxTrtSettings = apps.get_model("defaults", "DefaultPpxTrtSettings")
    DefaultUltTrtSettings = apps.get_model("defaults", "DefaultUltTrtSettings")
    DefaultFlareTrtSettings.objects.update_or_create(
        user=None,
    )
    DefaultPpxTrtSettings.objects.update_or_create(
        user=None,
    )
    DefaultUltTrtSettings.objects.update_or_create(
        user=None,
    )


def create_or_update_default_trt_medhistory_contras(apps, schema_editor):
    """Method that creates or updates DefaultMedHistory objects in the database.
    Uses historys_get_treatments_contras to get the Gouthelper dict of default
    values.
    """
    DefaultMedHistory = apps.get_model("defaults", "DefaultMedHistory")
    mh_trt_contras = historys_get_treatments_contras()
    for treatment, trttype_dict in mh_trt_contras.items():
        for trttype, contra_dict in trttype_dict.items():
            for medhistorytype, contraindication in contra_dict.items():
                DefaultMedHistory.objects.update_or_create(
                    contraindication=contraindication,
                    medhistorytype=medhistorytype,
                    treatment=treatment,
                    trttype=trttype,
                    user=None,
                )


def create_or_update_default_treatments(apps, schema_editor):
    """Method that creates or updates DefaultTrt objects in the database.
    Uses treatments_get_default_dosing to get the Gouthelper dict of default
    values.
    """
    DefaultTrt = apps.get_model("defaults", "DefaultTrt")
    dosing_dict = treatments_get_default_dosing()
    for trt, trttype_dict in dosing_dict.items():
        for key, val in trttype_dict.items():
            trttype, dosing_dict = key, val
            DefaultTrt.objects.update_or_create(
                treatment=trt,
                trttype=trttype,
                user=None,
                **dosing_dict,
            )


def delete_obsolete_default_trt_medhistory_contras(apps, schema_editor):
    """Method that deletes obsolete DefaultMedHistory objects in the database.
    Uses historys_get_treatments_contras to get the Gouthelper list of default
    values.
    """
    DefaultMedHistory = apps.get_model("defaults", "DefaultMedHistory")
    mh_trt_contras = historys_get_treatments_contras()
    defaults = DefaultMedHistory.objects.filter(user=None).all()
    for default in defaults:
        try:
            mh_trt_contras[default.treatment][default.trttype][default.medhistorytype]
        except KeyError:
            default.delete()


def delete_obsolete_default_treatments(apps, schema_editor):
    """Method that deletes obsolete DefaultTrt objects in the database.
    Uses treatments_get_default_dosing to get the Gouthelper list of default
    values.
    """
    DefaultTrt = apps.get_model("defaults", "DefaultTrt")
    dosing_dict = treatments_get_default_dosing()
    defaults = DefaultTrt.objects.filter(user=None).all()
    for default in defaults:
        try:
            dosing_dict[default.treatment][default.trttype]
        except KeyError:
            default.delete()


def update_defaults(apps, schema_editor):
    """Method that runs all the update and delete methods in this file,
    typically as part of a migration, but can also be run from the shell."""
    create_or_update_default_settings(apps, schema_editor)
    delete_obsolete_default_treatments(apps, schema_editor)
    create_or_update_default_treatments(apps, schema_editor)
    delete_obsolete_default_trt_medhistory_contras(apps, schema_editor)
    create_or_update_default_trt_medhistory_contras(apps, schema_editor)
