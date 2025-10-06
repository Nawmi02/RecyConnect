from decimal import Decimal
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Avg, Count, F
from django.utils import timezone
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser

class Product(models.Model):
    class Kind(models.TextChoices):
        PLASTIC = "plastic", "Plastic"
        PAPER   = "paper",   "Paper"
        GLASS   = "glass",   "Glass"
        METAL   = "metal",   "Metal"
        E_WASTE = "e_waste", "E-waste"

   
    CO2_PER_KG = {
        Kind.PLASTIC: Decimal("1.5"),
        Kind.GLASS:   Decimal("0.3"),
        Kind.METAL:   Decimal("2.0"),
        Kind.PAPER:   Decimal("1.8"),
        Kind.E_WASTE: Decimal("5.0"),
    }

    kind = models.CharField(
        max_length=10,
        choices=Kind.choices,
        help_text="Product type",
    )
    weight = models.DecimalField(
        max_digits=8, decimal_places=3,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Weight in kilograms",
    )
    price = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        default=Decimal("0.00"),
        help_text="Price in your currency",
    )

    def __str__(self):
        return f"{self.get_kind_display()} — {self.weight} kg @ {self.price}"

    class Meta:
        ordering = ("kind",)

    # ---- helpers ----
    @property
    def co2_per_kg(self) -> Decimal:
        """Fixed CO2 factor for this product kind."""
        return self.CO2_PER_KG[Product.Kind(self.kind)]

    def co2_saved_for_weight(self, weight: Decimal | None = None) -> Decimal:
        """CO2 saved = weight * factor (Decimal-সেফ)"""
        w = Decimal(weight if weight is not None else self.weight or 0)
        return (w * self.co2_per_kg).quantize(Decimal("0.001"))