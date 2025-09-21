from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.base_user import BaseUserManager
from urllib.parse import urlparse


# === Manager ===
class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        if not password:
            raise ValueError("A password is required.")

        email = self.normalize_email(email)

        # sensible defaults
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

    # identity
    email = models.EmailField(unique=True, db_index=True)
    password = models.CharField(max_length=128)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    # public profile
    name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)

    # profile picture (NOT required at registration)
    profile_image = models.ImageField(
        upload_to="user_avatars/%Y/%m/",
        blank=True, null=True,
        help_text="Upload a clear profile photo.",
    )

    # Google Maps link (NOT required at registration; validated if provided)
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

    # Collector / Recycling Centre proof (required at registration for those roles)
    id_card_image = models.ImageField(
        upload_to="user_ids/%Y/%m/",
        blank=True, null=True,
        help_text="ID/visiting card (required for Collector and Recycling Centre).",
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["role"]

    def __str__(self):
        return f"{self.email} ({self.role})"

    # helpers
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

    # validations at save-time (keep light so registration passes)
    def clean(self):
        super().clean()
        errors = {}

        if self.map_url and not self._is_valid_google_maps_url():
            errors["map_url"] = (
                "Please provide a valid Google Maps URL "
                "(e.g., https://maps.google.com/... or https://maps.app.goo.gl/...)."
            )

        # Keep hard requirement for collectors/recyclers at registration:
        if self.role in ("collector", "recycler") and not self.id_card_image:
            errors["id_card_image"] = (
                "An ID or visiting card image is required for Collector and Recycling Centre accounts."
            )

        if errors:
            raise ValidationError(errors)

    # approval gate 
    def approve(self, by_user):
        approve_errors = {}
        # Now enforce required fields at approval time:
        if not self.profile_image:
            approve_errors["profile_image"] = "A profile picture is required before approval."
        if not (self.is_staff or self.is_superuser):
            if not self.map_url or not self._is_valid_google_maps_url():
                approve_errors["map_url"] = "A valid Google Maps URL is required before approval."
        if self.role in ("collector", "recycler") and not self.id_card_image:
            approve_errors["id_card_image"] = "An ID/visiting card image is required before approval."

        if approve_errors:
            raise ValidationError(approve_errors)

        self.is_approved = True
        self.is_active = True
        self.approved_at = timezone.now()
        self.approved_by = by_user
        self.save(update_fields=["is_approved", "is_active", "approved_at", "approved_by"])

    @property
    def requires_id_image(self) -> bool:
        return self.role in ("collector", "recycler")

    class Meta:
        ordering = ("-date_joined",)
