from typing import TYPE_CHECKING, Union

from ...utils.services import APIMixin
from ..choices import MedHistoryTypes
from ..models import (
    Angina,
    Anticoagulation,
    Bleed,
    Cad,
    Chf,
    Ckd,
    Colchicineinteraction,
    Diabetes,
    Erosions,
    Gastricbypass,
    Gout,
    Heartattack,
    Hepatitis,
    Hypertension,
    Hyperuricemia,
    Ibd,
    MedHistory,
    Menopause,
    Organtransplant,
    Osteoporosis,
    Pud,
    Pvd,
    Stroke,
    Tophi,
    Uratestones,
    Xoiinteraction,
)

if TYPE_CHECKING:
    from uuid import UUID

    from ...users.models import Pseudopatient
    from ...utils.types import MedHistoryNames, MedHistorys


class MedHistoryAPIMixin(APIMixin):
    class Meta:
        abstract = True

    patient: Union["Pseudopatient", None]

    MedHistoryTypes = MedHistoryTypes

    def set_attrs_from_qs(self) -> None:
        obj = self.get_queryset().get()
        setattr(self, obj.__class__.__name__.lower(), obj)
        self.patient = obj.user if not self.patient else self.patient

    def create_medhistory(
        self, mh_arg: Union["MedHistoryTypes", "UUID", None], mh_name: "MedHistoryNames", mh_model: "MedHistoryTypes"
    ) -> "MedHistory":
        self.check_for_medhistory_create_errors(
            mh_arg=mh_arg,
            mh_name=mh_name,
        )
        self.check_for_and_raise_errors(model_name=mh_name)
        new_mh = mh_model.objects.create(
            user=self.patient,
        )
        setattr(
            self,
            mh_name,
            new_mh,
        )
        return new_mh

    def check_for_medhistory_create_errors(
        self,
        mh_arg: Union["MedHistorys", "UUID", None],
        mh_name: "MedHistoryNames",
    ):
        if mh_arg is not None:
            self.add_errors(
                api_args=[(f"{mh_name}", f"{mh_arg} already exists.")],
            )

        if self.patient_has_medhistory(mh_name=mh_name):
            self.add_errors(
                api_args=[(f"{mh_name}", f"{self.patient} already has a {getattr(self.patient, mh_name)}.")],
            )

    def patient_has_medhistory(self, mh_name: "MedHistoryNames") -> bool:
        return bool(getattr(self.patient, mh_name))

    def mh_arg_is_medhistory(self, mh_arg: Union["MedHistorys", "UUID", None]) -> bool:
        return isinstance(mh_arg, MedHistory)

    def delete_medhistory(self, mh_arg: Union["MedHistoryTypes", "UUID", None]) -> None:
        if self.is_uuid(mh_arg):
            self.set_attrs_from_qs()
        mh_name = mh_arg.__class__.__name__.lower()
        self.check_for_medhistory_delete_errors(
            mh_arg=mh_arg,
            mh_name=mh_name,
        )
        self.check_for_and_raise_errors(model_name=mh_name)
        mh_arg.delete()

    def check_for_medhistory_delete_errors(
        self, mh_arg: Union["MedHistoryTypes", "UUID", None], mh_name: "MedHistoryNames"
    ):
        if not mh_arg:
            self.add_errors(
                api_args=[(f"{mh_name}", f"{mh_name} does not exist.")],
            )

        if getattr(self, f"{mh_name}__value"):
            self.add_errors(
                api_args=[
                    (
                        f"{mh_name}__value",
                        f"{mh_name}__value must be False to delete {mh_arg}.",
                    )
                ],
            )

    def process_medhistory(
        self,
        mh_val: bool | None,
        mh_arg: Union["MedHistoryTypes", "UUID", None],
        mh_name: "MedHistoryNames",
        mh_model: "MedHistoryTypes",
    ) -> None:
        if mh_val and not self.mh_arg_is_medhistory(mh_arg):
            self.create_medhistory(mh_arg=mh_arg, mh_name=mh_name, mh_model=mh_model)
        elif not mh_val and self.patient_has_medhistory(mh_name=mh_name):
            self.delete_medhistory(mh_arg=mh_arg)


