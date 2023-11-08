from factory.django import DjangoModelFactory  # type: ignore

from ..models import (
    Allopurinolhypersensitivity,
    Angina,
    Anticoagulation,
    Bleed,
    Cad,
    Chf,
    Ckd,
    Colchicineinteraction,
    Diabetes,
    Erosions,
    Febuxostathypersensitivity,
    Gastricbypass,
    Gout,
    Heartattack,
    Hypertension,
    Hyperuricemia,
    Ibd,
    MedHistory,
    Menopause,
    Organtransplant,
    Osteoporosis,
    Pvd,
    Stroke,
    Tophi,
    Uratestones,
    Xoiinteraction,
)


class MedHistoryFactory(DjangoModelFactory):
    class Meta:
        model = MedHistory


class AllopurinolhypersensitivityFactory(MedHistoryFactory):
    class Meta:
        model = Allopurinolhypersensitivity


class AnginaFactory(MedHistoryFactory):
    class Meta:
        model = Angina


class AnticoagulationFactory(MedHistoryFactory):
    class Meta:
        model = Anticoagulation


class BleedFactory(MedHistoryFactory):
    class Meta:
        model = Bleed


class CadFactory(MedHistoryFactory):
    """Factory for creating Cad MedHistory objects."""

    class Meta:
        model = Cad


class ChfFactory(MedHistoryFactory):
    class Meta:
        model = Chf


class CkdFactory(MedHistoryFactory):
    class Meta:
        model = Ckd


class ColchicineinteractionFactory(MedHistoryFactory):
    class Meta:
        model = Colchicineinteraction


class DiabetesFactory(MedHistoryFactory):
    class Meta:
        model = Diabetes


class ErosionsFactory(MedHistoryFactory):
    class Meta:
        model = Erosions


class FebuxostathypersensitivityFactory(MedHistoryFactory):
    class Meta:
        model = Febuxostathypersensitivity


class GastricbypassFactory(MedHistoryFactory):
    class Meta:
        model = Gastricbypass


class GoutFactory(MedHistoryFactory):
    class Meta:
        model = Gout


class HeartattackFactory(MedHistoryFactory):
    class Meta:
        model = Heartattack


class HypertensionFactory(MedHistoryFactory):
    class Meta:
        model = Hypertension


class HyperuricemiaFactory(MedHistoryFactory):
    class Meta:
        model = Hyperuricemia


class IbdFactory(MedHistoryFactory):
    class Meta:
        model = Ibd


class MenopauseFactory(MedHistoryFactory):
    class Meta:
        model = Menopause


class OrgantransplantFactory(MedHistoryFactory):
    class Meta:
        model = Organtransplant


class OsteoporosisFactory(MedHistoryFactory):
    class Meta:
        model = Osteoporosis


class PvdFactory(MedHistoryFactory):
    class Meta:
        model = Pvd


class StrokeFactory(MedHistoryFactory):
    class Meta:
        model = Stroke


class TophiFactory(MedHistoryFactory):
    class Meta:
        model = Tophi


class UratestonesFactory(MedHistoryFactory):
    class Meta:
        model = Uratestones


class XoiinteractionFactory(MedHistoryFactory):
    class Meta:
        model = Xoiinteraction
