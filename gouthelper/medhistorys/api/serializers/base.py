from rest_framework import serializers

from ...models import MedHistory


class MedHistorySerializer(serializers.ModelSerializer):
    value = serializers.BooleanField(default=False)

    class Meta:
        model = MedHistory
        fields = ["id", "medhistorytype", "value", "user"]
