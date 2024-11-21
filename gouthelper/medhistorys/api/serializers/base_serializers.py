from typing import TYPE_CHECKING

from rest_framework import serializers

from ....utils.api.serializers import GoutHelperModelSerializer
from ...models import MedHistory

if TYPE_CHECKING:
    from ...types import MedHistoryData


class MedHistorySerializer(GoutHelperModelSerializer):
    value = serializers.BooleanField(default=False)

    class Meta:
        abstract = True
        model = MedHistory
        fields = [
            "id",
            "value",
            "medhistorytype",
            "flareaid",
            "flare",
            "goalurate",
            "ppxaid",
            "ppx",
            "ultaid",
            "ult",
            "user",
        ]
        extra_kwargs = {
            "flareaid": {"required": False, "allow_null": True},
            "flare": {"required": False, "allow_null": True},
            "goalurate": {"required": False, "allow_null": True},
            "ppxaid": {"required": False, "allow_null": True},
            "ppx": {"required": False, "allow_null": True},
            "ultaid": {"required": False, "allow_null": True},
            "ult": {"required": False, "allow_null": True},
        }

    value = serializers.BooleanField(default=False)

    def save(self) -> MedHistory | None:
        try:
            if self.should_delete(self.validated_data):
                self.instance.delete()
                return None
            elif self.should_create_or_update(self.validated_data):
                return super().save()
            else:
                return self.instance or None
        except Exception as e:
            raise serializers.ValidationError(e)

    def should_create_or_update(self, validated_data: "MedHistoryData") -> bool:
        return (
            "value" in validated_data
            and validated_data["value"]
            and not self.instance
            or self.instance
            and not self.instance.user
            and self.patient
            and not self.should_delete(validated_data)
        )

    def should_delete(self, validated_data: "MedHistoryData") -> bool:
        return "value" in validated_data and not validated_data["value"] and self.instance

    @classmethod
    def create_medhistory(cls, validated_data: "MedHistoryData") -> MedHistory:
        validated_data.pop("value", None)
        medhistory = cls.Meta.model.objects.create(**validated_data)
        return medhistory

    def create(self, validated_data: "MedHistoryData") -> MedHistory:
        validated_data["user"] = self.patient
        return self.create_medhistory(validated_data)

    @classmethod
    def update_medhistory(cls, instance: MedHistory, validated_data: "MedHistoryData") -> MedHistory:
        validated_data.pop("value", None)
        instance.update(
            **validated_data,
        )
        return instance

    def update(self, instance: MedHistory, validated_data: "MedHistoryData") -> MedHistory:
        validated_data["user"] = self.patient
        return self.update_medhistory(instance, validated_data)
