from django.db.models import Manager  # type: ignore

from .choices import LabTypes, LowerLimits, Units, UpperLimits


class CreatinineManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(labtype=LabTypes.CREATININE)

    def create(self, **kwargs):
        kwargs.update({"labtype": LabTypes.CREATININE})
        kwargs.update({"lower_limit": LowerLimits.CREATININEMGDL})
        kwargs.update({"units": Units.MGDL})
        kwargs.update({"upper_limit": UpperLimits.CREATININEMGDL})
        return super().create(**kwargs)


class UrateManager(Manager):
    def get_queryset(self):
        return super().get_queryset().filter(labtype=LabTypes.URATE)

    def create(self, **kwargs):
        kwargs.update({"labtype": LabTypes.URATE})
        kwargs.update({"lower_limit": LowerLimits.URATEMGDL})
        kwargs.update({"units": Units.MGDL})
        kwargs.update({"upper_limit": UpperLimits.URATEMGDL})
        return super().create(**kwargs)
