import logging
import threading
from copy import copy
from queue import PriorityQueue

from django.db.models import Q
from django.db import connection

from jobqueue_manager.manager_helper import get_priority, PublicQueue, QueueFile, QueueBatch, cleanup_fileupload
import queue_settings

logger = logging.getLogger(__name__)

q = PriorityQueue()
public_queue = PublicQueue()


def start_extractor():
    while True:
        warnings = []
        batch = q.get()
        public_queue.set_active()
        successful_files = []

        # TODO: To be investigated, as queue is not per tenant
        with connection.cursor() as cursor:
            cursor.execute("SET abd.active_tenant = %s", [batch[2].user.company_id])

        # TODO: removed exclude battery --> needs check for further impl.
        files_in_batch = batch[2].uploadfile_set.all().filter(~Q(status='SUCCESS') & Q(forget=False)).exclude(celltest__isnull=False).order_by('id')
        if batch[3]:
            files_in_batch = files_in_batch.filter(pk=batch[3])
        logger.info("+++++++++++ Start Batch +++++++++++")
        logger.info(f"{len(files_in_batch)} files selected for upload.")
        from jobqueue_manager.manager_helper import map_extractor_types
        map_extractor_types(batch[2].extractor_type, files_in_batch, batch[2].user.company, batch[4])
        logger.info("Extraction complete, starting cleaning up")
        try:
            batch[2].delete_files()
        except Exception:
            # TODO: keine symptoms bekämpfung!!! ursache lösen!!!!
            pass
        logger.info("Successfully deleted all remaining files")
        public_queue.remove_active()
        unhandled_files = list(set(map(lambda x: x.file.name, files_in_batch)) - set(successful_files))
        if len(warnings) > 0:
            for warning in warnings:
                logger.warning(warning)
        logger.info(
            f"{len(successful_files)}/{len(files_in_batch)} successfully uploaded, {len(unhandled_files)}/{len(files_in_batch)} could not be uploaded")
        logger.info("++++++++++++ End Batch ++++++++++++")


def start_queue():
    global thread
    thread = threading.Thread(target=start_extractor, daemon=True)
    thread.start()
    # cleanup is buggy
    if q.empty():
        # comment out for local dev
        cleanup_fileupload()


def is_queue_alive():
    try:
        return thread.is_alive()
    except Exception:
        return False


def add_to_queue(batch, user, argument_list: list = None, target_file_id=None):
    if not is_queue_alive():
        start_queue()
    error_message = None
    current_queue_size = public_queue.get_total_size()
    if current_queue_size < queue_settings.max_queue_size:
        priority = get_priority(user)
        queue_file_list = list()
        file_list = []
        all_files = batch.uploadfile_set.all().filter(~Q(status='SUCCESS') & Q(forget=False)).exclude(celltest__isnull=False).order_by('id')
        if target_file_id:
            all_files = all_files.filter(pk=target_file_id)
        sum_size_kb = 0
        for file in all_files:
            file_list.append(file.kb)
            queue_file_list.append(QueueFile(file.file_name, file.kb, file.checksum))
            sum_size_kb += file.kb
        if sum_size_kb < queue_settings.max_batch_size:
            if current_queue_size + sum_size_kb < queue_settings.max_queue_size:
                for index, file in enumerate(file_list):
                    if sum_size_kb == 0:
                        file_list[index] = (file, 0)
                    else:
                        file_list[index] = (file, file / sum_size_kb * 100)
                public_queue.add_to_batches(QueueBatch(batch.id, user, queue_file_list))
                q.put((priority, batch.__hash__(), batch, target_file_id, argument_list))
                logger.info(f"Successfully added {len(file_list)} files to queue with {sum_size_kb:,}kb!")
            else:
                error_message = f"Selected batch would exceed queue threshold of {int(queue_settings.max_queue_size):,}kb to {int(current_queue_size + sum_size_kb - queue_settings.max_queue_size):,}kb. Please try a smaller batch or try later!"
        else:
            error_message = f"Selected batch is too big for queue ({sum_size_kb:,}kb <= {int(queue_settings.max_batch_size):,}kb). Please select less files!"
            logger.error(error_message)
    else:
        error_message = f"Queue is already full ({current_queue_size:,}/{queue_settings.max_queue_size:,}kb. Please try later!"
        logger.error(error_message)
    return error_message


def get_queue_status(user=None):
    if not is_queue_alive() or len(public_queue.batches) < 1:
        return
    users_in_queue = list(batch.user for batch in public_queue.batches)
    map_user_to_id = lambda x: [(x[t], t) for t in range(len(x))]
    user_to_id_dict = dict(map_user_to_id(list(set(users_in_queue))))

    anon_public_queue = PublicQueue()

    public_queue.sort_by_priority()
    for batch in public_queue.batches:
        anon_batch = copy(batch)
        if not anon_batch.user == user:
            anon_batch.user = user_to_id_dict[anon_batch.user]
        anon_public_queue.add_to_batches(anon_batch)
    return anon_public_queue
