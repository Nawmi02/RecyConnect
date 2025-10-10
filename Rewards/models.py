from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import F
from django.contrib.auth import get_user_model

UserModel = get_user_model()


class Activity(models.Model):
    product = models.ForeignKey(
        "RecyCon.Product", 
        on_delete=models.PROTECT,
        related_name="activities",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="activities",
    )

    weight_kg = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Weight in kilograms for this activity",
    )
    co2_saved_kg = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal("0.000"),
        help_text="Auto: weight × CO₂ factor (kg)",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["created_at"]),
        ]

    CO2_PER_KG = {
        "plastic": Decimal("1.5"),
        "glass":   Decimal("0.3"),
        "metal":   Decimal("2.0"),
        "paper":   Decimal("1.8"),
        "e_waste": Decimal("5.0"),
    }

    def _factor_for_kind(self) -> Decimal:
        kind_key = str(self.product.kind)
        return self.CO2_PER_KG.get(kind_key, Decimal("0.0"))

    def save(self, *args, **kwargs):
        if not self.co2_saved_kg or self.co2_saved_kg == Decimal("0.000"):
            factor = self._factor_for_kind()
            self.co2_saved_kg = (Decimal(self.weight_kg) * factor).quantize(
                Decimal("0.001"), rounding=ROUND_HALF_UP
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user_id} {self.weight_kg}kg {getattr(self.product, 'kind', '-')}"

class Badge(models.Model):
    class Rarity(models.TextChoices):
        COMMON     = "Common", "Common"
        RARE       = "Rare", "Rare"
        EPIC       = "Epic", "Epic"
        LEGENDARY  = "Legendary", "Legendary"
        EXCLUSIVE  = "Exclusive", "Exclusive"
    code = models.SlugField(
        unique=True,
        help_text="Stable code for logic (e.g., first_recycler, pickups_20)"
    )

    name = models.CharField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    emoji = models.CharField(
        max_length=16, blank=True,
        help_text="Emoji or short icon (multi-codepoint supported)"
    )
    rarity = models.CharField(
        max_length=20, choices=Rarity.choices, default=Rarity.COMMON
    )
    points_bonus = models.PositiveIntegerField(
        default=0, help_text="Extra points awarded with this badge"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "name")

    def __str__(self):
        return self.name


class UserBadge(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_badges",
    )
    badge = models.ForeignKey(
        Badge,
        on_delete=models.CASCADE,
        related_name="awards",
    )
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "badge")
        ordering = ("-awarded_at",)
        indexes = [
            models.Index(fields=["user", "awarded_at"]),
            models.Index(fields=["badge", "awarded_at"]),
        ]

    def __str__(self):
        return f"{self.user_id} ↦ {self.badge.name}"

class RewardItem(models.Model):
    title = models.CharField(max_length=120)
    image = models.ImageField(upload_to="reward_items/%Y/%m/", blank=True, null=True)
    cost_points = models.PositiveIntegerField()
    stock = models.PositiveIntegerField(
        null=True, blank=True, help_text="Blank = unlimited"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "title")

    def __str__(self):
        return f"{self.title} ({self.cost_points} pts)"

    @property
    def is_in_stock(self) -> bool:
        return self.stock is None or self.stock > 0


class Redemption(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="redemptions",
    )
    reward = models.ForeignKey(
        RewardItem,
        on_delete=models.PROTECT,
        related_name="redemptions",
    )
    points_spent = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["reward", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user_id} -> {self.reward_id} ({self.points_spent} pts)"

    @classmethod
    def redeem(cls, *, user, reward: RewardItem):
        if not getattr(user, "pk", None):
            raise ValidationError("User must be authenticated.")

        with transaction.atomic():
            u = UserModel.objects.select_for_update().get(pk=user.pk)
            r = RewardItem.objects.select_for_update().get(pk=reward.pk, is_active=True)

            user_points = int(u.points or 0)
            cost = int(r.cost_points or 0)
            stock_val = r.stock if r.stock is None else int(r.stock)

            if user_points < cost:
                raise ValidationError("Not enough points to redeem.")
            if stock_val is not None and stock_val <= 0:
                raise ValidationError("Reward out of stock.")
            
            u.points = F("points") - cost
          
            if stock_val is not None:
                r.stock = F("stock") - 1

            u.save(update_fields=["points"])
            r.save()

            return cls.objects.create(user=u, reward=r, points_spent=cost)