from datetime import date
from decimal import Decimal

import pytest
from factory.faker import faker  # type: ignore

from ...dateofbirths.helpers import age_calc
from ...dateofbirths.models import DateOfBirth
from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...genders.choices import Genders
from ...genders.models import Gender
from ...genders.tests.factories import GenderFactory
from ...labs.models import Urate
from ...medhistorys.choices import CVDiseases, MedHistoryTypes
from ...medhistorys.lists import FLARE_MEDHISTORYS
from ...users.tests.factories import create_psp
from ..choices import LimitedJointChoices
from ..models import Flare
from .factories import create_flare, flare_data_factory

pytestmark = pytest.mark.django_db

fake = faker.Faker()


def test__flare_data_factory():
    # Test the method without a User *arg
    for _ in range(10):
        # Create some fake data to test against
        data = flare_data_factory()

        # Test Flare-specific data
        assert "onset" in data
        assert isinstance(data["onset"], bool)
        assert "redness" in data
        assert isinstance(data["redness"], bool)
        assert "joints" in data
        assert isinstance(data["joints"], list)
        if data["joints"]:
            for joint in data["joints"]:
                assert joint in LimitedJointChoices.values
        assert "date_started" in data
        assert isinstance(data["date_started"], str)
        if "date_ended" in data:
            assert isinstance(data["date_ended"], str)
        if "urate-value" in data:
            assert isinstance(data["urate-value"], Decimal)
            assert "urate_check" in data
            assert data["urate_check"] is True
        else:
            assert "urate_check" in data
            assert data["urate_check"] is False
        assert "diagnosed" in data
        assert isinstance(data["diagnosed"], bool)
        if data["diagnosed"]:
            assert "aspiration" in data
            assert isinstance(data["aspiration"], bool)
            if data["aspiration"]:
                assert "crystal_analysis" in data
                assert isinstance(data["crystal_analysis"], bool)
            else:
                assert "crystal_analysis" not in data or data["crystal_analysis"] == ""
        else:
            assert "aspiration" not in data

        # Test the onetoone field data
        assert "dateofbirth-value" in data
        assert isinstance(data["dateofbirth-value"], int)
        assert "gender-value" in data
        assert isinstance(data["gender-value"], int)

        # Test the medhistory data
        for mh in FLARE_MEDHISTORYS:
            assert f"{mh}-value" in data
            if mh == MedHistoryTypes.MENOPAUSE:
                assert data[f"{mh}-value"] in [True, False, ""]
            elif mh in CVDiseases.values + [MedHistoryTypes.HYPERTENSION]:
                assert data[f"{mh}-value"] in [True, ""]
            else:
                assert data[f"{mh}-value"] in [True, False]

    # Test the method with a User *arg
    for _ in range(10):
        psp = create_psp(plus=True)
        data = flare_data_factory(psp)

        # Test Flare-specific data
        assert "onset" in data
        assert isinstance(data["onset"], bool)
        assert "redness" in data
        assert isinstance(data["redness"], bool)
        assert "joints" in data
        assert isinstance(data["joints"], list)
        if data["joints"]:
            for joint in data["joints"]:
                assert joint in LimitedJointChoices.values
        assert "date_started" in data
        assert isinstance(data["date_started"], str)
        if "date_ended" in data:
            assert isinstance(data["date_ended"], str)
        if "urate-value" in data:
            assert isinstance(data["urate-value"], Decimal)
            assert "urate_check" in data
            assert data["urate_check"] is True
        else:
            assert "urate_check" in data
            assert data["urate_check"] is False
        assert "diagnosed" in data
        assert isinstance(data["diagnosed"], bool)
        if data["diagnosed"]:
            assert "aspiration" in data
            assert isinstance(data["aspiration"], bool)
            if data["aspiration"]:
                assert "crystal_analysis" in data
                assert isinstance(data["crystal_analysis"], bool)
            else:
                assert "crystal_analysis" not in data or data["crystal_analysis"] == ""
        else:
            assert "aspiration" not in data

        # Test the onetoone field data
        assert "dateofbirth-value" not in data
        assert "gender-value" not in data

        # Test the medhistory data
        for mh in FLARE_MEDHISTORYS:
            assert f"{mh}-value" in data
            if mh in CVDiseases.values + [MedHistoryTypes.HYPERTENSION]:
                assert data[f"{mh}-value"] in [True, ""]
            else:
                assert data[f"{mh}-value"] in [True, False]


