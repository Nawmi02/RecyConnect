from decimal import Decimal
from typing import Optional, Tuple

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render

from .models import Badge, UserBadge, RewardItem
from .services import redeem_reward, ensure_core_badges
from Pickup.models import PickupRequest

User = get_user_model()


# helpers
def _template_for_role(role: str) -> str:
    role = (role or "").lower()
    if role == "collector":
        return "Collector/c_rewards.html"
    if role == "buyer":
        return "Buyer/b_rewards.html"
    if role == "household":
        return "Household/h_rewards.html"
    return "Admin/ad_rewards.html"


def _is_admin(user) -> bool:
    return bool(user and (user.is_staff or user.is_superuser))


def _to_int(v: Optional[str], default: Optional[int] = None) -> Optional[int]:
    try:
        return int(v) if v is not None and v != "" else default
    except (TypeError, ValueError):
        return default


def _to_bool(v: Optional[str]) -> bool:
    return str(v).lower() in {"1", "true", "on", "yes"}


def _role_pickup_qs(user, role: str):
    
    role = (role or "").lower()
    if role == "collector":
        return PickupRequest.objects.filter(
            collector_id=user.id,
            status=PickupRequest.Status.COMPLETED,
        )
    return PickupRequest.objects.filter(
        requester_id=user.id,
        status=PickupRequest.Status.COMPLETED,
    )


def _completed_stats_for_role(user, role: str) -> Tuple[int, Decimal]:
    qs = _role_pickup_qs(user, role)
    completed_count = qs.count()
    total_weight = qs.aggregate(s=Sum("weight_kg"))["s"] or Decimal("0")
    try:
        total_weight = Decimal(str(total_weight)).quantize(Decimal("0.001"))
    except Exception:
        total_weight = Decimal("0.000")
    return completed_count, total_weight


@login_required
def rewards_page(request, role: str):
    template = _template_for_role(role)

    ensure_core_badges()

    # POST actions 
    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()

        # Redeem reward
        if action == "redeem":
            raw_id = (request.POST.get("reward_id") or "").strip()
            try:
                reward_id = int(raw_id)
            except (TypeError, ValueError):
                messages.error(request, "Invalid reward selection.")
                return redirect(request.path)

            reward = get_object_or_404(RewardItem, pk=reward_id, is_active=True)
            try:
                redeem_reward(user=request.user, reward=reward)
                messages.success(request, "You will get your reward soon.")
            except ValidationError as e:
                messages.error(request, e.message)
            except Exception as e:
                messages.error(request, f"Redemption failed: {e}")
            return redirect(request.path)

        # Admin: create/update badge
        elif action == "admin_save_badge":
            if not _is_admin(request.user):
                messages.error(request, "Unauthorized.")
                return redirect(request.path)

            badge_id = request.POST.get("badge_id")
            code = (request.POST.get("code") or "").strip()
            name = (request.POST.get("name") or "").strip()
            description = request.POST.get("description") or ""
            emoji = request.POST.get("emoji") or ""
            rarity = request.POST.get("rarity") or Badge.Rarity.COMMON
            points_bonus = _to_int(request.POST.get("points_bonus"), 0) or 0

            try:
                if badge_id:
                    badge = get_object_or_404(Badge, pk=badge_id)
                    if code:
                        badge.code = code
                    if name:
                        badge.name = name
                    badge.description = description
                    badge.emoji = emoji
                    badge.rarity = rarity
                    badge.points_bonus = points_bonus
                    badge.save()
                    messages.success(request, "Badge updated.")
                else:
                    Badge.objects.create(
                        code=code,
                        name=name,
                        description=description,
                        emoji=emoji,
                        rarity=rarity,
                        points_bonus=points_bonus,
                    )
                    messages.success(request, "Badge created.")
            except IntegrityError:
                messages.error(request, "Badge code or name must be unique.")
            return redirect(request.path)

        # Admin: create/update reward item
        elif action == "admin_save_reward":
            if not _is_admin(request.user):
                messages.error(request, "Unauthorized.")
                return redirect(request.path)

            reward_id = request.POST.get("reward_id")
            title = (request.POST.get("title") or "").strip()
            cost_points = _to_int(request.POST.get("cost_points"), 0) or 0
            stock = _to_int(request.POST.get("stock"), None)  
            is_active = _to_bool(request.POST.get("is_active"))
            image = request.FILES.get("image")

            try:
                if reward_id:
                    r = get_object_or_404(RewardItem, pk=reward_id)
                    if title:
                        r.title = title
                    r.cost_points = cost_points
                    r.stock = stock
                    r.is_active = is_active
                    if image:
                        r.image = image
                    r.save()
                    messages.success(request, "Reward updated.")
                else:
                    RewardItem.objects.create(
                        title=title,
                        cost_points=cost_points,
                        stock=stock,
                        is_active=is_active,
                        image=image,
                    )
                    messages.success(request, "Reward created.")
            except Exception as e:
                messages.error(request, f"Failed to save reward item: {e}")
            return redirect(request.path)

        else:
            messages.error(request, "Unknown action.")
            return redirect(request.path)

    user = request.user

    # Completed-only stats per role
    completed_count, completed_weight = _completed_stats_for_role(user, role)

    overview = {
        "points": user.points,
        "total_co2": user.total_co2_saved_kg,  
        "total_pickups": completed_count,      
        "total_weight": completed_weight,      
        "recent_badges": (
            UserBadge.objects.filter(user=user)
            .select_related("badge")
            .order_by("-awarded_at")[:6]
        ),
    }

    earned_ids = set(
        UserBadge.objects.filter(user=user).values_list("badge_id", flat=True)
    )
    all_badges = Badge.objects.all().order_by("points_bonus", "name")

    top_users = (
        User.objects.filter(points__gt=0)
        .only("id", "name", "email", "role", "points")
        .order_by("-points")[:100]
    )

    items = RewardItem.objects.filter(is_active=True).order_by("cost_points")

    context = {
        "overview": overview,
        "all_badges": all_badges,
        "earned_ids": earned_ids,
        "top_users": top_users,
        "items": items,
        "is_admin": _is_admin(user),
        "admin_badges": all_badges if _is_admin(user) else [],
        "admin_rewards": (
            RewardItem.objects.all().order_by("-is_active", "cost_points")
            if _is_admin(user) else []
        ),
        "rarity_choices": Badge.Rarity.choices,
    }
    return render(request, template, context)
