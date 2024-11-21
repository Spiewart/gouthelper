from django.contrib.auth import get_user_model
from django.utils.functional import cached_property
from rest_framework import serializers

from ...users.models import Pseudopatient

User = get_user_model()


class GoutHelperModelSerializer(serializers.ModelSerializer):
    class Meta:
        abstract = True

    @cached_property
    def patient(self) -> Pseudopatient:
        if self.instance and self.instance.user:
            return self.instance.user
        else:
            try:
                user_or_data = self.validated_data.get("user", None)
                if isinstance(user_or_data, User):
                    return user_or_data
                else:
                    user__id = user_or_data.get("id") if user_or_data else None
                    return Pseudopatient.objects.get(id=user__id) if user__id else None
            except Exception as e:
                raise serializers.ValidationError(e)
