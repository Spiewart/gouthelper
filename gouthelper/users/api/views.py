import uuid

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.functional import cached_property
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from ..models import Pseudopatient
from .rules import PseudopatientAddPermissionViewSetMixin
from .serializers.base import UserSerializer
from .serializers.nested import PseudopatientSerializer

User = get_user_model()


class UserViewSet(RetrieveModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    lookup_field = "username"

    def get_queryset(self, *args, **kwargs):
        assert isinstance(self.request.user.id, uuid.UUID)
        return self.queryset.filter(id=self.request.user.id)

    @action(detail=False)
    def me(self, request):
        serializer = UserSerializer(request.user, context={"request": request})
        return Response(status=status.HTTP_200_OK, data=serializer.data)


class PseudopatientViewSet(PseudopatientAddPermissionViewSetMixin, ModelViewSet):
    serializer_class = PseudopatientSerializer
    queryset = Pseudopatient.profile_objects.all()

    def get_queryset(self):
        return self.queryset.filter(
            Q(pseudopatientprofile__provider=self.request.user) | Q(pseudopatientprofile__provider__isnull=True)
        )

    @action(detail=False, methods=["post"])
    def provider_create(self, request):
        if not self.provider:
            return Response(
                {"provider_username": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Add the provider to the serializer kwargs, which will be incorporated into
        # creating the Pseudopatient instance.
        serializer = PseudopatientSerializer(data=request.data, provider=self.provider)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(status=status.HTTP_201_CREATED)
        else:
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

    @cached_property
    def provider(self) -> User | None:
        if hasattr(self, "object"):
            return self.object.provider
        else:
            provider_username = self.request.data.pop("provider_username", None)
            return User.objects.get(username=provider_username) if provider_username else None
