from decimal import Decimal
from django.db import models
from django.conf import settings
from django.db.models import Q

class PickupRequest(models.Model):
    class Status(models.TextChoices):
        PENDING   = "pending",   "Pending"
        ACCEPTED  = "accepted",  "Accepted"
        DECLINED  = "declined",  "Declined"
        COMPLETED = "completed", "Completed"

    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pickup_requests_made",
        limit_choices_to=Q(role="household") | Q(role="buyer"),
        help_text="User who created the pickup request (household or buyer).",
    )

    collector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pickup_requests_received",
        limit_choices_to={"role": "collector"},
    )

    product = models.ForeignKey(
        "RecyCon.Product",
        on_delete=models.PROTECT,
        related_name="pickup_requests",
    )

    kind      = models.CharField(max_length=10)
    weight_kg = models.DecimalField(max_digits=8, decimal_places=3, default=Decimal("0.000"))
    price     = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    status     = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["requester", "created_at"]),
            models.Index(fields=["collector", "status"]),
        ]
        unique_together = (("requester", "collector", "product"),)

    def save(self, *args, **kwargs):
        if self.product_id and (not self.kind or not self.weight_kg):
            self.kind = getattr(self.product, "kind", self.kind)
            self.weight_kg = getattr(self.product, "weight", self.weight_kg)
            self.price = getattr(self.product, "price", self.price)
        super().save(*args, **kwargs)

    def get_kind_label(self):
        from RecyCon.models import Product
        try:
            return Product.Kind(self.kind).label
        except Exception:
            return self.kind
