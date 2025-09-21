from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.urls import reverse

def _abs(path: str) -> str:
    base = getattr(settings, "SITE_URL", "http://127.0.0.1:8000").rstrip("/")
    return base + path

def send_account_approved_email(user):
    ctx = {
        "user": user,
        "login_url": _abs(reverse("user:login")),
    }
    html = render_to_string("Admin/account_approved.html", ctx)
    text = strip_tags(html)
    send_mail(
        subject="RecyConnect Account Approval",
        message=text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html,
        fail_silently=False,
    )

def send_admin_created_email(admin_user, raw_password):
    ctx = {
        "user": admin_user,
        "temp_password": raw_password,
        "login_url": _abs(reverse("user:login")),
    }
    html = render_to_string("Admin/admin_created.html", ctx)
    text = strip_tags(html)
    send_mail(
        subject="You’ve been added as a RecyConnect Admin",
        message=text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[admin_user.email],
        html_message=html,
        fail_silently=False,
    )
