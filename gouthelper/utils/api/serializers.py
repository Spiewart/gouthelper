from django.utils.functional import cached_property
from rest_framework import serializers

from ...users.models import Pseudopatient


class GoutHelperModelSerializer(serializers.ModelSerializer):
    class Meta:
        abstract = True

    @cached_property
    def patient(self) -> Pseudopatient:
        user_data = self.validated_data.get("user", None)
        user__id = user_data.get("id") if user_data else None
        return (
            self.instance.user
            if self.instance and self.instance.user
            else Pseudopatient.objects.get(id=user__id)
            if user__id
            else None
        )
