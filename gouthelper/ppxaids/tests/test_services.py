from datetime import timedelta
from decimal import Decimal

import pytest  # type: ignore
from django.db import connection  # type: ignore
from django.test import TestCase  # type: ignore
from django.test.utils import CaptureQueriesContext  # type: ignore
from django.utils import timezone  # type: ignore

from ...dateofbirths.helpers import age_calc
from ...dateofbirths.tests.factories import DateOfBirthFactory
from ...defaults.models import DefaultPpxTrtSettings
from ...defaults.tests.factories import DefaultPpxTrtSettingsFactory
from ...labs.models import BaselineCreatinine
from ...labs.tests.factories import BaselineCreatinineFactory
from ...medhistorydetails.choices import Stages
from ...medhistorydetails.tests.factories import CkdDetailFactory
from ...medhistorys.choices import CVDiseases, MedHistoryTypes
from ...medhistorys.lists import OTHER_NSAID_CONTRAS, PPXAID_MEDHISTORYS
from ...medhistorys.tests.factories import CkdFactory
from ...treatments.choices import FlarePpxChoices, Freqs, NsaidChoices, Treatments, TrtTypes
from ...users.tests.factories import create_psp
from ..models import PpxAid
from ..selectors import ppxaid_user_qs, ppxaid_userless_qs
from ..services import PpxAidDecisionAid
from .factories import create_ppxaid

pytestmark = pytest.mark.django_db