def test__create_flare():
    for _ in range(5):
        # Create Flare
        flare = create_flare()
        assert isinstance(flare, Flare)
        assert not (flare.user)

        # Test Flare-specific fields
        assert hasattr(flare, "onset")
        assert isinstance(flare.onset, bool)
        assert hasattr(flare, "redness")
        assert isinstance(flare.redness, bool)
        assert getattr(flare, "joints")
        assert isinstance(flare.joints, list)
        if flare.joints:
            for joint in flare.joints:
                assert joint in LimitedJointChoices.values
        assert getattr(flare, "date_started")
        assert isinstance(flare.date_started, date)
        if flare.date_ended:
            assert isinstance(flare.date_ended, date)
            assert flare.date_ended > flare.date_started
        assert hasattr(flare, "diagnosed")
        if flare.diagnosed:
            assert isinstance(flare.diagnosed, bool)
        else:
            assert not flare.diagnosed
        if flare.diagnosed:
            if getattr(flare, "crystal_analysis", None):
                assert isinstance(flare.crystal_analysis, bool)
        else:
            assert not getattr(flare, "crystal_analysis")

        # Test OneToOne fields
        assert hasattr(flare, "dateofbirth")
        assert isinstance(flare.dateofbirth, DateOfBirth)
        assert hasattr(flare, "gender")
        assert getattr(flare, "gender")
        assert isinstance(flare.gender, Gender)
        age = age_calc(flare.dateofbirth.value)
        menopause = [
            mh.medhistorytype for mh in flare.medhistorys_qs if mh.medhistorytype == MedHistoryTypes.MENOPAUSE
        ]
        if flare.gender.value == Genders.FEMALE and age >= 60:
            assert menopause
        elif flare.gender.value == Genders.FEMALE and menopause:
            assert age >= 40
        else:
            assert not menopause
        if getattr(flare, "urate", None):
            assert isinstance(flare.urate, Urate)
            assert hasattr(flare.urate, "flare")
            assert flare.urate.flare == flare

        # Test MedHistorys
        assert hasattr(flare, "medhistorys_qs")
        if flare.medhistorys_qs:
            for medhistory in flare.medhistorys_qs:
                assert medhistory.medhistorytype in FLARE_MEDHISTORYS
                assert medhistory.user is None
                assert medhistory.flare == flare

    # Test creating Flares with a User
    for _ in range(5):
        # Create Flare with a User
        psp = create_psp(plus=True)
        flare = create_flare(user=psp)
        assert isinstance(flare, Flare)
        assert hasattr(flare, "user")
        assert flare.user == psp

        # Test that the user has the right attrs and the flare does not
        assert hasattr(flare.user, "dateofbirth")
        assert isinstance(flare.user.dateofbirth, DateOfBirth)
        assert hasattr(flare.user, "gender")
        assert isinstance(flare.user.gender, Gender)
        assert not (flare.dateofbirth)
        assert not (flare.gender)

        # Test Menopause
        age = age_calc(flare.user.dateofbirth.value)
        menopause = [
            mh.medhistorytype for mh in flare.medhistorys_qs if mh.medhistorytype == MedHistoryTypes.MENOPAUSE
        ]
        if flare.user.gender.value == Genders.FEMALE and age >= 60:
            assert menopause
        elif flare.user.gender.value == Genders.FEMALE and menopause:
            assert age >= 40
        else:
            assert not menopause

        # Test Urate
        if getattr(flare, "urate", None):
            assert isinstance(flare.urate, Urate)
            assert hasattr(flare.urate, "flare")
            assert flare.urate.flare == flare
            assert hasattr(flare.urate, "user")
            assert flare.urate.user == psp

        # Test Flare-specific fields
        assert hasattr(flare, "onset")
        assert isinstance(flare.onset, bool)
        assert hasattr(flare, "redness")
        assert isinstance(flare.redness, bool)
        assert getattr(flare, "joints")
        assert isinstance(flare.joints, list)
        if flare.joints:
            for joint in flare.joints:
                assert joint in LimitedJointChoices.values
        assert getattr(flare, "date_started")
        assert isinstance(flare.date_started, date)
        if flare.date_ended:
            assert isinstance(flare.date_ended, date)
            assert flare.date_ended > flare.date_started
        assert hasattr(flare, "diagnosed")
        if flare.diagnosed:
            assert isinstance(flare.diagnosed, bool)
        else:
            assert not flare.diagnosed
        if flare.diagnosed:
            if getattr(flare, "crystal_analysis", None):
                assert isinstance(flare.crystal_analysis, bool)
        else:
            assert not getattr(flare, "crystal_analysis")

        # Test MedHistorys
        assert hasattr(flare, "medhistorys_qs")
        if flare.medhistorys_qs:
            for medhistory in flare.medhistorys_qs:
                assert medhistory.medhistorytype in FLARE_MEDHISTORYS
                assert medhistory.user is flare.user
                assert medhistory.flare is None


