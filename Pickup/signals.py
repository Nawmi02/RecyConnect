from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import PickupRequest

@receiver(post_save, sender=PickupRequest)
def _on_pickup_completed(sender, instance: PickupRequest, created, **kwargs):
    if created or instance.status != PickupRequest.Status.COMPLETED:
        return
    try:
        from Rewards.services import log_activity_and_update
        log_activity_and_update(
            user=instance.requester,          
            product=instance.product,
            weight_kg=instance.weight_kg,
        )
    except Exception:
        pass