class AnginaAPIMixin(MedHistoryAPIMixin):
    angina: Union[Angina, "UUID", None]
    angina__value: bool | None

    def get_queryset(self) -> Angina:
        if not self.is_uuid(self.angina):
            raise TypeError("angina arg must be a UUID to call get_queryset()")
        return Angina.objects.filter(pk=self.model_attr).select_related("user")

    def process_angina(self) -> None:
        self.process_medhistory(
            mh_val=self.angina__value,
            mh_arg=self.angina,
            mh_name=MedHistoryTypes.ANGINA.lower(),
            mh_model=Angina,
        )


class AnticoagulationAPIMixin(MedHistoryAPIMixin):
    anticoagulation: Union[Anticoagulation, "UUID", None]
    anticoagulation__value: bool | None

    def get_queryset(self) -> Anticoagulation:
        if not self.is_uuid(self.anticoagulation):
            raise TypeError("anticoagulation arg must be a UUID to call get_queryset()")
        return Anticoagulation.objects.filter(pk=self.model_attr).select_related("user")

    def process_anticoagulation(self) -> None:
        self.process_medhistory(
            mh_val=self.anticoagulation__value,
            mh_arg=self.anticoagulation,
            mh_name=MedHistoryTypes.ANTICOAGULATION.lower(),
            mh_model=Anticoagulation,
        )


class BleedAPIMixin(MedHistoryAPIMixin):
    bleed: Union[Bleed, "UUID", None]
    bleed__value: bool | None

    def get_queryset(self) -> Bleed:
        if not self.is_uuid(self.bleed):
            raise TypeError("bleed arg must be a UUID to call get_queryset()")
        return Bleed.objects.filter(pk=self.model_attr).select_related("user")

    def process_bleed(self) -> None:
        self.process_medhistory(
            mh_val=self.bleed__value,
            mh_arg=self.bleed,
            mh_name=MedHistoryTypes.BLEED.lower(),
            mh_model=Bleed,
        )


class CadAPIMixin(MedHistoryAPIMixin):
    cad: Union[Cad, "UUID", None]
    cad__value: bool | None

    def get_queryset(self) -> Cad:
        if not self.is_uuid(self.cad):
            raise TypeError("cad arg must be a UUID to call get_queryset()")
        return Cad.objects.filter(pk=self.model_attr).select_related("user")

    def process_cad(self) -> None:
        self.process_medhistory(
            mh_val=self.cad__value,
            mh_arg=self.cad,
            mh_name=MedHistoryTypes.CAD.lower(),
            mh_model=Cad,
        )


class ChfAPIMixin(MedHistoryAPIMixin):
    chf: Union[Chf, "UUID", None]
    chf__value: bool | None

    def get_queryset(self) -> Chf:
        if not self.is_uuid(self.chf):
            raise TypeError("chf arg must be a UUID to call get_queryset()")
        return Chf.objects.filter(pk=self.model_attr).select_related("user")

    def process_chf(self) -> None:
        self.process_medhistory(
            mh_val=self.chf__value,
            mh_arg=self.chf,
            mh_name=MedHistoryTypes.CHF.lower(),
            mh_model=Chf,
        )


class CkdAPIMixin(MedHistoryAPIMixin):
    ckd: Union[Ckd, "UUID", None]
    ckd__value: bool | None

    def get_queryset(self) -> Ckd:
        if not self.is_uuid(self.ckd):
            raise TypeError("ckd arg must be a UUID to call get_queryset()")
        return Ckd.objects.filter(pk=self.model_attr).select_related("user")

    def process_ckd(self) -> None:
        self.process_medhistory(
            mh_val=self.ckd__value,
            mh_arg=self.ckd,
            mh_name=MedHistoryTypes.CKD.lower(),
            mh_model=Ckd,
        )


