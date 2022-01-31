import datetime as dt
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from rest_framework.authentication import TokenAuthentication
from rest_framework import exceptions


DEFAULT_EXPIRY_TIME = 60*60*24  # 1 day


class ExpiringTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, key):
        model = self.get_model()
        try:
            token = model.objects.select_related('user').get(key=key)
        except model.DoesNotExist:
            raise exceptions.AuthenticationFailed(_('Invalid token.'))

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed(_('User inactive or deleted.'))

        if timezone.now() - token.created > dt.timedelta(
                seconds=getattr(settings, "TOKEN_EXPIRY_TIME_SECONDS", DEFAULT_EXPIRY_TIME)):
            raise exceptions.AuthenticationFailed(_('Token expired.'))

        return token.user, token
