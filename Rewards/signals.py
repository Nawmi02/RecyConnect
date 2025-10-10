from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from .models import UserBadge, Activity   
from Notifications.services import create_notification

User = get_user_model()

@receiver(post_save, sender=UserBadge)
def notify_on_new_badge(sender, instance: UserBadge, created, **kwargs):
    if not created:
        return
    b = instance.badge
    bonus = int(getattr(b, "points_bonus", 0) or 0)
    msg = f"You earned {b.name}" + (f" (+{bonus} pts)" if bonus else "")
    create_notification(
        user=instance.user,
        title="🎉 New Badge Earned!",
        message=msg,
        category="badge",
        data={"badge_id": b.id, "badge_name": b.name, "points_bonus": bonus},
        link_url="",  
    )

@receiver(post_save, sender=Activity)
def notify_on_points_activity(sender, instance: Activity, created, **kwargs):
    if not created:
        return
    delta = getattr(instance, "points_delta", None)
    if delta is None:
        delta = getattr(instance, "points", 0)
    try:
        delta = int(delta or 0)
    except Exception:
        delta = 0
    if delta <= 0:
        return
    create_notification(
        user=instance.user,
        title="⭐ Points Added",
        message=f"You received +{delta} points.",
        category="points",
        data={
            "activity_id": instance.id,
            "reason": getattr(instance, "reason", None) or getattr(instance, "type", None),
            "points_delta": delta,
        },
        link_url="",  
    )
