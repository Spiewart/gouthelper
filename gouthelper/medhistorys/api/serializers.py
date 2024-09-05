from rest_framework import serializers

from ...medhistorydetails.api.serializers import GoutDetailSerializer
from ..models import MedHistory


class MedHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MedHistory
        fields = ["id", "medhistorytype", "user"]


class MedHistoryGoutSerializer(MedHistorySerializer):
    goutdetail = GoutDetailSerializer(read_only=True)

    class Meta:
        model = MedHistory
        fields = ["id", "medhistorytype", "user", "goutdetail"]
