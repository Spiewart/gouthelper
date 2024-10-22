from typing import TYPE_CHECKING, Union

from django.apps import apps

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
    from ...utils.types import AidTypes, MedHistorys


class MedHistoryAPIMixin(APIMixin):
    class Meta:
        abstract = True

    patient: Union["Pseudopatient", None]
    mh_relations: Union[
        "AidTypes",
        list["AidTypes"],
        None,
    ]

    MedHistoryTypes = MedHistoryTypes

    def create_medhistory(
        self,
        medhistory: Union["MedHistory", "UUID", None],
        medhistorytype: "MedHistoryTypes",
    ) -> "MedHistory":
        self.check_for_medhistory_create_errors(
            medhistory=medhistory,
            medhistorytype=medhistorytype,
        )
        self.check_for_and_raise_errors(model_name=medhistorytype.value.lower())
        related_aids: list["AidTypes"] = (
            [relation for relation in self.mh_relations if medhistorytype in relation.poss_medhistorytypes]
            if (self.mh_relations and isinstance(self.mh_relations, list))
            else [self.mh_relations]
            if self.mh_relations
            else []
        )

        new_mh = self.get_medhistory_model_from_medhistorytype(medhistorytype=medhistorytype).objects.create(
            user=self.patient,
            *[(related_aid.__class__.__name__.lower(), related_aid) for related_aid in related_aids],
        )
        setattr(
            self,
            medhistorytype.value.lower(),
            new_mh,
        )
        return new_mh

    def add_mh_relation(self, relation: "AidTypes") -> None:
        self.mh_relations.append(relation)

    def check_for_medhistory_create_errors(
        self,
        medhistory: Union[MedHistory, "UUID", None],
        medhistorytype: "MedHistoryTypes",
    ):
        if medhistory is not None:
            self.add_errors(
                api_args=[(f"{medhistorytype.value.lower()}", f"{medhistory} already exists.")],
            )

        if self.patient_has_medhistory(medhistorytype):
            self.add_errors(
                api_args=[
                    (
                        f"{medhistorytype.value.lower()}",
                        f"{self.patient} already has a {getattr(self.patient, medhistorytype.value.lower())}.",
                    )
                ],
            )

    def patient_has_medhistory(self, medhistorytype: "MedHistoryTypes") -> bool:
        return self.patient and bool(getattr(self.patient, medhistorytype.value.lower()))

    def get_queryset(self) -> "MedHistory":
        raise NotImplementedError("get_queryset() must be implemented in a subclass")

    def set_attrs_from_qs(self) -> None:
        obj = self.get_queryset().get()
        setattr(self, obj.__class__.__name__.lower(), obj)
        self.patient = obj.user if not self.patient else self.patient

    def delete_medhistory(self, medhistory: Union["MedHistoryTypes", "UUID", None]) -> None:
        if self.is_uuid(medhistory):
            self.set_attrs_from_qs()
        self.check_for_medhistory_delete_errors(
            medhistory=medhistory,
        )
        self.check_for_and_raise_errors(model_name=medhistory.medhistorytype.value.lower())
        medhistory.delete()

    def check_for_medhistory_delete_errors(self, medhistory: Union["MedHistory", None]):
        if not medhistory:
            self.add_errors(
                api_args=[
                    (f"{self.medhistorytype.value.lower()}", f"{self.medhistorytype.value.lower()} does not exist.")
                ],
            )
        else:
            mhtype_attr = medhistory.medhistorytype.value.lower()
            if getattr(self, f"{mhtype_attr}__value"):
                self.add_errors(
                    api_args=[
                        (
                            f"{mhtype_attr}__value",
                            f"{mhtype_attr}__value must be False to delete {medhistory}.",
                        )
                    ],
                )

    def process_medhistory(
        self,
        mh_val: bool | None,
        medhistory: Union[MedHistory, "UUID", None],
        medhistorytype: "MedHistoryTypes",
    ) -> None:
        if mh_val and not medhistory:
            self.create_medhistory(medhistory=medhistory, medhistorytype=medhistorytype)
        elif not mh_val and self.patient_has_medhistory(medhistorytype=medhistorytype):
            self.delete_medhistory(medhistory=medhistory)
        else:
            pass

    def medhistory_needs_update(
        self,
        medhistory: MedHistory,
    ) -> bool:
        return medhistory.user != self.patient or (
            self.mh_relations
            and any(
                getattr(
                    medhistory,
                    relation.__class__.__name__.lower(),
                )
                != relation
                for relation in self.mh_relations
            )
        )

    @classmethod
    def get_medhistory_model_from_medhistorytype(
        cls,
        medhistorytype: "MedHistoryTypes",
    ) -> "MedHistorys":
        return apps.get_model(app_label="medhistorys", model_name=medhistorytype.value.lower())


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
            medhistory=self.angina,
            medhistorytype=Angina,
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
            medhistory=self.anticoagulation,
            medhistorytype=Anticoagulation,
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
            medhistory=self.bleed,
            medhistorytype=Bleed,
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
            medhistory=self.cad,
            medhistorytype=Cad,
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
            medhistory=self.chf,
            medhistorytype=Chf,
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
            medhistory=self.ckd,
            medhistorytype=Ckd,
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
            medhistory=self.colchicineinteraction,
            medhistorytype=Colchicineinteraction,
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
            medhistory=self.diabetes,
            medhistorytype=Diabetes,
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
            medhistory=self.erosions,
            medhistorytype=Erosions,
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
            medhistory=self.gastricbypass,
            medhistorytype=Gastricbypass,
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
            medhistory=self.gout,
            medhistorytype=Gout,
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
            medhistory=self.heartattack,
            medhistorytype=Heartattack,
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
            medhistory=self.hepatitis,
            medhistorytype=Hepatitis,
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
            medhistory=self.hypertension,
            medhistorytype=Hypertension,
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
            medhistory=self.hyperuricemia,
            medhistorytype=Hyperuricemia,
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
            medhistory=self.ibd,
            medhistorytype=Ibd,
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
            medhistory=self.menopause,
            medhistorytype=Menopause,
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
            medhistory=self.organtransplant,
            medhistorytype=Organtransplant,
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
            medhistory=self.osteoporosis,
            medhistorytype=Osteoporosis,
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
            medhistory=self.pud,
            medhistorytype=Pud,
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
            medhistory=self.pvd,
            medhistorytype=Pvd,
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
            medhistory=self.stroke,
            medhistorytype=Stroke,
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
            medhistory=self.tophi,
            medhistorytype=Tophi,
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
            medhistory=self.uratestones,
            medhistorytype=Uratestones,
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
            medhistory=self.xoiinteraction,
            medhistorytype=Xoiinteraction,
        )
