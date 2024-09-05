from rest_framework import serializers

from ...users.api.serializers.base import PseudopatientSerializer
from ..models import PseudopatientProfile


class PseudopatientProfileSerializer(serializers.ModelSerializer):
    user = PseudopatientSerializer(read_only=True)

    class Meta:
        model = PseudopatientProfile
        fields = ["id", "user", "provider"]
