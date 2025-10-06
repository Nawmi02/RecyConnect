# services.py
import re
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F

from .models import Activity, Badge, UserBadge, RewardItem, Redemption

UserModel = get_user_model()

if TYPE_CHECKING:
    from User.models import User as UserType
else:
    UserType = Any


#  Ensure + helpers 
def _ensure_badge(
    code: str, *, name: str, description: str, emoji: str, rarity: str, points_bonus: int
) -> Badge:
    badge, _ = Badge.objects.get_or_create(
        code=code,
        defaults={
            "name": name,
            "description": description,
            "emoji": emoji,
            "rarity": rarity,
            "points_bonus": points_bonus,
        },
    )
    return badge


def _award_badge(user: "UserType", badge: Badge) -> bool:
    """
    Award if not already earned; add bonus points once.
    Returns True only when newly created.
    """
    created = UserBadge.objects.get_or_create(user_id=user.pk, badge=badge)[1]
    if created and badge.points_bonus:
        UserModel.objects.filter(pk=user.pk).update(points=F("points") + badge.points_bonus)
    return created


def _has_badge(user: "UserType", code: str) -> bool:
    return UserBadge.objects.filter(user_id=user.pk, badge__code=code).exists()


# Special-case: first_recycler 
def award_first_recycler_global(*, user: "UserType", is_first_for_user: bool) -> None:
    """Platform-wide unique (household only). Creates the badge if missing."""
    if user.role != "household" or not is_first_for_user:
        return

    badge = _ensure_badge(
        "first_recycler",
        name="Eco Starter",
        description="First Recycler of Recyconnect",
        emoji="💚",
        rarity=Badge.Rarity.EXCLUSIVE,
        points_bonus=250,
    )

    badge = Badge.objects.select_for_update().get(pk=badge.pk)
    if UserBadge.objects.filter(badge=badge).exists():
        return

    _award_badge(user, badge)

def award_first_timer(user: "UserType") -> None:
    if _has_badge(user, "first_timer"):
        return
    badge = _ensure_badge(
        "first_timer",
        name="First Timer",
        description="Completed First Pickup",
        emoji="🌟",
        rarity=Badge.Rarity.COMMON,
        points_bonus=100,
    )
    if user.total_pickups >= 1:
        _award_badge(user, badge)


def award_pickups_20(user: "UserType") -> None:
    if _has_badge(user, "pickups_20"):
        return
    badge = _ensure_badge(
        "pickups_20",
        name="Eco Warrior",
        description="Completed 20+ successful pickups",
        emoji="♻️",
        rarity=Badge.Rarity.RARE,
        points_bonus=300,
    )
    if user.total_pickups >= 20:
        _award_badge(user, badge)


def award_co2_50(user: "UserType") -> None:
    if _has_badge(user, "CO2_50"):
        return
    badge = _ensure_badge(
        "CO2_50",
        name="Planet Protector",
        description="Saved 50 KG+ CO2 Emission",
        emoji="🌍",
        rarity=Badge.Rarity.EPIC,
        points_bonus=500,
    )
    if user.total_co2_saved_kg >= Decimal("50"):
        _award_badge(user, badge)


# Dynamic rules from DB (admin-created) 
# Accept codes like: pickups_20, pickups_50, CO2_50, CO2_200 (case-insensitive)
_PICKUP_RE = re.compile(r"^(pickups)_(\d+)$", re.IGNORECASE)
_CO2_RE    = re.compile(r"^(co2)_(\d+)$",      re.IGNORECASE)

def _iter_dynamic_badges():
    qs = Badge.objects.filter(code__iregex=r'^(pickups|co2)_[0-9]+$') \
                      .only("id", "code", "points_bonus", "name", "description", "emoji", "rarity")
    for b in qs:
        code = (b.code or "").strip()
        m = _PICKUP_RE.match(code) or _CO2_RE.match(code)
        if not m:
            continue
        kind, num = m.group(1).lower(), int(m.group(2))
        yield kind, num, b


def _award_dynamic_badges_from_db(user: "UserType") -> None:
 
    earned_codes_lower = set(
        (c or "").lower()
        for c in UserBadge.objects.filter(user_id=user.pk).values_list("badge__code", flat=True)
    )

    rules = sorted(_iter_dynamic_badges(), key=lambda t: t[1])  

    total_pickups = int(user.total_pickups or 0)
    total_co2 = Decimal(user.total_co2_saved_kg or Decimal("0"))

    for kind, threshold, badge in rules:
        code_lc = (badge.code or "").lower()
        if code_lc in earned_codes_lower:
            continue

        if kind == "pickups":
            if total_pickups >= threshold and _award_badge(user, badge):
                earned_codes_lower.add(code_lc)
        elif kind == "co2":
            if total_co2 >= Decimal(threshold) and _award_badge(user, badge):
                earned_codes_lower.add(code_lc)


def _evaluate_all_badges(*, user: "UserType", is_first_for_user: bool) -> None:
    """
    Run badge engine after an activity: special -> static -> dynamic.
    """
    user = UserModel.objects.only(
        "id", "role", "total_pickups", "total_co2_saved_kg", "points"
    ).get(pk=user.pk)

    award_first_recycler_global(user=user, is_first_for_user=is_first_for_user)
    award_first_timer(user)
    award_pickups_20(user)
    award_co2_50(user)
    _award_dynamic_badges_from_db(user)


#  Public services
@transaction.atomic
def log_activity_and_update(*, user: "UserType", product, weight_kg: Decimal) -> Activity:
 
    is_first_for_user = not Activity.objects.filter(user=user).exists()

    act = Activity.objects.create(user=user, product=product, weight_kg=weight_kg)

    co2 = act.co2_saved_kg
    add_points = int(co2) * 2

    UserModel.objects.filter(pk=user.pk).update(
        total_co2_saved_kg=F("total_co2_saved_kg") + co2,
        total_pickups=F("total_pickups") + 1,
        points=F("points") + add_points,
    )

    _evaluate_all_badges(user=user, is_first_for_user=is_first_for_user)
    return act


@transaction.atomic
def redeem_reward(*, user: "UserType", reward: RewardItem) -> Redemption:
    """User-initiated redemption (atomic + checks handled in model)."""
    return Redemption.redeem(user=user, reward=reward)


def ensure_core_badges() -> None:
    _ensure_badge(
        "first_recycler",
        name="Eco Starter",
        description="First Recycler of Recyconnect",
        emoji="💚",
        rarity=Badge.Rarity.EXCLUSIVE,
        points_bonus=250,
    )
    _ensure_badge(
        "first_timer",
        name="First Timer",
        description="Completed First Pickup",
        emoji="🌟",
        rarity=Badge.Rarity.COMMON,
        points_bonus=100,
    )
    _ensure_badge(
        "pickups_20",
        name="Eco Warrior",
        description="Completed 20+ successful pickups",
        emoji="♻️",
        rarity=Badge.Rarity.RARE,
        points_bonus=300,
    )
    _ensure_badge(
        "CO2_50",
        name="Planet Protector",
        description="Saved 50 KG+ CO2 Emission",
        emoji="🌍",
        rarity=Badge.Rarity.EPIC,
        points_bonus=500,
    )
