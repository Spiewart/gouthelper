from typing import TYPE_CHECKING, Union

from django.contrib.auth.base_user import BaseUserManager

from ..dateofbirths.helpers import age_calc
from ..dateofbirths.models import DateOfBirth
from ..ethnicitys.models import Ethnicity
from ..flareaids.selectors import flareaid_user_relations
from ..flares.selectors import flare_user_relations
from ..genders.models import Gender
from ..goalurates.selectors import goalurate_user_relations
from ..labs.selectors import dated_urates_relation
from ..medhistorydetails.models import GoutDetail
from ..medhistorys.models import Gout
from ..ppxaids.selectors import ppxaid_user_relations
from ..ppxs.selectors import ppx_user_relations
from ..profiles.helpers import get_provider_alias
from ..profiles.models import PseudopatientProfile
from ..ultaids.selectors import ultaid_user_relations
from ..ults.selectors import ult_user_relations
from .choices import Roles
from .selectors import pseudopatient_base_relations, pseudopatient_related_aids, pseudopatient_relations

if TYPE_CHECKING:
    from datetime import date
    from uuid import UUID

    from django.contrib.auth import get_user_model
    from django.db.models import QuerySet  # type: ignore

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
        **kwargs,
    ) -> "User":
        kwargs.update({"role": Roles.PSEUDOPATIENT})
        pseudopatient = self.create(**kwargs)
        DateOfBirth.objects.create(user=pseudopatient, value=dateofbirth)
        Gender.objects.create(user=pseudopatient, value=gender)
        Ethnicity.objects.create(user=pseudopatient, value=ethnicity)
        provider_alias = get_provider_alias(
            provider,
            age_calc(dateofbirth),
            gender,
        )
        print(provider_alias)
        PseudopatientProfile.objects.create(
            user=pseudopatient,
            provider=provider,
            provider_alias=get_provider_alias(
                provider,
                age_calc(dateofbirth),
                gender,
            )
            if provider
            else None,
        )
        GoutDetail.objects.create(
            medhistory=Gout.objects.create(user=pseudopatient),
            at_goal=at_goal,
            at_goal_long_term=at_goal_long_term,
            flaring=flaring,
            on_ppx=on_ppx,
            on_ult=on_ult,
            starting_ult=starting_ult,
        )
        return pseudopatient

    def api_update(
        self,
        dateofbirth: "date",
        ethnicity: "Ethnicitys",
        gender: "Genders",
        at_goal: bool | None,
        at_goal_long_term: bool,
        flaring: bool | None,
        on_ppx: bool,
        on_ult: bool,
        starting_ult: bool,
        **kwargs,
    ) -> "User":
        pseudopatient = self.get(**kwargs)
        if pseudopatient.dateofbirth.value_needs_update(dateofbirth):
            pseudopatient.dateofbirth.update_value(dateofbirth)
        if pseudopatient.ethnicity.value_needs_update(ethnicity):
            pseudopatient.ethnicity.update_value(ethnicity)
        if pseudopatient.gender.value_needs_update(gender):
            pseudopatient.gender.update_value(gender)
        if pseudopatient.goutdetail.editable_fields_need_update(
            at_goal=at_goal,
            at_goal_long_term=at_goal_long_term,
            flaring=flaring,
            on_ppx=on_ppx,
            on_ult=on_ult,
            starting_ult=starting_ult,
        ):
            pseudopatient.goutdetail.update_editable_fields(
                at_goal=at_goal,
                at_goal_long_term=at_goal_long_term,
                flaring=flaring,
                on_ppx=on_ppx,
                on_ult=on_ult,
                starting_ult=starting_ult,
                commit=True,
            )
        return pseudopatient
