from django.db.models import Manager  # type: ignore

from .choices import MedHistoryTypes


class AllopurinolhypersensitivityManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(medhistorytype=MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY)

    def create(self, **kwargs):
        kwargs.update({"medhistorytype": MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY})
        return super().create(**kwargs)


class AnginaManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(medhistorytype=MedHistoryTypes.ANGINA)

    def create(self, **kwargs):
        kwargs.update({"medhistorytype": MedHistoryTypes.ANGINA})
        return super().create(**kwargs)


class AnticoagulationManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(medhistorytype=MedHistoryTypes.ANTICOAGULATION)

    def create(self, **kwargs):
        kwargs.update({"medhistorytype": MedHistoryTypes.ANTICOAGULATION})
        return super().create(**kwargs)


class BleedManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(medhistorytype=MedHistoryTypes.BLEED)

    def create(self, **kwargs):
        kwargs.update({"medhistorytype": MedHistoryTypes.BLEED})
        return super().create(**kwargs)


class CadManager(Manager):
    """Manager for Cad MedHistory proxy model."""

    def get_queryset(self):
        """Filters QuerySet to only include Cad MedHistory objects."""
        return super().get_queryset().filter(medhistorytype=MedHistoryTypes.CAD)

    def create(self, **kwargs):
        """Creates a new MedHistory object with medhistorytype=CAD."""
        kwargs.update({"medhistorytype": MedHistoryTypes.CAD})
        return super().create(**kwargs)


class ChfManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(medhistorytype=MedHistoryTypes.CHF)

    def create(self, **kwargs):
        kwargs.update({"medhistorytype": MedHistoryTypes.CHF})
        return super().create(**kwargs)


class CkdManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(medhistorytype=MedHistoryTypes.CKD)

    def create(self, **kwargs):
        kwargs.update({"medhistorytype": MedHistoryTypes.CKD})
        return super().create(**kwargs)


class CkdRelationsManager(CkdManager):
    def get_queryset(self):
        return super().get_queryset().select_related("baselinecreatinine", "ckddetail")


class ColchicineinteractionManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(medhistorytype=MedHistoryTypes.COLCHICINEINTERACTION)

    def create(self, **kwargs):
        kwargs.update({"medhistorytype": MedHistoryTypes.COLCHICINEINTERACTION})
        return super().create(**kwargs)


class DiabetesManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(medhistorytype=MedHistoryTypes.DIABETES)

    def create(self, **kwargs):
        kwargs.update({"medhistorytype": MedHistoryTypes.DIABETES})
        return super().create(**kwargs)


class ErosionsManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(medhistorytype=MedHistoryTypes.EROSIONS)

    def create(self, **kwargs):
        kwargs.update({"medhistorytype": MedHistoryTypes.EROSIONS})
        return super().create(**kwargs)


class FebuxostathypersensitivityManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(medhistorytype=MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY)

    def create(self, **kwargs):
        kwargs.update({"medhistorytype": MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY})
        return super().create(**kwargs)


class GastricbypassManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(medhistorytype=MedHistoryTypes.GASTRICBYPASS)

    def create(self, **kwargs):
        kwargs.update({"medhistorytype": MedHistoryTypes.GASTRICBYPASS})
        return super().create(**kwargs)


class GoutManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(medhistorytype=MedHistoryTypes.GOUT)

    def create(self, **kwargs):
        kwargs.update({"medhistorytype": MedHistoryTypes.GOUT})
        return super().create(**kwargs)


class GoutRelationsManager(GoutManager):
    def get_queryset(self):
        return super().get_queryset().select_related("goutdetail")


class HeartattackManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(medhistorytype=MedHistoryTypes.HEARTATTACK)

    def create(self, **kwargs):
        kwargs.update({"medhistorytype": MedHistoryTypes.HEARTATTACK})
        return super().create(**kwargs)


class HypertensionManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(medhistorytype=MedHistoryTypes.HYPERTENSION)

    def create(self, **kwargs):
        kwargs.update({"medhistorytype": MedHistoryTypes.HYPERTENSION})
        return super().create(**kwargs)


class HyperuricemiaManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(medhistorytype=MedHistoryTypes.HYPERURICEMIA)

    def create(self, **kwargs):
        kwargs.update({"medhistorytype": MedHistoryTypes.HYPERURICEMIA})
        return super().create(**kwargs)


class IbdManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(medhistorytype=MedHistoryTypes.IBD)

    def create(self, **kwargs):
        kwargs.update({"medhistorytype": MedHistoryTypes.IBD})
        return super().create(**kwargs)


class MenopauseManager(Manager):
    """Sets medhistorytype to Menopause when creating a new instance and
    filters queryset to only include Menopause instances."""

    def get_queryset(self):
        return super().get_queryset().filter(medhistorytype=MedHistoryTypes.MENOPAUSE)

    def create(self, **kwargs):
        kwargs.update({"medhistorytype": MedHistoryTypes.MENOPAUSE})
        return super().create(**kwargs)


class OrgantransplantManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(medhistorytype=MedHistoryTypes.ORGANTRANSPLANT)

    def create(self, **kwargs):
        kwargs.update({"medhistorytype": MedHistoryTypes.ORGANTRANSPLANT})
        return super().create(**kwargs)


class OsteoporosisManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(medhistorytype=MedHistoryTypes.OSTEOPOROSIS)

    def create(self, **kwargs):
        kwargs.update({"medhistorytype": MedHistoryTypes.OSTEOPOROSIS})
        return super().create(**kwargs)


class PudManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(medhistorytype=MedHistoryTypes.PUD)

    def create(self, **kwargs):
        kwargs.update({"medhistorytype": MedHistoryTypes.PUD})
        return super().create(**kwargs)


class PvdManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(medhistorytype=MedHistoryTypes.PVD)

    def create(self, **kwargs):
        kwargs.update({"medhistorytype": MedHistoryTypes.PVD})
        return super().create(**kwargs)


class StrokeManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(medhistorytype=MedHistoryTypes.STROKE)

    def create(self, **kwargs):
        kwargs.update({"medhistorytype": MedHistoryTypes.STROKE})
        return super().create(**kwargs)


class TophiManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(medhistorytype=MedHistoryTypes.TOPHI)

    def create(self, **kwargs):
        kwargs.update({"medhistorytype": MedHistoryTypes.TOPHI})
        return super().create(**kwargs)


class UratestonesManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(medhistorytype=MedHistoryTypes.URATESTONES)

    def create(self, **kwargs):
        kwargs.update({"medhistorytype": MedHistoryTypes.URATESTONES})
        return super().create(**kwargs)


class XoiinteractionManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(medhistorytype=MedHistoryTypes.XOIINTERACTION)

    def create(self, **kwargs):
        kwargs.update({"medhistorytype": MedHistoryTypes.XOIINTERACTION})
        return super().create(**kwargs)
