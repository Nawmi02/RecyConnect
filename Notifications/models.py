from django.conf import settings
from django.db import models

class Notification(models.Model):
    class Category(models.TextChoices):
        GENERAL = "general", "General"
        BADGE   = "badge",   "Badge"
        POINTS  = "points",  "Points"
        ORDER   = "order",   "Order"
        SYSTEM  = "system",  "System"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        db_index=True,
    )
    title    = models.CharField(max_length=140)
    message  = models.TextField(blank=True)
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.GENERAL, db_index=True
    )
    link_url = models.URLField(blank=True)
    payload  = models.JSONField(default=dict, blank=True)

    is_read    = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["user", "is_read", "created_at"]),
            models.Index(fields=["user", "category", "created_at"]),
        ]

    def str(self):
        return f"[{self.category}] {self.title} → {self.user_id}"