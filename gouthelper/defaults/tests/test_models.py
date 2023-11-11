from datetime import timedelta

import pytest
from django.db.utils import IntegrityError  # type: ignore
from django.forms.models import model_to_dict
from django.test import TestCase

from ...medhistorys.choices import Contraindications
from ...treatments.choices import Treatments, TrtTypes
from ...users.tests.factories import UserFactory
from ..models import DefaultMedHistory, DefaultTrt
from .factories import (
    DefaultAllopurinolFactory,
    DefaultCelecoxibFlareFactory,
    DefaultColchicineFlareFactory,
    DefaultFebuxostatFactory,
    DefaultMedHistoryFactory,
    DefaultNaproxenPpxFactory,
)

pytestmark = pytest.mark.django_db


class TestDefaultMedHistory(TestCase):
    def setUp(self):
        self.user = UserFactory()

    def test___str__(self):
        # Get one of the DefaultMedHistory objects
        default = DefaultMedHistory.objects.last()
        # Assert that __str__ returns the expected value
        self.assertEqual(
            default.__str__(),
            f"{default.medhistorytype.lower().capitalize()}: \
{Treatments(default.treatment).label} ({TrtTypes(default.trttype).label}), \
Contraindication: {Contraindications(default.contraindication).label}",
        )

    def test__unique_user_default_constraint(self):
        default = DefaultMedHistoryFactory(user=self.user, treatment=Treatments.ALLOPURINOL, trttype=TrtTypes.ULT)
        with self.assertRaises(IntegrityError):
            DefaultMedHistoryFactory(
                user=self.user,
                medhistorytype=default.medhistorytype,
                treatment=default.treatment,
                trttype=default.trttype,
                contraindication=default.contraindication,
            )

    def test__contraindication_valid_constraint(self):
        with self.assertRaises(IntegrityError):
            DefaultMedHistoryFactory(
                user=self.user,
                medhistorytype=DefaultMedHistory.MedHistoryTypes.GOUT,
                treatment=DefaultMedHistory.Treatments.ALLOPURINOL,
                trttype=DefaultMedHistory.TrtTypes.ULT,
                contraindication=55,
            )

    def test__medhistorytype_valid_constraint(self):
        with self.assertRaises(IntegrityError):
            DefaultMedHistoryFactory(
                user=self.user,
                medhistorytype="Jungle wart",
                treatment=DefaultMedHistory.Treatments.ALLOPURINOL,
                trttype=DefaultMedHistory.TrtTypes.ULT,
            )

    def test__treatment_valid_constraint(self):
        with self.assertRaises(IntegrityError):
            DefaultMedHistoryFactory(
                user=self.user,
                medhistorytype=DefaultMedHistory.MedHistoryTypes.GOUT,
                treatment="Jungle mushroom",
                trttype=DefaultMedHistory.TrtTypes.ULT,
            )

    def test__trttype_valid_constraint(self):
        with self.assertRaises(IntegrityError):
            DefaultMedHistoryFactory(
                user=self.user,
                medhistorytype=DefaultMedHistory.MedHistoryTypes.GOUT,
                treatment=DefaultMedHistory.Treatments.ALLOPURINOL,
                trttype=233,
            )

    # Test that violating each of the subconstraints raises an IntegrityError
    def test__treatment_trttype_valid_constraint_colchicine(self):
        with self.assertRaises(IntegrityError):
            DefaultMedHistoryFactory(
                user=self.user,
                medhistorytype=DefaultMedHistory.MedHistoryTypes.GOUT,
                treatment=DefaultMedHistory.Treatments.COLCHICINE,
                trttype=DefaultMedHistory.TrtTypes.ULT,
            )

    def test__treatment_trttype_valid_constraint_celecoxib(self):
        with self.assertRaises(IntegrityError):
            DefaultMedHistoryFactory(
                user=self.user,
                medhistorytype=DefaultMedHistory.MedHistoryTypes.GOUT,
                treatment=DefaultMedHistory.Treatments.CELECOXIB,
                trttype=DefaultMedHistory.TrtTypes.ULT,
            )

    def test__treatment_trttype_valid_constraint_prednisone(self):
        with self.assertRaises(IntegrityError):
            DefaultMedHistoryFactory(
                user=self.user,
                medhistorytype=DefaultMedHistory.MedHistoryTypes.GOUT,
                treatment=DefaultMedHistory.Treatments.PREDNISONE,
                trttype=DefaultMedHistory.TrtTypes.ULT,
            )

    def test__treatment_trttype_valid_constraint_methylprednisolone(self):
        with self.assertRaises(IntegrityError):
            DefaultMedHistoryFactory(
                user=self.user,
                medhistorytype=DefaultMedHistory.MedHistoryTypes.GOUT,
                treatment=DefaultMedHistory.Treatments.METHYLPREDNISOLONE,
                trttype=DefaultMedHistory.TrtTypes.ULT,
            )

    def test__treatment_trttype_valid_constraint_ibuprofen(self):
        with self.assertRaises(IntegrityError):
            DefaultMedHistoryFactory(
                user=self.user,
                medhistorytype=DefaultMedHistory.MedHistoryTypes.GOUT,
                treatment=DefaultMedHistory.Treatments.IBUPROFEN,
                trttype=DefaultMedHistory.TrtTypes.ULT,
            )

    def test__treatment_trttype_valid_constraint_diclofenac(self):
        with self.assertRaises(IntegrityError):
            DefaultMedHistoryFactory(
                user=self.user,
                medhistorytype=DefaultMedHistory.MedHistoryTypes.GOUT,
                treatment=DefaultMedHistory.Treatments.DICLOFENAC,
                trttype=DefaultMedHistory.TrtTypes.ULT,
            )

    def test__treatment_trttype_valid_constraint_indomethacin(self):
        with self.assertRaises(IntegrityError):
            DefaultMedHistoryFactory(
                user=self.user,
                medhistorytype=DefaultMedHistory.MedHistoryTypes.GOUT,
                treatment=DefaultMedHistory.Treatments.INDOMETHACIN,
                trttype=DefaultMedHistory.TrtTypes.ULT,
            )

    def test__treatment_trttype_valid_constraint_meloxicam(self):
        with self.assertRaises(IntegrityError):
            DefaultMedHistoryFactory(
                user=self.user,
                medhistorytype=DefaultMedHistory.MedHistoryTypes.GOUT,
                treatment=DefaultMedHistory.Treatments.MELOXICAM,
                trttype=DefaultMedHistory.TrtTypes.ULT,
            )

    def test__treatment_trttype_valid_constraint_allopurinol_ppx(self):
        with self.assertRaises(IntegrityError):
            DefaultMedHistoryFactory(
                user=self.user,
                medhistorytype=DefaultMedHistory.MedHistoryTypes.GOUT,
                treatment=DefaultMedHistory.Treatments.ALLOPURINOL,
                trttype=DefaultMedHistory.TrtTypes.PPX,
            )

    def test__treatment_trttype_valid_constraint_allopurinol_flare(self):
        with self.assertRaises(IntegrityError):
            DefaultMedHistoryFactory(
                user=self.user,
                medhistorytype=DefaultMedHistory.MedHistoryTypes.GOUT,
                treatment=DefaultMedHistory.Treatments.ALLOPURINOL,
                trttype=DefaultMedHistory.TrtTypes.FLARE,
            )

    def test__treatment_trttype_valid_constraint_febuxostat_ppx(self):
        with self.assertRaises(IntegrityError):
            DefaultMedHistoryFactory(
                user=self.user,
                medhistorytype=DefaultMedHistory.MedHistoryTypes.GOUT,
                treatment=DefaultMedHistory.Treatments.FEBUXOSTAT,
                trttype=DefaultMedHistory.TrtTypes.PPX,
            )

    def test__treatment_trttype_valid_constraint_febuxostat_flare(self):
        with self.assertRaises(IntegrityError):
            DefaultMedHistoryFactory(
                user=self.user,
                medhistorytype=DefaultMedHistory.MedHistoryTypes.GOUT,
                treatment=DefaultMedHistory.Treatments.FEBUXOSTAT,
                trttype=DefaultMedHistory.TrtTypes.FLARE,
            )

    def test__treatment_trttype_valid_constraint_probenecid_ppx(self):
        with self.assertRaises(IntegrityError):
            DefaultMedHistoryFactory(
                user=self.user,
                medhistorytype=DefaultMedHistory.MedHistoryTypes.GOUT,
                treatment=DefaultMedHistory.Treatments.PROBENECID,
                trttype=DefaultMedHistory.TrtTypes.PPX,
            )

    def test__treatment_trttype_valid_constraint_probenecid_flare(self):
        with self.assertRaises(IntegrityError):
            DefaultMedHistoryFactory(
                user=self.user,
                medhistorytype=DefaultMedHistory.MedHistoryTypes.GOUT,
                treatment=DefaultMedHistory.Treatments.PROBENECID,
                trttype=DefaultMedHistory.TrtTypes.FLARE,
            )


