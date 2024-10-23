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
        related_aids: list["AidTypes"] = self.get_related_aids_for_medhistorytype(medhistorytype)

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

    def get_related_aids_for_medhistorytype(self, medhistorytype: "MedHistoryTypes") -> list["AidTypes"]:
        return (
            [relation for relation in self.mh_relations if medhistorytype in relation.poss_medhistorytypes]
            if (self.mh_relations and isinstance(self.mh_relations, list))
            else [self.mh_relations]
            if self.mh_relations
            else []
        )

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

    def get_queryset(self, medhistory: "UUID", medhistorytype: Union["MedHistoryTypes"]) -> "MedHistory":
        return (
            self.get_medhistory_model_from_medhistorytype(medhistorytype=medhistorytype)
            .objects.filter(pk=medhistory)
            .select_related("user__pseudopatientprofile__provider")
        )

    def set_attrs_from_qs(self, medhistory: "UUID", medhistorytype: Union["MedHistoryTypes"]) -> None:
        obj = self.get_queryset(medhistory=medhistory, medhistorytype=medhistorytype).get()
        setattr(self, medhistorytype.lower(), obj)
        self.patient = obj.user if not self.patient else self.patient

    def delete_medhistory(
        self, medhistory: Union["MedHistoryTypes", "UUID", None], medhistorytype: Union["MedHistoryTypes"]
    ) -> None:
        if self.is_uuid(medhistory):
            self.set_attrs_from_qs(medhistory=medhistory, medhistorytype=medhistorytype)
        self.check_for_medhistory_delete_errors(
            medhistory=medhistory,
            medhistorytype=medhistorytype,
        )
        self.check_for_and_raise_errors(model_name=medhistorytype.value.lower())
        medhistory.delete()
        setattr(self, medhistorytype.value.lower(), None)

    def check_for_medhistory_delete_errors(
        self, medhistory: Union["MedHistory", None], medhistorytype: Union["MedHistoryTypes"]
    ):
        mhtype_attr = medhistorytype.value.lower()
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
        elif not mh_val and medhistory:
            self.delete_medhistory(medhistory=medhistory, medhistorytype=medhistorytype)
        else:
            if self.medhistory_needs_update(medhistory=medhistory):
                self.update_medhistory(medhistory=medhistory, medhistorytype=medhistorytype)

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

    def update_medhistory(self, medhistory: MedHistory, medhistorytype: Union["MedHistoryTypes"]) -> None:
        if self.is_uuid(medhistory):
            self.set_attrs_from_qs(medhistory=medhistory, medhistorytype=medhistorytype)
        kwargs = {"user": self.patient}
        if self.mh_relations:
            if self.patient:
                for relation in self.mh_relations:
                    kwargs.update({relation.__class__.__name__.lower(): None})
            else:
                related_aids: list["AidTypes"] = self.get_related_aids_for_medhistorytype(medhistorytype)
                kwargs.update({relation.__class__.__name__.lower(): relation for relation in related_aids})
        medhistory.update(**kwargs)

    @classmethod
    def get_medhistory_model_from_medhistorytype(
        cls,
        medhistorytype: "MedHistoryTypes",
    ) -> "MedHistorys":
        return apps.get_model(app_label="medhistorys", model_name=medhistorytype.value.lower())


class AnginaAPIMixin(MedHistoryAPIMixin):
    angina: Union[Angina, "UUID", None]
    angina__value: bool | None

    def process_angina(self) -> None:
        self.process_medhistory(
            mh_val=self.angina__value,
            medhistory=self.angina,
            medhistorytype=Angina,
        )


class AnticoagulationAPIMixin(MedHistoryAPIMixin):
    anticoagulation: Union[Anticoagulation, "UUID", None]
    anticoagulation__value: bool | None

    def process_anticoagulation(self) -> None:
        self.process_medhistory(
            mh_val=self.anticoagulation__value,
            medhistory=self.anticoagulation,
            medhistorytype=Anticoagulation,
        )


