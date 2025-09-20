from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

def send_approval_email(user):
    html = render_to_string("emails/account_approved.html", {"user": user})
    text = strip_tags(html)
    send_mail(
        "RecyConnect Account Approval",
        text,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html,
        fail_silently=False,
    )
