from django.apps import AppConfig

class ECommerceappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ECommerceApp'

    def ready(self):
        import ECommerceApp.signals