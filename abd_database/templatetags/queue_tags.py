from django import template
import queue_settings
from jobqueue_manager import manager

register = template.Library()


@register.simple_tag(name="get_max_queue_size")
def get_max_queue_size():
    return int(queue_settings.max_queue_size/1000)


@register.simple_tag(name="get_max_batch_size")
def get_max_batch_size():
    return int(queue_settings.max_batch_size/1000)


@register.simple_tag(name="get_current_queue_size")
def get_current_queue_size():
    if manager.public_queue:
        return int(manager.public_queue.get_total_size()/1000)
    return 0


@register.simple_tag(name="is_in_queue")
def is_in_queue(batch_id, public_queue):
    if public_queue:
        for public_batch in public_queue.batches:
            if batch_id == public_batch.id:
                return True
    return False
