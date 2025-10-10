from django.db import transaction
from django.utils import timezone
from .models import Notification

def create_notification(*, user, title: str, message: str,
                        category: str = "general", data: dict | None = None,
                        link_url: str = ""):
    def _create():
        Notification.objects.create(
            user=user,
            title=title,
            message=message,
            category=category,
            payload=data or {},
            link_url=link_url,
            created_at=timezone.now(),
            is_read=False,
        )
    transaction.on_commit(_create)
