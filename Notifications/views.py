from django.shortcuts import render, redirect, get_object_or_404
from .models import Notifications
from django import forms

class NotificationForm(forms.ModelForm):
    class Meta:
        model = Notifications
        fields = ['text', 'icon', 'is_read']

def notification_list(request):
    notifications = Notifications.objects.all().order_by('-created_at')
    return render(request, 'notifications/notification_list.html', {'notifications': notifications})

def notification_create(request):
    if request.method == "POST":
        form = NotificationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('notification_list')
    else:
        form = NotificationForm()
    return render(request, 'notifications/notification_form.html', {'form': form})

def notification_update(request, id):
    notification = get_object_or_404(Notifications, id=id)
    if request.method == "POST":
        form = NotificationForm(request.POST, instance=notification)
        if form.is_valid():
            form.save()
            return redirect('notification_list')
    else:
        form = NotificationForm(instance=notification)
    return render(request, 'notifications/notification_form.html', {'form': form})

def notification_delete(request, id):
    notification = get_object_or_404(Notifications, id=id)
    if request.method == "POST":
        notification.delete()
        return redirect('notification_list')
    return render(request, 'notifications/notification_confirm_delete.html', {'notification': notification})
