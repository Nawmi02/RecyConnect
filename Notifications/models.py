from django.db import models


class Notifications(models.Model):
    text = models.CharField(max_length=200)
    created_at = models.DateTimeField(default=True)
    icon = models.CharField(max_length=20)
    is_read = models.BooleanField(default=False)


    def __str__(self):
        return self.text
