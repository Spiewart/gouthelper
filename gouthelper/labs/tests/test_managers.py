from django.test import TestCase

from ...medhistorys.tests.factories import CkdFactory
from ..choices import LabTypes, LowerLimits, Units, UpperLimits
from ..models import BaselineCreatinine, Urate


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
        self.assertEqual(creatinine.labtype, LabTypes.CREATININE)
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
        self.assertEqual(urate.labtype, LabTypes.URATE)
        self.assertEqual(urate.lower_limit, LowerLimits.URATEMGDL)
        self.assertEqual(urate.units, Units.MGDL)
        self.assertEqual(urate.upper_limit, UpperLimits.URATEMGDL)
