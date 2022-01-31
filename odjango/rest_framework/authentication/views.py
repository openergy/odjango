import datetime as dt

from rest_framework import parsers, renderers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.views import ObtainAuthToken as ObtainAuthTokenBase
from rest_framework.authtoken.models import Token
from django.utils import timezone
from django.conf import settings
from .expiring_token_authentication import DEFAULT_EXPIRY_TIME


class LogoutToken(APIView):
    throttle_classes = ()
    permission_classes = ()
    parser_classes = (parsers.FormParser, parsers.MultiPartParser, parsers.JSONParser,)
    renderer_classes = (renderers.JSONRenderer,)

    def get(self, request, *args, **kwargs):
        request.auth.delete()
        return Response({'message': 'Successfully logged out'})


class ObtainAuthToken(ObtainAuthTokenBase):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        if not created:
            # check if expired
            if timezone.now() - token.created > dt.timedelta(
                    seconds=getattr(settings, "TOKEN_EXPIRY_TIME_SECONDS", DEFAULT_EXPIRY_TIME)):
                token.delete()
                token = Token.objects.create(user=user)
        return Response({'token': token.key})


obtain_auth_token = ObtainAuthToken.as_view()
logout_token = LogoutToken.as_view()
