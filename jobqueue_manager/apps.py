from django.apps import AppConfig

from jobqueue_manager.manager import start_queue


class JobqueueManagerConfig(AppConfig):
    name = "jobqueue_manager"

    def ready(self):
        start_queue()
