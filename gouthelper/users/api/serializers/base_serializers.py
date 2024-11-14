from django.contrib.auth import get_user_model
from rest_framework import serializers

from ...models import Pseudopatient
from ...models import User as UserType

User = get_user_model()


class UserSerializer(serializers.ModelSerializer[UserType]):
    class Meta:
        model = User
        fields = ["username", "name", "url"]
        read_only_fields = ["username"]

        extra_kwargs = {
            "url": {"view_name": "api:user-detail", "lookup_field": "username"},
        }


class PseudopatientSerializer(serializers.ModelSerializer[Pseudopatient]):
    class Meta:
        model = Pseudopatient
        fields = ["id", "url"]

        extra_kwargs = {
            "url": {"view_name": "api:pseudopatient-detail", "lookup_field": "pk"},
        }
