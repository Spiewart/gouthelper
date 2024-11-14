from typing import TYPE_CHECKING

from rest_framework import serializers

from ..models import Gender

if TYPE_CHECKING:
    from ..types import GenderData


class GenderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gender
        fields = ["value", "id", "user"]
        extra_kwargs = {
            "user": {"validators": []},
        }

    def __init__(self, *args, **kwargs):
        self.optional: bool = kwargs.pop("optional", False)
        if self.optional:
            self.fields["value"].required = False

        self.patient_edit: bool = kwargs.pop("patient_edit", False)
        if self.patient_edit is False:
            self.fields["value"].read_only = True

        super().__init__(*args, **kwargs)

    @classmethod
    def create_gender(cls, validated_data: "GenderData") -> Gender:
        return Gender.objects.create(value=validated_data.get("value"), user=validated_data.get("user"))

    def create(
        self,
        validated_data: "GenderData",
    ) -> Gender:
        return self.create_gender(validated_data)

    @classmethod
    def update_gender(cls, instance: Gender, validated_data: "GenderData") -> Gender:
        return instance.update(validated_data)

    def update(
        self,
        instance: Gender,
        validated_data: "GenderData",
    ) -> Gender:
        return self.update_gender(instance, validated_data)
