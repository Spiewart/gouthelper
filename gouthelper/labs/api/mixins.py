from typing import TYPE_CHECKING, Union

from ...labs.models import Creatinine, Urate
from ...utils.services import APIMixin
from ..helpers import labs_sort_list_by_date_drawn

if TYPE_CHECKING:
    from datetime import date
    from decimal import Decimal
    from uuid import UUID

    from ...users.models import Pseudopatient
    from ...utils.types import CreatinineData


class CreatininesAPIMixin(APIMixin):
    creatinines_data: list["CreatinineData", None]
    patient: Union["Pseudopatient", "UUID", None]


class CreatininesAPICreateMixin(CreatininesAPIMixin):
    def create_creatinines(self) -> list[Creatinine]:
        creatinines = []
        for creatinine_data in self.creatinines_data:
            if creatinine_data.get("id", None):
                raise ValueError("Can't create a Creatinine with an ID.")
            creatinines.append(
                Creatinine.objects.create(
                    user=self.patient,
                    **creatinine_data,
                )
            )
        labs_sort_list_by_date_drawn(creatinines)
        return creatinines


class CreatininesAPIUpdateMixin(CreatininesAPIMixin):
    """API for updating Creatinines. Creatinines without data are deleted."""

    creatinines: list["Creatinine", "UUID", None]

    def update_creatinines(self) -> None:
        creatinines = []
        for creatinine_data in self.creatinines_data:
            creatinine = self.get_creatinine(creatinine_data)
            if creatinine:
                if self.is_uuid(creatinine):
                    Creatinine.objects.filter(id=creatinine).update(
                        creatinine_data.get("value"),
                        creatinine_data.get("date_drawn"),
                        creatinine_data.get("aki", None),
                        creatinine_data.get("user", None),
                    )
                else:
                    creatinine.update(
                        creatinine_data.get("value"),
                        creatinine_data.get("date_drawn"),
                        creatinine_data.get("aki", None),
                        creatinine_data.get("user", None),
                    )
            else:
                creatinine = Creatinine.objects.create(
                    user=self.patient,
                    **creatinine_data,
                )
            creatinines.append(creatinine)

        for creatinine in self.creatinines:
            if creatinine not in creatinines:
                if self.is_uuid(creatinine):
                    creatinine = Creatinine.objects.get(id=creatinine).delete()
                else:
                    creatinine.delete()

        labs_sort_list_by_date_drawn(creatinines)
        self.creatinines = creatinines

    def get_creatinine(self, creatinine_data: "CreatinineData") -> Creatinine | None:
        return (
            next(
                iter(
                    creatinine
                    for creatinine in self.creatinines
                    if (
                        self.is_uuid(creatinine)
                        and creatinine == creatinine_data["id"]
                        or creatinine.id == creatinine_data["id"]
                    )
                ),
                None,
            )
            if "id" in creatinine_data
            else None
        )


class UrateAPIMixin(APIMixin):
    urate__value: Union["Decimal"]
    urate__date_drawn: Union["date"]
    patient: Union["Pseudopatient", "UUID", None]


class UrateAPICreateMixin(UrateAPIMixin):
    def create_urate(self) -> Urate:
        self.check_for_urate_create_errors()
        self.check_for_and_raise_errors(model_name="Urate")
        self.urate = Urate.objects.create(
            user=self.patient,
            value=self.urate__value,
            date_drawn=self.urate__date_drawn,
        )
        return self.urate

    def check_for_urate_create_errors(self):
        if not self.urate__value or not self.urate__date_drawn:
            if not self.urate__value:
                self.add_gouthelper_validation_error(
                    self.errors,
                    [
                        (
                            "urate__value",
                            "urate__value is required.",
                        )
                    ],
                )
            if not self.urate__date_drawn:
                self.add_gouthelper_validation_error(
                    self.errors,
                    [
                        (
                            "urate__date_drawn",
                            "urate__date_drawn is required.",
                        )
                    ],
                )

    def urate_should_be_created(self) -> bool:
        return self.urate__value


class UrateAPIUpdateMixin(UrateAPIMixin):
    urate__value: Union["Decimal", None]
    urate__date_drawn: Union["date", None]
    urate: Union["Urate", "UUID"]

    def get_queryset(self) -> Urate:
        if self.urate and self.is_uuid(self.urate):
            urate = Urate.related_objects.filter(id=self.urate).get()
            if urate.user and self.patient:
                if not self.urate_user_is_patient(urate=urate, patient=self.patient):
                    raise ValueError("Urate's user ({self.urate.user}) is not the patient {self.patient}.")
            return urate
        else:
            raise TypeError("urate arg must be a UUID to call get_queryset().")

    def urate_user_is_patient(
        self,
        urate: Urate,
        patient: Union["Pseudopatient", "UUID"],
    ):
        if self.is_uuid(patient):
            return urate.user.id == patient
        else:
            return urate.user is patient

    def set_attrs_from_qs(self) -> None:
        self.urate = self.get_queryset()
        self.patient = self.urate.user if not self.patient else self.patient

    def update_urate(self) -> Urate | None:
        if self.is_uuid(self.urate):
            self.set_attrs_from_qs()
        self.check_for_urate_update_errors()
        self.check_for_and_raise_errors(model_name="Urate")
        if self.urate_should_be_deleted:
            self.urate.delete()
            self.urate = None
            return None
        else:
            kwargs = {
                "value": self.urate__value,
                "date_drawn": self.urate__date_drawn,
            }
            if self.patient:
                if self.is_uuid(self.patient):
                    kwargs.update({"user__id": self.patient})
                else:
                    kwargs.update({"user": self.patient})
            else:
                kwargs.update({"user": None})
            self.urate.update(
                **kwargs,
            )
            return self.urate

    def check_for_urate_update_errors(self):
        if not self.urate:
            self.add_errors(api_args=[("urate", "Urate instance is required.")])

    @property
    def urate_should_be_deleted(self) -> bool:
        return self.urate and not self.urate__value