class BleedAPIMixin(MedHistoryAPIMixin):
    bleed: Union[Bleed, "UUID", None]
    bleed__value: bool | None

    def process_bleed(self) -> None:
        self.process_medhistory(
            mh_val=self.bleed__value,
            medhistory=self.bleed,
            medhistorytype=Bleed,
        )


class CadAPIMixin(MedHistoryAPIMixin):
    cad: Union[Cad, "UUID", None]
    cad__value: bool | None

    def process_cad(self) -> None:
        self.process_medhistory(
            mh_val=self.cad__value,
            medhistory=self.cad,
            medhistorytype=Cad,
        )


class ChfAPIMixin(MedHistoryAPIMixin):
    chf: Union[Chf, "UUID", None]
    chf__value: bool | None

    def process_chf(self) -> None:
        self.process_medhistory(
            mh_val=self.chf__value,
            medhistory=self.chf,
            medhistorytype=Chf,
        )


class CkdAPIMixin(MedHistoryAPIMixin):
    ckd: Union[Ckd, "UUID", None]
    ckd__value: bool | None

    def process_ckd(self) -> None:
        self.process_medhistory(
            mh_val=self.ckd__value,
            medhistory=self.ckd,
            medhistorytype=Ckd,
        )


class ColchicineinteractionAPIMixin(MedHistoryAPIMixin):
    colchicineinteraction: Union[Colchicineinteraction, "UUID", None]
    colchicineinteraction__value: bool | None

    def process_colchicineinteraction(self) -> None:
        self.process_medhistory(
            mh_val=self.colchicineinteraction__value,
            medhistory=self.colchicineinteraction,
            medhistorytype=Colchicineinteraction,
        )


class DiabetesAPIMixin(MedHistoryAPIMixin):
    diabetes: Union[Diabetes, "UUID", None]
    diabetes__value: bool | None

    def process_diabetes(self) -> None:
        self.process_medhistory(
            mh_val=self.diabetes__value,
            medhistory=self.diabetes,
            medhistorytype=Diabetes,
        )


class ErosionsAPIMixin(MedHistoryAPIMixin):
    erosions: Union[Erosions, "UUID", None]
    erosions__value: bool | None

    def process_erosions(self) -> None:
        self.process_medhistory(
            mh_val=self.erosions__value,
            medhistory=self.erosions,
            medhistorytype=Erosions,
        )


class GastricbypassAPIMixin(MedHistoryAPIMixin):
    gastricbypass: Union[Gastricbypass, "UUID", None]
    gastricbypass__value: bool | None

    def process_gastricbypass(self) -> None:
        self.process_medhistory(
            mh_val=self.gastricbypass__value,
            medhistory=self.gastricbypass,
            medhistorytype=Gastricbypass,
        )


class GoutAPIMixin(MedHistoryAPIMixin):
    gout: Union[Gout, "UUID", None]
    gout__value: bool | None

    def process_gout(self) -> None:
        self.process_medhistory(
            mh_val=self.gout__value,
            medhistory=self.gout,
            medhistorytype=Gout,
        )


class HeartattackAPIMixin(MedHistoryAPIMixin):
    heartattack: Union[Heartattack, "UUID", None]
    heartattack__value: bool | None

    def process_heartattack(self) -> None:
        self.process_medhistory(
            mh_val=self.heartattack__value,
            medhistory=self.heartattack,
            medhistorytype=Heartattack,
        )


class HepatitisAPIMixin(MedHistoryAPIMixin):
    hepatitis: Union[Hepatitis, "UUID", None]
    hepatitis__value: bool | None

    def process_hepatitis(self) -> None:
        self.process_medhistory(
            mh_val=self.hepatitis__value,
            medhistory=self.hepatitis,
            medhistorytype=Hepatitis,
        )


class HypertensionAPIMixin(MedHistoryAPIMixin):
    hypertension: Union[Hypertension, "UUID", None]
    hypertension__value: bool | None

    def process_hypertension(self) -> None:
        self.process_medhistory(
            mh_val=self.hypertension__value,
            medhistory=self.hypertension,
            medhistorytype=Hypertension,
        )