class ColchicineinteractionAPIMixin(MedHistoryAPIMixin):
    colchicineinteraction: Union[Colchicineinteraction, "UUID", None]
    colchicineinteraction__value: bool | None

    def get_queryset(self) -> Colchicineinteraction:
        if not self.is_uuid(self.colchicineinteraction):
            raise TypeError("colchicineinteraction arg must be a UUID to call get_queryset()")
        return Colchicineinteraction.objects.filter(pk=self.model_attr).select_related("user")

    def process_colchicineinteraction(self) -> None:
        self.process_medhistory(
            mh_val=self.colchicineinteraction__value,
            mh_arg=self.colchicineinteraction,
            mh_name=MedHistoryTypes.COLCHICINEINTERACTION.lower(),
            mh_model=Colchicineinteraction,
        )


class DiabetesAPIMixin(MedHistoryAPIMixin):
    diabetes: Union[Diabetes, "UUID", None]
    diabetes__value: bool | None

    def get_queryset(self) -> Diabetes:
        if not self.is_uuid(self.diabetes):
            raise TypeError("diabetes arg must be a UUID to call get_queryset()")
        return Diabetes.objects.filter(pk=self.model_attr).select_related("user")

    def process_diabetes(self) -> None:
        self.process_medhistory(
            mh_val=self.diabetes__value,
            mh_arg=self.diabetes,
            mh_name=MedHistoryTypes.DIABETES.lower(),
            mh_model=Diabetes,
        )


class ErosionsAPIMixin(MedHistoryAPIMixin):
    erosions: Union[Erosions, "UUID", None]
    erosions__value: bool | None

    def get_queryset(self) -> Erosions:
        if not self.is_uuid(self.erosions):
            raise TypeError("erosions arg must be a UUID to call get_queryset()")
        return Erosions.objects.filter(pk=self.model_attr).select_related("user")

    def process_erosions(self) -> None:
        self.process_medhistory(
            mh_val=self.erosions__value,
            mh_arg=self.erosions,
            mh_name=MedHistoryTypes.EROSIONS.lower(),
            mh_model=Erosions,
        )


class GastricbypassAPIMixin(MedHistoryAPIMixin):
    gastricbypass: Union[Gastricbypass, "UUID", None]
    gastricbypass__value: bool | None

    def get_queryset(self) -> Gastricbypass:
        if not self.is_uuid(self.gastricbypass):
            raise TypeError("gastricbypass arg must be a UUID to call get_queryset()")
        return Gastricbypass.objects.filter(pk=self.model_attr).select_related("user")

    def process_gastricbypass(self) -> None:
        self.process_medhistory(
            mh_val=self.gastricbypass__value,
            mh_arg=self.gastricbypass,
            mh_name=MedHistoryTypes.GASTRICBYPASS.lower(),
            mh_model=Gastricbypass,
        )


class GoutAPIMixin(MedHistoryAPIMixin):
    gout: Union[Gout, "UUID", None]
    gout__value: bool | None

    def get_queryset(self) -> Gout:
        if not self.is_uuid(self.gout):
            raise TypeError("gout arg must be a UUID to call get_queryset()")
        return Gout.objects.filter(pk=self.model_attr).select_related("user")

    def process_gout(self) -> None:
        self.process_medhistory(
            mh_val=self.gout__value,
            mh_arg=self.gout,
            mh_name=MedHistoryTypes.GOUT.lower(),
            mh_model=Gout,
        )


class HeartattackAPIMixin(MedHistoryAPIMixin):
    heartattack: Union[Heartattack, "UUID", None]
    heartattack__value: bool | None

    def get_queryset(self) -> Heartattack:
        if not self.is_uuid(self.heartattack):
            raise TypeError("heartattack arg must be a UUID to call get_queryset()")
        return Heartattack.objects.filter(pk=self.model_attr).select_related("user")

    def process_heartattack(self) -> None:
        self.process_medhistory(
            mh_val=self.heartattack__value,
            mh_arg=self.heartattack,
            mh_name=MedHistoryTypes.HEARTATTACK.lower(),
            mh_model=Heartattack,
        )


class HepatitisAPIMixin(MedHistoryAPIMixin):
    hepatitis: Union[Hepatitis, "UUID", None]
    hepatitis__value: bool | None

    def get_queryset(self) -> Hepatitis:
        if not self.is_uuid(self.hepatitis):
            raise TypeError("hepatitis arg must be a UUID to call get_queryset()")
        return Hepatitis.objects.filter(pk=self.model_attr).select_related("user")

    def process_hepatitis(self) -> None:
        self.process_medhistory(
            mh_val=self.hepatitis__value,
            mh_arg=self.hepatitis,
            mh_name=MedHistoryTypes.HEPATITIS.lower(),
            mh_model=Hepatitis,
        )


