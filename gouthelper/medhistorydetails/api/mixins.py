from typing import TYPE_CHECKING, Union

from ...utils.services import APIMixin
from ..models import GoutDetail

if TYPE_CHECKING:
    from uuid import UUID

    from ...medhistorys.models import Gout
    from ...users.models import Pseudopatient


class GoutDetailAPIMixin(APIMixin):
    goutdetail: Union[GoutDetail, "UUID", None]
    goutdetail__at_goal: bool | None
    goutdetail__at_goal_long_term: bool | None
    goutdetail__flaring: bool | None
    goutdetail__on_ppx: bool | None
    goutdetail__on_ult: bool | None
    goutdetail__starting_ult: bool
    gout: Union["Gout", "UUID", None]
    patient: Union["Pseudopatient", None]

    def get_queryset(self) -> "GoutDetail":
        if not self.is_uuid(self.goutdetail):
            raise TypeError("goutdetail arg must be a UUID to call get_queryset()")
        return GoutDetail.objects.filter(pk=self.goutdetail).select_related("medhistory__user")

    def set_attrs_from_qs(self) -> None:
        self.goutdetail = self.get_queryset().get()
        self.gout = self.goutdetail.medhistory if not self.gout else self.gout
        self.patient = self.goutdetail.medhistory.user if not self.patient else self.patient

    def create_goutdetail(self) -> "GoutDetail":
        self.check_for_goutdetail_create_errors()
        self.check_for_and_raise_errors(model_name="GoutDetail")
        self.goutdetail = GoutDetail.objects.create(
            medhistory=self.gout,
            at_goal=self.goutdetail__at_goal,
            at_goal_long_term=self.goutdetail__at_goal_long_term,
            flaring=self.goutdetail__flaring,
            on_ppx=self.goutdetail__on_ppx,
            on_ult=self.goutdetail__on_ult,
            starting_ult=self.goutdetail__starting_ult,
        )
        return self.goutdetail

    def check_for_goutdetail_create_errors(self):
        if not self.gout:
            self.add_errors(
                api_args=[("gout", "Gout is required to create a GoutDetail.")],
            )

        if self.goutdetail:
            self.add_errors(
                api_args=[("goutdetail", f"{self.goutdetail} already exists.")],
            )

        if self.goutdetail__at_goal_long_term is None:
            self.add_errors(
                api_args=[
                    ("goutdetail__at_goal_long_term", "at_goal_long_term is required to create a GoutDetail instance.")
                ],
            )

        if self.at_goal_long_term_but_not_at_goal:
            self.add_errors(
                api_args=[("goutdetail__at_goal_long_term", "at_goal_long_term cannot be True if at_goal is False.")],
            )

        if self.goutdetail__on_ppx is None:
            self.add_errors(
                api_args=[("goutdetail__on_ppx", "on_ppx is required to create a GoutDetail instance.")],
            )

        if self.goutdetail__on_ult is None:
            self.add_errors(
                api_args=[("goutdetail__on_ult", "on_ult is required to create a GoutDetail instance.")],
            )

        if self.goutdetail__starting_ult is None:
            self.add_errors(
                api_args=[("goutdetail__starting_ult", "starting_ult is required to create a GoutDetail instance.")],
            )

        if self.gout_with_patient_without_patient_arg:
            self.add_errors([("patient", f"{self.gout} has a user but no patient arg.")])

        if self.patient and self.patient_has_goutdetail:
            self.add_errors(
                api_args=[("patient", f"{self.patient} already has a GoutDetail ({self.patient.goutdetail}).")],
            )

    @property
    def at_goal_long_term_but_not_at_goal(self) -> bool:
        return self.goutdetail__at_goal_long_term and not self.goutdetail__at_goal

    @property
    def patient_has_goutdetail(self) -> bool:
        return self.patient.goutdetail

    @property
    def gout_with_patient_without_patient_arg(self) -> bool:
        return self.gout and self.gout.user and not self.patient

    def update_goutdetail(self) -> GoutDetail:
        if self.is_uuid(self.goutdetail):
            self.set_attrs_from_qs()
        self.check_for_goutdetail_update_errors()
        self.check_for_and_raise_errors(model_name="GoutDetail")
        if self.goutdetail_needs_save:
            self.update_goutdetail_instance()
        return self.goutdetail

    def check_for_goutdetail_update_errors(self):
        if not self.goutdetail:
            self.add_errors(
                api_args=[("goutdetail", "GoutDetail is required to update a GoutDetail instance.")],
            )

        if self.goutdetail_has_medhistory_that_is_not_gout:
            self.add_errors(
                api_args=[("goutdetail", f"{self.goutdetail} has a medhistory that is not a {self.gout}.")],
            )

        if self.goutdetail__at_goal_long_term is None:
            self.add_errors(
                api_args=[
                    ("goutdetail__at_goal_long_term", "at_goal_long_term is required to update a GoutDetail instance.")
                ],
            )

        if self.at_goal_long_term_but_not_at_goal:
            self.add_errors(
                api_args=[("goutdetail__at_goal_long_term", "at_goal_long_term cannot be True if at_goal is False.")],
            )

        if self.goutdetail__on_ppx is None:
            self.add_errors(
                api_args=[("goutdetail__on_ppx", "on_ppx is required to update a GoutDetail instance.")],
            )

        if self.goutdetail__on_ult is None:
            self.add_errors(
                api_args=[("goutdetail__on_ult", "on_ult is required to update a GoutDetail instance.")],
            )

        if self.goutdetail__starting_ult is None:
            self.add_errors(
                api_args=[("goutdetail__starting_ult", "starting_ult is required to update a GoutDetail instance.")],
            )

        if self.goutdetail and self.goutdetail_has_user_who_is_not_patient:
            self.add_errors(
                api_args=[
                    ("goutdetail", f"{self.goutdetail} has a user who is not {self.patient}."),
                ],
            )

    @property
    def goutdetail_has_medhistory_that_is_not_gout(self) -> bool:
        return self.goutdetail and self.goutdetail.medhistory and self.gout and self.goutdetail.medhistory != self.gout

    @property
    def goutdetail_has_user_who_is_not_patient(self) -> bool:
        return self.goutdetail.medhistory.user and self.goutdetail.medhistory.user != self.patient

    @property
    def goutdetail_needs_save(self) -> bool:
        return self.goutdetail.editable_fields_need_update(
            at_goal=self.goutdetail__at_goal,
            at_goal_long_term=self.goutdetail__at_goal_long_term,
            flaring=self.goutdetail__flaring,
            on_ppx=self.goutdetail__on_ppx,
            on_ult=self.goutdetail__on_ult,
            starting_ult=self.goutdetail__starting_ult,
        )

    def update_goutdetail_instance(self) -> None:
        self.goutdetail.update_editable_fields(
            at_goal=self.goutdetail__at_goal,
            at_goal_long_term=self.goutdetail__at_goal_long_term,
            flaring=self.goutdetail__flaring,
            on_ppx=self.goutdetail__on_ppx,
            on_ult=self.goutdetail__on_ult,
            starting_ult=self.goutdetail__starting_ult,
            commit=True,
        )
