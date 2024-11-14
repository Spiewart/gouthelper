from rest_framework import serializers

from ...models import MedHistory


class MedHistorySerializer(serializers.ModelSerializer):
    value = serializers.BooleanField(default=False)

    class Meta:
        model = MedHistory
        fields = ["id", "medhistorytype", "value", "user"]

    def save(self) -> MedHistory | None:
        if self.should_create_or_update:
            return super().save()
        elif self.should_delete and self.instance:
            self.instance.delete()
            return None

    @property
    def should_create_or_update(self) -> bool:
        return "value" in self.validated_data and self.validated_data["value"]

    @property
    def should_delete(self) -> bool:
        return "value" in self.validated_data and not self.validated_data["value"]
