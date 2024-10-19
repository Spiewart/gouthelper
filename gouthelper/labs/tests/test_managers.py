from django.test import TestCase

from ...flares.tests.factories import create_flare
from ...medhistorys.tests.factories import CkdFactory
from ...ppxs.tests.factories import create_ppx
from ...users.tests.factories import create_psp
from ..choices import LowerLimits, Units, UpperLimits
from ..models import BaselineCreatinine, Urate
from .factories import UrateFactory


class CreatinineManagerTestCase(TestCase):
    def test_get_queryset(self):
        # Count baselinecreatinine objects using the manager
        bc_count = BaselineCreatinine.objects.count()

        # Create some Creatinine objects
        BaselineCreatinine.objects.create(medhistory=CkdFactory(), value=1.0)
        BaselineCreatinine.objects.create(medhistory=CkdFactory(), value=2.0)
        BaselineCreatinine.objects.create(medhistory=CkdFactory(), value=3.0)

        # Get the queryset using the manager
        queryset = BaselineCreatinine.objects.get_queryset()

        # Assert that the queryset contains all Creatinine objects
        self.assertEqual(queryset.count(), bc_count + 3)

    def test_create(self):
        # Count baselinecreatinine objects using the manager
        bc_count = BaselineCreatinine.objects.count()

        # Create a Creatinine object using the manager
        BaselineCreatinine.objects.create(medhistory=CkdFactory(), value=1.5)

        # Assert that the object was created
        self.assertEqual(BaselineCreatinine.objects.count(), bc_count + 1)

        # Assert that the created object has the right attrs
        creatinine = BaselineCreatinine.objects.get()
        self.assertEqual(creatinine.value, 1.5)
        self.assertEqual(creatinine.lower_limit, LowerLimits.CREATININEMGDL)
        self.assertEqual(creatinine.units, Units.MGDL)
        self.assertEqual(creatinine.upper_limit, UpperLimits.CREATININEMGDL)


class UrateManagerTestCase(TestCase):
    def test_get_queryset(self):
        # Create some Urate objects
        Urate.objects.create(value=4.0)
        Urate.objects.create(value=5.0)
        Urate.objects.create(value=6.0)

        # Get the queryset using the manager
        queryset = Urate.objects.get_queryset()

        # Assert that the queryset contains all Urate objects
        self.assertEqual(queryset.count(), 3)

    def test_create(self):
        # Create a Urate object using the manager
        Urate.objects.create(value=5.5)

        # Assert that the object was created
        self.assertEqual(Urate.objects.count(), 1)

        # Assert that the created object has the right attrs
        urate = Urate.objects.get()
        self.assertEqual(urate.value, 5.5)
        self.assertEqual(urate.lower_limit, LowerLimits.URATEMGDL)
        self.assertEqual(urate.units, Units.MGDL)
        self.assertEqual(urate.upper_limit, UpperLimits.URATEMGDL)

    def test__related_objects(self):
        urate = UrateFactory(user=create_psp())
        urate_with_flare = UrateFactory()
        create_flare(urate=urate_with_flare)
        urate_with_ppx = UrateFactory()
        create_ppx(labs=[urate_with_ppx])

        with self.assertNumQueries(1):
            accurate_qs = Urate.related_objects.filter(id=urate.id).get()
            self.assertEqual(accurate_qs, urate)
            self.assertEqual(accurate_qs.user, urate.user)

        with self.assertNumQueries(1):
            accurate_qs = Urate.related_objects.filter(id=urate_with_flare.id).get()
            self.assertEqual(accurate_qs, urate_with_flare)
            self.assertEqual(accurate_qs.flare, urate_with_flare.flare)

        with self.assertNumQueries(1):
            accurate_qs = Urate.related_objects.filter(id=urate_with_ppx.id).get()
            self.assertEqual(accurate_qs, urate_with_ppx)
            self.assertEqual(accurate_qs.ppx, urate_with_ppx.ppx)