class TestPpxAidMethods(TestCase):
    def setUp(self):
        medhistorys = [
            MedHistoryTypes.ANGINA,
            MedHistoryTypes.ANTICOAGULATION,
            MedHistoryTypes.BLEED,
            MedHistoryTypes.CHF,
            MedHistoryTypes.COLCHICINEINTERACTION,
            MedHistoryTypes.DIABETES,
            MedHistoryTypes.GASTRICBYPASS,
            MedHistoryTypes.HEARTATTACK,
            MedHistoryTypes.CKD,
        ]
        self.ppxaid = create_ppxaid(mhs=medhistorys, mas=[Treatments.COLCHICINE])
        if not self.ppxaid.baselinecreatinine:
            self.baselinecreatinine = BaselineCreatinineFactory(value=Decimal("2.20"), medhistory=self.ppxaid.ckd)
        self.decisionaid = PpxAidDecisionAid(qs=ppxaid_userless_qs(pk=self.ppxaid.pk))
        self.empty_ppxaid = create_ppxaid(mhs=[], mas=[])
        self.empty_decisionaid = PpxAidDecisionAid(qs=ppxaid_userless_qs(pk=self.empty_ppxaid.pk))

    def test__init_without_user(self):
        """Test the __init__() method when the QuerySet is a PpxAid without a user."""
        for ppxaid in PpxAid.objects.filter(user__isnull=True).all():
            with CaptureQueriesContext(connection) as context:
                ppxaid_qs = ppxaid_userless_qs(pk=ppxaid.pk).get()
                decisionaid = PpxAidDecisionAid(qs=ppxaid_qs)
            self.assertEqual(len(context.captured_queries), 4)  # 4 queries for medhistorys
            self.assertEqual(age_calc(ppxaid_qs.dateofbirth.value), decisionaid.age)
            self.assertEqual(ppxaid_qs.gender, decisionaid.gender)
            self.assertTrue(hasattr(decisionaid, "defaultsettings"))
            self.assertEqual(
                decisionaid.defaultsettings, DefaultPpxTrtSettings.objects.filter(user__isnull=True).get()
            )
            if ppxaid_qs.ckd:
                if hasattr(ppxaid_qs.ckd, "baselinecreatinine"):
                    self.assertEqual(ppxaid_qs.ckd.baselinecreatinine, decisionaid.baselinecreatinine)
                else:
                    self.assertIsNone(decisionaid.baselinecreatinine)
                if hasattr(ppxaid_qs.ckd, "ckddetail"):
                    self.assertEqual(ppxaid_qs.ckd.ckddetail, decisionaid.ckddetail)
                else:
                    self.assertIsNone(decisionaid.ckddetail)
            for medhistory in ppxaid_qs.medhistorys_qs:
                self.assertIn(medhistory, decisionaid.medhistorys)
            self.assertEqual(ppxaid, decisionaid.ppxaid)
            for medallergy in ppxaid_qs.medallergys_qs:
                self.assertIn(medallergy, decisionaid.medallergys)

    def test__init__with_user(self):
        """Test that __init__() assigns the correct attrs when the QuerySet is a user
        with related models."""

        ppxaid = create_ppxaid(user=True)
        if not ppxaid.user.ckd:
            del ppxaid.user.ckd
            CkdFactory(user=ppxaid.user)
        if not hasattr(ppxaid.user.ckd, "baselinecreatinine"):
            BaselineCreatinineFactory(medhistory=ppxaid.user.ckd)
        defaultppxtrtsettings = DefaultPpxTrtSettingsFactory(user=ppxaid.user)
        qs = ppxaid_user_qs(username=ppxaid.user.username)
        with self.assertNumQueries(3):
            # QuerySet is 3 queries because the user has a defaultppxtrtsettings
            qs = qs.get()
            decisionaid = PpxAidDecisionAid(qs=qs)
        self.assertTrue(hasattr(decisionaid, "ppxaid"))
        self.assertEqual(decisionaid.ppxaid, ppxaid)  # pylint: disable=no-member
        self.assertTrue(hasattr(decisionaid, "user"))
        self.assertEqual(decisionaid.user, ppxaid.user)
        self.assertTrue(hasattr(decisionaid, "dateofbirth"))
        self.assertEqual(decisionaid.dateofbirth, ppxaid.user.dateofbirth)
        self.assertTrue(decisionaid.age)
        self.assertEqual(decisionaid.age, age_calc(ppxaid.user.dateofbirth.value))
        self.assertTrue(hasattr(decisionaid, "defaultsettings"))
        self.assertEqual(decisionaid.defaultsettings, defaultppxtrtsettings)
        if hasattr(ppxaid.user, "gender"):
            self.assertEqual(decisionaid.gender, ppxaid.user.gender)
        self.assertTrue(hasattr(decisionaid, "medallergys"))
        self.assertEqual(decisionaid.medallergys, qs.medallergys_qs)
        self.assertTrue(hasattr(decisionaid, "medhistorys"))
        self.assertEqual(decisionaid.medhistorys, qs.medhistorys_qs)
        self.assertTrue(hasattr(decisionaid, "baselinecreatinine"))
        self.assertEqual(decisionaid.baselinecreatinine, BaselineCreatinine.objects.get(medhistory=ppxaid.user.ckd))
        self.assertTrue(hasattr(decisionaid, "ckddetail"))
        self.assertEqual(decisionaid.ckddetail, ppxaid.ckddetail)
        self.assertTrue(hasattr(decisionaid, "sideeffects"))
        self.assertEqual(decisionaid.sideeffects, None)

    def test__default_medhistorys(self):
        empty_defaults = self.empty_decisionaid.default_medhistorys
        self.assertEqual(len(empty_defaults), 0)
        ppxaid_medhistorys = [
            medhistory.medhistorytype
            for medhistory in self.empty_decisionaid.medhistorys
            if medhistory.medhistorytype in PPXAID_MEDHISTORYS
        ]
        for medhistory in [medhistory for medhistory in ppxaid_medhistorys if medhistory in PPXAID_MEDHISTORYS]:
            self.assertIn(medhistory.medhistorytype, [default.medhistorytype for default in empty_defaults])
        for default in empty_defaults:
            self.assertEqual(default.trttype, TrtTypes.PPX)
        defaults = self.empty_decisionaid.default_medhistorys
        self.assertEqual(len(defaults), 0)
        ppxaid_medhistorys = [
            medhistory.medhistorytype
            for medhistory in self.empty_decisionaid.medhistorys
            if medhistory.medhistorytype in PPXAID_MEDHISTORYS
        ]
        for medhistory in [medhistory for medhistory in ppxaid_medhistorys if medhistory in PPXAID_MEDHISTORYS]:
            self.assertIn(medhistory.medhistorytype, [default.medhistorytype for default in defaults])
        for default in defaults:
            self.assertEqual(default.trttype, TrtTypes.PPX)

    def test__default_trts(self):
        """Test that the default_trts property returns the correct QuerySet of DefaultTrt objects."""
        defaults = self.empty_decisionaid.default_trts
        for treatment in FlarePpxChoices.values:
            self.assertIn(treatment, [default.treatment for default in defaults])
        for default in defaults:
            self.assertEqual(default.trttype, TrtTypes.PPX)

    def test__baseline_methods_work_with_user(self):
        """Test that a PpxAid's options and recommendation work and are correct
        when the PpxAid has a user."""
        psp = create_psp(medhistorys=[], medallergys=[])
        # Create a PpxAid with a user that doesn't have any medhistorys or medallergys
        ppxaid = create_ppxaid(user=psp)
        # Test that the options and recommendation are correct
        self.assertIn(Treatments.NAPROXEN, ppxaid.options)
        self.assertIn(Treatments.COLCHICINE, ppxaid.options)
        self.assertIn(Treatments.PREDNISONE, ppxaid.options)
        self.assertIn(Treatments.NAPROXEN, ppxaid.recommendation)

    def test__baseline_methods_work_no_user(self):
        """Test that a basically empty PpxAid's options and recommendation work and are correct
        when it doesn't have a user."""
        # Create a PpxAid without any medhistorys or medallergys
        ppxaid = create_ppxaid(
            mhs=[],
            mas=[],
            dateofbirth=DateOfBirthFactory(value=timezone.now().date() - timedelta(days=365 * 50)),
        )

        # Test that the options and recommendation are correct
        self.assertIn(Treatments.NAPROXEN, ppxaid.options)
        self.assertIn(Treatments.COLCHICINE, ppxaid.options)
        self.assertIn(Treatments.PREDNISONE, ppxaid.options)
        self.assertIn(Treatments.NAPROXEN, ppxaid.recommendation)

    def test__process_nsaids_works_with_user(self):
        """Test that a PpxAid that has a user with a medhistory or medallergy that is a contraindication to NSAIDs
        does not include NSAIDs in the options or recommendation."""
        NSAID_CONTRAS = CVDiseases.values + OTHER_NSAID_CONTRAS + [MedHistoryTypes.CKD]
        # Iterate over the PpxAid's with a User and get the user's username
        for username in PpxAid.objects.filter(user__isnull=False).values_list("user__username", flat=True):
            # Iterate over the username and get the ppxaid_user_qs
            ppxaid_qs = ppxaid_user_qs(username=username).get()
            # Assign the ppxaid from the User
            ppxaid = ppxaid_qs.ppxaid

            # Check the queryset for MedHistorys or MedAllergys that are contraindications to NSAIDs
            if [mh for mh in ppxaid_qs.medhistorys_qs if mh.medhistorytype in NSAID_CONTRAS] or [
                ma for ma in ppxaid_qs.medallergys_qs if ma.treatment in NsaidChoices.values
            ]:
                # Test that the options and recommendation are correct and exclude NSAIDs
                for nsaid in NsaidChoices.values:
                    self.assertNotIn(nsaid, ppxaid.options)
                    if ppxaid.recommendation:
                        self.assertNotIn(nsaid, ppxaid.recommendation)
            else:
                # Test that the options and recommendation are correct and include NSAIDs
                for nsaid in NsaidChoices.values:
                    self.assertIn(nsaid, ppxaid.options)
                if ppxaid.recommendation:
                    self.assertEqual(NsaidChoices.NAPROXEN, ppxaid.recommendation[0])

    def test__process_nsaids_works_no_user(self):
        """Test that a PpxAid that has a medhistory or medallergy that is a contraindication to NSAIDs
        does not include NSAIDs in the options or recommendation."""
        # Create a PpxAid with a medhistory that is a contraindication to NSAIDs
        ppxaid = create_ppxaid(
            mhs=[MedHistoryTypes.HEARTATTACK],
            mas=[],
        )

        # Test that the options and recommendation are correct and exclude NSAIDs
        for nsaid in NsaidChoices.values:
            self.assertNotIn(nsaid, ppxaid.options)
            self.assertNotIn(nsaid, ppxaid.recommendation)

    def test__colchicine_dose_reduced_ckd_3(self):
        """Test that a PpxAid that has colchicine as an option alters the dose
        when indicated by the CKD stage."""
        # Create a PpxAid for which colchicine is an option
        ppxaid = create_ppxaid(mhs=[], mas=[])

        # Assert that colchicine is in the options dict

        self.assertIn(Treatments.COLCHICINE, ppxaid.options)

        # Assert that the dose and frequency are correct

        colch_dict = ppxaid.options[Treatments.COLCHICINE]
        self.assertEqual(Decimal("0.6"), colch_dict["dose"])
        self.assertEqual(Freqs.QDAY, colch_dict["freq"])

        # Add a CKD medhistory with a CkdDetail stage <= 3 to the PpxAid
        ckd = CkdFactory(ppxaid=ppxaid)
        CkdDetailFactory(medhistory=ckd, stage=Stages.THREE)

        # Update the PpxAid
        ppxaid.update_aid()

        # Refresh the ppxaid from the database in order to update the decisionaid field
        ppxaid.refresh_from_db()
        # Delete the aid_dict cached_property so that it will be recalculated
        del ppxaid.aid_dict

        # Test that the colchicine dosing is adjusted
        self.assertIn(Treatments.COLCHICINE, ppxaid.options)
        colch_dict = ppxaid.options[Treatments.COLCHICINE]
        self.assertEqual(Decimal("0.3"), colch_dict["dose"])
        self.assertEqual(Freqs.QDAY, colch_dict["freq"])

    def test__colchicine_freq_reduced_ckd_3_custom_user_settings(self):
        """Test that a PpxAid that has colchicine as an option alters the frequency
        of dosing when indicated by the CKD stage and custom DefaultPpxTrtSettings."""
        # Create a PpxAid for which colchicine is an option

        ppxaid = create_ppxaid(mhs=[], mas=[])

        # Assert that colchicine is in the options dict
        self.assertIn(Treatments.COLCHICINE, ppxaid.options)
        # Assert that the dose and frequency are correct
        colch_dict = ppxaid.options[Treatments.COLCHICINE]
        self.assertEqual(Decimal("0.6"), colch_dict["dose"])
        self.assertEqual(Freqs.QDAY, colch_dict["freq"])

        # Add a CKD medhistory with a CkdDetail stage <= 3 to the PpxAid
        ckd = CkdFactory(ppxaid=ppxaid)
        CkdDetailFactory(medhistory=ckd, stage=Stages.THREE)

        # Modify the GoutHelper default DefaultPpxTrtSettings to have colchicine
        # frequency be adjusted for CKD, not the dose
        default_ppx_trt_settings = DefaultPpxTrtSettings.objects.get()
        default_ppx_trt_settings.colch_dose_adjust = False
        default_ppx_trt_settings.save()

        # Update the PpxAid
        ppxaid.update_aid()

        # Refresh the ppxaid from the database in order to update the decisionaid field
        ppxaid.refresh_from_db()
        # Delete the aid_dict cached_property so that it will be recalculated
        del ppxaid.aid_dict

        # Test that the colchicine dosing frequency is adjusted rather than the dose
        self.assertIn(Treatments.COLCHICINE, ppxaid.options)
        colch_dict = ppxaid.options[Treatments.COLCHICINE]
        self.assertEqual(Decimal("0.6"), colch_dict["dose"])
        self.assertEqual(Freqs.QOTHERDAY, colch_dict["freq"])

    def test__update_updates_decisionaid_json(self):
        """Test that the update() method creates/updates the decisionaid field."""
        # Get a PpxAid without a user
        ppxaid = PpxAid.objects.filter(user__isnull=True).last()

        # Assert that the decisionaid field is empty
        self.assertFalse(ppxaid.decisionaid)
        self.assertEqual({}, ppxaid.decisionaid)

        # Update the PpxAid and refresh from the database
        ppxaid.update_aid()
        ppxaid.refresh_from_db()

        # Assert that the decisionaid field is not empty, should be a str because it's a JSONField
        self.assertTrue(isinstance(ppxaid.decisionaid, str))

    def test__aid_dict_returns_dict(self):
        """Test that the aid_dict property returns a dict with the correct keys."""
        # Set the decisionaid_dict
        decisionaid_dict = self.ppxaid.aid_dict

        # Test that it contains the correct keys
        self.assertTrue(isinstance(decisionaid_dict, dict))
        for treatment in FlarePpxChoices.values:
            self.assertIn(treatment, decisionaid_dict.keys())
        for key, val_dict in decisionaid_dict.items():
            self.assertIn(key, FlarePpxChoices)
            self.assertIn("dose", val_dict.keys())
            self.assertIn("freq", val_dict.keys())