class HypertensionAPIMixin(MedHistoryAPIMixin):
    hypertension: Union[Hypertension, "UUID", None]
    hypertension__value: bool | None

    def get_queryset(self) -> Hypertension:
        if not self.is_uuid(self.hypertension):
            raise TypeError("hypertension arg must be a UUID to call get_queryset()")
        return Hypertension.objects.filter(pk=self.model_attr).select_related("user")

    def process_hypertension(self) -> None:
        self.process_medhistory(
            mh_val=self.hypertension__value,
            mh_arg=self.hypertension,
            mh_name=MedHistoryTypes.HYPERTENSION.lower(),
            mh_model=Hypertension,
        )


class HyperuricemiaAPIMixin(MedHistoryAPIMixin):
    hyperuricemia: Union[Hyperuricemia, "UUID", None]
    hyperuricemia__value: bool | None

    def get_queryset(self) -> Hyperuricemia:
        if not self.is_uuid(self.hyperuricemia):
            raise TypeError("hyperuricemia arg must be a UUID to call get_queryset()")
        return Hyperuricemia.objects.filter(pk=self.model_attr).select_related("user")

    def process_hyperuricemia(self) -> None:
        self.process_medhistory(
            mh_val=self.hyperuricemia__value,
            mh_arg=self.hyperuricemia,
            mh_name=MedHistoryTypes.HYPERURICEMIA.lower(),
            mh_model=Hyperuricemia,
        )


class IbdAPIMixin(MedHistoryAPIMixin):
    ibd: Union[Ibd, "UUID", None]
    ibd__value: bool | None

    def get_queryset(self) -> Ibd:
        if not self.is_uuid(self.ibd):
            raise TypeError("ibd arg must be a UUID to call get_queryset()")
        return Ibd.objects.filter(pk=self.model_attr).select_related("user")

    def process_ibd(self) -> None:
        self.process_medhistory(
            mh_val=self.ibd__value,
            mh_arg=self.ibd,
            mh_name=MedHistoryTypes.IBD.lower(),
            mh_model=Ibd,
        )


class MenopauseAPIMixin(MedHistoryAPIMixin):
    menopause: Union[Menopause, "UUID", None]
    menopause__value: bool | None

    def get_queryset(self) -> Menopause:
        if not self.is_uuid(self.menopause):
            raise TypeError("menopause arg must be a UUID to call get_queryset()")
        return Menopause.objects.filter(pk=self.model_attr).select_related("user")

    def process_menopause(self) -> None:
        self.process_medhistory(
            mh_val=self.menopause__value,
            mh_arg=self.menopause,
            mh_name=MedHistoryTypes.MENOPAUSE.lower(),
            mh_model=Menopause,
        )


class OrgantransplantAPIMixin(MedHistoryAPIMixin):
    organtransplant: Union[Organtransplant, "UUID", None]
    organtransplant__value: bool | None

    def get_queryset(self) -> Organtransplant:
        if not self.is_uuid(self.organtransplant):
            raise TypeError("organtransplant arg must be a UUID to call get_queryset()")
        return Organtransplant.objects.filter(pk=self.model_attr).select_related("user")

    def process_organtransplant(self) -> None:
        self.process_medhistory(
            mh_val=self.organtransplant__value,
            mh_arg=self.organtransplant,
            mh_name=MedHistoryTypes.ORGANTRANSPLANT.lower(),
            mh_model=Organtransplant,
        )


class OsteoporosisAPIMixin(MedHistoryAPIMixin):
    osteoporosis: Union[Osteoporosis, "UUID", None]
    osteoporosis__value: bool | None

    def get_queryset(self) -> Osteoporosis:
        if not self.is_uuid(self.osteoporosis):
            raise TypeError("osteoporosis arg must be a UUID to call get_queryset()")
        return Osteoporosis.objects.filter(pk=self.model_attr).select_related("user")

    def process_osteoporosis(self) -> None:
        self.process_medhistory(
            mh_val=self.osteoporosis__value,
            mh_arg=self.osteoporosis,
            mh_name=MedHistoryTypes.OSTEOPOROSIS.lower(),
            mh_model=Osteoporosis,
        )


