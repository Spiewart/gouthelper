from rest_framework import serializers

from ...medhistorys.choices import MedHistoryTypes
from ..models import CkdDetail, GoutDetail


class CkdDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = CkdDetail
        fields = ["id", "dialysis", "stage", "dialysis_duration", "dialysis_type"]


class GoutDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoutDetail
        fields = ["id", "medhistory", "at_goal", "at_goal_long_term", "flaring", "on_ppx", "on_ult", "starting_ult"]
        extra_kwargs = {
            "medhistory": {"required": False},
            "at_goal": {"required": True},
            "at_goal_long_term": {"required": False, "default": False},
            "flaring": {"required": True},
            "on_ppx": {"required": True},
            "on_ult": {"required": True},
            "starting_ult": {"required": True},
        }

    def validate(self, data):
        if data["at_goal_long_term"] and not data["at_goal"]:
            raise serializers.ValidationError("Cannot be at goal long term without being at goal.")
        return data

    def validate_medhistory(self, value):
        if self.context["request"].method == "POST":
            if not value:
                raise serializers.ValidationError("This field is required.")
            elif value.medhistorytype != MedHistoryTypes.GOUT:
                raise serializers.ValidationError("This field must be a Gout medhistory.")

    def create(self, validated_data):
        return GoutDetail.objects.create(**validated_data)

    def update(self, instance, validated_data):
        if instance.update(validated_data):
            return instance
