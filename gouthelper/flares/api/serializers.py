from rest_framework import serializers

from ...akis.api.serializers import AkiSerializer
from ...medhistorys.api.serializers import MedHistorySerializer
from ..models import Flare


class FlareSerializer(serializers.ModelSerializer):
    aki = AkiSerializer(required=False)
    medhistorys_qs = MedHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Flare
        fields = [
            "id",
            "created",
            "modified",
            "crystal_analysis",
            "date_ended",
            "date_started",
            "diagnosed",
            "joints",
            "onset",
            "redness",
            "likelihood",
            "prevalence",
            "aki",
            "dateofbirth",
            "flareaid",
            "gender",
            "urate",
            "user",
            "medhistorys_qs",
        ]
