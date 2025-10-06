from django.apps import AppConfig


class PickupConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Pickup'

    def ready(self):
        from . import signals  