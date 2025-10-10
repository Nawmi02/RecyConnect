# notifications/views.py
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from .models import Notification

ROLE_TEMPLATES = {
    "buyer": "Buyer/b_notifications.html",
    "collector": "Collector/c_notifications.html",
    "household": "Household/h_notifications.html",
}

def _template_for_role(user) -> str:
    role = (getattr(user, "role", "") or "").lower()
    tpl = ROLE_TEMPLATES.get(role)
    if not tpl:
        raise Http404("No notifications page for this role.")
    return tpl


@login_required
def inbox(request):
    template = _template_for_role(request.user)

    # total count (all), list (latest 100)
    total_count = Notification.objects.filter(user=request.user).count()
    items = (
        Notification.objects
        .filter(user=request.user)
        .order_by("-created_at")[:100]
    )

    ctx = {
        "items": items,
        "total_count": total_count,   # 👈 মোট নোটিফিকেশনের সংখ্যা
        "role": getattr(request.user, "role", ""),
    }
    return render(request, template, ctx)


@login_required
@require_POST
def delete(request, pk: int):
    """Single notification delete."""
    n = get_object_or_404(Notification, pk=pk, user=request.user)
    n.delete()
    return redirect("notifications:inbox")


@login_required
@require_POST
def delete_all(request):
    """Delete all notifications for this user."""
    Notification.objects.filter(user=request.user).delete()
    return redirect("notifications:inbox")
