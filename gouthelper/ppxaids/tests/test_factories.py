from decimal import Decimal

import pytest
from factory.faker import faker  # type: ignore

from ...dateofbirths.helpers import age_calc
from ...labs.helpers import labs_eGFR_calculator, labs_stage_calculator
from ...medhistorydetails.choices import DialysisChoices, DialysisDurations, Stages
from ...medhistorys.choices import CVDiseases, MedHistoryTypes
from ...medhistorys.lists import OTHER_NSAID_CONTRAS, PPXAID_MEDHISTORYS
from ...treatments.choices import FlarePpxChoices
from ...users.tests.factories import PseudopatientPlusFactory
from .factories import PpxAidFactory, ppxaid_data_factory

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
        assert "gender-value" in data
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
                        if "stage" in data:
                            assert data["stage"] in Stages.values
                        if "baselinecreatinine-value" in data:
                            assert isinstance(data["baselinecreatinine-value"], Decimal)
                        if "stage" in data and "baselinecreatinine-value" in data:
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
        psp = PseudopatientPlusFactory()
        data = ppxaid_data_factory(psp)

        # Test the onetoone field data
        assert "dateofbirth-value" in data
        assert data["dateofbirth-value"] == age_calc(psp.dateofbirth.value)
        assert "gender-value" in data
        assert data["gender-value"] == psp.gender.value

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
                            assert isinstance(data["baselinecreatinine-value"], Decimal)
                        if "stage" in data and "baselinecreatinine-value" in data:
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


def test__ppxaid_factory():
    for _ in range(10):
        ppxaid = PpxAidFactory()
        assert getattr(ppxaid, "dateofbirth")
        assert getattr(ppxaid, "gender")
        for mh in ppxaid.medhistorys.all():
            assert mh.medhistorytype in PPXAID_MEDHISTORYS
        for ma in ppxaid.medallergys.all():
            assert ma.treatment in FlarePpxChoices.values
