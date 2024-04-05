import logging

from django import template
from django.db.models import Q

from abd_database.models import UploadBatch, UploadFile

register = template.Library()

logger = logging.getLogger(__name__)


@register.simple_tag(name="get_batch_status")
def get_batch_status(batch_id):
    batch = UploadBatch.objects.get(pk=batch_id)
    if batch:
        files = batch.uploadfile_set.all().filter(Q(forget=False))
        status_list = set(list(file.status for file in files))
        if status_list:
            if all(status == UploadFile.StatusCodes.SUCCESSFUL for status in status_list):
                return UploadFile.StatusCodes.SUCCESSFUL
            elif any(status == UploadFile.StatusCodes.ERROR for status in status_list):
                return UploadFile.StatusCodes.ERROR
            elif any(status == UploadFile.StatusCodes.SAVING for status in status_list):
                return UploadFile.StatusCodes.SAVING
            elif any(status == UploadFile.StatusCodes.PREPARED for status in status_list):
                return UploadFile.StatusCodes.PREPARED
            elif any(status == UploadFile.StatusCodes.CLEANING for status in status_list):
                return UploadFile.StatusCodes.CLEANING
            elif any(status == UploadFile.StatusCodes.EXTRACTING for status in status_list):
                return UploadFile.StatusCodes.EXTRACTING
            elif any(status == UploadFile.StatusCodes.INITIAL for status in status_list):
                return UploadFile.StatusCodes.INITIAL
            else:
                logger.warning("Could not get batch status")
                return UploadFile.StatusCodes.UNHANDLED
    else:
        # TODO: do something if no files are found
        message = "Could not find batch with id: " + batch_id
        logger.error(message)
        raise Exception(message)


@register.simple_tag(name="has_undeleted_files")
def has_undeleted_files(batch_id):
    batch = UploadBatch.objects.get(pk=batch_id)
    if batch:
        all_files = batch.uploadfile_set.all().filter(Q(forget=False) and Q(is_deleted=False))
        return len(all_files) > 0
    else:
        # TODO: throw error, batch could not be found
        raise Exception("Could not find batch with id: " + batch_id)