class HyperuricemiaAPIMixin(MedHistoryAPIMixin):
    hyperuricemia: Union[Hyperuricemia, "UUID", None]
    hyperuricemia__value: bool | None

    def process_hyperuricemia(self) -> None:
        self.process_medhistory(
            mh_val=self.hyperuricemia__value,
            medhistory=self.hyperuricemia,
            medhistorytype=Hyperuricemia,
        )


class IbdAPIMixin(MedHistoryAPIMixin):
    ibd: Union[Ibd, "UUID", None]
    ibd__value: bool | None

    def process_ibd(self) -> None:
        self.process_medhistory(
            mh_val=self.ibd__value,
            medhistory=self.ibd,
            medhistorytype=Ibd,
        )


class MenopauseAPIMixin(MedHistoryAPIMixin):
    menopause: Union[Menopause, "UUID", None]
    menopause__value: bool | None

    def process_menopause(self) -> None:
        self.process_medhistory(
            mh_val=self.menopause__value,
            medhistory=self.menopause,
            medhistorytype=Menopause,
        )


class OrgantransplantAPIMixin(MedHistoryAPIMixin):
    organtransplant: Union[Organtransplant, "UUID", None]
    organtransplant__value: bool | None

    def process_organtransplant(self) -> None:
        self.process_medhistory(
            mh_val=self.organtransplant__value,
            medhistory=self.organtransplant,
            medhistorytype=Organtransplant,
        )


class OsteoporosisAPIMixin(MedHistoryAPIMixin):
    osteoporosis: Union[Osteoporosis, "UUID", None]
    osteoporosis__value: bool | None

    def process_osteoporosis(self) -> None:
        self.process_medhistory(
            mh_val=self.osteoporosis__value,
            medhistory=self.osteoporosis,
            medhistorytype=Osteoporosis,
        )


class PudAPIMixin(MedHistoryAPIMixin):
    pud: Union[Pud, "UUID", None]
    pud__value: bool | None

    def process_pud(self) -> None:
        self.process_medhistory(
            mh_val=self.pud__value,
            medhistory=self.pud,
            medhistorytype=Pud,
        )


class PvdAPIMixin(MedHistoryAPIMixin):
    pvd: Union[Pvd, "UUID", None]
    pvd__value: bool | None

    def process_pvd(self) -> None:
        self.process_medhistory(
            mh_val=self.pvd__value,
            medhistory=self.pvd,
            medhistorytype=Pvd,
        )


class StrokeAPIMixin(MedHistoryAPIMixin):
    stroke: Union[Stroke, "UUID", None]
    stroke__value: bool | None

    def process_stroke(self) -> None:
        self.process_medhistory(
            mh_val=self.stroke__value,
            medhistory=self.stroke,
            medhistorytype=Stroke,
        )


class TophiAPIMixin(MedHistoryAPIMixin):
    tophi: Union[Tophi, "UUID", None]
    tophi__value: bool | None

    def process_tophi(self) -> None:
        self.process_medhistory(
            mh_val=self.tophi__value,
            medhistory=self.tophi,
            medhistorytype=Tophi,
        )


class UratestonesAPIMixin(MedHistoryAPIMixin):
    uratestones: Union[Uratestones, "UUID", None]
    uratestones__value: bool | None

    def process_uratestones(self) -> None:
        self.process_medhistory(
            mh_val=self.uratestones__value,
            medhistory=self.uratestones,
            medhistorytype=Uratestones,
        )


class XoiinteractionAPIMixin(MedHistoryAPIMixin):
    xoiinteraction: Union[Xoiinteraction, "UUID", None]
    xoiinteraction__value: bool | None

    def process_xoiinteraction(self) -> None:
        self.process_medhistory(
            mh_val=self.xoiinteraction__value,
            medhistory=self.xoiinteraction,
            medhistorytype=Xoiinteraction,
        )
