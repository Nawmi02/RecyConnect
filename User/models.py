from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.base_user import BaseUserManager
from django.conf import settings
from django.db.models import Avg, Count
from urllib.parse import urlparse
from decimal import Decimal, ROUND_HALF_UP

# Manager 
class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        if not password:
            raise ValueError("A password is required.")

        email = self.normalize_email(email)

        extra_fields.setdefault("role", extra_fields.get("role") or "household")
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_active", False)
        extra_fields.setdefault("is_approved", False)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        if not password:
            raise ValueError("Superusers must have a password.")

        extra_fields.setdefault("role", extra_fields.get("role") or "household")
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_approved", True)

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser):
    ROLE_CHOICES = [
        ("household", "Household"),
        ("collector", "Collector"),
        ("recycler",  "Recycling Centre"),
        ("buyer",     "Buyer"),
    ]

    class ProductKind(models.TextChoices):
        PLASTIC = "plastic", "Plastic"
        PAPER   = "paper",   "Paper"
        GLASS   = "glass",   "Glass"
        METAL   = "metal",   "Metal"
        E_WASTE = "e_waste", "E-waste"

    # identity
    email = models.EmailField(unique=True, db_index=True)
    password = models.CharField(max_length=128)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    # collector only (optional at registration)
    collector_product = models.CharField(
        max_length=12,
        choices=ProductKind.choices,
        blank=True,
        help_text="Collector only: what type of material you collect.",
    )

    # public profile
    name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)

    profile_image = models.ImageField(
        upload_to="user_avatars/%Y/%m/", blank=True, null=True,
        help_text="Upload a clear profile photo.",
    )

    map_url = models.URLField(
        blank=True,
        help_text="Google Maps link to your address.",
    )

    # socials
    facebook = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    twitter  = models.URLField(blank=True)

    # admin status
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        "self", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="approved_users"
    )

    date_joined = models.DateTimeField(default=timezone.now)

    # Collector / Recycling Centre proof (needed for registration)
    id_card_image = models.ImageField(
        upload_to="user_ids/%Y/%m/",
        blank=True, null=True,
        help_text="ID/visiting card (required for Collector and Recycling Centre).",
    )

    # ratings(for collectors) 
    average_rating = models.FloatField(default=0.0)
    ratings_count  = models.PositiveIntegerField(default=0)

     #Rewards/Points
    points = models.PositiveIntegerField(default=0, help_text="Total points available to redeem.")
    total_co2_saved_kg = models.DecimalField(
        max_digits=12, decimal_places=3, default=Decimal("0.000"),
        help_text="Lifetime CO₂ saved (kg).",
    )
    total_pickups = models.PositiveIntegerField(default=0, help_text="Lifetime pickups/recycles.")

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["role"]

    def __str__(self):
        return f"{self.email} ({self.role})"

    def _is_valid_google_maps_url(self) -> bool:
        if not self.map_url:
            return False
        p = urlparse(self.map_url)
        host = (p.netloc or "").lower()
        path = (p.path or "").lower()
        return (
            ("google." in host and "/maps" in path) or
            host in {"maps.app.goo.gl", "goo.gl"} or
            (host.endswith(".google.com") and path.startswith("/maps"))
        )

    @property
    def is_collector(self) -> bool:
        return self.role == "collector"

    def clean(self):
        super().clean()
        errors = {}

        if self.map_url and not self._is_valid_google_maps_url():
            errors["map_url"] = (
                "Please provide a valid Google Maps URL "
                "(e.g., https://maps.google.com/... or https://maps.app.goo.gl/...)."
            )

        if self.role in ("collector", "recycler") and not self.id_card_image:
            errors["id_card_image"] = (
                "An ID or visiting card image is required for Collector and Recycling Centre accounts."
            )

        if errors:
            raise ValidationError(errors)

    def approve(self, by_user):
        approve_errors = {}
        if not self.profile_image:
            approve_errors["profile_image"] = "A profile picture is required before approval."
        if not (self.is_staff or self.is_superuser):
            if not self.map_url or not self._is_valid_google_maps_url():
                approve_errors["map_url"] = "A valid Google Maps URL is required before approval."
        if self.role in ("collector", "recycler") and not self.id_card_image:
            approve_errors["id_card_image"] = "An ID/visiting card image is required before approval."
        if self.role == "collector" and not self.collector_product:
            approve_errors["collector_product"] = "Select what material the Collector handles."

        if approve_errors:
            raise ValidationError(approve_errors)

        self.is_approved = True
        self.is_active = True
        self.approved_at = timezone.now()
        self.approved_by = by_user
        self.save(update_fields=["is_approved", "is_active", "approved_at", "approved_by"])

    def recompute_rating(self):
        agg = self.received_ratings.aggregate(avg=Avg("stars"), cnt=Count("id"))
        avg = float(agg["avg"] or 0.0)
        cnt = int(agg["cnt"] or 0)
        self.average_rating = round(avg, 2)
        self.ratings_count = cnt
        self.save(update_fields=["average_rating", "ratings_count"])

    @property
    def requires_id_image(self) -> bool:
        return self.role in ("collector", "recycler")

    class Meta:
        ordering = ("-date_joined",)


# Rating model: ANY user can rate a COLLECTOR (no self-rating)
class CollectorRating(models.Model):
    """
    One rater (any role) -> one Collector rating (0..5).
    """
    collector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_ratings",
        limit_choices_to={"role": "collector"},  
    )
    rater = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="given_ratings",
    )
    stars = models.PositiveSmallIntegerField(help_text="0–5")
    comment = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("collector", "rater")
        constraints = [
            models.CheckConstraint(
                check=models.Q(stars__gte=0) & models.Q(stars__lte=5),
                name="collector_rating_stars_0_5",
            )
        ]
        ordering = ("-updated_at",)

    def __str__(self):
        return f"Rating {self.stars}/5 by {self.rater_id} -> {self.collector_id}"

    def clean(self):
        errors = {}
        if self.collector_id == self.rater_id:
            errors["collector"] = "You cannot rate yourself."
        if getattr(self.collector, "role", None) != "collector":
            errors["collector"] = "Target user must be a Collector."
        if not (0 <= int(self.stars) <= 5):
            errors["stars"] = "Stars must be between 0 and 5."
        if errors:
            raise ValidationError(errors)


# Signals: keep User.average_rating & ratings_count in sync 
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=CollectorRating)
def _on_rating_saved(sender, instance: CollectorRating, **kwargs):
    if instance.collector_id:
        instance.collector.recompute_rating()

@receiver(post_delete, sender=CollectorRating)
def _on_rating_deleted(sender, instance: CollectorRating, **kwargs):
    if instance.collector_id:
        instance.collector.recompute_rating()
