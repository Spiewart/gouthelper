from decimal import Decimal
from typing import TYPE_CHECKING, Union

from factory import post_generation  # type: ignore
from factory.django import DjangoModelFactory  # type: ignore
from factory.fuzzy import FuzzyChoice

from ...labs.helpers import labs_sort_list_by_date_drawn
from ...labs.models import Creatinine
from ...labs.tests.factories import CreatinineFactory, create_creatinine_api_data
from ...utils.helpers import get_or_create_qs_attr
from ..choices import Statuses

if TYPE_CHECKING:
    from ...genders.choices import Genders
    from ...labs.types import CreatinineData
    from ...medhistorydetails.choices import Stages
    from ...users.models import Pseudopatient
    from ..models import Aki
    from ..types import AkiData


class AkiFactory(DjangoModelFactory):
    class Meta:
        model = "akis.Aki"

    status = FuzzyChoice(choices=Statuses.values)
    user = None

    @post_generation
    def creatinines(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for creatinine in extracted:
                if isinstance(creatinine, Decimal):
                    creatinine = CreatinineFactory(value=creatinine, aki=self)
                elif isinstance(creatinine, tuple) and isinstance(creatinine[0], Decimal):
                    creatinine = CreatinineFactory(value=creatinine[0], date_drawn=creatinine[1], aki=self)
                    creatinine.full_clean()
                    creatinine.save()
                elif isinstance(creatinine, Creatinine):
                    creatinine.aki = self
                    creatinine.full_clean()
                    creatinine.save()
                else:
                    raise ValueError("creatinine must be a Decimal or Creatinine object")
                get_or_create_qs_attr(self, "creatinines").append(creatinine)
            labs_sort_list_by_date_drawn(self.creatinines_qs)


def create_aki_api_data(
    aki: Union["Aki", None] = None,
    status: Union["Statuses", None] = None,
    creatinines: list["CreatinineData", "Creatinine"] | None = None,
    age: int | None = None,
    gender: Union["Genders", None] = None,
    baselinecreatinine: Decimal | None = None,
    stage: Union["Stages", None] = None,
    user: Union["Pseudopatient", None] = None,
) -> "AkiData":
    refined_creatinines = []
    if creatinines:
        for creatinine in creatinines:
            refined_creatinines.append(creatinine_convert_model_or_data_to_data(creatinine))
    elif aki:
        if hasattr(aki, "creatinines_qs"):
            for creatinine in aki.creatinines_qs:
                refined_creatinines.append(create_creatinine_api_data(creatinine))
        else:
            for creatinine in aki.creatinines.all():
                refined_creatinines.append(create_creatinine_api_data(creatinine))
    if not user and aki and aki.user:
        user = aki.user
    return {
        "id": aki.id if aki else None,
        "status": status if status else aki.status if aki else None,
        "creatinines": refined_creatinines,
        "age": age if age else user.age if user else None,
        "gender": gender if gender is not None else user.gender.value if user else None,
        "baselinecreatinine": baselinecreatinine
        if baselinecreatinine
        else user.baselinecreatinine.value
        if user and user.baselinecreatinine
        else None,
        "stage": stage if stage else user.ckddetail.stage if user and user.ckddetail else None,
        "user": user.id if user else aki.user.id if aki and aki.user else None,
    }


def creatinine_convert_model_or_data_to_data(creatinine: Union[Creatinine, "CreatinineData"]) -> "CreatinineData":
    if isinstance(creatinine, Creatinine):
        return create_creatinine_api_data(creatinine=creatinine)
    elif isinstance(creatinine, dict):
        return creatinine
    else:
        raise ValueError("creatinine must be a Creatinine object or dict")
