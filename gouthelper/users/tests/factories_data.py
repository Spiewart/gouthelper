# Need separate file for data factories because some imports cause a circular import error
# when placed in the same file as the model factories

from typing import Any

from django.contrib.auth import get_user_model
from factory.faker import faker  # type: ignore

from ...medhistorys.choices import MedHistoryTypes
from ...utils.factories import MedHistoryDataMixin, OneToOneDataMixin

fake = faker.Faker()

User = get_user_model()


class CreatePseudopatientFormData(MedHistoryDataMixin, OneToOneDataMixin):
    def create(self):
        mh_data = self.create_mh_data()
        oto_data = self.create_oto_data()
        return {
            **mh_data,
            **oto_data,
        }


def pseudopatient_form_data_factory(
    mh_dets: dict[MedHistoryTypes : dict[str:Any]] = None,
    otos: dict[str:Any] | None = None,
) -> dict[str, Any]:
    """Method that creates fake data for a pseudopatient_form for testing."""

    return CreatePseudopatientFormData(
        aid_mhs=[MedHistoryTypes.GOUT],
        bool_mhs=[MedHistoryTypes.GOUT],
        req_mhs=[MedHistoryTypes.GOUT],
        aid_mh_dets=[MedHistoryTypes.GOUT],
        mh_dets=mh_dets,
        req_mh_dets=[MedHistoryTypes.GOUT],
        aid_otos=["dateofbirth", "gender", "urate"],
        otos=otos,
    ).create()
