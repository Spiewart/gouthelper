from typing import TYPE_CHECKING, Union

from django.apps import apps

from ...medhistorydetails.api.mixins import CkdDetailAPIMixin
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
    from datetime import date
    from decimal import Decimal
    from uuid import UUID

    from django.db.models import QuerySet

    from ...dateofbirths.models import DateOfBirth
    from ...genders.choices import Genders
    from ...genders.models import Gender
    from ...labs.models import BaselineCreatinine
    from ...medhistorydetails.choices import DialysisChoices, DialysisDurations, Stages
    from ...medhistorydetails.models import CkdDetail
    from ...medhistorys.types import GoutData
    from ...users.models import Pseudopatient
    from ...utils.types import AidTypes, MedHistorys


class MedHistoryAPIMixin(APIMixin):
    class Meta:
        abstract = True

    patient: Union["Pseudopatient", None]
    medhistorytypes: list[MedHistoryTypes]
    mh_relations: Union[
        "AidTypes",
        list["AidTypes"],
        None,
    ]

    MedHistoryTypes = MedHistoryTypes

    def set_medhistorytypes(self) -> list[MedHistoryTypes]:
        if not hasattr(self, "medhistorytypes"):
            self.medhistorytypes = []

    def create_medhistory(
        self,
        medhistory__value: bool | None,
        medhistory: Union["MedHistory", "UUID", None],
        medhistorytype: "MedHistoryTypes",
    ) -> Union["MedHistory", None]:
        if not hasattr(self, f"{medhistorytype.value.lower()}_errors"):
            self.check_for_medhistory_create_errors(
                medhistory__value=medhistory__value,
                medhistory=medhistory,
                medhistorytype=medhistorytype,
            )

        if not self.errors:
            related_aids: list["AidTypes"] = self.get_related_aids_for_medhistorytype(medhistorytype)

            new_mh = self.get_medhistory_model_from_medhistorytype(medhistorytype=medhistorytype).objects.create(
                user=self.patient,
                *[(related_aid.__class__.__name__.lower(), related_aid) for related_aid in related_aids],
            )

            self.set_medhistory(new_mh)
            return new_mh

    def set_medhistory(self, medhistory: "MedHistory") -> None:
        if self.object:
            setattr(self.object, medhistory.__class__.__name__.lower(), medhistory)
        else:
            setattr(self, medhistory.__class__.__name__.lower(), medhistory)

    def get_related_aids_for_medhistorytype(self, medhistorytype: "MedHistoryTypes") -> list["AidTypes"]:
        if hasattr(self, "mh_relations") and self.mh_relations:
            return (
                [relation for relation in self.mh_relations if medhistorytype in relation.poss_medhistorytypes]
                if isinstance(self.mh_relations, list)
                else [self.mh_relations]
            )
        return []

    def add_mh_relation(self, relation: "AidTypes") -> None:
        self.mh_relations.append(relation)

    def check_for_medhistory_create_errors(
        self,
        medhistory__value: bool | None,
        medhistory: Union[MedHistory, "UUID", None],
        medhistorytype: "MedHistoryTypes",
    ):
        if medhistory is not None:
            self.add_errors(
                api_args=[(f"{medhistorytype.value.lower()}", f"{medhistory} already exists.")],
            )

        if not medhistory__value:
            self.add_errors(
                api_args=[
                    (f"{medhistorytype.value.lower()}__value", f"{medhistorytype.value.lower()}__value isn't True.")
                ],
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

        if medhistory is not None or self.patient_has_medhistory(medhistorytype):
            setattr(self, f"{medhistorytype.value.lower()}_errors", True)
        else:
            setattr(self, f"{medhistorytype.value.lower()}_errors", False)

    def patient_has_medhistory(self, medhistorytype: "MedHistoryTypes") -> bool:
        return self.patient and bool(getattr(self.patient, medhistorytype.value.lower()))

    def get_queryset(self, medhistory: "UUID", medhistorytype: Union["MedHistoryTypes"]) -> "QuerySet":
        return (
            self.get_medhistory_model_from_medhistorytype(medhistorytype=medhistorytype)
            .objects.filter(pk=medhistory)
            .select_related("user__pseudopatientprofile__provider")
        )

    def delete_medhistory(
        self,
        medhistory__value: bool | None,
        medhistory: Union["MedHistory", "UUID", None],
        medhistorytype: Union["MedHistoryTypes"],
    ) -> None:
        if not hasattr(self, f"{medhistorytype.value.lower()}_errors"):
            self.check_for_medhistory_delete_errors(
                medhistory__value=medhistory__value,
                medhistory=medhistory,
                medhistorytype=medhistorytype,
            )

        if not self.errors:
            medhistory.delete()
            setattr(self, medhistorytype.value.lower(), None)

    def check_for_medhistory_delete_errors(
        self,
        medhistory__value: bool | None,
        medhistory: Union["MedHistory", None],
        medhistorytype: Union["MedHistoryTypes"],
    ):
        mhtype_attr = medhistorytype.value.lower()
        if medhistory__value:
            self.add_errors(
                api_args=[
                    (
                        f"{mhtype_attr}__value",
                        f"{mhtype_attr}__value must be False to delete {medhistory}.",
                    )
                ],
            )
            setattr(self, f"{mhtype_attr}_errors", True)
        else:
            setattr(self, f"{mhtype_attr}_errors", False)

    def process_medhistory_errors(
        self,
        medhistory__value: bool | None,
        medhistory: Union["MedHistory", "UUID", None],
        medhistorytype: "MedHistoryTypes",
    ) -> None:
        if self.is_uuid(medhistory):
            self.set_attrs_from_qs(medhistory=medhistory, medhistorytype=medhistorytype)
        if self.attempt_create(medhistory__value=medhistory__value, medhistory=medhistory):
            self.check_for_medhistory_create_errors(
                medhistory__value=medhistory__value,
                medhistory=medhistory,
                medhistorytype=medhistorytype,
            )
        elif self.attempt_delete(medhistory__value=medhistory__value, medhistory=medhistory):
            self.check_for_medhistory_delete_errors(
                medhistory__value=medhistory__value,
                medhistory=medhistory,
                medhistorytype=medhistorytype,
            )
        elif self.attempt_update(medhistory):
            self.check_for_medhistory_update_errors(
                medhistory__value=medhistory__value,
                medhistory=medhistory,
                medhistorytype=medhistorytype,
            )

    @staticmethod
    def attempt_create(
        medhistory__value: bool | None,
        medhistory: Union["MedHistory", "UUID", None],
    ) -> bool:
        return medhistory__value and not medhistory

    @staticmethod
    def attempt_delete(
        medhistory__value: bool | None,
        medhistory: Union["MedHistory", "UUID", None],
    ) -> bool:
        return not medhistory__value and medhistory

    def attempt_update(self, medhistory: Union["MedHistory", "UUID", None]) -> bool:
        return self.medhistory_needs_update(medhistory=medhistory)

    def check_for_medhistory_update_errors(
        self,
        medhistory__value: bool | None,
        medhistory: Union["MedHistory", None],
        medhistorytype: "MedHistoryTypes",
    ) -> None:
        if not medhistory:
            self.add_errors(
                api_args=[(f"{medhistorytype.value.lower()}", f"{medhistorytype.value.lower()} does not exist.")],
            )
        if not medhistory__value:
            self.add_errors(
                api_args=[
                    (f"{medhistorytype.value.lower()}__value", f"{medhistorytype.value.lower()}__value is required.")
                ],
            )
        if not medhistory or not medhistory__value:
            setattr(self, f"{medhistorytype.value.lower()}_errors", True)
        else:
            setattr(self, f"{medhistorytype.value.lower()}_errors", False)

    def process_medhistory(
        self,
        medhistory__value: bool | None,
        medhistory: Union[MedHistory, "UUID", None],
        medhistorytype: "MedHistoryTypes",
    ) -> None:
        if self.attempt_create(medhistory__value=medhistory__value, medhistory=medhistory):
            self.create_medhistory(
                medhistory__value=medhistory__value, medhistory=medhistory, medhistorytype=medhistorytype
            )
        elif self.attempt_delete(medhistory__value=medhistory__value, medhistory=medhistory):
            self.delete_medhistory(
                medhistory__value=medhistory__value, medhistory=medhistory, medhistorytype=medhistorytype
            )
        elif self.attempt_update(medhistory):
            self.update_medhistory(
                medhistory__value=medhistory__value, medhistory=medhistory, medhistorytype=medhistorytype
            )

    def medhistory_needs_update(
        self,
        medhistory: MedHistory,
    ) -> bool:
        return medhistory.user != self.patient or (
            hasattr(self, "mh_relations")
            and self.mh_relations
            and any(
                getattr(
                    medhistory,
                    relation.__class__.__name__.lower(),
                )
                != relation
                for relation in self.mh_relations
            )
        )

    def update_medhistory(
        self, medhistory__value: bool | None, medhistory: MedHistory, medhistorytype: Union["MedHistoryTypes"]
    ) -> None:
        if not hasattr(self, f"{medhistorytype.value.lower()}_errors"):
            self.check_for_medhistory_update_errors(
                medhistory__value=medhistory__value,
                medhistory=medhistory,
                medhistorytype=medhistorytype,
            )

        if not self.errors:
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

    def check_for_process_medhistory_errors(self) -> None:
        for mhtype in self.medhistorytypes:
            getattr(self, f"process_{mhtype.value.lower()}_errors")()


class AnginaAPIMixin(MedHistoryAPIMixin):
    angina: Union[Angina, "UUID", None]
    angina__value: bool | None

    def set_medhistorytypes(self) -> list[MedHistoryTypes]:
        super().set_medhistorytypes()
        self.medhistorytypes.append(MedHistoryTypes.ANGINA)

    def process_angina(self) -> None:
        self.process_medhistory(
            medhistory__value=self.angina__value,
            medhistory=self.angina,
            medhistorytype=MedHistoryTypes.ANGINA,
        )

    def process_angina_errors(self) -> None:
        self.process_medhistory_errors(
            medhistory__value=self.angina__value,
            medhistory=self.angina,
            medhistorytype=MedHistoryTypes.ANGINA,
        )


class AnticoagulationAPIMixin(MedHistoryAPIMixin):
    anticoagulation: Union[Anticoagulation, "UUID", None]
    anticoagulation__value: bool | None

    def set_medhistorytypes(self) -> list[MedHistoryTypes]:
        super().set_medhistorytypes()
        self.medhistorytypes.append(MedHistoryTypes.ANTICOAGULATION)

    def process_anticoagulation(self) -> None:
        self.process_medhistory(
            medhistory__value=self.anticoagulation__value,
            medhistory=self.anticoagulation,
            medhistorytype=MedHistoryTypes.ANTICOAGULATION,
        )

    def process_anticoagulation_errors(self) -> None:
        self.process_medhistory_errors(
            medhistory__value=self.anticoagulation__value,
            medhistory=self.anticoagulation,
            medhistorytype=MedHistoryTypes.ANTICOAGULATION,
        )


class BleedAPIMixin(MedHistoryAPIMixin):
    bleed: Union[Bleed, "UUID", None]
    bleed__value: bool | None

    def set_medhistorytypes(self) -> list[MedHistoryTypes]:
        super().set_medhistorytypes()
        self.medhistorytypes.append(MedHistoryTypes.BLEED)

    def process_bleed(self) -> None:
        self.process_medhistory(
            medhistory__value=self.bleed__value,
            medhistory=self.bleed,
            medhistorytype=MedHistoryTypes.BLEED,
        )

    def process_bleed_errors(self) -> None:
        self.process_medhistory_errors(
            medhistory__value=self.bleed__value,
            medhistory=self.bleed,
            medhistorytype=MedHistoryTypes.BLEED,
        )


class CadAPIMixin(MedHistoryAPIMixin):
    cad: Union[Cad, "UUID", None]
    cad__value: bool | None

    def set_medhistorytypes(self) -> list[MedHistoryTypes]:
        super().set_medhistorytypes()
        self.medhistorytypes.append(MedHistoryTypes.CAD)

    def process_cad(self) -> None:
        self.process_medhistory(
            medhistory__value=self.cad__value,
            medhistory=self.cad,
            medhistorytype=MedHistoryTypes.CAD,
        )

    def process_cad_errors(self) -> None:
        self.process_medhistory_errors(
            medhistory__value=self.cad__value,
            medhistory=self.cad,
            medhistorytype=MedHistoryTypes.CAD,
        )


class ChfAPIMixin(MedHistoryAPIMixin):
    chf: Union[Chf, "UUID", None]
    chf__value: bool | None

    def set_medhistorytypes(self) -> list[MedHistoryTypes]:
        super().set_medhistorytypes()
        self.medhistorytypes.append(MedHistoryTypes.CHF)

    def process_chf(self) -> None:
        self.process_medhistory(
            medhistory__value=self.chf__value,
            medhistory=self.chf,
            medhistorytype=MedHistoryTypes.CHF,
        )

    def process_chf_errors(self) -> None:
        self.process_medhistory_errors(
            medhistory__value=self.chf__value,
            medhistory=self.chf,
            medhistorytype=MedHistoryTypes.CHF,
        )


class CkdAPIMixin(MedHistoryAPIMixin, CkdDetailAPIMixin):
    ckd: Union[Ckd, "UUID", None]
    ckd__value: bool | None
    ckddetail: Union["CkdDetail", "UUID", None]
    ckddetail__medhistory: Union["Ckd", "UUID", None]
    ckddetail__dialysis: bool | None
    ckddetail__dialysis_type: Union["DialysisChoices", None]
    ckddetail__dialysis_duration: Union["DialysisDurations", None]
    ckddetail__stage: Union["Stages", None]
    dateofbirth: Union["DateOfBirth", "UUID", "date", None]
    baselinecreatinine: Union["BaselineCreatinine", "UUID", "Decimal", None]
    gender: Union["Gender", "UUID", "Genders", None]

    ckddetail_optional: bool = False

    def set_medhistorytypes(self) -> list[MedHistoryTypes]:
        super().set_medhistorytypes()
        self.medhistorytypes.append(MedHistoryTypes.CKD)

    def process_ckd(self) -> None:
        self.process_medhistory(
            medhistory__value=self.ckd__value,
            medhistory=self.ckd,
            medhistorytype=MedHistoryTypes.CKD,
        )
        self.process_ckddetail()

    def process_ckd_errors(self) -> None:
        self.process_medhistory_errors(
            medhistory__value=self.ckd__value,
            medhistory=self.ckd,
            medhistorytype=MedHistoryTypes.CKD,
        )


class ColchicineinteractionAPIMixin(MedHistoryAPIMixin):
    colchicineinteraction: Union[Colchicineinteraction, "UUID", None]
    colchicineinteraction__value: bool | None

    def set_medhistorytypes(self) -> list[MedHistoryTypes]:
        super().set_medhistorytypes()
        self.medhistorytypes.append(MedHistoryTypes.COLCHICINEINTERACTION)

    def process_colchicineinteraction(self) -> None:
        self.process_medhistory(
            medhistory__value=self.colchicineinteraction__value,
            medhistory=self.colchicineinteraction,
            medhistorytype=MedHistoryTypes.COLCHICINEINTERACTION,
        )

    def process_colchicineinteraction_errors(self) -> None:
        self.process_medhistory_errors(
            medhistory__value=self.colchicineinteraction__value,
            medhistory=self.colchicineinteraction,
            medhistorytype=MedHistoryTypes.COLCHICINEINTERACTION,
        )


class DiabetesAPIMixin(MedHistoryAPIMixin):
    diabetes: Union[Diabetes, "UUID", None]
    diabetes__value: bool | None

    def set_medhistorytypes(self) -> list[MedHistoryTypes]:
        super().set_medhistorytypes()
        self.medhistorytypes.append(MedHistoryTypes.DIABETES)

    def process_diabetes(self) -> None:
        self.process_medhistory(
            medhistory__value=self.diabetes__value,
            medhistory=self.diabetes,
            medhistorytype=MedHistoryTypes.DIABETES,
        )

    def process_diabetes_errors(self) -> None:
        self.process_medhistory_errors(
            medhistory__value=self.diabetes__value,
            medhistory=self.diabetes,
            medhistorytype=MedHistoryTypes.DIABETES,
        )


class ErosionsAPIMixin(MedHistoryAPIMixin):
    erosions: Union[Erosions, "UUID", None]
    erosions__value: bool | None

    def set_medhistorytypes(self) -> list[MedHistoryTypes]:
        super().set_medhistorytypes()
        self.medhistorytypes.append(MedHistoryTypes.EROSIONS)

    def process_erosions(self) -> None:
        self.process_medhistory(
            medhistory__value=self.erosions__value,
            medhistory=self.erosions,
            medhistorytype=MedHistoryTypes.EROSIONS,
        )

    def process_erosions_errors(self) -> None:
        self.process_medhistory_errors(
            medhistory__value=self.erosions__value,
            medhistory=self.erosions,
            medhistorytype=MedHistoryTypes.EROSIONS,
        )


class GastricbypassAPIMixin(MedHistoryAPIMixin):
    gastricbypass: Union[Gastricbypass, "UUID", None]
    gastricbypass__value: bool | None

    def set_medhistorytypes(self) -> list[MedHistoryTypes]:
        super().set_medhistorytypes()
        self.medhistorytypes.append(MedHistoryTypes.GASTRICBYPASS)

    def process_gastricbypass(self) -> None:
        self.process_medhistory(
            medhistory__value=self.gastricbypass__value,
            medhistory=self.gastricbypass,
            medhistorytype=MedHistoryTypes.GASTRICBYPASS,
        )

    def process_gastricbypass_errors(self) -> None:
        self.process_medhistory_errors(
            medhistory__value=self.gastricbypass__value,
            medhistory=self.gastricbypass,
            medhistorytype=MedHistoryTypes.GASTRICBYPASS,
        )


class GoutAPIMixin(MedHistoryAPIMixin):
    gout_data: "GoutData"

    @property
    def gout(self) -> Gout | None:
        if not hasattr(self, "object"):
            self.object = self.get_queryset().get() if self.gout__id else None
        if self.object:
            if isinstance(self.object, Gout):
                return self.object
            return self.object.gout
        return None

    def get_queryset(self) -> "QuerySet":
        qs = super().get_queryset()
        return qs.select_related("goutdetail")

    @property
    def gout__id(self) -> "UUID":
        return self.gout_data.get("id")

    @property
    def gout__value(self) -> bool | None:
        return self.gout_data.get("value")

    def set_medhistorytypes(self) -> list[MedHistoryTypes]:
        super().set_medhistorytypes()
        self.medhistorytypes.append(MedHistoryTypes.GOUT)

    def process_gout(self) -> None:
        self.process_medhistory(
            medhistory__value=self.gout__value,
            medhistory=self.gout,
            medhistorytype=MedHistoryTypes.GOUT,
        )

    def process_gout_errors(self) -> None:
        self.process_medhistory_errors(
            medhistory__value=self.gout__value,
            medhistory=self.gout,
            medhistorytype=MedHistoryTypes.GOUT,
        )


class HeartattackAPIMixin(MedHistoryAPIMixin):
    heartattack: Union[Heartattack, "UUID", None]
    heartattack__value: bool | None

    def set_medhistorytypes(self) -> list[MedHistoryTypes]:
        super().set_medhistorytypes()
        self.medhistorytypes.append(MedHistoryTypes.HEARTATTACK)

    def process_heartattack(self) -> None:
        self.process_medhistory(
            medhistory__value=self.heartattack__value,
            medhistory=self.heartattack,
            medhistorytype=MedHistoryTypes.HEARTATTACK,
        )

    def process_heartattack_errors(self) -> None:
        self.process_medhistory_errors(
            medhistory__value=self.heartattack__value,
            medhistory=self.heartattack,
            medhistorytype=MedHistoryTypes.HEARTATTACK,
        )


class HepatitisAPIMixin(MedHistoryAPIMixin):
    hepatitis: Union[Hepatitis, "UUID", None]
    hepatitis__value: bool | None

    def set_medhistorytypes(self) -> list[MedHistoryTypes]:
        super().set_medhistorytypes()
        self.medhistorytypes.append(MedHistoryTypes.HEPATITIS)

    def process_hepatitis(self) -> None:
        self.process_medhistory(
            medhistory__value=self.hepatitis__value,
            medhistory=self.hepatitis,
            medhistorytype=MedHistoryTypes.HEPATITIS,
        )

    def process_hepatitis_errors(self) -> None:
        self.process_medhistory_errors(
            medhistory__value=self.hepatitis__value,
            medhistory=self.hepatitis,
            medhistorytype=MedHistoryTypes.HEPATITIS,
        )


class HypertensionAPIMixin(MedHistoryAPIMixin):
    hypertension: Union[Hypertension, "UUID", None]
    hypertension__value: bool | None

    def set_medhistorytypes(self) -> list[MedHistoryTypes]:
        super().set_medhistorytypes()
        self.medhistorytypes.append(MedHistoryTypes.HYPERTENSION)

    def process_hypertension(self) -> None:
        self.process_medhistory(
            medhistory__value=self.hypertension__value,
            medhistory=self.hypertension,
            medhistorytype=MedHistoryTypes.HYPERTENSION,
        )

    def process_hypertension_errors(self) -> None:
        self.process_medhistory_errors(
            medhistory__value=self.hypertension__value,
            medhistory=self.hypertension,
            medhistorytype=MedHistoryTypes.HYPERTENSION,
        )


class HyperuricemiaAPIMixin(MedHistoryAPIMixin):
    hyperuricemia: Union[Hyperuricemia, "UUID", None]
    hyperuricemia__value: bool | None

    def set_medhistorytypes(self) -> list[MedHistoryTypes]:
        super().set_medhistorytypes()
        self.medhistorytypes.append(MedHistoryTypes.HYPERURICEMIA)

    def process_hyperuricemia(self) -> None:
        self.process_medhistory(
            medhistory__value=self.hyperuricemia__value,
            medhistory=self.hyperuricemia,
            medhistorytype=MedHistoryTypes.HYPERURICEMIA,
        )

    def process_hyperuricemia_errors(self) -> None:
        self.process_medhistory_errors(
            medhistory__value=self.hyperuricemia__value,
            medhistory=self.hyperuricemia,
            medhistorytype=MedHistoryTypes.HYPERURICEMIA,
        )


class IbdAPIMixin(MedHistoryAPIMixin):
    ibd: Union[Ibd, "UUID", None]
    ibd__value: bool | None

    def set_medhistorytypes(self) -> list[MedHistoryTypes]:
        super().set_medhistorytypes()
        self.medhistorytypes.append(MedHistoryTypes.IBD)

    def process_ibd(self) -> None:
        self.process_medhistory(
            medhistory__value=self.ibd__value,
            medhistory=self.ibd,
            medhistorytype=MedHistoryTypes.IBD,
        )

    def process_ibd_errors(self) -> None:
        self.process_medhistory_errors(
            medhistory__value=self.ibd__value,
            medhistory=self.ibd,
            medhistorytype=MedHistoryTypes.IBD,
        )


class MenopauseAPIMixin(MedHistoryAPIMixin):
    menopause: Union[Menopause, "UUID", None]
    menopause__value: bool | None

    def set_medhistorytypes(self) -> list[MedHistoryTypes]:
        super().set_medhistorytypes()
        self.medhistorytypes.append(MedHistoryTypes.MENOPAUSE)

    def process_menopause(self) -> None:
        self.process_medhistory(
            medhistory__value=self.menopause__value,
            medhistory=self.menopause,
            medhistorytype=MedHistoryTypes.MENOPAUSE,
        )

    def process_menopause_errors(self) -> None:
        self.process_medhistory_errors(
            medhistory__value=self.menopause__value,
            medhistory=self.menopause,
            medhistorytype=MedHistoryTypes.MENOPAUSE,
        )


class OrgantransplantAPIMixin(MedHistoryAPIMixin):
    organtransplant: Union[Organtransplant, "UUID", None]
    organtransplant__value: bool | None

    def set_medhistorytypes(self) -> list[MedHistoryTypes]:
        super().set_medhistorytypes()
        self.medhistorytypes.append(MedHistoryTypes.ORGANTRANSPLANT)

    def process_organtransplant(self) -> None:
        self.process_medhistory(
            medhistory__value=self.organtransplant__value,
            medhistory=self.organtransplant,
            medhistorytype=MedHistoryTypes.ORGANTRANSPLANT,
        )

    def process_organtransplant_errors(self) -> None:
        self.process_medhistory_errors(
            medhistory__value=self.organtransplant__value,
            medhistory=self.organtransplant,
            medhistorytype=MedHistoryTypes.ORGANTRANSPLANT,
        )


class OsteoporosisAPIMixin(MedHistoryAPIMixin):
    osteoporosis: Union[Osteoporosis, "UUID", None]
    osteoporosis__value: bool | None

    def set_medhistorytypes(self) -> list[MedHistoryTypes]:
        super().set_medhistorytypes()
        self.medhistorytypes.append(MedHistoryTypes.OSTEOPOROSIS)

    def process_osteoporosis(self) -> None:
        self.process_medhistory(
            medhistory__value=self.osteoporosis__value,
            medhistory=self.osteoporosis,
            medhistorytype=MedHistoryTypes.OSTEOPOROSIS,
        )

    def process_osteoporosis_errors(self) -> None:
        self.process_medhistory_errors(
            medhistory__value=self.osteoporosis__value,
            medhistory=self.osteoporosis,
            medhistorytype=MedHistoryTypes.OSTEOPOROSIS,
        )


class PudAPIMixin(MedHistoryAPIMixin):
    pud: Union[Pud, "UUID", None]
    pud__value: bool | None

    def set_medhistorytypes(self) -> list[MedHistoryTypes]:
        super().set_medhistorytypes()
        self.medhistorytypes.append(MedHistoryTypes.PUD)

    def process_pud(self) -> None:
        self.process_medhistory(
            medhistory__value=self.pud__value,
            medhistory=self.pud,
            medhistorytype=MedHistoryTypes.PUD,
        )

    def process_pud_errors(self) -> None:
        self.process_medhistory_errors(
            medhistory__value=self.pud__value,
            medhistory=self.pud,
            medhistorytype=MedHistoryTypes.PUD,
        )


class PvdAPIMixin(MedHistoryAPIMixin):
    pvd: Union[Pvd, "UUID", None]
    pvd__value: bool | None

    def set_medhistorytypes(self) -> list[MedHistoryTypes]:
        super().set_medhistorytypes()
        self.medhistorytypes.append(MedHistoryTypes.PVD)

    def process_pvd(self) -> None:
        self.process_medhistory(
            medhistory__value=self.pvd__value,
            medhistory=self.pvd,
            medhistorytype=MedHistoryTypes.PVD,
        )

    def process_pvd_errors(self) -> None:
        self.process_medhistory_errors(
            medhistory__value=self.pvd__value,
            medhistory=self.pvd,
            medhistorytype=MedHistoryTypes.PVD,
        )


class StrokeAPIMixin(MedHistoryAPIMixin):
    stroke: Union[Stroke, "UUID", None]
    stroke__value: bool | None

    def set_medhistorytypes(self) -> list[MedHistoryTypes]:
        super().set_medhistorytypes()
        self.medhistorytypes.append(MedHistoryTypes.STROKE)

    def process_stroke(self) -> None:
        self.process_medhistory(
            medhistory__value=self.stroke__value,
            medhistory=self.stroke,
            medhistorytype=MedHistoryTypes.STROKE,
        )

    def process_stroke_errors(self) -> None:
        self.process_medhistory_errors(
            medhistory__value=self.stroke__value,
            medhistory=self.stroke,
            medhistorytype=MedHistoryTypes.STROKE,
        )


class TophiAPIMixin(MedHistoryAPIMixin):
    tophi: Union[Tophi, "UUID", None]
    tophi__value: bool | None

    def set_medhistorytypes(self) -> list[MedHistoryTypes]:
        super().set_medhistorytypes()
        self.medhistorytypes.append(MedHistoryTypes.TOPHI)

    def process_tophi(self) -> None:
        self.process_medhistory(
            medhistory__value=self.tophi__value,
            medhistory=self.tophi,
            medhistorytype=MedHistoryTypes.TOPHI,
        )

    def process_tophi_errors(self) -> None:
        self.process_medhistory_errors(
            medhistory__value=self.tophi__value,
            medhistory=self.tophi,
            medhistorytype=MedHistoryTypes.TOPHI,
        )


class UratestonesAPIMixin(MedHistoryAPIMixin):
    uratestones: Union[Uratestones, "UUID", None]
    uratestones__value: bool | None

    def set_medhistorytypes(self) -> list[MedHistoryTypes]:
        super().set_medhistorytypes()
        self.medhistorytypes.append(MedHistoryTypes.URATESTONES)

    def process_uratestones(self) -> None:
        self.process_medhistory(
            medhistory__value=self.uratestones__value,
            medhistory=self.uratestones,
            medhistorytype=MedHistoryTypes.URATESTONES,
        )

    def process_uratestones_errors(self) -> None:
        self.process_medhistory_errors(
            medhistory__value=self.uratestones__value,
            medhistory=self.uratestones,
            medhistorytype=MedHistoryTypes.URATESTONES,
        )


class XoiinteractionAPIMixin(MedHistoryAPIMixin):
    xoiinteraction: Union[Xoiinteraction, "UUID", None]
    xoiinteraction__value: bool | None

    def set_medhistorytypes(self) -> list[MedHistoryTypes]:
        super().set_medhistorytypes()
        self.medhistorytypes.append(MedHistoryTypes.XOIINTERACTION)

    def process_xoiinteraction(self) -> None:
        self.process_medhistory(
            medhistory__value=self.xoiinteraction__value,
            medhistory=self.xoiinteraction,
            medhistorytype=MedHistoryTypes.XOIINTERACTION,
        )

    def process_xoiinteraction_errors(self) -> None:
        self.process_medhistory_errors(
            medhistory__value=self.xoiinteraction__value,
            medhistory=self.xoiinteraction,
            medhistorytype=MedHistoryTypes.XOIINTERACTION,
        )
