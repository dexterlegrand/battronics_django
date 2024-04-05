from django.apps import AppConfig


class AbdDatabaseConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'abd_database'

    def ready(self):
        from . import signals
