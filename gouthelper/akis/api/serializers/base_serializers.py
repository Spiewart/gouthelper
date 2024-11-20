from typing import TYPE_CHECKING

from rest_framework import serializers

from ....genders.choices import Genders
from ....labs.api.serializers import CreatinineSerializer
from ....medhistorydetails.choices import Stages
from ....utils.api.serializers import GoutHelperModelSerializer
from ...helpers import AkiStatusCreatininesProcessor
from ...models import Aki

if TYPE_CHECKING:
    from ...types import AkiData


class AkiSerializer(GoutHelperModelSerializer):
    class Meta:
        model = Aki
        fields = [
            "id",
            "status",
            "user",
            "creatinines",
            "age",
            "gender",
            "baselinecreatinine",
            "stage",
        ]
        extra_kwargs = {
            "status": {"required": False, "allow_null": True},
            "user": {"required": False, "allow_null": True},
            "creatinines": {"required": False, "allow_null": True},
            "age": {"required": False, "allow_null": True},
            "gender": {"required": False, "allow_null": True},
            "baselinecreatinine": {"required": False, "allow_null": True},
            "stage": {"required": False, "allow_null": True},
        }

    creatinines = CreatinineSerializer(many=True, required=False, allow_null=True)
    age = serializers.IntegerField(required=False, allow_null=True)
    gender = gender = serializers.ChoiceField(choices=Genders.choices, required=False, allow_null=True)
    baselinecreatinine = serializers.DecimalField(max_digits=4, decimal_places=2, required=False, allow_null=True)
    stage = serializers.ChoiceField(choices=Stages.choices, required=False, allow_null=True)

    def validate(self, data: "AkiData") -> "AkiData":
        errors = AkiStatusCreatininesProcessor(
            status=data.get("status", None),
            creatinines=data.get("creatinines", []),
            age=data.get("age", None),
            gender=data.get("gender", None),
            baselinecreatinine=data.get("baselinecreatinine", None),
            stage=data.get("stage", None),
        ).get_errors()

        if errors:
            raise serializers.ValidationError(errors)

        return data

    @classmethod
    def create_aki(cls, validated_data: "AkiData") -> Aki:
        creatinines = validated_data.get("creatinines", [])
        status = validated_data.get("status", None)
        user = validated_data.get("user", None)

        if not status and creatinines:
            status = AkiStatusCreatininesProcessor(
                status=status,
                creatinines=creatinines,
                age=validated_data.get("age", None),
                gender=validated_data.get("gender", None),
                baselinecreatinine=validated_data.get("baselinecreatinine", None),
                stage=validated_data.get("stage", None),
            ).get_status_from_creatinines()

        aki = Aki.objects.create(
            status=status,
            user=user,
        )

        for creatinine in creatinines:
            creatinine.update({"aki": aki, "user": user})
            CreatinineSerializer.create_creatinine(validated_data=creatinine)

        return aki

    def create(self, validated_data: "AkiData") -> Aki:
        return self.create_aki(validated_data)

    @classmethod
    def update_aki(cls, instance: Aki, validated_data: "AkiData") -> Aki:
        creatinines = validated_data.get("creatinines", [])
        status = validated_data.get("status", None)
        user = validated_data.get("user", None)

        if not status and creatinines:
            status = AkiStatusCreatininesProcessor(
                status=status,
                creatinines=creatinines,
                age=validated_data.get("age", None),
                gender=validated_data.get("gender", None),
                baselinecreatinine=validated_data.get("baselinecreatinine", None),
                stage=validated_data.get("stage", None),
            ).get_status_from_creatinines()

        instance.update(
            status=status,
            user=user,
        )

        for creatinine in (
            instance.creatinines_qs if hasattr(instance, "creatinines_qs") else instance.creatinine_set.all()
        ):
            if creatinine.id not in [c.get("id") for c in creatinines]:
                creatinine.delete()
            for creatinine in creatinines:
                if "id" in creatinine:
                    CreatinineSerializer.update_creatinine(instance=creatinine["id"], validated_data=creatinine)
                else:
                    creatinine.update({"aki": instance, "user": user})
                    CreatinineSerializer.create_creatinine(validated_data=creatinine)

        return instance

    def update(self, instance: Aki, validated_data: "AkiData") -> Aki:
        return self.update_aki(instance, validated_data)
