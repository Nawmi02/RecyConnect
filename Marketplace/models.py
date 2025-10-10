from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.utils.crypto import get_random_string


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
    class Meta:
        db_table = "Marketplace_markettag"   
        ordering = ("id",)


class MarketplaceQuerySet(models.QuerySet):
    def with_seller_info(self):
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
    price  = models.DecimalField(max_digits=10, decimal_places=2) # price per kg (BDT)
    tags   = models.ManyToManyField(MarketTag, blank=True, related_name="items")
    product_image = models.ImageField(
        upload_to="marketplace/products/",
        blank=True,
        null=True,
        help_text="Product image",
    )

    objects = MarketplaceQuerySet.as_manager()

    class Meta:
       db_table = "Marketplace_marketplace" 
       ordering = ("id",)

    def __str__(self) -> str:
        return f"{self.name} — {self.get_product_type_display()}"

    # ✅ Validation & seller helpers belong to Marketplace (not MarketOrder)
    def clean(self):
        super().clean()
        if self.seller:
            if self.seller.role not in ("collector", "buyer", "recycler"):
                raise ValidationError({"seller": "Seller must be Collector/Buyer/Recycler."})
            if not self.seller.is_approved:
                raise ValidationError({"seller": "Seller must be approved."})

    @property
    def seller_name(self) -> str:
        return (self.seller.name or "").strip() or self.seller.email

    @property
    def seller_role(self) -> str:
        return self.seller.role if self.seller_id else ""

    @property
    def seller_average_rating(self) -> float:
        return float(getattr(self.seller, "average_rating", 0.0) or 0.0)


class MarketOrder(models.Model):
    class Status(models.TextChoices):
        PENDING   = "pending",   "Pending"
        DELIVERED = "delivered", "Delivered"

    order_no     = models.CharField(max_length=20, unique=True, db_index=True)
    buyer        = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="market_orders"
    )
    collector    = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="collector_sales"
    )
    marketplace  = models.ForeignKey(
        "Marketplace",
        on_delete=models.PROTECT,
        related_name="orders"
    )

    product_name = models.CharField(max_length=120)
    weight_kg    = models.DecimalField(max_digits=8, decimal_places=3)
    unit_price   = models.DecimalField(max_digits=10, decimal_places=2)
    total_price  = models.DecimalField(max_digits=12, decimal_places=2)

    status       = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "Marketplace_marketorder"
        ordering = ("-id",)
        indexes = [
            models.Index(fields=["buyer", "created_at"]),
            models.Index(fields=["collector", "status"]),
        ]

    def __str__(self):
        return f"{self.order_no} ({self.product_name})"

    @staticmethod
    def new_order_no() -> str:
        return f"ORD-{get_random_string(8).upper()}"
