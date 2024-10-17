from typing import TYPE_CHECKING, Union

from ...labs.models import Creatinine
from ...utils.services import APIMixin
from ..helpers import labs_sort_list_by_date_drawn

if TYPE_CHECKING:
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
    creatinines: list["Creatinine", "UUID", None]

    def update_creatinines(self) -> None:
        creatinines = []
        for creatinine_data in self.creatinines_data:
            creatinine = self.get_creatinine(creatinine_data)
            if creatinine:
                if self.is_uuid(creatinine):
                    Creatinine.objects.get(id=creatinine).update(
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
