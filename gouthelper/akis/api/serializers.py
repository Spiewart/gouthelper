from rest_framework import serializers

from ...labs.api.serializers import CreatinineSerializer
from ..models import Aki


class AkiSerializer(serializers.ModelSerializer[Aki]):
    creatinines_qs = CreatinineSerializer(many=True, read_only=True)

    class Meta:
        model = Aki
        fields = [
            "id",
            "created",
            "modified",
            "status",
            "user",
            "creatinines_qs",
        ]
