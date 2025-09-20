from django.db import transaction
from django.utils import timezone
from .utils import send_approval_email

def approve_user(user, by_user):
    if user.is_approved:
        return False
    user.is_approved = True
    user.is_active = True
    user.approved_at = timezone.now()
    user.approved_by = by_user
    user.save(update_fields=["is_approved","is_active","approved_at","approved_by"])
    transaction.on_commit(lambda: send_approval_email(user))
    return True
