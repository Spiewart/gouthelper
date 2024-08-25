from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.test import TestCase  # type: ignore
from django.utils import timezone  # type: ignore
from factory.faker import faker  # type: ignore

from ...akis.choices import Statuses
from ...dateofbirths.helpers import age_calc
from ...dateofbirths.models import DateOfBirth
from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...flareaids.tests.factories import CustomFlareAidFactory
from ...genders.choices import Genders
from ...genders.models import Gender
from ...genders.tests.factories import GenderFactory
from ...labs.helpers import labs_eGFR_calculator, labs_stage_calculator
from ...labs.models import Urate
from ...medhistorydetails.choices import Stages
from ...medhistorys.choices import CVDiseases, MedHistoryTypes
from ...medhistorys.lists import FLARE_MEDHISTORYS, FLAREAID_MEDHISTORYS
from ...users.tests.factories import create_psp
from ...utils.test_helpers import date_days_ago
from ..choices import DiagnosedChoices, LimitedJointChoices
from ..models import Flare
from .factories import CustomFlareFactory, create_flare, flare_data_factory

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
        if data["medical_evaluation"]:
            assert "diagnosed" in data
            assert data["diagnosed"] in DiagnosedChoices.values or data["diagnosed"] == ""
            assert "aspiration" in data
            assert isinstance(data["aspiration"], bool)
            if data["aspiration"]:
                assert "crystal_analysis" in data
                assert isinstance(data["crystal_analysis"], bool)
            else:
                assert "crystal_analysis" not in data or data["crystal_analysis"] == ""
            if "urate-value" in data:
                assert isinstance(data["urate-value"], Decimal)
                assert "urate_check" in data
                assert data["urate_check"] is True
            else:
                assert "urate_check" in data
                assert data["urate_check"] is False
        else:
            assert data["aspiration"] == ""

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
            assert data["urate_check"] is False or data["urate_check"] == ""
        assert "medical_evaluation" in data
        assert isinstance(data["medical_evaluation"], bool)
        if data["medical_evaluation"]:
            assert "diagnosed" in data
            assert data["diagnosed"] in DiagnosedChoices.values or data["diagnosed"] == ""
            assert "aspiration" in data
            assert isinstance(data["aspiration"], bool)
            if data["aspiration"]:
                assert "crystal_analysis" in data
                assert isinstance(data["crystal_analysis"], bool)
            else:
                assert "crystal_analysis" not in data or data["crystal_analysis"] == ""
            assert "urate_check" in data
            assert isinstance(data["urate_check"], bool)
            if data["urate_check"]:
                assert "urate-value" in data
                assert isinstance(data["urate-value"], Decimal)
        else:
            assert "aspiration" not in data or data["aspiration"] == ""
            assert "crystal_analysis" not in data or data["crystal_analysis"] == ""
            assert "diagnosed" not in data or data["diagnosed"] == ""
            assert "urate_check" not in data or data["urate_check"] == ""
            assert "urate-value" not in data or data["urate-value"] == ""

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

        # Test Aki
        if getattr(flare, "aki", None):
            assert flare.aki.user == psp
        else:
            assert not psp.aki_set.exists()

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


class TestAki(TestCase):
    def test__create_flare_with_aki(self):
        flare = create_flare(aki=True)
        assert hasattr(flare, "aki")
        assert hasattr(flare.aki, "flare")
        assert flare.aki.flare == flare
        if flare.user:
            assert hasattr(flare.aki, "user")
            assert flare.aki.user == flare.user


