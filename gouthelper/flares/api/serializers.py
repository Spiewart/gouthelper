from rest_framework import serializers

from ...akis.api.serializers.base import AkiSerializer
from ...labs.api.serializers import UrateSerializer
from ...medhistorys.api.serializers.with_relations import MedHistorySerializer
from ..models import Flare


class FlareSerializer(serializers.ModelSerializer):
    aki = AkiSerializer(required=False)
    medhistorys_qs = MedHistorySerializer(many=True, read_only=True)
    urate = UrateSerializer(required=False)

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
