import factory  # type: ignore
import pytest  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore

from ...labs.choices import LabTypes
from ..models import Ppx

pytestmark = pytest.mark.django_db


class PpxFactory(DjangoModelFactory):
    class Meta:
        model = Ppx

    # Need to create Gout MedHistory and GoutDetail object when calling the constructor
    # for PpxFactory

    @factory.post_generation
    def labs(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            # A list of labs (Urates) were passed in, use them
            for lab in extracted:
                if lab.labtype == LabTypes.URATE:
                    self.labs.add(lab)
                else:
                    raise TypeError(f"LabType {lab.lab_type} is not a valid lab for a Ppx.")

    @factory.post_generation
    def medhistorys(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            # A list of medhistorys were passed in, use them
            for medhistory in extracted:
                self.medhistorys.add(medhistory)

    @factory.post_generation
    def goutdetail(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            # A GoutDetail was passed in, use it
            self.goutdetail = extracted
