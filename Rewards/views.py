from decimal import Decimal
from typing import Optional

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render

from .models import Badge, UserBadge, RewardItem
from .services import redeem_reward, ensure_core_badges  

User = get_user_model()


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


@login_required
def rewards_page(request, role: str):
    template = _template_for_role(role)


    ensure_core_badges()

    # ---------- POST actions ----------
    if request.method == "POST":
        action = request.POST.get("action", "").strip()

        if action == "redeem":
            reward_id = request.POST.get("reward_id")
            reward = get_object_or_404(RewardItem, pk=reward_id, is_active=True)
            try:
                redeem_reward(user=request.user, reward=reward)
                messages.success(request, "You will get your reward soon.")
            except ValidationError as e:
                messages.error(request, e.message)
            except Exception:
                messages.error(request, "Redemption failed. Please try again.")
            return redirect(request.path)

        if action == "admin_save_badge":
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
                    badge.code = code or badge.code
                    badge.name = name or badge.name
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

        if action == "admin_save_reward":
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
                    r.title = title or r.title
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
            except Exception:
                messages.error(request, "Failed to save reward item.")
            return redirect(request.path)

        messages.error(request, "Unknown action.")
        return redirect(request.path)

    # ---------- GET: build context ----------
    user = request.user

    overview = {
        "points": user.points,
        "total_co2": user.total_co2_saved_kg,
        "total_pickups": user.total_pickups,
        "recent_badges": UserBadge.objects.filter(user=user)
            .select_related("badge").order_by("-awarded_at")[:6],
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
        "admin_rewards": RewardItem.objects.all().order_by("-is_active", "cost_points")
                        if _is_admin(user) else [],
        "rarity_choices": Badge.Rarity.choices,
    }
    return render(request, template, context)
