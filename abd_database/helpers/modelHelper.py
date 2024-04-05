import hashlib
import logging
from django.db import transaction
from django.utils import timezone

from abd_database.models import UploadFile, UploadBatch

logger = logging.getLogger(__name__)


def get_checksum(file):
    hash_md5 = hashlib.md5()
    with open(file.file.temporary_file_path(), 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


@transaction.atomic(savepoint=False)
def save_files(files, user, extractor_type, battery=None, dataset=None):
    """
    Creates a new batch-entry in the database and a new hdf5-entry per uploaded file
    @param files: uploaded files from the user
    @param user: user that performed the fileupload
    @param extractor_type: corresponding type of the extractor to the filetypes (only one filetype per batch)
    @param battery: set corresponding battery for tracing unsuccessful upload
    @param dataset: only for re-uploading failed batches
    @return batch: the created batch-entry-object linked with all uploaded files
    @return duplicates_in_db: list of tuples with the primary key of the uploaded file and a list of the primary keys of the related duplicated files
    @return duplicates_in_queue: list of filenames of duplicates found in the queue
    """
    batch = None
    duplicates_in_db = []
    duplicates_in_queue = []

    if dataset:
        batch = UploadBatch(user=user, extractor_type=extractor_type, dataset=dataset).save()
    else:
        batch = UploadBatch(user=user, extractor_type=extractor_type).save()

    for file in files:
        # TODO: check if reupload still works bc of not editable checksum
        UploadFile(file=file, batch=batch, kb=int(file.size / 1000), time=timezone.now(), battery=battery).save()

    # TODO: optimize duplicate check per type
    duplicates_in_db.extend(batch.check_for_duplicates())
    duplicates_in_queue.extend(batch.check_for_duplicates_in_queue())

    return batch, (duplicates_in_db, duplicates_in_queue)
