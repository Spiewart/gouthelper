from typing import TYPE_CHECKING

from rest_framework import serializers

from ...genders.choices import Genders
from ..choices import Stages
from ..helpers import CkdDetailProcessor
from ..models import CkdDetail, GoutDetail

if TYPE_CHECKING:
    from ..types import CkdDetailData, GoutDetailData


class CkdDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = CkdDetail
        fields = [
            "id",
            "medhistory",
            "dialysis",
            "stage",
            "dialysis_duration",
            "dialysis_type",
            "age",
            "gender",
            "baselinecreatinine",
        ]
        extra_kwargs = {
            "medhistory": {"required": False, "read_only": True},
            "dialysis": {"required": True},
            "stage": {"required": False, "allow_null": True},
            "dialysis_duration": {"required": False, "allow_null": True},
            "dialysis_type": {"required": False, "allow_null": True},
            "age": {"required": False, "allow_null": True},
            "gender": {"required": False, "allow_null": True},
            "baselinecreatinine": {"required": False, "allow_null": True},
        }

    age = serializers.IntegerField(required=False, allow_null=True)
    gender = gender = serializers.ChoiceField(choices=Genders.choices, required=False, allow_null=True)
    baselinecreatinine = serializers.DecimalField(max_digits=4, decimal_places=2, required=False, allow_null=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        request = self.context.get("request", None)
        if request and request.method == "POST":
            self.fields["medhistory"].required = True

    def validate(self, data: "CkdDetailData") -> "CkdDetailData":
        errors = CkdDetailProcessor(
            dialysis=data["dialysis"],
            stage=data.get("stage", None),
            dialysis_type=data.get("dialysis_type", None),
            dialysis_duration=data.get("dialysis_duration", None),
            age=data.get("age", None),
            baselinecreatinine=data.get("baselinecreatinine", None),
            gender=data.get("gender", None),
        ).get_errors()

        if errors:
            raise serializers.ValidationError(errors)

        return data

    def create(self, validated_data):
        dialysis = validated_data["dialysis"]
        if dialysis:
            validated_data["stage"] = Stages.FIVE
        return CkdDetail.objects.create(
            medhistory=validated_data["medhistory"],
            dialysis=dialysis,
            stage=validated_data.get("stage", None),
            dialysis_duration=validated_data.get("dialysis_duration", None),
            dialysis_type=validated_data.get("dialysis_type", None),
        )

    def update(self, instance, validated_data):
        if validated_data["dialysis"]:
            validated_data["stage"] = Stages.FIVE
        instance.update(validated_data)
        return instance


class GoutDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoutDetail
        fields = ["id", "medhistory", "at_goal", "at_goal_long_term", "flaring", "on_ppx", "on_ult", "starting_ult"]
        extra_kwargs = {
            "medhistory": {"required": False, "read_only": True},
            "at_goal": {"required": True},
            "at_goal_long_term": {"required": False, "default": False},
            "flaring": {"required": True},
            "on_ppx": {"required": True},
            "on_ult": {"required": True},
            "starting_ult": {"required": True},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        request = self.context.get("request", None)
        if request and request.method == "POST":
            self.fields["medhistory"].required = True

    def validate(self, data: "GoutDetailData") -> "GoutDetailData":
        if data["at_goal_long_term"] and not data["at_goal"]:
            raise serializers.ValidationError("Cannot be at goal long term without being at goal.")
        return data

    def create(self, validated_data):
        return GoutDetail.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.update(validated_data)
        return instance
