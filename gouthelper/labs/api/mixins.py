from typing import TYPE_CHECKING, Union

from ...labs.models import BaselineCreatinine, Creatinine, Urate
from ...utils.services import APIMixin
from ..helpers import labs_sort_list_by_date_drawn
from ..schema import BaselineCreatinineSchema

if TYPE_CHECKING:
    from datetime import date
    from decimal import Decimal
    from uuid import UUID

    from django.db.models import QuerySet

    from ...medhistorys.models import Ckd
    from ...users.models import Pseudopatient
    from ...utils.types import CreatinineData


class BaselineCreatinineAPIMixin(APIMixin):
    baselinecreatinine: BaselineCreatinineSchema
    baselinecreatinine__value: Union["Decimal", None]
    baselinecreatinine__medhistory: Union["Ckd", "UUID", None]

    def set_attrs(self) -> None:
        self.baselinecreatinine__value = self.baselinecreatinine.get("value", None)

    def process_baselinecreatinine(self) -> None:
        if self.baselinecreatinine:
            if self.is_uuid(self.baselinecreatinine):
                self.baselinecreatinine = self.get_queryset().get()
            if self.baselinecreatinine_should_be_deleted:
                self.delete_baselinecreatinine()
            elif self.baselinecreatinine_needs_update:
                self.update_baselinecreatinine()
        elif self.baselinecreatinine_should_be_created:
            self.create_baselinecreatinine()

    def get_queryset(self) -> "QuerySet":
        if not self.is_uuid(self.baselinecreatinine):
            raise TypeError("baselinecreatinine arg must be a UUID to call get_queryset().")
        return BaselineCreatinine.related_objects.filter(id=self.baselinecreatinine)

    @property
    def baselinecreatinine_should_be_deleted(self) -> bool:
        self.check_for_baselinecreatinine_delete_errors()
        return not self.baselinecreatinine__value

    def check_for_baselinecreatinine_delete_errors(self) -> None:
        if not self.baselinecreatinine:
            self.add_gouthelper_validation_error(
                self.errors,
                [
                    (
                        "baselinecreatinine",
                        "BaselineCreatinine instance required for deletion.",
                    )
                ],
            )

    def delete_baselinecreatinine(self) -> None:
        if not self.has_errors:
            print(self.errors)
            self.baselinecreatinine.delete()
            self.baselinecreatinine = None

    @property
    def baselinecreatinine_needs_update(self) -> bool:
        self.check_for_baselinecreatinine_update_errors()
        return (
            (
                self.baselinecreatinine__value
                and self.baselinecreatinine.value != self.baselinecreatinine__value
                or self.baselinecreatinine__medhistory
                and self.baselinecreatinine.medhistory != self.baselinecreatinine__medhistory
            )
            if self.baselinecreatinine
            else False
        )

    def check_for_baselinecreatinine_update_errors(self) -> None:
        if not self.baselinecreatinine:
            self.add_gouthelper_validation_error(
                self.errors,
                [
                    (
                        "baselinecreatinine",
                        "BaselineCreatinine required for update.",
                    )
                ],
            )
        if not self.baselinecreatinine__value:
            self.add_gouthelper_validation_error(
                self.errors,
                [
                    (
                        "baselinecreatinine__value",
                        "baselinecreatinine__value is required for update.",
                    )
                ],
            )

    def update_baselinecreatinine(self) -> BaselineCreatinine:
        if not self.has_errors:
            self.baselinecreatinine.update(
                value=self.baselinecreatinine__value,
                medhistory=self.baselinecreatinine__medhistory,
            )
            return self.baselinecreatinine

    @property
    def baselinecreatinine_should_be_created(self) -> bool:
        self.check_for_baselinecreatinine_create_errors()
        return self.baselinecreatinine__value and not self.baselinecreatinine

    def check_for_baselinecreatinine_create_errors(self):
        if self.baselinecreatinine:
            self.add_gouthelper_validation_error(
                self.errors,
                [
                    (
                        "baselinecreatinine",
                        "BaselineCreatinine instance already exists.",
                    )
                ],
            )
        if not self.baselinecreatinine__value:
            self.add_gouthelper_validation_error(
                self.errors,
                [
                    (
                        "baselinecreatinine__value",
                        "baselinecreatinine__value is required for creation.",
                    )
                ],
            )
        if not self.baselinecreatinine__medhistory:
            self.add_gouthelper_validation_error(
                self.errors,
                [
                    (
                        "baselinecreatinine__medhistory",
                        "baselinecreatinine__medhistory is required for creation.",
                    )
                ],
            )

    def create_baselinecreatinine(self) -> BaselineCreatinine:
        if not self.has_errors:
            self.baselinecreatinine = BaselineCreatinine.objects.create(
                value=self.baselinecreatinine__value,
                medhistory=self.baselinecreatinine__medhistory,
            )
            return self.baselinecreatinine


class CreatininesAPIMixin(APIMixin):
    creatinines: list["Creatinine", "UUID"] | None
    creatinines_data: list["CreatinineData", None]
    patient: Union["Pseudopatient", "UUID", None]

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
    urate: Union["Urate", "UUID"]
    urate__value: Union["Decimal"]
    urate__date_drawn: Union["date", None]
    patient: Union["Pseudopatient", "UUID", None]

    def create_urate(self) -> Urate:
        self.check_for_urate_create_errors()
        if not self.errors:
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

    @property
    def urate_should_be_created(self) -> bool:
        return self.urate__value

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
        if not self.errors:
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

    def process_urate(self):
        if self.urate:
            if self.urate_should_be_deleted:
                self.delete_urate()
            elif self.urate_needs_update:
                self.update_urate()
        elif self.urate_should_be_created:
            self.create_urate()

    def delete_urate(self) -> None:
        if self.is_uuid(self.urate):
            self.set_attrs_from_qs()
        if not self.errors:
            self.urate.delete()
            self.urate = None

    @property
    def urate_needs_update(self) -> bool:
        return (
            self.urate__value
            and self.urate__value != self.urate.value
            or self.urate__date_drawn
            and self.urate__date_drawn != self.urate.date_drawn
            or self.patient
            and self.urate.user != self.patient
        )
