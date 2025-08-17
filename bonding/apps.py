from django.apps import AppConfig


class BondingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bonding'

    def ready(self):
        import bonding.signals
        
