from datetime import timedelta

import pytest
from django.test import TestCase  # type: ignore
from django.utils import timezone

from ...dateofbirths.helpers import age_calc
from ...dateofbirths.models import DateOfBirth
from ...ethnicitys.choices import Ethnicitys
from ...ethnicitys.models import Ethnicity
from ...genders.choices import Genders
from ...genders.models import Gender
from ...labs.models import Hlab5801
from ...medhistorydetails.choices import Stages
from ...medhistorys.choices import MedHistoryTypes
from ...medhistorys.lists import ULTAID_MEDHISTORYS
from ...treatments.choices import UltChoices
from ...users.tests.factories import create_psp
from ..models import UltAid
from .factories import create_ultaid, ultaid_data_factory

pytestmark = pytest.mark.django_db


class TestUltAidDataFactory(TestCase):
    def setUp(self):
        self.user_with_ultaid = create_psp(plus=True)
        self.user_ultaid = create_ultaid(user=self.user_with_ultaid)
        self.user_without_ultaid = create_psp()
        self.ultaid_no_user = create_ultaid()
        self.bools = [True, False]
        self.bools_or_empty_str = [True, False, ""]
        self.True_or_empty_str = [True, ""]
        self.bool_mhs = [
            MedHistoryTypes.ALLOPURINOLHYPERSENSITIVITY,
            MedHistoryTypes.CKD,
            MedHistoryTypes.FEBUXOSTATHYPERSENSITIVITY,
            MedHistoryTypes.ORGANTRANSPLANT,
            MedHistoryTypes.XOIINTERACTION,
        ]

    def test__without_user_or_ultaid(self):
        """Tests that the data factory returns a dict with the correct keys and values
        when called without a user."""
        for _ in range(10):
            data = ultaid_data_factory()
            assert isinstance(data, dict)
            for mh in ULTAID_MEDHISTORYS:
                self.assertIn(f"{mh}-value", data)
                self.assertIn(data[f"{mh}-value"], self.bools_or_empty_str)
            for treatment in UltChoices.values:
                self.assertIn(f"medallergy_{treatment}", data)
                self.assertIn(data[f"medallergy_{treatment}"], self.True_or_empty_str)
            if data.get("hlab5801-value", None):
                self.assertIn(data["hlab5801-value"], self.bools)
            if data.get("baselinecreatinine-value", None):
                self.assertIn("dateofbirth-value", data)
                self.assertIn("gender-value", data)
            if data.get("dateofbirth-value", None):
                self.assertTrue(isinstance(data["dateofbirth-value"], int))
            self.assertIn("ethnicity-value", data)
            self.assertIn(data["ethnicity-value"], Ethnicitys.values)
            if data.get("gender-value", None):
                self.assertIn(data["gender-value"], Genders.values)

    def test__without_user_or_ultaid_with_medallergys_medhistorys(self):
        """Tests that the data factory returns a dict with the correct keys and values
        when called without a user."""
        for _ in range(10):
            data = ultaid_data_factory(mhs=[MedHistoryTypes.CKD, MedHistoryTypes.CAD], mas=[UltChoices.ALLOPURINOL])
            assert isinstance(data, dict)
            for mh in ULTAID_MEDHISTORYS:
                self.assertIn(f"{mh}-value", data)
                self.assertIn(data[f"{mh}-value"], self.bools_or_empty_str)
            self.assertIn(f"{MedHistoryTypes.CKD}-value", data)
            self.assertTrue(data[f"{MedHistoryTypes.CKD}-value"])
            self.assertIn(f"{MedHistoryTypes.CAD}-value", data)
            self.assertTrue(data[f"{MedHistoryTypes.CAD}-value"])
            for treatment in UltChoices.values:
                self.assertIn(f"medallergy_{treatment}", data)
                self.assertIn(data[f"medallergy_{treatment}"], self.True_or_empty_str)
            self.assertIn(f"medallergy_{UltChoices.ALLOPURINOL}", data)
            self.assertTrue(data[f"medallergy_{UltChoices.ALLOPURINOL}"])
            if data.get("hlab5801-value", None):
                self.assertIn(data["hlab5801-value"], self.bools)
            if data.get("baselinecreatinine-value", None):
                self.assertIn("dateofbirth-value", data)
                self.assertIn("gender-value", data)
            if data.get("dateofbirth-value", None):
                self.assertTrue(isinstance(data["dateofbirth-value"], int))
            self.assertIn("ethnicity-value", data)
            self.assertIn(data["ethnicity-value"], Ethnicitys.values)
            if data.get("gender-value", None):
                self.assertIn(data["gender-value"], Genders.values)

    def test__without_user_or_ultaid_with_oto_kwargs(self):
        """Tests that the data factory returns a dict with the correct keys and values
        when called without a user."""
        for _ in range(10):
            data = ultaid_data_factory(
                otos={"dateofbirth": 50, "ethnicity": Ethnicitys.CAUCASIANAMERICAN, "gender": Genders.FEMALE}
            )
            assert isinstance(data, dict)
            for mh in ULTAID_MEDHISTORYS:
                self.assertIn(f"{mh}-value", data)
                self.assertIn(data[f"{mh}-value"], self.bools_or_empty_str)
            for treatment in UltChoices.values:
                self.assertIn(f"medallergy_{treatment}", data)
                self.assertIn(data[f"medallergy_{treatment}"], self.True_or_empty_str)
            if data.get("hlab5801-value", None):
                self.assertIn(data["hlab5801-value"], self.bools)
            if data.get("baselinecreatinine-value", None):
                self.assertIn("dateofbirth-value", data)
                self.assertIn("gender-value", data)
            self.assertIn("dateofbirth-value", data)
            self.assertEqual(data["dateofbirth-value"], 50)
            self.assertIn("ethnicity-value", data)
            self.assertEqual(data["ethnicity-value"], Ethnicitys.CAUCASIANAMERICAN)
            self.assertIn("gender-value", data)
            self.assertEqual(data["gender-value"], Genders.FEMALE)

    def test__with_user(self):
        for _ in range(10):
            data = ultaid_data_factory(user=self.user_with_ultaid)
            assert isinstance(data, dict)
            for mh in ULTAID_MEDHISTORYS:
                self.assertIn(f"{mh}-value", data)
                self.assertEqual(
                    data[f"{mh}-value"],
                    True if getattr(self.user_with_ultaid, mh.lower()) else False if mh in self.bool_mhs else "",
                )
            for treatment in UltChoices.values:
                self.assertIn(f"medallergy_{treatment}", data)
                self.assertEqual(
                    data[f"medallergy_{treatment}"],
                    True if getattr(self.user_with_ultaid, f"{treatment.lower()}_allergy") else "",
                )
            if data.get("hlab5801-value", None):
                if data["hlab5801-value"] is True:
                    self.assertEqual(data["hlab5801-value"], self.user_with_ultaid.hlab5801.value)
                else:
                    self.assertEqual(data["hlab5801-value"], False)
            self.assertNotIn("dateofbirth-value", data)
            self.assertNotIn("ethnicity-value", data)
            self.assertNotIn("gender-value", data)

    def test__with_user_with_medallergys_medhistorys(self):
        for _ in range(10):
            data = ultaid_data_factory(
                user=self.user_with_ultaid,
                mhs=[MedHistoryTypes.CKD, MedHistoryTypes.CAD],
                mas=[UltChoices.ALLOPURINOL],
            )
            assert isinstance(data, dict)
            for mh in ULTAID_MEDHISTORYS:
                self.assertIn(f"{mh}-value", data)
                if mh not in [MedHistoryTypes.CKD, MedHistoryTypes.CAD]:
                    self.assertEqual(
                        data[f"{mh}-value"],
                        True if getattr(self.user_with_ultaid, mh.lower()) else False if mh in self.bool_mhs else "",
                    )
            self.assertIn(f"{MedHistoryTypes.CKD}-value", data)
            self.assertTrue(data[f"{MedHistoryTypes.CKD}-value"])
            self.assertIn(f"{MedHistoryTypes.CAD}-value", data)
            self.assertTrue(data[f"{MedHistoryTypes.CAD}-value"])
            for treatment in UltChoices.values:
                self.assertIn(f"medallergy_{treatment}", data)
                if treatment != UltChoices.ALLOPURINOL:
                    self.assertEqual(
                        data[f"medallergy_{treatment}"],
                        True if getattr(self.user_with_ultaid, f"{treatment.lower()}_allergy") else "",
                    )
            self.assertIn(f"medallergy_{UltChoices.ALLOPURINOL}", data)
            self.assertTrue(data[f"medallergy_{UltChoices.ALLOPURINOL}"])
            if data.get("hlab5801-value", None):
                if data["hlab5801-value"] is True:
                    self.assertEqual(data["hlab5801-value"], self.user_with_ultaid.hlab5801.value)
                else:
                    self.assertEqual(data["hlab5801-value"], False)
            self.assertNotIn("dateofbirth-value", data)
            self.assertNotIn("ethnicity-value", data)
            self.assertNotIn("gender-value", data)

    def test__with_ultaid(self):
        for _ in range(10):
            data = ultaid_data_factory(ultaid=self.ultaid_no_user)
            assert isinstance(data, dict)
            for mh in ULTAID_MEDHISTORYS:
                self.assertIn(f"{mh}-value", data)
                self.assertEqual(
                    data[f"{mh}-value"],
                    True if getattr(self.ultaid_no_user, mh.lower()) else False if mh in self.bool_mhs else "",
                )
            for treatment in UltChoices.values:
                self.assertIn(f"medallergy_{treatment}", data)
                self.assertEqual(
                    data[f"medallergy_{treatment}"],
                    True if getattr(self.ultaid_no_user, f"{treatment.lower()}_allergy") else "",
                )
            if data.get("hlab5801-value", None):
                self.assertEqual(
                    data["hlab5801-value"],
                    self.ultaid_no_user.hlab5801.value if self.ultaid_no_user.hlab5801 else False,
                )
            if data.get("baselinecreatinine-value", None):
                self.assertIn("dateofbirth-value", data)
                self.assertIn("gender-value", data)
            if data.get("dateofbirth-value", None) and data["dateofbirth-value"] != "":
                self.assertEqual(data["dateofbirth-value"], age_calc(self.ultaid_no_user.dateofbirth.value))
            self.assertIn("ethnicity-value", data)
            self.assertEqual(data["ethnicity-value"], (self.ultaid_no_user.ethnicity.value))
            if data.get("gender-value", None):
                self.assertEqual(data["gender-value"], self.ultaid_no_user.gender.value)

    def test__with_ultaid_with_medallergys_medhistorys(self):
        for _ in range(10):
            data = ultaid_data_factory(
                ultaid=self.ultaid_no_user,
                mhs=[MedHistoryTypes.CKD, MedHistoryTypes.CAD],
                mas=[UltChoices.ALLOPURINOL],
            )
            assert isinstance(data, dict)
            for mh in ULTAID_MEDHISTORYS:
                self.assertIn(f"{mh}-value", data)
                if mh not in [MedHistoryTypes.CKD, MedHistoryTypes.CAD]:
                    self.assertEqual(
                        data[f"{mh}-value"],
                        True if getattr(self.ultaid_no_user, mh.lower()) else False if mh in self.bool_mhs else "",
                    )
            self.assertIn(f"{MedHistoryTypes.CKD}-value", data)
            self.assertTrue(data[f"{MedHistoryTypes.CKD}-value"])
            self.assertIn(f"{MedHistoryTypes.CAD}-value", data)
            self.assertTrue(data[f"{MedHistoryTypes.CAD}-value"])
            for treatment in UltChoices.values:
                self.assertIn(f"medallergy_{treatment}", data)
                if treatment != UltChoices.ALLOPURINOL:
                    self.assertEqual(
                        data[f"medallergy_{treatment}"],
                        True if getattr(self.ultaid_no_user, f"{treatment.lower()}_allergy") else "",
                    )
            self.assertIn(f"medallergy_{UltChoices.ALLOPURINOL}", data)
            self.assertTrue(data[f"medallergy_{UltChoices.ALLOPURINOL}"])
            if data.get("hlab5801-value", None):
                self.assertEqual(
                    data["hlab5801-value"],
                    self.ultaid_no_user.hlab5801.value if self.ultaid_no_user.hlab5801 else False,
                )
            if data.get("baselinecreatinine-value", None):
                self.assertIn("dateofbirth-value", data)
                self.assertIn("gender-value", data)
            if data.get("dateofbirth-value", None) and data["dateofbirth-value"] != "":
                self.assertEqual(data["dateofbirth-value"], age_calc(self.ultaid_no_user.dateofbirth.value))
            self.assertIn("ethnicity-value", data)
            self.assertEqual(data["ethnicity-value"], (self.ultaid_no_user.ethnicity.value))
            if data.get("gender-value", None):
                self.assertEqual(data["gender-value"], self.ultaid_no_user.gender.value)

    def test__with_ultaid_with_otos(self):
        for _ in range(10):
            data = ultaid_data_factory(
                ultaid=self.ultaid_no_user,
                otos={"dateofbirth": 50, "ethnicity": Ethnicitys.CAUCASIANAMERICAN, "gender": Genders.FEMALE},
            )
            assert isinstance(data, dict)
            for mh in ULTAID_MEDHISTORYS:
                self.assertIn(f"{mh}-value", data)
                self.assertEqual(
                    data[f"{mh}-value"],
                    True if getattr(self.ultaid_no_user, mh.lower()) else False if mh in self.bool_mhs else "",
                )
            for treatment in UltChoices.values:
                self.assertIn(f"medallergy_{treatment}", data)
                self.assertEqual(
                    data[f"medallergy_{treatment}"],
                    True if getattr(self.ultaid_no_user, f"{treatment.lower()}_allergy") else "",
                )
            if data.get("hlab5801-value", None):
                self.assertEqual(
                    data["hlab5801-value"],
                    self.ultaid_no_user.hlab5801.value if self.ultaid_no_user.hlab5801 else False,
                )
            self.assertIn("dateofbirth-value", data)
            self.assertEqual(data["dateofbirth-value"], 50)
            self.assertIn("ethnicity-value", data)
            self.assertEqual(data["ethnicity-value"], Ethnicitys.CAUCASIANAMERICAN)
            self.assertIn("gender-value", data)
            self.assertEqual(data["gender-value"], Genders.FEMALE)