def test__create_flare_with_onetoones():
    for _ in range(5):
        gender = GenderFactory()
        dateofbirth = DateOfBirthFactory()
        flare = create_flare(gender=gender, dateofbirth=dateofbirth)
        assert getattr(flare, "gender", None)
        assert isinstance(flare.gender, Gender)
        assert flare.gender == gender
        assert getattr(flare, "dateofbirth", None)
        assert isinstance(flare.dateofbirth, DateOfBirth)
        assert flare.dateofbirth == dateofbirth


def test__create_flare_with_medhistorys():
    flare = create_flare(mhs=[MedHistoryTypes.ANGINA, MedHistoryTypes.CAD, MedHistoryTypes.CKD])
    assert hasattr(flare, "medhistorys_qs")
    if flare.gender.value == Genders.MALE:
        assert len(flare.medhistorys_qs) == 3
    else:
        assert len(flare.medhistorys_qs) == 3 or len(flare.medhistorys_qs) == 4
    mhtypes = [mh.medhistorytype for mh in flare.medhistorys_qs]
    assert MedHistoryTypes.ANGINA in mhtypes
    assert MedHistoryTypes.CAD in mhtypes
    assert MedHistoryTypes.CKD in mhtypes
    for mh in flare.medhistorys_qs:
        assert mh.user is None
        assert mh.flare == flare
    for mh in flare.medhistory_set.all():
        assert mh.user is None
        assert mh.flare == flare


def test__create_flare_with_medhistorys_and_user():
    """Test that the MedHistorys are created with the User."""
    flare = create_flare(user=True, mhs=[MedHistoryTypes.ANGINA, MedHistoryTypes.CAD, MedHistoryTypes.CKD])
    assert hasattr(flare, "medhistorys_qs")
    if flare.user.gender.value == Genders.MALE:
        assert len(flare.medhistorys_qs) == 3
    else:
        assert len(flare.medhistorys_qs) == 3 or len(flare.medhistorys_qs) == 4
    mhtypes = [mh.medhistorytype for mh in flare.medhistorys_qs]
    assert MedHistoryTypes.ANGINA in mhtypes
    assert MedHistoryTypes.CAD in mhtypes
    assert MedHistoryTypes.CKD in mhtypes
    for mh in flare.medhistorys_qs:
        assert mh.user == flare.user
        assert mh.flare is None
    for mh in flare.user.medhistory_set.all():
        assert mh.user == flare.user
        assert mh.flare is None


def test__create_flare_with_user():
    flare = create_flare(user=True)
    assert hasattr(flare, "user")
    assert not getattr(flare, "dateofbirth", None)
    assert hasattr(flare.user, "dateofbirth")
    assert not getattr(flare, "gender", None)
    assert hasattr(flare.user, "gender")
    assert hasattr(flare, "medhistorys_qs")
    user_mhs = flare.user.medhistory_set.all()
    for mh in flare.medhistorys_qs:
        assert mh.user == flare.user
        assert mh in user_mhs
