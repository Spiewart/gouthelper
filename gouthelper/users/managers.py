from typing import TYPE_CHECKING, Union

from django.contrib.auth.base_user import BaseUserManager
from django.db.models import QuerySet

from ..flareaids.selectors import flareaid_user_relations
from ..flares.selectors import flare_user_relations
from ..goalurates.selectors import goalurate_user_relations
from ..labs.selectors import dated_urates_relation
from ..ppxaids.selectors import ppxaid_user_relations
from ..ppxs.selectors import ppx_user_relations
from ..ultaids.selectors import ultaid_user_relations
from ..ults.selectors import ult_user_relations
from .api.services import PseudopatientAPIMixin
from .choices import Roles
from .selectors import pseudopatient_base_relations, pseudopatient_related_aids, pseudopatient_relations

if TYPE_CHECKING:
    from datetime import date
    from uuid import UUID

    from django.contrib.auth import get_user_model

    from ..ethnicitys.choices import Ethnicitys
    from ..genders.choices import Genders

    User = get_user_model()


class AdminManager(BaseUserManager):
    def get_queryset(self, *args, **kwargs):
        results = super().get_queryset(*args, **kwargs)
        return results.filter(role=Roles.ADMIN)


class GoutHelperUserManager(BaseUserManager):
    """Custom User model manager for GoutHelper. It only overrides the create_superuser method."""

    def create_user(self, username, email, password=None):
        """Create and save a User with the given email and password."""
        user = self.model(
            username=username,
            email=email,
        )
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password. Set
        role to ADMIN."""
        user = self.model(
            email=email,
            is_staff=True,
            is_superuser=True,
            role=Roles.ADMIN,
            **extra_fields,
        )
        user.set_password(password)
        user.save()
        return user


class PatientManager(BaseUserManager):
    def get_queryset(self, *args, **kwargs):
        results = super().get_queryset(*args, **kwargs)
        return results.filter(role=Roles.PATIENT)

    def create(self, **kwargs):
        kwargs.update({"role": Roles.PATIENT})
        return super().create(**kwargs)


class ProviderManager(BaseUserManager):
    def get_queryset(self, *args, **kwargs):
        results = super().get_queryset(*args, **kwargs)
        return results.filter(role=Roles.PROVIDER)


class PseudopatientManager(BaseUserManager):
    def get_queryset(self, *args, **kwargs):
        results = super().get_queryset(*args, **kwargs)
        return results.filter(role=Roles.PSEUDOPATIENT)

    def all_related_objects(self):
        return pseudopatient_relations(self.get_queryset())

    def flareaid_qs(self, flare_id: Union["UUID", None] = None):
        return flareaid_user_relations(self.get_queryset(), flare_id=flare_id)

    def flares_qs(self, flare_pk: Union["UUID", None] = None):
        return flare_user_relations(self.get_queryset(), **{"flare_pk": flare_pk} if flare_pk else {})

    def flare_qs(self, flare_pk: "UUID"):
        return self.flares_qs(flare_pk=flare_pk)

    def goalurate_qs(self):
        return goalurate_user_relations(self.get_queryset())

    def ppxaid_qs(self):
        return ppxaid_user_relations(self.get_queryset())

    def ppx_qs(self):
        return ppx_user_relations(self.get_queryset())

    def profile_qs(self) -> "QuerySet":
        return pseudopatient_base_relations(self.get_queryset())

    def related_aids(self):
        return pseudopatient_related_aids(self.get_queryset())

    def ultaid_qs(self):
        return ultaid_user_relations(self.get_queryset())

    def ult_qs(self):
        return ult_user_relations(self.get_queryset())

    def urates_dated_qs(self):
        return dated_urates_relation(self.get_queryset())

    def create(self, **kwargs):
        kwargs.update({"role": Roles.PSEUDOPATIENT})
        return super().create(**kwargs)


class PseudopatientProfileManager(BaseUserManager):
    def get_queryset(self, *args, **kwargs):
        return pseudopatient_base_relations(super().get_queryset(*args, **kwargs))

    def api_create(
        self,
        dateofbirth: "date",
        gender: "Genders",
        ethnicity: "Ethnicitys",
        provider: Union["User", None],
        at_goal: bool | None,
        at_goal_long_term: bool,
        flaring: bool | None,
        on_ppx: bool,
        on_ult: bool,
        starting_ult: bool,
    ) -> "User":
        return PseudopatientAPIMixin(
            patient=None,
            dateofbirth__value=dateofbirth,
            ethnicity__value=ethnicity,
            gender__value=gender,
            provider=provider,
            goutdetail__at_goal=at_goal,
            goutdetail__at_goal_long_term=at_goal_long_term,
            goutdetail__flaring=flaring,
            goutdetail__on_ppx=on_ppx,
            goutdetail__on_ult=on_ult,
            goutdetail__starting_ult=starting_ult,
        ).create_pseudopatient_and_profile()

    def api_update(
        self,
        patient: "UUID",
        dateofbirth: "date",
        ethnicity: "Ethnicitys",
        gender: "Genders",
        at_goal: bool | None,
        at_goal_long_term: bool,
        flaring: bool | None,
        on_ppx: bool,
        on_ult: bool,
        starting_ult: bool,
    ) -> "User":
        patient = self.get_queryset().get(pk=patient)

        return PseudopatientAPIMixin(
            patient=patient,
            dateofbirth__value=dateofbirth,
            ethnicity__value=ethnicity,
            gender__value=gender,
            provider=patient.provider,
            goutdetail__at_goal=at_goal,
            goutdetail__at_goal_long_term=at_goal_long_term,
            goutdetail__flaring=flaring,
            goutdetail__on_ppx=on_ppx,
            goutdetail__on_ult=on_ult,
            goutdetail__starting_ult=starting_ult,
        ).update_pseudopatient_and_profile()