class TestDefaultTrt(TestCase):
    def setUp(self):
        self.user = UserFactory()

    def test_get_allopurinol_defaults(self):
        default = DefaultTrt.objects.get(
            user=None,
            trttype=DefaultTrt.TrtTypes.ULT,
            treatment=DefaultTrt.Treatments.ALLOPURINOL,
        )
        default_dict = default.get_defaults()
        assert isinstance(default_dict, dict)

    def test___str__(self):
        default = DefaultTrt.objects.last()
        self.assertEqual(
            default.__str__(),
            f"Default {default.Treatments(default.treatment).label} \
{default.TrtTypes(default.trttype).label}",
        )

    # Test constraints
    def test__unique_user_trt_constraint(self):
        default = DefaultFebuxostatFactory(user=self.user)
        with self.assertRaisesMessage(
            IntegrityError,
            "defaults_defaulttrt_user_trt",
        ):
            model_fields = model_to_dict(default)
            model_fields.pop("user")
            DefaultTrt.objects.create(
                user=self.user,
                **model_fields,
            )

    def test__unique_trt_constraint(self):
        default = DefaultTrt.objects.last()
        with self.assertRaisesMessage(
            IntegrityError,
            "defaults_defaulttrt_gouthelper_default",
        ):
            model_fields = model_to_dict(default)
            model_fields.pop("user")
            DefaultTrt.objects.create(
                user=None,
                **model_fields,
            )

    def test__freq_valid_constraint(self):
        default = DefaultCelecoxibFlareFactory(user=self.user)
        with self.assertRaisesMessage(
            IntegrityError,
            "defaults_defaulttrt_freq_valid",
        ):
            fields = model_to_dict(default)
            fields.pop("user")
            fields["freq"] = 999
            DefaultTrt.objects.create(
                **fields,
            )

    def test__freq2_valid_constraint(self):
        default = DefaultColchicineFlareFactory(user=self.user)
        with self.assertRaisesMessage(
            IntegrityError,
            "defaults_defaulttrt_freq2_valid",
        ):
            default.freq2 = 999
            default.save()

    def test__freq3_valid_constraint(self):
        default = DefaultColchicineFlareFactory(user=self.user)
        with self.assertRaisesMessage(
            IntegrityError,
            "defaults_defaulttrt_freq3_valid",
        ):
            default.freq3 = 999
            default.save()

    def test__duration_valid_constraint_ult(self):
        allopurinol = DefaultAllopurinolFactory(user=self.user)
        with self.assertRaisesMessage(
            IntegrityError,
            "defaults_defaulttrt_duration_valid",
        ):
            allopurinol.duration = timedelta(days=999)
            allopurinol.save()

    def test__duration_valid_constraint_ppx(self):
        naproxen = DefaultNaproxenPpxFactory(user=self.user)
        with self.assertRaisesMessage(
            IntegrityError,
            "defaults_defaulttrt_duration_valid",
        ):
            naproxen.duration = timedelta(days=999)
            naproxen.save()

    def test__duration_valid_constraint_flare(self):
        colchicine = DefaultColchicineFlareFactory(user=self.user)
        with self.assertRaisesMessage(
            IntegrityError,
            "defaults_defaulttrt_duration_valid",
        ):
            colchicine.duration = None
            colchicine.save()

    def test__duration2_valid_constraint_ult(self):
        allopurinol = DefaultAllopurinolFactory(user=self.user)
        with self.assertRaisesMessage(
            IntegrityError,
            "defaults_defaulttrt_duration2_valid",
        ):
            allopurinol.duration2 = timedelta(days=999)
            allopurinol.save()

    def test__duration2_valid_constraint_ppx(self):
        naproxen = DefaultNaproxenPpxFactory(user=self.user)
        with self.assertRaisesMessage(
            IntegrityError,
            "defaults_defaulttrt_duration2_valid",
        ):
            naproxen.duration2 = timedelta(days=999)
            naproxen.save()

    def test__duration3_valid_constraint_ult(self):
        allopurinol = DefaultAllopurinolFactory(user=self.user)
        with self.assertRaisesMessage(
            IntegrityError,
            "defaults_defaulttrt_duration3_valid",
        ):
            allopurinol.duration3 = timedelta(days=999)
            allopurinol.save()

    def test__duration3_valid_constraint_ppx(self):
        naproxen = DefaultNaproxenPpxFactory(user=self.user)
        with self.assertRaisesMessage(
            IntegrityError,
            "defaults_defaulttrt_duration3_valid",
        ):
            naproxen.duration3 = timedelta(days=999)
            naproxen.save()

    def test__doses_under_max_dose_constraint_ult(self):
        allopurinol = DefaultAllopurinolFactory(user=self.user)
        with self.assertRaisesMessage(IntegrityError, "defaults_defaulttrt_doses_under_max_dose"):
            allopurinol.dose = 999
            allopurinol.save()

    def test__doses_under_max_dose_constraint_ppx(self):
        naproxen = DefaultNaproxenPpxFactory(user=self.user)
        with self.assertRaisesMessage(IntegrityError, "defaults_defaulttrt_doses_under_max_dose"):
            naproxen.dose = 999
            naproxen.save()

    def test__doses_under_max_dose_constraint_flare(self):
        colchicine = DefaultColchicineFlareFactory(user=self.user)
        # Assert that the error message contains the correct value
        with self.assertRaisesMessage(
            IntegrityError,
            "defaults_defaulttrt_doses_under_max_dose",
        ):
            colchicine.dose2 = 999
            colchicine.save()

    # TODO: Write tests for dosing / treatment -specific constraints
