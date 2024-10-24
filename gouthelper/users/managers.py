from typing import TYPE_CHECKING, Union

from django.contrib.auth.base_user import BaseUserManager  # pylint:disable=E0401, E0013, E0015 # type: ignore

from ..flareaids.selectors import flareaid_user_relations
from ..flares.selectors import flare_user_relations
from ..goalurates.selectors import goalurate_user_relations
from ..labs.selectors import dated_urates_relation
from ..ppxaids.selectors import ppxaid_user_relations
from ..ppxs.selectors import ppx_user_relations
from ..ultaids.selectors import ultaid_user_relations
from ..ults.selectors import ult_user_relations
from .choices import Roles
from .selectors import pseudopatient_related_aids, pseudopatient_relations

if TYPE_CHECKING:
    from uuid import UUID


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
