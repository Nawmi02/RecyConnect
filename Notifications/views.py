from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from .models import Notification

@login_required
def inbox(request):
    
    items = Notification.objects.filter(user=request.user).order_by("-created_at")[:100]
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    return render(request, "notifications/inbox.html", {
        "items": items,
        "unread_count": unread_count,
        "is_admin_panel": True,  
    })

@login_required
@require_POST
def mark_read(request, pk):
    n = get_object_or_404(Notification, pk=pk, user=request.user)
    n.is_read = True
    n.save(update_fields=["is_read"])
    return redirect(request.META.get("HTTP_REFERER") or "notifications:inbox")

@login_required
@require_POST
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect(request.META.get("HTTP_REFERER") or "notifications:inbox")

# ---------- APIs for navbar bell ----------
@login_required
def unread_count_api(request):
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({"unread": count})

@login_required
def list_api(request):
    # lightweight JSON list (e.g., navbar dropdown)
    qs = Notification.objects.filter(user=request.user).order_by("-created_at")[:20]
    data = [{
        "id": n.id,
        "title": n.title,
        "message": n.message,
        "category": n.category,
        "created_at": n.created_at.isoformat(),
        "is_read": n.is_read,
        "link_url": n.link_url,
        "payload": n.payload,
    } for n in qs]
    return JsonResponse({"items": data})