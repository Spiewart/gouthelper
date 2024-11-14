from typing import TYPE_CHECKING

from rest_framework import serializers

from ..models import DateOfBirth

if TYPE_CHECKING:
    from ..types import DateOfBirthData


class DateOfBirthSerializer(serializers.ModelSerializer):
    class Meta:
        model = DateOfBirth
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
    def create_dateofbirth(cls, validated_data: "DateOfBirthData") -> DateOfBirth:
        return DateOfBirth.objects.create(value=validated_data.get("value"), user=validated_data.get("user"))

    def create(
        self,
        validated_data: "DateOfBirthData",
    ) -> DateOfBirth:
        return self.create_dateofbirth(validated_data)

    @classmethod
    def update_dateofbirth(cls, instance: DateOfBirth, validated_data: "DateOfBirthData") -> DateOfBirth:
        return instance.update(validated_data)

    def update(
        self,
        instance: DateOfBirth,
        validated_data: "DateOfBirthData",
    ) -> DateOfBirth:
        return self.update_dateofbirth(instance, validated_data)
