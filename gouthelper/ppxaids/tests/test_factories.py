from decimal import Decimal

import pytest
from factory.faker import faker  # type: ignore

from ...dateofbirths.helpers import age_calc
from ...dateofbirths.models import DateOfBirth
from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...genders.models import Gender
from ...genders.tests.factories import GenderFactory
from ...labs.helpers import labs_eGFR_calculator, labs_stage_calculator
from ...medhistorydetails.choices import DialysisChoices, DialysisDurations, Stages
from ...medhistorys.choices import CVDiseases, MedHistoryTypes
from ...medhistorys.lists import OTHER_NSAID_CONTRAS, PPXAID_MEDHISTORYS
from ...treatments.choices import FlarePpxChoices
from ...users.tests.factories import create_psp
from ..models import PpxAid
from .factories import create_ppxaid, ppxaid_data_factory

pytestmark = pytest.mark.django_db

fake = faker.Faker()


def test__ppxaid_data_factory():
    # Test the method without a User *arg
    for _ in range(10):
        # Create some fake data to test against
        data = ppxaid_data_factory()

        # Test the onetoone field data
        assert "dateofbirth-value" in data
        assert isinstance(data["dateofbirth-value"], int)
        if data.get("gender", None):
            assert isinstance(data["gender-value"], int)

        # Test the medhistory data
        for mh in PPXAID_MEDHISTORYS:
            assert f"{mh}-value" in data
            if mh in CVDiseases.values or mh in OTHER_NSAID_CONTRAS or mh == MedHistoryTypes.HYPERTENSION:
                assert data[f"{mh}-value"] in [True, ""]
            else:
                assert data[f"{mh}-value"] in [True, False]
                if mh == MedHistoryTypes.CKD and data[f"{mh}-value"]:
                    assert "dialysis" in data
                    assert data["dialysis"] in [True, False]
                    if data["dialysis"]:
                        assert "dialysis_type" in data
                        assert data["dialysis_type"] in DialysisChoices.values
                        assert "dialysis_duration" in data
                        assert data["dialysis_duration"] in DialysisDurations.values
                    else:
                        assert "stage" in data or "baselinecreatinine-value" in data
                        stage_data = data.get("stage", None)
                        bc_data = data.get("baselinecreatinine-value", None)
                        if stage_data:
                            if stage_data != "":
                                assert stage_data in Stages.values
                            else:
                                assert stage_data == ""
                        if bc_data:
                            if bc_data != "":
                                assert isinstance(bc_data, Decimal)
                            else:
                                assert bc_data == ""
                            assert data["stage"] in Stages.values
                        if stage_data and stage_data != "" and bc_data and bc_data != "":
                            assert data["stage"] == labs_stage_calculator(
                                labs_eGFR_calculator(
                                    data["baselinecreatinine-value"],
                                    data["dateofbirth-value"],
                                    data["gender-value"],
                                )
                            )

        # Test the medallergy data
        for trt in FlarePpxChoices.values:
            assert f"medallergy_{trt}" in data
            assert data[f"medallergy_{trt}"] in [True, ""]

    # Test the method with a User *arg
    for _ in range(10):
        psp = create_psp(plus=True)
        data = ppxaid_data_factory(psp)

        # Test the onetoone field data
        assert "dateofbirth-value" not in data
        assert "gender-value" not in data

        # Test the medhistory data
        for mh in PPXAID_MEDHISTORYS:
            assert f"{mh}-value" in data
            if mh in CVDiseases.values or mh in OTHER_NSAID_CONTRAS or mh == MedHistoryTypes.HYPERTENSION:
                assert data[f"{mh}-value"] in [True, ""]
            else:
                assert data[f"{mh}-value"] in [True, False]
                if mh == MedHistoryTypes.CKD and data[f"{mh}-value"]:
                    assert "dialysis" in data
                    assert data["dialysis"] in [True, False]
                    if data["dialysis"]:
                        assert "dialysis_type" in data
                        assert data["dialysis_type"] in DialysisChoices.values
                        assert "dialysis_duration" in data
                        assert data["dialysis_duration"] in DialysisDurations.values
                    else:
                        assert "stage" in data or "baselinecreatinine-value" in data
                        if "stage" in data:
                            assert data["stage"] in Stages.values
                        if "baselinecreatinine-value" in data:
                            if data["baselinecreatinine-value"]:
                                assert isinstance(data["baselinecreatinine-value"], Decimal)
                            else:
                                assert data["baselinecreatinine-value"] == ""
                        if "stage" in data and data.get("baselinecreatinine-value", ""):
                            assert data["stage"] == labs_stage_calculator(
                                labs_eGFR_calculator(
                                    data["baselinecreatinine-value"],
                                    age_calc(psp.dateofbirth.value),
                                    psp.gender.value,
                                )
                            )

        # Test the medallergy data
        for trt in FlarePpxChoices.values:
            assert f"medallergy_{trt}" in data
            assert data[f"medallergy_{trt}"] in [True, ""]


