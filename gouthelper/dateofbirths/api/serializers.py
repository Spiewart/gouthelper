from rest_framework import serializers

from ..models import DateOfBirth


class DateOfBirthSerializer(serializers.ModelSerializer):
    class Meta:
        model = DateOfBirth
        fields = ["value", "id", "user"]
