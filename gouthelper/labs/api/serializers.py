from rest_framework import serializers

from ..models import BaselineCreatinine, Creatinine, Urate
from ..types import LabData


class BaselineCreatinineSerializer(serializers.ModelSerializer[BaselineCreatinine]):
    class Meta:
        model = BaselineCreatinine
        fields = ["id", "value", "medhistory"]


class CreatinineSerializer(serializers.ModelSerializer[Creatinine]):
    class Meta:
        model = Creatinine
        fields = ["id", "value", "date_drawn", "user", "aki"]

    @classmethod
    def create_creatinine(cls, validated_data: LabData) -> Creatinine:
        return Creatinine.objects.create(
            value=validated_data["value"],
            date_drawn=validated_data["date_drawn"],
            user=validated_data["user"],
            aki=validated_data["aki"] if "aki" in validated_data else None,
        )

    @classmethod
    def update_creatinine(cls, validated_data: LabData, instance: Creatinine) -> Creatinine:
        instance.update(
            value=validated_data["value"],
            date_drawn=validated_data["date_drawn"],
            user=validated_data["user"],
            aki=validated_data["aki"] if "aki" in validated_data else instance.aki,
        )
        return instance


class UrateSerializer(serializers.ModelSerializer[Urate]):
    class Meta:
        model = Urate
        fields = ["id", "value", "date_drawn", "user", "ppx"]

    @classmethod
    def create_urate(cls, validated_data: LabData) -> Urate:
        return Urate.objects.create(
            value=validated_data["value"],
            date_drawn=validated_data["date_drawn"],
            user=validated_data["user"],
            ppx=validated_data["ppx"] if "ppx" in validated_data else None,
        )

    @classmethod
    def update_urate(cls, validated_data: LabData, instance: Urate) -> Urate:
        instance.update(
            value=validated_data["value"],
            date_drawn=validated_data["date_drawn"],
            user=validated_data["user"],
            ppx=validated_data["ppx"] if "ppx" in validated_data else None,
        )
        return instance