class PudAPIMixin(MedHistoryAPIMixin):
    pud: Union[Pud, "UUID", None]
    pud__value: bool | None

    def get_queryset(self) -> Pud:
        if not self.is_uuid(self.pud):
            raise TypeError("pud arg must be a UUID to call get_queryset()")
        return Pud.objects.filter(pk=self.model_attr).select_related("user")

    def process_pud(self) -> None:
        self.process_medhistory(
            mh_val=self.pud__value,
            mh_arg=self.pud,
            mh_name=MedHistoryTypes.PUD.lower(),
            mh_model=Pud,
        )


class PvdAPIMixin(MedHistoryAPIMixin):
    pvd: Union[Pvd, "UUID", None]
    pvd__value: bool | None

    def get_queryset(self) -> Pvd:
        if not self.is_uuid(self.pvd):
            raise TypeError("pvd arg must be a UUID to call get_queryset()")
        return Pvd.objects.filter(pk=self.model_attr).select_related("user")

    def process_pvd(self) -> None:
        self.process_medhistory(
            mh_val=self.pvd__value,
            mh_arg=self.pvd,
            mh_name=MedHistoryTypes.PVD.lower(),
            mh_model=Pvd,
        )


class StrokeAPIMixin(MedHistoryAPIMixin):
    stroke: Union[Stroke, "UUID", None]
    stroke__value: bool | None

    def get_queryset(self) -> Stroke:
        if not self.is_uuid(self.stroke):
            raise TypeError("stroke arg must be a UUID to call get_queryset()")
        return Stroke.objects.filter(pk=self.model_attr).select_related("user")

    def process_stroke(self) -> None:
        self.process_medhistory(
            mh_val=self.stroke__value,
            mh_arg=self.stroke,
            mh_name=MedHistoryTypes.STROKE.lower(),
            mh_model=Stroke,
        )


class TophiAPIMixin(MedHistoryAPIMixin):
    tophi: Union[Tophi, "UUID", None]
    tophi__value: bool | None

    def get_queryset(self) -> Tophi:
        if not self.is_uuid(self.tophi):
            raise TypeError("tophi arg must be a UUID to call get_queryset()")
        return Tophi.objects.filter(pk=self.model_attr).select_related("user")

    def process_tophi(self) -> None:
        self.process_medhistory(
            mh_val=self.tophi__value,
            mh_arg=self.tophi,
            mh_name=MedHistoryTypes.TOPHI.lower(),
            mh_model=Tophi,
        )


class UratestonesAPIMixin(MedHistoryAPIMixin):
    uratestones: Union[Uratestones, "UUID", None]
    uratestones__value: bool | None

    def get_queryset(self) -> Uratestones:
        if not self.is_uuid(self.uratestones):
            raise TypeError("uratestones arg must be a UUID to call get_queryset()")
        return Uratestones.objects.filter(pk=self.model_attr).select_related("user")

    def process_uratestones(self) -> None:
        self.process_medhistory(
            mh_val=self.uratestones__value,
            mh_arg=self.uratestones,
            mh_name=MedHistoryTypes.URATESTONES.lower(),
            mh_model=Uratestones,
        )


class XoiinteractionAPIMixin(MedHistoryAPIMixin):
    xoiinteraction: Union[Xoiinteraction, "UUID", None]
    xoiinteraction__value: bool | None

    def get_queryset(self) -> Xoiinteraction:
        if not self.is_uuid(self.xoiinteraction):
            raise TypeError("xoiinteraction arg must be a UUID to call get_queryset()")
        return Xoiinteraction.objects.filter(pk=self.model_attr).select_related("user")

    def process_xoiinteraction(self) -> None:
        self.process_medhistory(
            mh_val=self.xoiinteraction__value,
            mh_arg=self.xoiinteraction,
            mh_name=MedHistoryTypes.XOIINTERACTION.lower(),
            mh_model=Xoiinteraction,
        )
