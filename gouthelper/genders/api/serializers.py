from rest_framework import serializers

from ..models import Gender


class GenderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gender
        fields = ["value", "id", "user"]