def test__create_ppxaid():
    for _ in range(5):
        ppxaid = create_ppxaid()
        assert isinstance(ppxaid, PpxAid)
        assert not (ppxaid.user)
        assert hasattr(ppxaid, "dateofbirth")
        assert isinstance(ppxaid.dateofbirth, DateOfBirth)
        assert hasattr(ppxaid, "gender")
        if ppxaid.ckd and getattr(ppxaid.ckd, "baselinecreatinine", None):
            assert getattr(ppxaid, "gender")
            assert isinstance(ppxaid.gender, Gender)
        assert hasattr(ppxaid, "medhistorys_qs")
        if ppxaid.medhistorys_qs:
            for medhistory in ppxaid.medhistorys_qs:
                assert medhistory.medhistorytype in PPXAID_MEDHISTORYS
                assert medhistory.user is None
                assert medhistory.ppxaid == ppxaid
        assert hasattr(ppxaid, "medallergys_qs")
        if ppxaid.medallergys_qs:
            for medallergy in ppxaid.medallergys_qs:
                assert medallergy.treatment in FlarePpxChoices.values
                assert medallergy.user is None
                assert medallergy.ppxaid == ppxaid


def test__create_ppxaid_with_onetoones():
    for _ in range(5):
        gender = GenderFactory()
        dateofbirth = DateOfBirthFactory()
        ppxaid = create_ppxaid(gender=gender, dateofbirth=dateofbirth)
        assert getattr(ppxaid, "gender", None)
        assert isinstance(ppxaid.gender, Gender)
        assert ppxaid.gender == gender
        assert getattr(ppxaid, "dateofbirth", None)
        assert isinstance(ppxaid.dateofbirth, DateOfBirth)
        assert ppxaid.dateofbirth == dateofbirth


def test__create_ppxaid_without_onetoones():
    ppxaid = create_ppxaid(gender=None)
    assert not getattr(ppxaid, "ethnicity", None)
    assert not getattr(ppxaid, "gender", None)


def test__create_ppxaid_with_medallergys():
    ppxaid = create_ppxaid(mas=[FlarePpxChoices.NAPROXEN, FlarePpxChoices.COLCHICINE])
    assert hasattr(ppxaid, "medallergys_qs")
    assert len(ppxaid.medallergys_qs) == 2
    for ma in ppxaid.medallergys_qs:
        assert ma.treatment in [FlarePpxChoices.NAPROXEN, FlarePpxChoices.COLCHICINE]
        assert ma.user is None
        assert ma.ppxaid == ppxaid
    for ma in ppxaid.medallergy_set.all():
        assert ma.treatment in [FlarePpxChoices.NAPROXEN, FlarePpxChoices.COLCHICINE]
        assert ma.user is None
        assert ma.ppxaid == ppxaid


def test__create_ppxaid_with_medhistorys():
    ppxaid = create_ppxaid(mhs=[MedHistoryTypes.CKD, MedHistoryTypes.COLCHICINEINTERACTION])
    assert hasattr(ppxaid, "medhistorys_qs")
    assert len(ppxaid.medhistorys_qs) == 2
    for mh in ppxaid.medhistorys_qs:
        assert mh.medhistorytype in [MedHistoryTypes.CKD, MedHistoryTypes.COLCHICINEINTERACTION]
        assert mh.user is None
        assert mh.ppxaid == ppxaid
    for mh in ppxaid.medhistory_set.all():
        assert mh.medhistorytype in [MedHistoryTypes.CKD, MedHistoryTypes.COLCHICINEINTERACTION]
        assert mh.user is None
        assert mh.ppxaid == ppxaid


def test__create_ppxaid_with_ckd_and_ckddetail():
    ppxaid = create_ppxaid(mhs=[MedHistoryTypes.CKD])
    assert hasattr(ppxaid, "ckd")
    assert hasattr(ppxaid, "ckddetail")
    assert hasattr(ppxaid, "gender")


def test__create_ppxaid_with_user():
    ppxaid = create_ppxaid(user=True)
    assert hasattr(ppxaid, "user")
    assert not getattr(ppxaid, "dateofbirth", None)
    assert hasattr(ppxaid.user, "dateofbirth")
    assert not getattr(ppxaid, "gender", None)
    if hasattr(ppxaid.user, "gender"):
        assert isinstance(ppxaid.user.gender, Gender)
    assert hasattr(ppxaid, "medallergys_qs")
    user_mas = ppxaid.user.medallergy_set.all()
    for ma in ppxaid.medallergys_qs:
        assert ma.user == ppxaid.user
        assert ma in user_mas
    assert hasattr(ppxaid, "medhistorys_qs")
    user_mhs = ppxaid.user.medhistory_set.all()
    for mh in ppxaid.medhistorys_qs:
        assert mh.user == ppxaid.user
        assert mh in user_mhs
