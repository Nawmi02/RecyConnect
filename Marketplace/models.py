from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

class MarketTag(models.Model):
    class Choices(models.TextChoices):
        CLEAN                 = "clean",                 "Clean"
        DRY                   = "dry",                   "Dry"
        SORTED                = "sorted",                "Sorted"
        RECYCLED              = "recycled",              "Recycled"
        NO_FOREIGN_MATERIALS  = "no_foreign_materials",  "No foreign materials"
        NO_BATTERY            = "no_battery",            "No battery"
        NO_LIQUID             = "no_liquid",             "No liquid"
        BROKEN                = "broken",                "Broken"
        NONFUNCTIONAL         = "nonfunctional",         "Nonfunctional"
        METAL_ONLY            = "metal_only",            "Metal only"

    name = models.CharField(
        max_length=40,
        choices=Choices.choices,
        unique=True,
        help_text="Quality/handling tags for marketplace items.",
    )

    def __str__(self) -> str:
        return self.get_name_display()


class MarketplaceQuerySet(models.QuerySet):
    def with_seller_info(self):
        """
        Annotate lightweight seller fields for list/detail pages.
        NOTE: Do NOT annotate 'seller_role' because there is a @property with that name.
        """
        return (
            self.select_related("seller")
                .annotate(
                    seller_display_name=models.F("seller__name"),
                    seller_avg=models.F("seller__average_rating"),
                )
        )


class Marketplace(models.Model):

    class ProductType(models.TextChoices):
        METAL   = "metal",   "Metal"
        PLASTIC = "plastic", "Plastic"
        PAPER   = "paper",   "Paper"
        E_WASTE = "ewaste",  "E-waste"
        GLASS   = "glass",   "Glass"

    # Seller: must be approved Collector / Buyer / Recycler
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="market_listings",
        null=True, blank=True,   
        limit_choices_to={
            "role__in": ["collector", "buyer", "recycler"],
            "is_approved": True,
        },
        help_text="Seller must be an approved Collector/Buyer/Recycler.",
    )

    # Product info
    name = models.CharField(max_length=200)
    product_type = models.CharField(max_length=20, choices=ProductType.choices)
    grade = models.IntegerField()
    is_available = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=200)
    weight = models.DecimalField(max_digits=8, decimal_places=2)  # available stock (kg)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # price per kg (BDT)
    tags = models.ManyToManyField(MarketTag, blank=True, related_name="items")
    product_image = models.ImageField(
        upload_to="marketplace/products/",
        blank=True,
        null=True,
        help_text="Product image",
    )

    objects = MarketplaceQuerySet.as_manager()

    class Meta:
        ordering = ("-id",)

    def __str__(self) -> str:
        return self.name

    # Validation: ensure seller has the right role/approval
    def clean(self):
        super().clean()
        if self.seller:
            if self.seller.role not in ("collector", "buyer", "recycler"):
                raise ValidationError({"seller": "Seller must be Collector/Buyer/Recycler."})
            if not self.seller.is_approved:
                raise ValidationError({"seller": "Seller must be approved."})

    @property
    def seller_name(self) -> str:
        """Display name with fallback to email if empty."""
        return (self.seller.name or "").strip() or self.seller.email

    @property
    def seller_role(self) -> str:
        return self.seller.role

    @property
    def seller_average_rating(self) -> float:
        return float(self.seller.average_rating or 0.0)
