import pytest
from factory.faker import faker  # type: ignore

from ...dateofbirths.helpers import age_calc
from ...dateofbirths.models import DateOfBirth
from ...ethnicitys.models import Ethnicity
from ...genders.choices import Genders
from ...genders.models import Gender
from ...medhistorys.choices import MedHistoryTypes
from ..models import Pseudopatient
from .factories import create_psp

pytestmark = pytest.mark.django_db

fake = faker.Faker()


def test__create_pseudopatient():
    for _ in range(10):
        psp = create_psp()
        assert isinstance(psp, Pseudopatient)
        assert isinstance(psp.dateofbirth, DateOfBirth)
        assert isinstance(psp.ethnicity, Ethnicity)
        assert isinstance(psp.gender, Gender)
        assert psp.medallergy_set.all().count() == 0
        psp_mhs = psp.medhistory_set.all()
        assert len(psp_mhs) == 1 or len(psp_mhs) == 2
        assert MedHistoryTypes.GOUT in [x.medhistorytype for x in psp_mhs]
        if psp.gender == Genders.FEMALE:
            if age_calc(psp.dateofbirth.value) >= 60:
                assert MedHistoryTypes.MENOPAUSE in [x.medhistorytype for x in psp_mhs]
            elif age_calc(psp.dateofbirth.value) < 40:
                assert MedHistoryTypes.MENOPAUSE not in [x.medhistorytype for x in psp_mhs]


def test__create_pseudopatient_plus():
    mas_created = False
    mhs_created = False
    for _ in range(10):
        psp = create_psp(plus=True)
        assert isinstance(psp, Pseudopatient)
        assert isinstance(psp.dateofbirth, DateOfBirth)
        assert isinstance(psp.ethnicity, Ethnicity)
        assert isinstance(psp.gender, Gender)
        if psp.medallergy_set.exists():
            mas_created = True
        psp_mhs = psp.medhistory_set.all()
        if len(psp_mhs) > 2:
            mhs_created = True
        assert MedHistoryTypes.GOUT in [x.medhistorytype for x in psp_mhs]
        if psp.gender == Genders.FEMALE:
            if age_calc(psp.dateofbirth.value) >= 60:
                assert MedHistoryTypes.MENOPAUSE in [x.medhistorytype for x in psp_mhs]
            elif age_calc(psp.dateofbirth.value) < 40:
                assert MedHistoryTypes.MENOPAUSE not in [x.medhistorytype for x in psp_mhs]
    assert mas_created
    assert mhs_created
