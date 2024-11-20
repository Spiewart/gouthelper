from typing import TYPE_CHECKING

from rest_framework import serializers

from ...models import MedHistory

if TYPE_CHECKING:
    from ...types import MedHistoryData


class MedHistorySerializer(serializers.ModelSerializer):
    value = serializers.BooleanField(default=False)

    class Meta:
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

    def save(self) -> MedHistory | None:
        if self.should_delete:
            self.instance.delete()
            return None
        elif self.should_create_or_update:
            return super().save()
        else:
            return None

    @property
    def should_create_or_update(self) -> bool:
        return (
            "value" in self.validated_data
            and self.validated_data["value"]
            or self.instance
            and not self.instance.user
            and "user" in self.validated_data
            and not self.should_delete
        )

    @property
    def should_delete(self) -> bool:
        return "value" in self.validated_data and not self.validated_data["value"] and self.instance

    @classmethod
    def create_medhistory(cls, validated_data: "MedHistoryData") -> MedHistory:
        medhistory = cls.Meta.model.objects.create(user=validated_data["user"])
        return medhistory

    def create(self, validated_data: "MedHistoryData") -> MedHistory:
        return self.create_medhistory(validated_data)

    @classmethod
    def update_medhistory(cls, instance: MedHistory, validated_data: "MedHistoryData") -> MedHistory:
        instance.update(
            user=validated_data["user"],
            flareaid=validated_data.get("flareaid", None),
            flare=validated_data.get("flare", None),
            goalurate=validated_data.get("goalurate", None),
            ppxaid=validated_data.get("ppxaid", None),
            ppx=validated_data.get("ppx", None),
            ultaid=validated_data.get("ultaid", None),
            ult=validated_data.get("ult", None),
        )
        return instance

    def update(self, instance: MedHistory, validated_data: "MedHistoryData") -> MedHistory:
        return self.update_medhistory(instance, validated_data)
