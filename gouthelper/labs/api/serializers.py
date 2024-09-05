from rest_framework import serializers

from ..models import BaselineCreatinine, Creatinine, Urate


class BaselineCreatinineSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaselineCreatinine
        fields = ["id", "value", "medhistory"]


class CreatinineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Creatinine
        fields = ["id", "value", "date_drawn", "user", "aki"]


class UrateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Urate
        fields = ["id", "value", "date_drawn", "user", "ppx"]
