from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User


class CaseInsensitiveModelBackend(ModelBackend):
    """
    Authenticates against username case-insensitively, since mobile
    keyboards often auto-capitalize the first letter of a fresh field.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        try:
            user = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            return None
        except User.MultipleObjectsReturned:
            # Two accounts differ only by case — fall back to exact match
            user = User.objects.get(username=username)

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None