class TestUltAid(TestCase):
    """Tests for the create_ultaid function."""

    def test__without_user(self):
        for _ in range(10):
            ultaid = create_ultaid()
            self.assertIsInstance(ultaid, UltAid)
            self.assertIsNone(ultaid.user)
            self.assertTrue(hasattr(ultaid, "medallergys_qs"))
            self.assertTrue(hasattr(ultaid, "medhistorys_qs"))
            self.assertTrue(hasattr(ultaid, "dateofbirth"))
            if getattr(ultaid, "dateofbirth", None):
                self.assertTrue(isinstance(ultaid.dateofbirth, DateOfBirth))
            self.assertTrue(getattr(ultaid, "ethnicity"))
            self.assertTrue(isinstance(ultaid.ethnicity, Ethnicity))
            self.assertTrue(hasattr(ultaid, "gender"))
            if getattr(ultaid, "gender", None):
                self.assertTrue(isinstance(ultaid.gender, Gender))
            self.assertTrue(hasattr(ultaid, "hlab5801"))
            if getattr(ultaid, "hlab5801", None):
                self.assertTrue(isinstance(ultaid.hlab5801, Hlab5801))

    def test__without_user_with_otos(self):
        for _ in range(10):
            dob = timezone.now() - timedelta(days=365 * 50)
            ultaid = create_ultaid(ethnicity=Ethnicitys.HANCHINESE, dateofbirth=dob, gender=Genders.FEMALE)
            self.assertIsInstance(ultaid, UltAid)
            self.assertIsNone(ultaid.user)
            self.assertTrue(hasattr(ultaid, "medallergys_qs"))
            self.assertTrue(hasattr(ultaid, "medhistorys_qs"))
            self.assertTrue(ultaid.dateofbirth)
            self.assertEqual(ultaid.dateofbirth.value, dob)
            self.assertTrue(ultaid.ethnicity)
            self.assertEqual(ultaid.ethnicity.value, Ethnicitys.HANCHINESE)
            self.assertTrue(ultaid.gender)
            self.assertEqual(ultaid.gender.value, Genders.FEMALE)
            self.assertTrue(hasattr(ultaid, "hlab5801"))
            if getattr(ultaid, "hlab5801", None):
                self.assertTrue(isinstance(ultaid.hlab5801, Hlab5801))

    def test__without_user_with_hlab5801(self):
        ultaid_none = create_ultaid(hlab5801=None)
        self.assertIsNone(ultaid_none.hlab5801)
        ultaid_false = create_ultaid(hlab5801=False)
        self.assertTrue(ultaid_false.hlab5801)
        self.assertFalse(ultaid_false.hlab5801.value)
        ultaid_true = create_ultaid(hlab5801=True)
        self.assertTrue(ultaid_true.hlab5801)
        self.assertTrue(ultaid_true.hlab5801.value)

    def test__without_user_ckd_no_ckddetail(self):
        ultaid = create_ultaid(mhs=[MedHistoryTypes.CKD], ckddetail=None)
        self.assertTrue(ultaid.ckd)
        self.assertFalse(ultaid.ckddetail)

    def test__without_user_ckd_and_ckddetail(self):
        ultaid = create_ultaid(mhs=[MedHistoryTypes.CKD], ckddetail={"stage": Stages.THREE})
        self.assertTrue(ultaid.ckd)
        self.assertTrue(ultaid.ckddetail)

    def test__without_user_ckd_and_ckddetail_kwargs(self):
        pass
