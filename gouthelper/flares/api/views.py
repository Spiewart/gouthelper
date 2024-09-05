from rest_framework import permissions, viewsets

from ..models import Flare
from .serializers import FlareSerializer


class FlareViewSet(viewsets.ModelViewSet):
    queryset = Flare.related_objects.order_by("date_started").all()
    serializer_class = FlareSerializer
    permission_classes = [permissions.IsAuthenticated]
