import random

import pytest  # type: ignore
from django.db import connection  # type: ignore
from django.db.models import QuerySet
from django.test import TestCase  # type: ignore
from django.test.utils import CaptureQueriesContext  # type: ignore

from ...dateofbirths.helpers import age_calc
from ...defaults.models import DefaultFlareTrtSettings, DefaultMedHistory, DefaultTrt
from ...defaults.selectors import defaults_defaultmedhistorys_trttype
from ...defaults.tests.factories import (
    DefaultColchicineFlareFactory,
    DefaultFlareTrtSettingsFactory,
    DefaultMedHistoryFactory,
)
from ...medallergys.tests.factories import MedAllergyFactory
from ...medhistorys.choices import Contraindications, MedHistoryTypes
from ...medhistorys.lists import FLAREAID_MEDHISTORYS
from ...treatments.choices import FlarePpxChoices, NsaidChoices, Treatments, TrtTypes
from ...utils.services import aids_dict_to_json
from ..models import FlareAid
from ..selectors import flareaid_user_qs, flareaid_userless_qs
from ..services import FlareAidDecisionAid
from .factories import create_flareaid

pytestmark = pytest.mark.django_db


class TestFlareAidMethods(TestCase):
    def setUp(self):
        # Create a FlareAids with Users and without for testing against
        self.fas_userless = []
        self.fas_user = []
        for _ in range(5):
            self.fas_userless.append(create_flareaid())
            self.fas_user.append(create_flareaid(user=True))

    def test__init_no_user(self):
        """Test that the __init__ method sets the attrs on the service class correctly
        when there is no user and that the custom settings are set correctly."""
        for fa in self.fas_userless:
            with CaptureQueriesContext(connection) as context:
                decisionaid = FlareAidDecisionAid(qs=flareaid_userless_qs(pk=fa.pk))
            self.assertEqual(len(context.captured_queries), 4)  # 3 queries for medhistorys
            self.assertEqual(age_calc(fa.dateofbirth.value), decisionaid.age)
            if hasattr(fa, "gender"):
                self.assertEqual(fa.gender, decisionaid.gender)
            else:
                self.assertIsNone(decisionaid.gender)
            if hasattr(fa, "ckddetail"):
                self.assertEqual(fa.ckddetail, decisionaid.ckddetail)
            else:
                self.assertIsNone(decisionaid.ckddetail)
            for mh in fa.medhistory_set.all():
                self.assertIn(mh, decisionaid.medhistorys)
            self.assertEqual(fa, decisionaid.flareaid)
            for ma in fa.medallergy_set.filter(treatment__in=FlarePpxChoices.values).all():
                self.assertIn(ma, decisionaid.medallergys)
            self.assertIsNone(decisionaid.user)
            self.assertIsNone(decisionaid.sideeffects)
            self.assertTrue(isinstance(decisionaid.defaultsettings, DefaultFlareTrtSettings))
            self.assertIsNone(decisionaid.defaultsettings.user)  # type: ignore

    def test__init_with_user(self):
        """Test that the __init__ method sets the attrs on the service class correctly
        when there is a user and that the custom settings are set correctly."""
        for fa in self.fas_user:
            custom_settings = DefaultFlareTrtSettingsFactory(user=fa.user)
            with CaptureQueriesContext(connection) as context:
                decisionaid = FlareAidDecisionAid(qs=flareaid_user_qs(username=fa.user.username))
            self.assertEqual(len(context.captured_queries), 3)
            self.assertEqual(age_calc(fa.user.dateofbirth.value), decisionaid.age)
            if hasattr(fa.user, "gender"):
                self.assertEqual(fa.user.gender, decisionaid.gender)
            else:
                self.assertIsNone(decisionaid.gender)
            for mh in fa.user.medhistory_set.filter(medhistorytype__in=FLAREAID_MEDHISTORYS).all():
                self.assertIn(mh, decisionaid.medhistorys)
                if mh.medhistorytype == MedHistoryTypes.CKD:
                    self.assertEqual(mh.ckddetail, decisionaid.ckddetail)
            for ma in fa.user.medallergy_set.filter(treatment__in=FlarePpxChoices.values).all():
                self.assertIn(ma, decisionaid.medallergys)
            self.assertIsNone(decisionaid.sideeffects)
            self.assertEqual(decisionaid.defaultsettings, custom_settings)

    def test__init_with_flareaid_with_user(self):
        """Test that when the Class Method is called with a FlareAid that has a User,
        the __init__ method removes attrs from the FlareAid after setting them
        on the service class in order to avoid saving a FlareAid with a user as well as
        onetoones that violate the model CheckConstraint (i.e. dateofbirth, gender)."""
        for fa in self.fas_user:
            fa_user = flareaid_user_qs(username=fa.user.username).get()
            fa = fa_user.flareaid
            fa.dateofbirth = fa.user.dateofbirth
            fa.gender = fa.user.gender if hasattr(fa.user, "gender") else None
            fa.medallergys_qs = fa_user.medallergys_qs
            fa.medhistorys_qs = fa_user.medhistorys_qs
            decisionaid = FlareAidDecisionAid(qs=fa)
            self.assertEqual(decisionaid.dateofbirth, fa.user.dateofbirth)
            if hasattr(fa.user, "gender"):
                self.assertEqual(decisionaid.gender, fa.user.gender)
            else:
                self.assertIsNone(decisionaid.gender)
            self.assertIsNone(decisionaid.flareaid.dateofbirth)
            self.assertIsNone(decisionaid.flareaid.gender)

    def test__init_with_DecisionAid_object(self):
        """Test that __init__() still sets the attrs correctly when called with an object, typically
        by an evaluated QuerySet or decorated with a _qs attrs from a view."""
        for fa in self.fas_user:
            custom_settings = DefaultFlareTrtSettingsFactory(user=fa.user)
            with CaptureQueriesContext(connection) as context:
                decisionaid = FlareAidDecisionAid(qs=flareaid_user_qs(username=fa.user.username).get())
            self.assertEqual(len(context.captured_queries), 3)
            self.assertEqual(age_calc(fa.user.dateofbirth.value), decisionaid.age)
            if hasattr(fa.user, "gender"):
                self.assertEqual(fa.user.gender, decisionaid.gender)
            else:
                self.assertIsNone(decisionaid.gender)
            for mh in fa.user.medhistory_set.filter(medhistorytype__in=FLAREAID_MEDHISTORYS).all():
                self.assertIn(mh, decisionaid.medhistorys)
                if mh.medhistorytype == MedHistoryTypes.CKD:
                    self.assertEqual(mh.ckddetail, decisionaid.ckddetail)
            for ma in fa.user.medallergy_set.filter(treatment__in=FlarePpxChoices.values).all():
                self.assertIn(ma, decisionaid.medallergys)
            self.assertIsNone(decisionaid.sideeffects)
            self.assertEqual(decisionaid.defaultsettings, custom_settings)

    def test__init_with_wrong_Type_raises_TypeError(self):
        with self.assertRaises(TypeError):
            FlareAidDecisionAid(qs="Hogwarts is not the place for me...")

    def test__defaulttrts_no_user(self):
        """Check that the default_trts property returns a QuerySet of DefaultTrts that is correct."""
        fa = FlareAid.objects.filter(user=None).last()
        default_trt_qs = DefaultTrt.objects.filter(
            user=None,
            trttype=TrtTypes.FLARE,
            treatment__in=FlarePpxChoices.values,
        ).all()
        da = FlareAidDecisionAid(qs=flareaid_userless_qs(pk=fa.pk))
        default_trts = da.default_trts
        self.assertTrue(isinstance(default_trts, QuerySet))
        for default in list(default_trts):
            self.assertTrue(isinstance(default, DefaultTrt))
            self.assertIsNone(default.user)
            self.assertIn(default, default_trt_qs)
        for flare_trt in FlarePpxChoices:
            self.assertTrue(default.treatment for default in list(default_trts) if default.treatment == flare_trt)
        self.assertEqual(len(default_trts), len(default_trt_qs))

    def test__defaulttrts_with_user(self):
        """Check that the default_trts property returns a QuerySet of DefaultTrts that is correct and filtered
        by the FlareAid or it's users default_trts."""
        fa = FlareAid.objects.filter(user__isnull=False).last()
        custom_colchicine_default = DefaultColchicineFlareFactory(user=fa.user)
        da = FlareAidDecisionAid(qs=flareaid_user_qs(username=fa.user.username))
        self.assertEqual(len(da.default_trts), 9)
        self.assertIn(custom_colchicine_default, da.default_trts)

    def test__defaultmedhistorys_no_user(self):
        """Test that the default_medhistorys property returns a QuerySet of DefaultMedHistorys
        that is correct and filtered by trttype=FLARE and the FlareAid or it's users medhistorys."""
        for fa in self.fas_userless:
            da = FlareAidDecisionAid(qs=flareaid_userless_qs(pk=fa.pk))
            default_mhs = da.default_medhistorys
            fa_mhtypes = [
                mh.medhistorytype for mh in fa.medhistory_set.filter(medhistorytype__in=FLAREAID_MEDHISTORYS).all()
            ]
            mhs_qs = DefaultMedHistory.objects.filter(
                user=None,
                trttype=TrtTypes.FLARE,
                medhistorytype__in=fa_mhtypes,
                treatment__in=FlarePpxChoices.values,
            ).all()
            for default in list(default_mhs):
                self.assertTrue(isinstance(default, DefaultMedHistory))
                self.assertIsNone(default.user)
                self.assertIn(default.medhistorytype, fa_mhtypes)
                self.assertIn(default, mhs_qs)
                self.assertNotEqual(default.medhistorytype, MedHistoryTypes.DIABETES)
                self.assertNotEqual(default.medhistorytype, MedHistoryTypes.GOUT)
            self.assertEqual(len(default_mhs), len(mhs_qs))

    def test__defaultmedhistorys_with_user(self):
        """Test that the default_medhistorys property returns a QuerySet of DefaultMedHistorys
        that is correct and filtered by trttype=FLARE and the FlareAid or it's users medhistorys."""
        for fa in self.fas_user:
            da = FlareAidDecisionAid(qs=flareaid_user_qs(username=fa.user.username))
            custom_default = DefaultMedHistoryFactory(
                user=fa.user,
                medhistorytype=random.choice(
                    [
                        mh.medhistorytype
                        for mh in fa.user.medhistory_set.filter(medhistorytype__in=FLAREAID_MEDHISTORYS).all()
                    ]
                ),
                treatment=Treatments.COLCHICINE,
                trttype=DefaultMedHistory.TrtTypes.FLARE,
            )
            default_mhs = da.default_medhistorys
            fa_mhs = fa.user.medhistory_set.filter(medhistorytype__in=FLAREAID_MEDHISTORYS).all()
            fa_mhtypes = [mh.medhistorytype for mh in fa_mhs]
            mhs_qs = defaults_defaultmedhistorys_trttype(fa_mhs, TrtTypes.FLARE, fa.user)
            for default in list(default_mhs):
                self.assertTrue(isinstance(default, DefaultMedHistory))
                self.assertIn(default.medhistorytype, fa_mhtypes)
                self.assertIn(default, mhs_qs)
            self.assertIn(custom_default, default_mhs)
            self.assertEqual(len(default_mhs), len(mhs_qs))

    def test___create_trts_dict(self):
        """Test that the _create_trts_dict method returns a dict with the correct keys and values."""
        da = FlareAidDecisionAid(qs=flareaid_userless_qs(pk=FlareAid.objects.filter(user__isnull=True).last().pk))
        trts_dict = da._create_trts_dict()  # pylint: disable=w0212
        self.assertTrue(isinstance(trts_dict, dict))
        for trt in FlarePpxChoices:
            self.assertIn(trt, trts_dict)
            self.assertTrue(isinstance(trts_dict[trt], dict))

    def test__decision_aid_dict_created(self):
        """Test that the _create_decisionaid_dict method returns a dict with the correct keys and values."""
        da = FlareAidDecisionAid(qs=flareaid_userless_qs(pk=FlareAid.objects.filter(user__isnull=True).last().pk))
        decisionaid_dict = da._create_decisionaid_dict()  # pylint: disable=w0212
        self.assertTrue(isinstance(decisionaid_dict, dict))
        for trt in FlarePpxChoices:
            self.assertIn(trt, decisionaid_dict)

    def test___create_decisionaid_dict_aids_process_medhistorys(self):
        """Test that the _create_decisionaid_dict method sets the contra value to True for each treatment
        that has a medhistory that contraindicates it."""
        for fa in self.fas_userless:
            da = FlareAidDecisionAid(qs=flareaid_userless_qs(pk=fa.pk))
            decisionaid_dict = da._create_decisionaid_dict()  # pylint: disable=w0212
            defaults = list(da.default_medhistorys)
            for default in defaults:
                if default.contraindication != Contraindications.DOSEADJ:
                    self.assertTrue(decisionaid_dict[default.treatment]["contra"])

    def test___create_decisionaid_dict_aids_process_medallergys(self):
        """Test that the _create_decisionaid_dict method sets the contra value to True for each treatment
        that has a medallergy that contraindicates it."""
        for fa in self.fas_userless:
            da = FlareAidDecisionAid(qs=flareaid_userless_qs(pk=fa.pk))
            decisionaid_dict = da._create_decisionaid_dict()  # pylint: disable=w0212
            for medallergy in da.medallergys:
                self.assertTrue(decisionaid_dict[medallergy.treatment]["contra"])

    def test__nsaids_equivalent(self):
        """Test that for the DecisionAid, if the user has custom settings that set nsaids_equivalent to True,
        the decisionaid_dict will contraindicate all NSAIDs together."""
        medallergy = MedAllergyFactory(treatment=Treatments.IBUPROFEN)
        flareaid = create_flareaid(mas=[medallergy])
        decisionaid = FlareAidDecisionAid(qs=flareaid_userless_qs(pk=flareaid.pk))
        decisionaid_dict = decisionaid._create_decisionaid_dict()  # pylint: disable=w0212
        for nsaid in NsaidChoices:
            self.assertTrue(decisionaid_dict[nsaid]["contra"])

    def test__nsaids_not_equivalent(self):
        """Test that for the DecisionAid, if the user has custom settings that set nsaids_equivalent to False,
        the decisionaid_dict will contraindicate each NSAID independently. Clinical note: this is probably not a good
        practice to default to."""
        DefaultFlareTrtSettings.objects.filter(user=None).update(nsaids_equivalent=False)
        medallergy = MedAllergyFactory(treatment=Treatments.IBUPROFEN)
        flareaid = create_flareaid(mas=[medallergy], mhs=[])
        decisionaid = FlareAidDecisionAid(qs=flareaid_userless_qs(pk=flareaid.pk))
        decisionaid_dict = decisionaid._create_decisionaid_dict()  # pylint: disable=w0212
        for nsaid in NsaidChoices:
            if nsaid == NsaidChoices.IBUPROFEN:
                self.assertTrue(decisionaid_dict[nsaid]["contra"])
            else:
                self.assertFalse(decisionaid_dict[nsaid]["contra"])

    def test__steroids_equivalent(self):
        """Test that for the DecisionAid, if the user has custom settings that set steroids_equivalent to True,
        the decisionaid_dict will contraindicate steroids together."""
        medallergy = MedAllergyFactory(treatment=Treatments.METHYLPREDNISOLONE)
        flareaid = create_flareaid(mas=[medallergy], mhs=[])
        decisionaid = FlareAidDecisionAid(qs=flareaid_userless_qs(pk=flareaid.pk))
        decisionaid_dict = decisionaid._create_decisionaid_dict()  # pylint: disable=w0212
        self.assertTrue(decisionaid_dict[Treatments.METHYLPREDNISOLONE]["contra"])
        self.assertTrue(decisionaid_dict[Treatments.PREDNISONE]["contra"])

    def test__custom_settings_for_steroids_not_equivalent(self):
        """Test that for the DecisionAid, if the user has custom settings that set steroids_equivalent to False,
        the decisionaid_dict will contraindicate steroids independently. Clinical note: this is probably not a good
        practice to default to."""
        DefaultFlareTrtSettings.objects.filter(user=None).update(steroids_equivalent=False)
        medallergy = MedAllergyFactory(treatment=Treatments.METHYLPREDNISOLONE)
        flareaid = create_flareaid(mas=[medallergy])
        decisionaid = FlareAidDecisionAid(qs=flareaid_userless_qs(pk=flareaid.pk))
        decisionaid_dict = decisionaid._create_decisionaid_dict()  # pylint: disable=w0212
        self.assertTrue(decisionaid_dict[Treatments.METHYLPREDNISOLONE]["contra"])
        self.assertFalse(decisionaid_dict[Treatments.PREDNISONE]["contra"])

    def test__save_trt_dict_to_decisionaid_saves(self):
        """Test that the _save_trt_dict_to_decisionaid method saves the decisionaid field as a JSON string.
        Also test that the decisionaid field is an empty dict, as this is the default for the field."""
        fa_user = flareaid_user_qs(username=FlareAid.objects.filter(user__isnull=False).last().user.username).get()
        fa = fa_user.flareaid
        da = FlareAidDecisionAid(qs=fa_user)
        da_dict = da._create_decisionaid_dict()  # pylint: disable=w0212, line-too-long # noqa: E501
        da._save_trt_dict_to_decisionaid(da_dict, commit=True)  # pylint: disable=w0212, line-too-long # noqa: E501
        # Assert that the decisionaid field is a str
        self.assertTrue(isinstance(fa.decisionaid, str))
        self.assertEqual(aids_dict_to_json(da_dict), fa.decisionaid)

    def test__save_trt_dict_to_decisionaid_commit_False_doesnt_save(self):
        """Test that the _save_trt_dict_to_decisionaid method doesn't save the decisionaid field
        when commit=False."""
        fa = flareaid_userless_qs(
            pk=FlareAid.objects.filter(user__isnull=True).values_list("pk", flat=True).last()
        ).get()
        da = FlareAidDecisionAid(qs=fa)
        da_dict = da._create_decisionaid_dict()  # pylint: disable=w0212, line-too-long # noqa: E501
        da._save_trt_dict_to_decisionaid(da_dict, commit=False)  # pylint: disable=w0212, line-too-long # noqa: E501
        # Assert that the decisionaid field is an empty dict, as this is the default for the field
        self.assertTrue(isinstance(fa.decisionaid, str))
        fa.refresh_from_db()
        self.assertFalse(fa.decisionaid)

    def test__update(self):
        """Test that update works by checking that it populates the FlareAid's decisionaid field."""
        fa = FlareAid.objects.filter(user__isnull=False).last()
        da = FlareAidDecisionAid(qs=flareaid_user_qs(username=fa.user.username))
        self.assertFalse(fa.decisionaid)
        da._update()  # pylint: disable=w0212
        fa.refresh_from_db()
        self.assertTrue(fa.decisionaid)
