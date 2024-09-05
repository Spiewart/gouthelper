from rest_framework import serializers

from ..models import Ethnicity


class EthnicitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Ethnicity
        fields = ["value", "id", "user"]
