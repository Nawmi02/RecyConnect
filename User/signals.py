# User/signals.py
import os
import logging
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

@receiver(post_migrate)
def create_default_superuser(sender, **kwargs):
    User = get_user_model()

    # if already there, skip
    if User.objects.filter(is_superuser=True).exists():
        return

    email = os.getenv("DEFAULT_SUPERUSER_EMAIL")
    password = os.getenv("DEFAULT_SUPERUSER_PASSWORD")

    if not email or not password:
        logger.warning("DEFAULT_SUPERUSER_EMAIL/PASSWORD not set; skipping default superuser creation.")
        return

    u = User(
        email=email.strip().lower(),
        role="household",          
        is_staff=True,
        is_superuser=True,
        is_active=True,
        is_approved=True,
        name="Super Admin",
    )
    u.set_password(password)
    u.save()
    logger.info("Default superuser created: %s", email)
