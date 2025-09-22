from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

class Product(models.Model):
    class Kind(models.TextChoices):
        PLASTIC = "plastic", "Plastic"
        PAPER   = "paper",   "Paper"
        GLASS   = "glass",   "Glass"
        METAL   = "metal",   "Metal"
        E_WASTE = "e_waste", "E-waste"

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
        help_text="Price in your currency",
    )

    def __str__(self):
        return f"{self.get_kind_display()} — {self.weight} kg @ {self.price}"

    class Meta:
        ordering = ("kind",)
