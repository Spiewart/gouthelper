from typing import TYPE_CHECKING

from rest_framework import serializers

from ..models import Ethnicity

if TYPE_CHECKING:
    from ..types import EthnicityData


class EthnicitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Ethnicity
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
    def create_ethnicity(cls, validated_data: "EthnicityData") -> Ethnicity:
        return Ethnicity.objects.create(value=validated_data.get("value"), user=validated_data.get("user"))

    def create(
        self,
        validated_data: "EthnicityData",
    ) -> Ethnicity:
        return self.create_ethnicity(validated_data)

    @classmethod
    def update_ethnicity(cls, instance: Ethnicity, validated_data: "EthnicityData") -> Ethnicity:
        return instance.update(validated_data)

    def update(
        self,
        instance: Ethnicity,
        validated_data: "EthnicityData",
    ) -> Ethnicity:
        return self.update_ethnicity(instance, validated_data)