class TestFlareFactory(TestCase):
    def test__flare_created(self):
        factory = CustomFlareFactory()
        flare = factory.create_object()
        self.assertTrue(isinstance(flare, Flare))

    def test__user_created(self) -> None:
        factory = CustomFlareFactory(user=True)
        flare = factory.create_object()
        self.assertTrue(hasattr(flare, "user"))
        self.assertTrue(flare.user)

    def test__user_created_with_dateofbirth(self) -> None:
        dateofbirth: date = (timezone.now() - timedelta(days=365 * 30)).date()
        factory = CustomFlareFactory(user=True, dateofbirth=dateofbirth)
        flare = factory.create_object()
        self.assertTrue(hasattr(flare, "user"))
        self.assertTrue(flare.user)
        self.assertTrue(hasattr(flare.user, "dateofbirth"))
        self.assertTrue(flare.user.dateofbirth)
        self.assertEqual(flare.user.dateofbirth.value, dateofbirth)

    def test__ValueError_raised_with_user_and_dateofbirth(self) -> None:
        user = create_psp()
        with self.assertRaises(ValueError):
            CustomFlareFactory(user=user, dateofbirth=True)

    def test__user_created_with_gender(self) -> None:
        factory = CustomFlareFactory(user=True, gender=Genders.FEMALE)
        flare = factory.create_object()
        self.assertTrue(hasattr(flare, "user"))
        self.assertTrue(flare.user)
        self.assertTrue(hasattr(flare.user, "gender"))
        self.assertTrue(flare.user.gender)
        self.assertEqual(flare.user.gender.value, Genders.FEMALE)

    def test__ValueError_raised_with_user_and_gender(self) -> None:
        user = create_psp()
        with self.assertRaises(ValueError):
            CustomFlareFactory(user=user, gender=True)

    def test__aki_created(self) -> None:
        factory = CustomFlareFactory(aki=Statuses.ONGOING)
        flare = factory.create_object()
        self.assertTrue(hasattr(flare, "aki"))
        self.assertTrue(flare.aki)
        self.assertEqual(flare.aki.status, Statuses.ONGOING)

    def test__aki_created_with_user(self) -> None:
        factory = CustomFlareFactory(aki=Statuses.ONGOING, user=True)
        flare = factory.create_object()
        self.assertTrue(hasattr(flare, "aki"))
        self.assertTrue(flare.aki)
        self.assertEqual(flare.aki.status, Statuses.ONGOING)
        self.assertTrue(hasattr(flare.aki, "user"))
        self.assertTrue(flare.aki.user)
        self.assertEqual(flare.aki.user, flare.user)

    def test__aki_created_with_creatinines(self) -> None:
        factory = CustomFlareFactory(
            creatinines=[(Decimal("1.0"), date_days_ago(0)), (Decimal("1.1"), date_days_ago(3))]
        )
        flare = factory.create_object()
        self.assertTrue(hasattr(flare, "aki"))
        self.assertTrue(hasattr(flare.aki, "creatinines"))
        self.assertTrue(flare.aki.creatinines)
        self.assertEqual(len(flare.aki.creatinines), 2)

    def test__creatinines_with_no_aki_raises_ValueError(self) -> None:
        with self.assertRaises(ValueError):
            CustomFlareFactory(
                aki=None, creatinines=[(Decimal("1.0"), date_days_ago(0)), (Decimal("1.1"), date_days_ago(3))]
            )

    def test__date_started(self) -> None:
        date_started = date_days_ago(3)
        factory = CustomFlareFactory(date_started=date_started)
        flare = factory.create_object()
        self.assertTrue(hasattr(flare, "date_started"))
        self.assertTrue(flare.date_started)
        self.assertTrue(isinstance(flare.date_started, date))
        self.assertEqual(flare.date_started, date_started)

    def test__date_ended(self) -> None:
        date_ended = date_days_ago(4)
        factory = CustomFlareFactory(date_ended=date_ended)
        flare = factory.create_object()
        self.assertTrue(hasattr(flare, "date_ended"))
        self.assertTrue(flare.date_ended)
        self.assertTrue(isinstance(flare.date_ended, date))
        self.assertEqual(flare.date_ended, date_ended)

    def test__stage_creates_ckddetail(self):
        factory = CustomFlareFactory(stage=Stages.THREE)
        flare = factory.create_object()
        self.assertTrue(flare.medhistory_set.filter(medhistorytype=MedHistoryTypes.CKD).exists())
        self.assertTrue(flare.ckd)
        self.assertTrue(flare.ckddetail)
        self.assertEqual(flare.ckddetail.stage, Stages.THREE)

    def test__creates_baselinecreatinine(self) -> None:
        factory = CustomFlareFactory(baselinecreatinine=Decimal("2.0"))
        flare = factory.create_object()
        self.assertTrue(flare.ckd)
        self.assertTrue(flare.ckddetail)
        self.assertTrue(flare.baselinecreatinine)
        self.assertEqual(flare.baselinecreatinine.value, Decimal("2.0"))
        self.assertEqual(
            flare.ckddetail.stage,
            labs_stage_calculator(
                labs_eGFR_calculator(flare.baselinecreatinine, age_calc(flare.dateofbirth.value), flare.gender.value)
            ),
        )

    def test__deletes_ckd_and_relations_when_ckd_is_False(self) -> None:
        factory = CustomFlareFactory(baselinecreatinine=Decimal("2.0"))
        flare = factory.create_object()
        next_factory = CustomFlareFactory(flare=flare, ckd=False)
        modified_flare = next_factory.create_object()
        self.assertFalse(modified_flare.ckd)
        self.assertFalse(modified_flare.ckddetail)
        self.assertFalse(modified_flare.baselinecreatinine)

    def test__creates_menopause(self) -> None:
        factory = CustomFlareFactory(menopause=True)
        flare = factory.create_object()
        self.assertTrue(flare.menopause)
        self.assertEqual(flare.gender.value, Genders.FEMALE)
        self.assertGreaterEqual(age_calc(flare.dateofbirth.value), 40)

    def test__menopause_raises_ValueError_for_tooyoung_female(self):
        dateofbirth = (timezone.now() - timedelta(days=365 * 35)).date()
        with self.assertRaises(ValueError):
            CustomFlareFactory(dateofbirth=dateofbirth, menopause=True, gender=Genders.FEMALE)

    def test__creates_urate(self) -> None:
        factory = CustomFlareFactory(urate=Decimal("5.0"))
        flare = factory.create_object()
        self.assertTrue(flare.urate)
        self.assertEqual(flare.urate.value, Decimal("5.0"))

    def test__updates_flare_urate(self) -> None:
        factory = CustomFlareFactory(urate=Decimal("5.0"))
        flare = factory.create_object()
        next_factory = CustomFlareFactory(flare=flare, urate=Decimal("6.0"))
        modified_flare = next_factory.create_object()
        self.assertTrue(modified_flare.urate)
        self.assertEqual(modified_flare.urate.value, Decimal("6.0"))

    def test__creates_flare_with_flareaid(self) -> None:
        factory = CustomFlareFactory(flareaid=True)
        flare = factory.create_object()
        self.assertTrue(flare.flareaid)

    def test__creates_flareaid_with_same_medhistorys_as_flare(self) -> None:
        factory = CustomFlareFactory(flareaid=True, ckd=True, angina=True, cad=True)
        flare = factory.create_object()
        for mh in flare.medhistorys_qs:
            if mh.medhistorytype in FLAREAID_MEDHISTORYS:
                self.assertTrue(flare.flareaid.medhistory_set.filter(medhistorytype=mh.medhistorytype).exists())
        self.assertTrue(flare.flareaid.medhistory_set.filter(medhistorytype=MedHistoryTypes.CKD).exists())
        self.assertTrue(flare.flareaid.medhistory_set.filter(medhistorytype=MedHistoryTypes.ANGINA).exists())
        self.assertTrue(flare.flareaid.medhistory_set.filter(medhistorytype=MedHistoryTypes.CAD).exists())

    def test__flareaid_medhistorys_are_the_same_objects_as_flares(self) -> None:
        factory = CustomFlareFactory(flareaid=True, ckd=True, angina=True, cad=True)
        flare = factory.create_object()
        flareaid = flare.flareaid
        flare_ckd = flare.medhistory_set.filter(medhistorytype=MedHistoryTypes.CKD).first()
        flare_angina = flare.medhistory_set.filter(medhistorytype=MedHistoryTypes.ANGINA).first()
        flare_cad = flare.medhistory_set.filter(medhistorytype=MedHistoryTypes.CAD).first()
        flareaid_ckd = flareaid.medhistory_set.filter(medhistorytype=MedHistoryTypes.CKD).first()
        flareaid_angina = flareaid.medhistory_set.filter(medhistorytype=MedHistoryTypes.ANGINA).first()
        flareaid_cad = flareaid.medhistory_set.filter(medhistorytype=MedHistoryTypes.CAD).first()
        self.assertEqual(
            flare_ckd,
            flareaid_ckd,
        )
        self.assertEqual(
            flare_ckd.pk,
            flareaid_ckd.pk,
        )
        self.assertEqual(
            flare_angina,
            flareaid_angina,
        )
        self.assertEqual(
            flare_angina.pk,
            flareaid_angina.pk,
        )
        self.assertEqual(
            flare_cad,
            flareaid_cad,
        )
        self.assertEqual(
            flare_cad.pk,
            flareaid_cad.pk,
        )
        for medhistory in flare.medhistory_set.filter(medhistorytype__in=FLAREAID_MEDHISTORYS):
            self.assertTrue(flareaid.medhistory_set.filter(pk=medhistory.pk).exists())
        for medhistory in flareaid.medhistory_set.filter(medhistorytype__in=FLARE_MEDHISTORYS):
            self.assertTrue(flare.medhistory_set.filter(pk=medhistory.pk).exists())

    def test__creates_flareaid_with_same_dateofbirth_as_flare(self) -> None:
        factory = CustomFlareFactory(flareaid=True)
        flare = factory.create_object()
        self.assertTrue(flare.flareaid.dateofbirth)
        self.assertEqual(flare.dateofbirth, flare.flareaid.dateofbirth)

    def test__creates_flareaid_with_same_gender_as_flare(self) -> None:
        factory = CustomFlareFactory(flareaid=True)
        flare = factory.create_object()
        self.assertTrue(flare.flareaid.gender)
        self.assertEqual(flare.gender, flare.flareaid.gender)

    def test__creates_flare_with_same_dateofbirth_as_flareaid(self) -> None:
        flareaid_factory = CustomFlareAidFactory()
        flareaid = flareaid_factory.create_object()
        factory = CustomFlareFactory(flareaid=flareaid)
        flare = factory.create_object()
        self.assertEqual(flare.dateofbirth, flareaid.dateofbirth)

    def test__creates_flare_with_same_gender_as_flareaid(self) -> None:
        flareaid_factory = CustomFlareAidFactory()
        flareaid = flareaid_factory.create_object()
        factory = CustomFlareFactory(flareaid=flareaid)
        flare = factory.create_object()
        self.assertEqual(flareaid.gender, flare.gender)

    def test__creates_flare_with_same_medhistorys_as_flareaid(self) -> None:
        flareaid_factory = CustomFlareAidFactory(angina=True, cad=True, ibd=False, colchicineinteraction=True)
        flareaid = flareaid_factory.create_object()
        factory = CustomFlareFactory(flareaid=flareaid)
        flare = factory.create_object()
        for mh in flareaid.medhistory_set.all():
            if mh.medhistorytype in FLARE_MEDHISTORYS:
                self.assertTrue(flare.medhistory_set.filter(medhistorytype=mh.medhistorytype).exists())
        self.assertTrue(flareaid.medhistory_set.filter(medhistorytype=MedHistoryTypes.ANGINA).exists())
        self.assertTrue(flareaid.medhistory_set.filter(medhistorytype=MedHistoryTypes.CAD).exists())
        self.assertFalse(flareaid.medhistory_set.filter(medhistorytype=MedHistoryTypes.IBD).exists())
        self.assertTrue(flareaid.medhistory_set.filter(medhistorytype=MedHistoryTypes.COLCHICINEINTERACTION).exists())
        self.assertTrue(flare.medhistory_set.filter(medhistorytype=MedHistoryTypes.ANGINA).exists())
        self.assertTrue(flare.medhistory_set.filter(medhistorytype=MedHistoryTypes.CAD).exists())
        self.assertFalse(flare.medhistory_set.filter(medhistorytype=MedHistoryTypes.IBD).exists())
        self.assertFalse(flare.medhistory_set.filter(medhistorytype=MedHistoryTypes.COLCHICINEINTERACTION).exists())
