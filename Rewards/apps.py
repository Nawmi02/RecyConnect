from django.apps import AppConfig

class RewardsConfig(AppConfig):
    name = "Rewards"
    def ready(self):
        from . import signals  
