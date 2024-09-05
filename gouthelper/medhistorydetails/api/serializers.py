from rest_framework import serializers

from ..models import CkdDetail, GoutDetail


class CkdDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = CkdDetail
        fields = ["id", "dialysis", "stage", "dialysis_duration", "dialysis_type"]


class GoutDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoutDetail
        fields = ["id", "at_goal", "at_goal_long_term", "flaring", "on_ppx", "on_ult", "starting_ult"]
        extra_kwargs = {
            "at_goal": {"required": True},
            "at_goal_long_term": {"required": True},
            "flaring": {"required": True},
            "on_ppx": {"required": True},
            "on_ult": {"required": True},
            "starting_ult": {"required": True},
        }
