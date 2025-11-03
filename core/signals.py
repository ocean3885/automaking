from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile

User = get_user_model()

@receiver(post_save, sender=User)
def create_profile_on_user_create(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

# allauth 가입 신호
try:
    from allauth.account.signals import user_signed_up

    @receiver(user_signed_up)
    def create_profile_on_allauth_signup(request, user, **kwargs):
        UserProfile.objects.get_or_create(user=user)
except Exception:
    pass